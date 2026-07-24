from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.devices.models import Device
from apps.messaging.models import InboundMessage, Message
from apps.tenants.services import create_tenant_with_owner


class MessagingFlowTests(APITestCase):
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
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def test_pair_send_status_inbound(self):
        pairing = self.client.post(
            reverse("devices-pairing-code"),
            {"name": "office-phone"},
            format="json",
            **self.auth,
        )
        self.assertEqual(pairing.status_code, status.HTTP_201_CREATED)
        code = pairing.data["code"]

        pair = self.client.post(
            reverse("agent-pair"),
            {
                "pairing_code": code,
                "device_info": {
                    "agent_version": "0.2.0",
                    "model": "Pixel",
                    "sims": [{"slot_index": 1, "operator": "Irancell", "number": "+98912"}],
                },
            },
            format="json",
        )
        self.assertEqual(pair.status_code, status.HTTP_201_CREATED)
        device_token = pair.data["device_token"]
        device_auth = {"HTTP_AUTHORIZATION": f"Device {device_token}"}

        hb = self.client.post(
            reverse("agent-heartbeat"),
            {"battery": 90, "charging": True, "signal": "good", "agent_version": "0.2.0"},
            format="json",
            **device_auth,
        )
        self.assertEqual(hb.status_code, status.HTTP_200_OK)

        project = self.client.post(
            reverse("projects-list"),
            {"name": "OTP", "slug": "otp"},
            format="json",
            **self.auth,
        )
        self.assertEqual(project.status_code, status.HTTP_201_CREATED)
        project_id = project.data["id"]
        devices = self.client.get(reverse("devices-list"), **self.auth)
        device_id = devices.data["results"][0]["id"]
        attach = self.client.put(
            reverse("projects-devices", kwargs={"project_id": project_id}),
            {"device_ids": [device_id]},
            format="json",
            **self.auth,
        )
        self.assertEqual(attach.status_code, status.HTTP_200_OK)

        send = self.client.post(
            reverse("messages-send"),
            {"to": "+989121111111", "text": "Hello OTP", "project": "otp"},
            format="json",
            **self.auth,
        )
        self.assertEqual(send.status_code, status.HTTP_202_ACCEPTED)
        message_id = send.data["id"]
        self.assertEqual(send.data["status"], Message.Status.ASSIGNED)

        pending = self.client.get(reverse("agent-commands-pending"), **device_auth)
        self.assertEqual(pending.status_code, status.HTTP_200_OK)
        self.assertEqual(len(pending.data["results"]), 1)
        self.assertEqual(pending.data["results"][0]["payload"]["message_id"], message_id)

        sending = self.client.post(
            reverse("agent-message-status", kwargs={"message_id": message_id}),
            {"status": "sending"},
            format="json",
            **device_auth,
        )
        self.assertEqual(sending.status_code, status.HTTP_200_OK)

        sent = self.client.post(
            reverse("agent-message-status", kwargs={"message_id": message_id}),
            {"status": "sent", "latency_ms": 120, "sim_slot": 1},
            format="json",
            **device_auth,
        )
        self.assertEqual(sent.status_code, status.HTTP_200_OK)
        self.assertEqual(sent.data["status"], Message.Status.SENT)

        inbound = self.client.post(
            reverse("agent-inbound"),
            {"from": "+989121111111", "body": "OK", "sim_slot": 1},
            format="json",
            **device_auth,
        )
        self.assertEqual(inbound.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InboundMessage.objects.count(), 1)

        messages = self.client.get(reverse("messages-list"), **self.auth)
        self.assertEqual(messages.status_code, status.HTTP_200_OK)
        self.assertEqual(len(messages.data["results"]), 1)

        inbox = self.client.get(reverse("inbound-list"), **self.auth)
        self.assertEqual(inbox.status_code, status.HTTP_200_OK)
        self.assertEqual(len(inbox.data["results"]), 1)

    def test_retry_on_failure(self):
        device = Device.objects.create(
            tenant=self.tenant,
            name="phone-a",
            status=Device.Status.ONLINE,
            device_token_hash="abc",
        )
        message = Message.objects.create(
            tenant=self.tenant,
            device=device,
            to_number="+98912",
            body="x",
            status=Message.Status.ASSIGNED,
        )
        from apps.messaging.services.messages import MessageService

        MessageService.update_status(
            message=message, status=Message.Status.FAILED, error_message="no service"
        )
        message.refresh_from_db()
        self.assertEqual(message.status, Message.Status.RETRYING)
        self.assertEqual(message.retry_count, 1)
        self.assertIsNotNone(message.next_retry_at)
