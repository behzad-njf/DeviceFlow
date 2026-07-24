from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.tenants.models import Membership, Role
from apps.tenants.services import create_tenant_with_owner


class EnterpriseHardeningTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin7@example.com", password="securepass1", name="Admin"
        )
        self.viewer = User.objects.create_user(
            email="viewer7@example.com", password="securepass1", name="Viewer"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.admin, name="HardCo", slug="hardco"
        )
        Membership.objects.create(
            tenant=self.tenant, user=self.viewer, role=Role.VIEWER
        )
        admin_login = self.client.post(
            reverse("auth-login"),
            {"email": "admin7@example.com", "password": "securepass1"},
            format="json",
        )
        viewer_login = self.client.post(
            reverse("auth-login"),
            {"email": "viewer7@example.com", "password": "securepass1"},
            format="json",
        )
        self.admin_auth = {"HTTP_AUTHORIZATION": f"Bearer {admin_login.data['access']}"}
        self.viewer_auth = {
            "HTTP_AUTHORIZATION": f"Bearer {viewer_login.data['access']}"
        }

    def test_viewer_cannot_send_or_invite(self):
        send = self.client.post(
            reverse("messages-send"),
            {"to": "+989121111111", "text": "nope"},
            format="json",
            **self.viewer_auth,
        )
        self.assertEqual(send.status_code, status.HTTP_403_FORBIDDEN)

        invite = self.client.post(
            reverse("users-invite"),
            {"email": "new@example.com", "role": "operator"},
            format="json",
            **self.viewer_auth,
        )
        self.assertEqual(invite.status_code, status.HTTP_403_FORBIDDEN)

    def test_invite_accept_and_audit(self):
        invite = self.client.post(
            reverse("users-invite"),
            {"email": "newbie@example.com", "role": "developer"},
            format="json",
            **self.admin_auth,
        )
        self.assertEqual(invite.status_code, status.HTTP_201_CREATED)
        token = invite.data["token"]
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant, action="invite.create"
            ).exists()
        )

        newbie = User.objects.create_user(
            email="newbie@example.com", password="securepass1", name="New"
        )
        accept = self.client.post(
            reverse("invites-accept"),
            {
                "token": token,
                "email": "newbie@example.com",
                "password": "securepass1",
                "name": "New",
            },
            format="json",
        )
        self.assertEqual(accept.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Membership.objects.filter(
                tenant=self.tenant, user=newbie, role=Role.DEVELOPER, is_active=True
            ).exists()
        )

        audit = self.client.get(reverse("audit-logs-list"), **self.admin_auth)
        self.assertEqual(audit.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(audit.data["results"]), 1)

        viewer_audit = self.client.get(reverse("audit-logs-list"), **self.viewer_auth)
        self.assertEqual(viewer_audit.status_code, status.HTTP_403_FORBIDDEN)

    def test_metrics_endpoint(self):
        resp = self.client.get(reverse("metrics"))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn("deviceflow_devices_online", body)
        self.assertIn("deviceflow_queue_depth", body)

    def test_users_list_admin(self):
        listing = self.client.get(reverse("users-list"), **self.admin_auth)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(listing.data["results"]), 2)
