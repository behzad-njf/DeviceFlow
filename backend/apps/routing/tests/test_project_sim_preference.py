from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.devices.models import Device, SimSlot
from apps.messaging.models import Message
from apps.projects.models import Project, ProjectDevice
from apps.routing.models import TenantRoutingConfig
from apps.routing.services.engine import route_message
from apps.tenants.services import create_tenant_with_owner


class ProjectSimPreferenceTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="simpref@example.com", password="securepass1", name="SimPref"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="SimPrefCo", slug="simprefco"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "simpref@example.com", "password": "securepass1"},
            format="json",
        )
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.project = Project.objects.create(
            tenant=self.tenant, name="P1", slug="p1"
        )
        self.device = self._pair_device("dual-phone")
        ProjectDevice.objects.create(
            project=self.project,
            device=self.device,
            priority=100,
            preferred_sim_slot=1,
            sim_fallback_enabled=False,
        )
        TenantRoutingConfig.objects.create(
            tenant=self.tenant,
            sim_daily_quota_default=100,
        )

    def _pair_device(self, name: str) -> Device:
        pairing = self.client.post(
            reverse("devices-pairing-code"),
            {"name": name},
            format="json",
            **self.auth,
        )
        pair = self.client.post(
            reverse("agent-pair"),
            {
                "pairing_code": pairing.data["code"],
                "device_info": {
                    "agent_version": "1.0.0",
                    "model": "Dual",
                    "sims": [
                        {"slot_index": 1, "operator": "MCI", "number": "+989121"},
                        {"slot_index": 2, "operator": "Irancell", "number": "+98935"},
                    ],
                },
            },
            format="json",
        )
        self.assertEqual(pair.status_code, status.HTTP_201_CREATED)
        device = Device.objects.get(id=pair.data["device_id"])
        device.status = Device.Status.ONLINE
        device.health_score = 100
        device.health = {"battery": 80, "permissions": {"sms": True}}
        device.save()
        return device

    def test_route_uses_project_preferred_sim(self):
        result = route_message(
            tenant=self.tenant,
            to_number="+989351000099",
            mode=Message.Mode.GENERAL,
            project=self.project,
        )
        self.assertIsNotNone(result.sim_slot)
        self.assertEqual(result.sim_slot.slot_index, 1)

    def test_route_fails_when_preferred_unavailable_and_no_fallback(self):
        sim1 = SimSlot.objects.get(device=self.device, slot_index=1)
        sim1.daily_sent = 100
        sim1.daily_quota = 100
        sim1.save()

        result = route_message(
            tenant=self.tenant,
            to_number="+989351000099",
            mode=Message.Mode.GENERAL,
            project=self.project,
        )
        self.assertIsNone(result.sim_slot)
        self.assertEqual(result.reason, "PREFERRED_SIM_UNAVAILABLE")

    def test_route_falls_back_when_enabled(self):
        link = ProjectDevice.objects.get(project=self.project, device=self.device)
        link.sim_fallback_enabled = True
        link.save()

        sim1 = SimSlot.objects.get(device=self.device, slot_index=1)
        sim1.daily_sent = 100
        sim1.daily_quota = 100
        sim1.save()

        result = route_message(
            tenant=self.tenant,
            to_number="+989351000099",
            mode=Message.Mode.GENERAL,
            project=self.project,
        )
        self.assertIsNotNone(result.sim_slot)
        self.assertEqual(result.sim_slot.slot_index, 2)

    def test_project_devices_api_persists_sim_settings(self):
        resp = self.client.put(
            reverse("projects-devices", kwargs={"project_id": self.project.id}),
            {
                "device_ids": [str(self.device.id)],
                "device_settings": {
                    str(self.device.id): {
                        "preferred_sim_slot": 2,
                        "sim_fallback_enabled": False,
                        "priority": 50,
                    }
                },
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["results"][0]["preferred_sim_slot"], 2)
        self.assertFalse(resp.data["results"][0]["sim_fallback_enabled"])

        result = route_message(
            tenant=self.tenant,
            to_number="+989121000099",
            mode=Message.Mode.GENERAL,
            project=self.project,
        )
        self.assertEqual(result.sim_slot.slot_index, 2)

    def test_two_projects_same_device_different_sims(self):
        project2 = Project.objects.create(
            tenant=self.tenant, name="P2", slug="p2"
        )
        ProjectDevice.objects.create(
            project=project2,
            device=self.device,
            priority=100,
            preferred_sim_slot=2,
            sim_fallback_enabled=False,
        )

        r1 = route_message(
            tenant=self.tenant,
            to_number="+989121000099",
            mode=Message.Mode.GENERAL,
            project=self.project,
        )
        r2 = route_message(
            tenant=self.tenant,
            to_number="+989121000099",
            mode=Message.Mode.GENERAL,
            project=project2,
        )
        self.assertEqual(r1.sim_slot.slot_index, 1)
        self.assertEqual(r2.sim_slot.slot_index, 2)
