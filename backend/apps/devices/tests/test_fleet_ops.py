from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.devices.models import Device, DeviceCommand
from apps.tenants.services import create_tenant_with_owner


class FleetOpsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ops@example.com", password="securepass1", name="Ops"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="Acme", slug="acme"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "ops@example.com", "password": "securepass1"},
            format="json",
        )
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {login.data['access']}"}
        self.device = Device.objects.create(
            tenant=self.tenant,
            name="office-1",
            status=Device.Status.ONLINE,
            device_token_hash="abc",
            health={"battery": 80, "permissions": {"sms": True}},
        )

    def test_analytics_and_queues(self):
        overview = self.client.get(reverse("analytics-overview"), **self.auth)
        self.assertEqual(overview.status_code, status.HTTP_200_OK)
        self.assertEqual(overview.data["devices"]["online"], 1)

        queues = self.client.get(reverse("queues-summary"), **self.auth)
        self.assertEqual(queues.status_code, status.HTTP_200_OK)
        self.assertEqual(len(queues.data["results"]), 1)

    def test_remote_command_and_ack(self):
        create = self.client.post(
            reverse("devices-commands", kwargs={"device_id": self.device.id}),
            {"command": "sync", "params": {}},
            format="json",
            **self.auth,
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        command_id = create.data["id"]

        # Simulate agent token auth by setting hash to match generated token path:
        # use DeviceTokenAuthentication via pairing flow is heavy; call service ack directly.
        command = DeviceCommand.objects.get(id=command_id)
        self.assertEqual(command.status, DeviceCommand.Status.PENDING)

        from apps.common.crypto import generate_device_token, hash_secret

        token = generate_device_token()
        self.device.device_token_hash = hash_secret(token)
        self.device.save(update_fields=["device_token_hash"])

        pending = self.client.get(
            reverse("agent-commands-pending"),
            HTTP_AUTHORIZATION=f"Device {token}",
        )
        self.assertEqual(pending.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any(c["type"] == "command.control" for c in pending.data["results"])
        )

        ack = self.client.post(
            reverse("agent-command-ack", kwargs={"command_id": command_id}),
            {"status": "acked", "result": {"ok": True}},
            format="json",
            HTTP_AUTHORIZATION=f"Device {token}",
        )
        self.assertEqual(ack.status_code, status.HTTP_200_OK)
        command.refresh_from_db()
        self.assertEqual(command.status, DeviceCommand.Status.ACKED)
