"""Phase 9 extensibility tests: plugins, notifications, automations, OTA."""
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from django.utils import timezone
from apps.accounts.models import User
from apps.automations.models import AutomationRule
from apps.devices.models import AgentRelease, Device
from apps.messaging.services.messages import MessageService
from apps.notifications.models import NotificationLog
from apps.notifications.services.notify import notify
from apps.plugins.models import PluginInstallation
from apps.plugins.registry import get_registry
from apps.tenants.services import create_tenant_with_owner


class ExtensibilityPhase9Tests(APITestCase):
    def setUp(self):
        cache.clear()
        get_registry().discover(force=True)
        self.user = User.objects.create_user(
            email="ext@example.com", password="securepass1", name="Ext"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="ExtCo", slug="extco"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "ext@example.com", "password": "securepass1"},
            format="json",
        )
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def _pair_device(self, name="ota-phone") -> Device:
        pairing = self.client.post(
            reverse("devices-pairing-code"),
            {"name": name},
            format="json",
            **self.auth,
        )
        code = pairing.data["code"]
        pair = self.client.post(
            reverse("agent-pair"),
            {
                "pairing_code": code,
                "device_info": {
                    "agent_version": "0.2.0-mock",
                    "model": "Mock",
                    "sims": [{"slot_index": 1, "operator": "MCI", "number": "+98912"}],
                },
            },
            format="json",
        )
        self.assertEqual(pair.status_code, status.HTTP_201_CREATED)
        device = Device.objects.get(id=pair.data["device_id"])
        self.device_token = pair.data["device_token"]
        device.status = Device.Status.ONLINE
        device.save()
        return device

    def test_sample_plugin_loads_and_installs(self):
        catalog = self.client.get(reverse("plugins-catalog"), **self.auth)
        self.assertEqual(catalog.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in catalog.data["results"]}
        self.assertIn("slack-notifier", ids)
        self.assertIn("telegram-notifier", ids)

        install = self.client.post(
            reverse("plugins-install"),
            {
                "plugin_id": "slack-notifier",
                "config": {},
                "enabled": True,
            },
            format="json",
            **self.auth,
        )
        self.assertIn(install.status_code, {200, 201})
        self.assertTrue(
            PluginInstallation.objects.filter(
                tenant=self.tenant, plugin_id="slack-notifier", enabled=True
            ).exists()
        )

        manifest = get_registry().get("slack-notifier")
        self.assertIsNotNone(manifest)
        events = getattr(manifest.py_module, "EVENTS", [])
        before = len(events)
        from apps.plugins.services.events import emit_plugin_event

        emit_plugin_event(
            tenant=self.tenant,
            event_type="device.offline",
            payload={"title": "offline", "body": "test"},
        )
        self.assertGreater(len(events), before)

    def test_notification_inapp_path(self):
        logs = notify(
            tenant=self.tenant,
            event="device.offline",
            severity="high",
            title="Device offline",
            body="phone-a missed heartbeats",
        )
        self.assertTrue(any(l.channel == "inapp" and l.status == "sent" for l in logs))
        self.assertTrue(
            NotificationLog.objects.filter(tenant=self.tenant, channel="inapp").exists()
        )

    def test_automation_inbound_contains(self):
        device = self._pair_device()
        called = {"n": 0}

        def fake_post(url, payload):
            called["n"] += 1
            called["url"] = url
            called["payload"] = payload

        AutomationRule.objects.create(
            tenant=self.tenant,
            name="STOP webhook",
            priority=200,
            match={"event": "inbound.received", "body_contains": "STOP"},
            action={"type": "webhook", "url": "https://example.com/hooks/stop"},
            enabled=True,
        )
        from apps.automations.services import engine as eng

        original = eng._post_webhook
        eng._post_webhook = fake_post
        try:
            MessageService.create_inbound(
                device=device,
                from_number="+989121111111",
                body="please STOP marketing",
                received_at=timezone.now(),
            )
        finally:
            eng._post_webhook = original
        self.assertEqual(called["n"], 1)
        self.assertIn("STOP", called["payload"]["body"])

    def test_ota_updates_mock_device(self):
        device = self._pair_device()
        release = AgentRelease.objects.create(
            tenant=self.tenant,
            version="0.9.0-mock",
            download_url="https://example.com/agent-0.9.0.apk",
            checksum_sha256="abc",
            is_active=True,
        )
        push = self.client.post(
            reverse("devices-ota", kwargs={"device_id": device.id}),
            {"release_id": str(release.id)},
            format="json",
            **self.auth,
        )
        self.assertEqual(push.status_code, status.HTTP_201_CREATED)
        command_id = push.data["id"]

        pending = self.client.get(
            reverse("agent-commands-pending"),
            HTTP_AUTHORIZATION=f"Device {self.device_token}",
        )
        self.assertEqual(pending.status_code, status.HTTP_200_OK)
        control = next(
            c for c in pending.data["results"] if c["type"] == "command.control"
        )
        self.assertEqual(control["payload"]["action"], "install_update")
        self.assertEqual(control["payload"]["params"]["version"], "0.9.0-mock")

        ack = self.client.post(
            reverse("agent-command-ack", kwargs={"command_id": command_id}),
            {
                "status": "acked",
                "result": {"version": "0.9.0-mock"},
            },
            format="json",
            HTTP_AUTHORIZATION=f"Device {self.device_token}",
        )
        self.assertEqual(ack.status_code, status.HTTP_200_OK)
        device.refresh_from_db()
        self.assertEqual(device.agent_version, "0.9.0-mock")
