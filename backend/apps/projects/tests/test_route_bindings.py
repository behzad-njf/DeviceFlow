from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.devices.models import Device
from apps.messaging.models import Message
from apps.projects.models import Project, ProjectDevice, ProjectRouteBinding
from apps.projects.services.apikeys import create_api_key
from apps.tenants.services import create_tenant_with_owner


class ProjectRouteBindingTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="routes@example.com", password="securepass1", name="Routes"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="RouteCo", slug="routeco"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "routes@example.com", "password": "securepass1"},
            format="json",
        )
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.project = Project.objects.create(
            tenant=self.tenant, name="PizoGold", slug="pizogold"
        )
        self.phone_a = self._pair_device("shop-a")
        self.phone_b = self._pair_device("shop-b")
        ProjectDevice.objects.create(project=self.project, device=self.phone_a)
        ProjectDevice.objects.create(project=self.project, device=self.phone_b)
        _row, self.api_key = create_api_key(
            project=self.project, name="shared", scopes=["messages.send"]
        )

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
                    "agent_version": "0.5.0",
                    "model": "Pixel",
                    "sims": [
                        {"slot_index": 1, "operator": "MCI", "number": "+98911"},
                        {"slot_index": 2, "operator": "Irancell", "number": "+98912"},
                    ],
                },
            },
            format="json",
        )
        device = Device.objects.get(id=pair.data["device_id"])
        device.status = Device.Status.ONLINE
        device.health = {
            "battery": 90,
            "charging": True,
            "permissions": {"sms": True},
        }
        device.save()
        return device

    def test_send_without_route_key_uses_project_pool(self):
        send = self.client.post(
            reverse("messages-send"),
            {"to": "+989121111111", "text": "pool"},
            format="json",
            HTTP_AUTHORIZATION=f"ApiKey {self.api_key}",
        )
        self.assertEqual(send.status_code, status.HTTP_202_ACCEPTED)
        msg = Message.objects.get(id=send.data["id"])
        self.assertIn(msg.device_id, {self.phone_a.id, self.phone_b.id})
        self.assertNotIn("route_key", msg.meta or {})

    def test_send_with_bound_route_key_forces_device(self):
        ProjectRouteBinding.objects.create(
            project=self.project,
            route_key="customer-aaa",
            device=self.phone_b,
            preferred_sim_slot=2,
            label="Shop B",
        )
        send = self.client.post(
            reverse("messages-send"),
            {
                "to": "+989121111112",
                "text": "routed",
                "route_key": "customer-aaa",
            },
            format="json",
            HTTP_AUTHORIZATION=f"ApiKey {self.api_key}",
        )
        self.assertEqual(send.status_code, status.HTTP_202_ACCEPTED)
        msg = Message.objects.get(id=send.data["id"])
        self.assertEqual(msg.device_id, self.phone_b.id)
        self.assertEqual(msg.sim_slot.slot_index, 2)
        self.assertEqual(msg.meta.get("route_key"), "customer-aaa")

    def test_unknown_route_key_returns_422(self):
        send = self.client.post(
            reverse("messages-send"),
            {
                "to": "+989121111113",
                "text": "missing",
                "route_key": "unknown-customer",
            },
            format="json",
            HTTP_AUTHORIZATION=f"ApiKey {self.api_key}",
        )
        self.assertEqual(send.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(send.data["error"]["code"], "ROUTE_NOT_CONFIGURED")
        self.assertFalse(Message.objects.filter(to_number="+989121111113").exists())

    def test_explicit_device_overrides_route_key(self):
        ProjectRouteBinding.objects.create(
            project=self.project,
            route_key="customer-aaa",
            device=self.phone_b,
        )
        send = self.client.post(
            reverse("messages-send"),
            {
                "to": "+989121111114",
                "text": "pin",
                "route_key": "customer-aaa",
                "device": str(self.phone_a.id),
            },
            format="json",
            HTTP_AUTHORIZATION=f"ApiKey {self.api_key}",
        )
        self.assertEqual(send.status_code, status.HTTP_202_ACCEPTED)
        msg = Message.objects.get(id=send.data["id"])
        self.assertEqual(msg.device_id, self.phone_a.id)

    def test_routes_crud(self):
        create = self.client.post(
            reverse("projects-routes", kwargs={"project_id": self.project.id}),
            {
                "route_key": "cust-1",
                "device_id": str(self.phone_a.id),
                "label": "Shop 1",
                "preferred_sim_slot": 1,
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        route_id = create.data["id"]

        listed = self.client.get(
            reverse("projects-routes", kwargs={"project_id": self.project.id}),
            **self.auth,
        )
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listed.data["results"]), 1)

        patched = self.client.patch(
            reverse(
                "projects-routes-detail",
                kwargs={"project_id": self.project.id, "route_id": route_id},
            ),
            {"label": "Shop 1 renamed", "device_id": str(self.phone_b.id)},
            format="json",
            **self.auth,
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data["label"], "Shop 1 renamed")
        self.assertEqual(patched.data["device_id"], str(self.phone_b.id))

        deleted = self.client.delete(
            reverse(
                "projects-routes-detail",
                kwargs={"project_id": self.project.id, "route_id": route_id},
            ),
            **self.auth,
        )
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectRouteBinding.objects.filter(id=route_id).exists())
