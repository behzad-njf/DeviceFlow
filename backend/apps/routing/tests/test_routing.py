from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.devices.models import Device
from apps.messaging.models import Message
from apps.messaging.services.messages import MessageService
from apps.projects.models import Project, ProjectDevice
from apps.routing.models import RoutingRule, TenantRoutingConfig
from apps.routing.services.engine import route_message
from apps.routing.services.ha import failover_device_messages
from apps.tenants.services import create_tenant_with_owner


class RoutingReliabilityTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="route@example.com", password="securepass1", name="Router"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="RouteCo", slug="routeco"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "route@example.com", "password": "securepass1"},
            format="json",
        )
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.project = Project.objects.create(
            tenant=self.tenant, name="OTP", slug="otp"
        )
        self.d1 = self._pair_device("phone-a")
        self.d2 = self._pair_device("phone-b")
        ProjectDevice.objects.create(project=self.project, device=self.d1, priority=100)
        ProjectDevice.objects.create(project=self.project, device=self.d2, priority=50)

    def _pair_device(self, name: str) -> Device:
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
                    "agent_version": "0.4.0",
                    "model": "Pixel",
                    "sims": [{"slot_index": 1, "operator": "MCI", "number": "+98912"}],
                },
            },
            format="json",
        )
        self.assertEqual(pair.status_code, status.HTTP_201_CREATED)
        device = Device.objects.get(id=pair.data["device_id"])
        device.status = Device.Status.ONLINE
        device.health_score = 100
        device.health = {"battery": 80, "charging": False, "permissions": {"sms": True}}
        device.save()
        return device

    def test_least_queue_spreads_across_devices(self):
        config = TenantRoutingConfig.objects.create(
            tenant=self.tenant,
            lb_strategy=TenantRoutingConfig.LBStrategy.LEAST_QUEUE,
            rate_limit_per_minute=1000,
            rate_limit_per_hour=10000,
            rate_limit_per_day=100000,
        )
        self.assertEqual(config.lb_strategy, "least_queue")

        assigned = []
        for i in range(4):
            msg = MessageService.enqueue(
                tenant=self.tenant,
                to_number=f"+98912100000{i}",
                body=f"msg-{i}",
                project=self.project,
            )
            assigned.append(str(msg.device_id))

        self.assertEqual(set(assigned), {str(self.d1.id), str(self.d2.id)})
        self.assertEqual(assigned.count(str(self.d1.id)), 2)
        self.assertEqual(assigned.count(str(self.d2.id)), 2)

    def test_routing_rule_force_device(self):
        RoutingRule.objects.create(
            tenant=self.tenant,
            name="Force B",
            priority=200,
            match={"to_prefix": ["+98912"]},
            action={"type": "force_device", "device_id": str(self.d2.id)},
            enabled=True,
        )
        result = route_message(
            tenant=self.tenant,
            to_number="+989121234567",
            project=self.project,
        )
        self.assertEqual(result.device.id, self.d2.id)
        self.assertTrue(result.forced)

    def test_rate_limit_returns_429(self):
        TenantRoutingConfig.objects.create(
            tenant=self.tenant,
            rate_limit_per_minute=1000,
            rate_limit_per_hour=1000,
            rate_limit_per_day=10000,
            project_rate_limit_per_minute=1,
        )
        first = self.client.post(
            reverse("messages-send"),
            {"to": "+989121111111", "text": "one", "project": "otp"},
            format="json",
            **self.auth,
        )
        self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED)
        second = self.client.post(
            reverse("messages-send"),
            {"to": "+989121111112", "text": "two", "project": "otp"},
            format="json",
            **self.auth,
        )
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(second.data["error"]["code"], "PROJECT_RATE_LIMIT_MINUTE")

    def test_ha_failover_moves_assigned_messages(self):
        TenantRoutingConfig.objects.create(
            tenant=self.tenant,
            ha_enabled=True,
            rate_limit_per_minute=1000,
            rate_limit_per_hour=10000,
            rate_limit_per_day=100000,
        )
        msg = MessageService.enqueue(
            tenant=self.tenant,
            to_number="+989129999999",
            body="failover-me",
            project=self.project,
            device=self.d1,
        )
        self.assertEqual(msg.device_id, self.d1.id)
        self.d1.status = Device.Status.OFFLINE
        self.d1.save(update_fields=["status"])
        moved = failover_device_messages(self.d1)
        self.assertEqual(moved, 1)
        msg.refresh_from_db()
        self.assertEqual(msg.device_id, self.d2.id)
        self.assertEqual(msg.status, Message.Status.ASSIGNED)

    def test_routing_rules_crud(self):
        create = self.client.post(
            reverse("routing-rules-list"),
            {
                "name": "Prefer A for OTP",
                "priority": 150,
                "match": {"mode": ["otp"]},
                "action": {"type": "prefer_devices", "device_ids": [str(self.d1.id)]},
                "enabled": True,
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        rule_id = create.data["id"]
        listing = self.client.get(reverse("routing-rules-list"), **self.auth)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listing.data["results"]), 1)
        patch = self.client.patch(
            reverse("routing-rules-detail", kwargs={"rule_id": rule_id}),
            {"enabled": False},
            format="json",
            **self.auth,
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.assertFalse(patch.data["enabled"])
        cfg = self.client.get(reverse("routing-config"), **self.auth)
        self.assertEqual(cfg.status_code, status.HTTP_200_OK)
        self.assertIn("lb_strategy", cfg.data)
