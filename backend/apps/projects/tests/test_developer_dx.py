from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.devices.models import Device
from apps.messaging.models import MessageTemplate
from apps.messaging.services.templates import render_template
from apps.projects.models import Project, ProjectDevice
from apps.projects.services.apikeys import create_api_key
from apps.tenants.services import create_tenant_with_owner
from apps.webhooks.models import WebhookDelivery, WebhookEndpoint
from apps.webhooks.services.delivery import sign_payload


class DeveloperDxTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="dev@example.com", password="securepass1", name="Dev"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="DevCo", slug="devco"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "dev@example.com", "password": "securepass1"},
            format="json",
        )
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.project = Project.objects.create(
            tenant=self.tenant, name="API", slug="api"
        )
        self.device = self._pair_device("dx-phone")
        ProjectDevice.objects.create(project=self.project, device=self.device)

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
                    "sims": [{"slot_index": 1, "operator": "MCI"}],
                },
            },
            format="json",
        )
        device = Device.objects.get(id=pair.data["device_id"])
        device.status = Device.Status.ONLINE
        device.health = {"battery": 90, "charging": True, "permissions": {"sms": True}}
        device.save()
        return device

    def test_api_key_send_and_revoke(self):
        create = self.client.post(
            reverse("project-api-keys", kwargs={"project_id": self.project.id}),
            {"name": "ci", "scopes": ["messages.send", "messages.read"]},
            format="json",
            **self.auth,
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        plaintext = create.data["key"]
        self.assertTrue(plaintext.startswith("df_live_"))

        send = self.client.post(
            reverse("messages-send"),
            {"to": "+989121111111", "text": "via key"},
            format="json",
            HTTP_AUTHORIZATION=f"ApiKey {plaintext}",
        )
        self.assertEqual(send.status_code, status.HTTP_202_ACCEPTED)

        revoke = self.client.post(
            reverse(
                "project-api-keys-revoke",
                kwargs={"project_id": self.project.id, "key_id": create.data["id"]},
            ),
            **self.auth,
        )
        self.assertEqual(revoke.status_code, status.HTTP_200_OK)
        denied = self.client.post(
            reverse("messages-send"),
            {"to": "+989121111112", "text": "nope"},
            format="json",
            HTTP_AUTHORIZATION=f"ApiKey {plaintext}",
        )
        self.assertEqual(denied.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_idempotency_key(self):
        headers = {
            **self.auth,
            "HTTP_IDEMPOTENCY_KEY": "order-42",
        }
        first = self.client.post(
            reverse("messages-send"),
            {"to": "+989121234567", "text": "hello", "project": "api"},
            format="json",
            **headers,
        )
        self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED)
        second = self.client.post(
            reverse("messages-send"),
            {"to": "+989121234567", "text": "hello", "project": "api"},
            format="json",
            **headers,
        )
        self.assertEqual(second.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(first.data["id"], second.data["id"])

        conflict = self.client.post(
            reverse("messages-send"),
            {"to": "+989129999999", "text": "different", "project": "api"},
            format="json",
            **headers,
        )
        self.assertEqual(conflict.status_code, status.HTTP_409_CONFLICT)

    def test_template_render_and_send(self):
        tpl = self.client.post(
            reverse("templates-list"),
            {"name": "otp", "body": "Code {{code}} for {{user}}", "project": self.project.id},
            format="json",
            **self.auth,
        )
        self.assertEqual(tpl.status_code, status.HTTP_201_CREATED)
        rendered = self.client.post(
            reverse("templates-render", kwargs={"template_id": tpl.data["id"]}),
            {"vars": {"code": "1234", "user": "Ali"}},
            format="json",
            **self.auth,
        )
        self.assertEqual(rendered.status_code, status.HTTP_200_OK)
        self.assertEqual(rendered.data["text"], "Code 1234 for Ali")
        send = self.client.post(
            reverse("messages-send"),
            {
                "to": "+989121000001",
                "template_id": tpl.data["id"],
                "vars": {"code": "9999", "user": "Sara"},
                "project": "api",
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(send.status_code, status.HTTP_202_ACCEPTED)
        from apps.messaging.models import Message

        msg = Message.objects.get(id=send.data["id"])
        self.assertEqual(msg.body, "Code 9999 for Sara")
        self.assertEqual(render_template("Hi {{n}}", {"n": "x"}), "Hi x")

    def test_webhook_endpoint_and_signed_delivery(self):
        create = self.client.post(
            reverse("project-webhooks", kwargs={"project_id": self.project.id}),
            {
                "url": "https://example.com/hooks/deviceflow",
                "events": ["message.assigned", "message.sent"],
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        self.assertIn("secret", create.data)
        endpoint = WebhookEndpoint.objects.get(id=create.data["id"])
        body = b'{"type":"message.assigned"}'
        sig = sign_payload(secret=endpoint.secret, timestamp="1700000000", body=body)
        self.assertTrue(sig.startswith("sha256="))

        send = self.client.post(
            reverse("messages-send"),
            {"to": "+989121234500", "text": "hook me", "project": "api"},
            format="json",
            **self.auth,
        )
        self.assertEqual(send.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(
            WebhookDelivery.objects.filter(
                endpoint=endpoint, event_type="message.assigned"
            ).exists()
        )

    def test_openapi_schema_available(self):
        resp = self.client.get(reverse("schema"), **self.auth)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b"openapi", resp.content.lower())
