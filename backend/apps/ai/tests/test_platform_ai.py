"""Phase 10 platform + AI tests."""
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.ai.services.anomaly import detect_tenant_anomalies
from apps.ai.services.drafts import suggest_inbox_draft
from apps.contacts.models import Conversation
from apps.devices.models import Device, DeviceCommand
from apps.devices.services.capabilities import USSD_RUN, normalize_capabilities
from apps.messaging.models import Message
from apps.notifications.models import NotificationLog
from apps.routing.services import throttle
from apps.tenants.services import create_tenant_with_owner


class PlatformAIPhase10Tests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="plat@example.com", password="securepass1", name="Plat"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="PlatCo", slug="platco"
        )
        # Enable experimental USSD for this tenant
        self.tenant.settings = {
            "features": {"ussd": True, "call_hooks": False},
            "ai": {
                "anomaly_enabled": True,
                "draft_assist": True,
                "routing_suggestions": True,
            },
        }
        self.tenant.save(update_fields=["settings"])
        login = self.client.post(
            reverse("auth-login"),
            {"email": "plat@example.com", "password": "securepass1"},
            format="json",
        )
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def _pair_device(self, name="lab-phone") -> Device:
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
                    "agent_version": "1.0.0-mock",
                    "model": "Lab",
                    "capabilities": [
                        "sms.send",
                        "sms.receive",
                        "ussd.run",
                        "ota.update",
                    ],
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

    def test_ussd_action_on_lab_device(self):
        device = self._pair_device()
        self.assertIn(USSD_RUN, normalize_capabilities(device.capabilities))

        resp = self.client.post(
            reverse("devices-actions", kwargs={"device_id": device.id}),
            {"capability": "ussd.run", "params": {"code": "*141#"}},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["action"], "ussd_run")

        pending = self.client.get(
            reverse("agent-commands-pending"),
            HTTP_AUTHORIZATION=f"Device {self.device_token}",
        )
        control = next(
            c for c in pending.data["results"] if c["type"] == "command.control"
        )
        self.assertEqual(control["payload"]["action"], "ussd_run")
        self.assertEqual(control["payload"]["params"]["code"], "*141#")

        ack = self.client.post(
            reverse("agent-command-ack", kwargs={"command_id": resp.data["id"]}),
            {
                "status": "acked",
                "result": {"ussd_response": "Balance: 10"},
            },
            format="json",
            HTTP_AUTHORIZATION=f"Device {self.device_token}",
        )
        self.assertEqual(ack.status_code, status.HTTP_200_OK)
        cmd = DeviceCommand.objects.get(id=resp.data["id"])
        self.assertEqual(cmd.status, DeviceCommand.Status.ACKED)
        self.assertEqual(cmd.result.get("ussd_response"), "Balance: 10")

    def test_ussd_gated_when_feature_off(self):
        self.tenant.settings = {"features": {"ussd": False}}
        self.tenant.save(update_fields=["settings"])
        device = self._pair_device("gated")
        resp = self.client.post(
            reverse("devices-actions", kwargs={"device_id": device.id}),
            {"capability": "ussd.run", "params": {"code": "*141#"}},
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["error"]["code"], "FEATURE_DISABLED")

    def test_anomaly_alert_path(self):
        device = self._pair_device("anom")
        for _ in range(8):
            throttle.record_outcome(device_id=str(device.id), success=False)
        findings = detect_tenant_anomalies(self.tenant, notify_on_find=True)
        self.assertTrue(any(f["type"] == "device_failure_spike" for f in findings))
        self.assertTrue(
            NotificationLog.objects.filter(
                tenant=self.tenant, event="anomaly.detected", channel="inapp"
            ).exists()
        )
        scan = self.client.post(reverse("ai-anomaly-scan"), **self.auth)
        self.assertEqual(scan.status_code, status.HTTP_200_OK)

    def test_inbox_draft_and_routing_suggestions(self):
        Conversation.objects.create(
            tenant=self.tenant,
            phone_number="+989121234567",
            last_preview="Please HELP with my order",
        )
        conv = Conversation.objects.get(tenant=self.tenant)
        draft = suggest_inbox_draft(conversation=conv)
        self.assertTrue(draft["draft"])
        self.assertIn(draft["source"], {"heuristic", "llm"})

        api = self.client.post(
            reverse("ai-inbox-draft", kwargs={"conversation_id": conv.id}),
            **self.auth,
        )
        self.assertEqual(api.status_code, status.HTTP_200_OK)
        self.assertTrue(api.data["draft"])

        suggestions = self.client.get(reverse("ai-routing-suggestions"), **self.auth)
        self.assertEqual(suggestions.status_code, status.HTTP_200_OK)
        self.assertIn("results", suggestions.data)
