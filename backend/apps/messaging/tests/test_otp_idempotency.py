from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.devices.models import Device
from apps.messaging.models import Message
from apps.messaging.services.messages import MessageService
from apps.projects.models import Project, ProjectDevice
from apps.tenants.services import create_tenant_with_owner


class OtpIdempotencyTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="otp@example.com", password="securepass1", name="OTP"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="OtpCo", slug="otpco"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "otp@example.com", "password": "securepass1"},
            format="json",
        )
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.project = Project.objects.create(
            tenant=self.tenant, name="Auth", slug="auth", mode_default=Project.Mode.OTP
        )
        self.device = self._pair_device()
        ProjectDevice.objects.create(project=self.project, device=self.device)

    def _pair_device(self) -> Device:
        pairing = self.client.post(
            reverse("devices-pairing-code"),
            {"name": "otp-phone"},
            format="json",
            **self.auth,
        )
        pair = self.client.post(
            reverse("agent-pair"),
            {
                "pairing_code": pairing.data["code"],
                "device_info": {
                    "agent_version": "1.0.0",
                    "sims": [
                        {"slot_index": 1, "operator": "MCI", "number": "+98912"},
                    ],
                },
            },
            format="json",
        )
        device = Device.objects.get(id=pair.data["device_id"])
        device.status = Device.Status.ONLINE
        device.health_score = 100
        device.health = {"battery": 80, "permissions": {"sms": True}}
        device.save()
        return device

    def test_otp_client_ref_resend_supersedes(self):
        first = MessageService.enqueue(
            tenant=self.tenant,
            to_number="09012669015",
            body="Your code is 111111",
            project=self.project,
            mode=Message.Mode.OTP,
            client_ref="otp-09012669015",
        )
        second = MessageService.enqueue(
            tenant=self.tenant,
            to_number="09012669015",
            body="Your code is 222222",
            project=self.project,
            mode=Message.Mode.OTP,
            client_ref="otp-09012669015",
        )
        first.refresh_from_db()
        self.assertEqual(first.status, Message.Status.CANCELLED)
        self.assertEqual(first.client_ref, "")
        self.assertEqual(second.body, "Your code is 222222")
        self.assertEqual(second.client_ref, "otp-09012669015")
        self.assertEqual(second.status, Message.Status.ASSIGNED)

    def test_otp_idempotency_key_resend_via_api(self):
        headers = {
            **self.auth,
            "HTTP_IDEMPOTENCY_KEY": "otp-09012669015",
        }
        first = self.client.post(
            reverse("messages-send"),
            {
                "to": "09012669015",
                "text": "Code 111111",
                "project": "auth",
                "mode": "otp",
            },
            format="json",
            **headers,
        )
        self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED)

        second = self.client.post(
            reverse("messages-send"),
            {
                "to": "09012669015",
                "text": "Code 222222",
                "project": "auth",
                "mode": "otp",
            },
            format="json",
            **headers,
        )
        self.assertEqual(second.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(second.data["body"], "Code 222222")
