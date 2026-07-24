from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.email_utils import normalize_email_identity
from apps.accounts.models import User


class AuthFlowTests(APITestCase):
    def test_register_login_me(self):
        register = self.client.post(
            reverse("auth-register"),
            {
                "email": "ops@example.com",
                "password": "securepass1",
                "name": "Ops User",
                "tenant_name": "Acme Co",
                "tenant_slug": "acme",
                "locale": "en",
            },
            format="json",
        )
        self.assertEqual(register.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", register.data)
        self.assertEqual(register.data["role"], "admin")
        self.assertEqual(register.data["tenant"]["slug"], "acme")

        login = self.client.post(
            reverse("auth-login"),
            {"email": "ops@example.com", "password": "securepass1"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        token = login.data["access"]

        me = self.client.get(
            reverse("auth-me"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["user"]["email"], "ops@example.com")
        self.assertEqual(len(me.data["memberships"]), 1)

        tenant_me = self.client.get(
            reverse("tenants-me"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(tenant_me.status_code, status.HTTP_200_OK)
        self.assertEqual(tenant_me.data["tenant"]["slug"], "acme")
        self.assertIn("tenant.write", tenant_me.data["permissions"])

    def test_email_identity_ignores_case_and_dots(self):
        self.assertEqual(
            normalize_email_identity("Behzad.Njf@Example.COM"),
            "behzadnjf@example.com",
        )
        register = self.client.post(
            reverse("auth-register"),
            {
                "email": "Behzad.Njf@Example.COM",
                "password": "securepass1",
                "name": "Behzad",
                "tenant_name": "Dot Co",
                "tenant_slug": "dotco",
            },
            format="json",
        )
        self.assertEqual(register.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get().email, "behzadnjf@example.com")

        # Same identity via different casing / dots must be rejected.
        dup = self.client.post(
            reverse("auth-register"),
            {
                "email": "behzadnjf@example.com",
                "password": "securepass1",
                "name": "Other",
                "tenant_name": "Other Co",
                "tenant_slug": "otherco",
            },
            format="json",
        )
        self.assertEqual(dup.status_code, status.HTTP_400_BAD_REQUEST)

        login = self.client.post(
            reverse("auth-login"),
            {"email": "behzad.njf@example.com", "password": "securepass1"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
