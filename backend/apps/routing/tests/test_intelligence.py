from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.devices.models import Device, SimSlot
from apps.devices.services.health import compute_health_score
from apps.messaging.models import Message
from apps.messaging.services.messages import MessageService
from apps.projects.models import Project, ProjectDevice
from apps.routing.models import TenantRoutingConfig
from apps.routing.services import throttle
from apps.routing.services.engine import route_message
from apps.routing.services.modes import priority_for_mode
from apps.tenants.services import create_tenant_with_owner


class IntelligencePhase8Tests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="intel@example.com", password="securepass1", name="Intel"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="IntelCo", slug="intelco"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "intel@example.com", "password": "securepass1"},
            format="json",
        )
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.project = Project.objects.create(
            tenant=self.tenant, name="Main", slug="main"
        )
        self.device = self._pair_device("phone-intel")
        ProjectDevice.objects.create(
            project=self.project, device=self.device, priority=100
        )
        self.config = TenantRoutingConfig.objects.create(
            tenant=self.tenant,
            lb_strategy=TenantRoutingConfig.LBStrategy.LEAST_QUEUE,
            rate_limit_per_minute=1000,
            rate_limit_per_hour=10000,
            rate_limit_per_day=100000,
            marketing_jitter_max_seconds=30,
            sim_daily_quota_default=5,
            adaptive_throttle_enabled=True,
            adaptive_failure_threshold=0.3,
        )

    def _pair_device(self, name: str, sims=None) -> Device:
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
                    "agent_version": "0.8.0",
                    "model": "Pixel",
                    "sims": sims
                    or [
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
        device.health = {
            "battery": 80,
            "charging": False,
            "signal": 3,
            "permissions": {"sms": True},
        }
        device.meta = {"lat": 35.6892, "lng": 51.3890, "city": "Tehran"}
        device.save()
        return device

    def test_otp_priority_better_than_marketing(self):
        """Exit criteria: OTP path is ahead of marketing (priority + no jitter)."""
        otp = MessageService.enqueue(
            tenant=self.tenant,
            to_number="+989121000001",
            body="OTP 1234",
            project=self.project,
            mode=Message.Mode.OTP,
        )
        marketing = MessageService.enqueue(
            tenant=self.tenant,
            to_number="+989121000002",
            body="Sale today",
            project=self.project,
            mode=Message.Mode.MARKETING,
        )
        self.assertEqual(otp.status, Message.Status.ASSIGNED)
        self.assertEqual(otp.priority, priority_for_mode(Message.Mode.OTP))
        self.assertLess(otp.priority, marketing.priority)
        self.assertEqual(marketing.status, Message.Status.SCHEDULED)
        self.assertIsNotNone(marketing.scheduled_at)
        self.assertGreater(marketing.scheduled_at, timezone.now())

        # Agent pull order: OTP before any future marketing work
        pending = MessageService.pending_for_device(self.device)
        self.assertTrue(pending)
        self.assertEqual(pending[0].id, otp.id)
        self.assertEqual(pending[0].mode, Message.Mode.OTP)

    def test_health_score_computation(self):
        self.device.health = {
            "battery": 50,
            "signal": 2,
            "permissions": {"sms": True},
        }
        self.device.status = Device.Status.ONLINE
        score = compute_health_score(self.device)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertLess(score, 100)  # not perfect with 50% battery / mid signal

    def test_sim_rotation_on_quota(self):
        sim1 = SimSlot.objects.get(device=self.device, slot_index=1)
        sim2 = SimSlot.objects.get(device=self.device, slot_index=2)
        sim1.daily_sent = 5  # exhausted at default quota 5
        sim1.daily_quota = 5
        sim1.save()
        sim2.daily_sent = 0
        sim2.daily_quota = 5
        sim2.save()

        result = route_message(
            tenant=self.tenant,
            to_number="+989351000099",
            mode=Message.Mode.GENERAL,
            project=self.project,
        )
        self.assertIsNotNone(result.sim_slot)
        self.assertEqual(result.sim_slot.slot_index, 2)

    def test_adaptive_throttle_reduces_limits(self):
        device_id = str(self.device.id)
        for _ in range(8):
            throttle.record_outcome(device_id=device_id, success=False)
        for _ in range(2):
            throttle.record_outcome(device_id=device_id, success=True)
        factor = throttle.adaptive_factor(
            device_id=device_id, enabled=True, threshold=0.3
        )
        self.assertLess(factor, 1.0)
        scaled = throttle.apply_adaptive_limits(
            device_id=device_id,
            limits={"per_minute": 100, "per_hour": 500, "per_day": 5000},
            enabled=True,
            threshold=0.3,
        )
        self.assertLess(scaled["per_minute"], 100)

    def test_analytics_endpoints(self):
        MessageService.enqueue(
            tenant=self.tenant,
            to_number="+989121000010",
            body="hi",
            project=self.project,
            mode=Message.Mode.OTP,
        )
        overview = self.client.get(reverse("analytics-overview"), **self.auth)
        self.assertEqual(overview.status_code, status.HTTP_200_OK)
        self.assertIn("by_mode_today", overview.data)

        latency = self.client.get(reverse("analytics-latency"), **self.auth)
        self.assertEqual(latency.status_code, status.HTTP_200_OK)

        operators = self.client.get(reverse("analytics-operators"), **self.auth)
        self.assertEqual(operators.status_code, status.HTTP_200_OK)

        devices = self.client.get(reverse("analytics-devices"), **self.auth)
        self.assertEqual(devices.status_code, status.HTTP_200_OK)

        ts = self.client.get(reverse("analytics-timeseries"), **self.auth)
        self.assertEqual(ts.status_code, status.HTTP_200_OK)

        geo = self.client.get(reverse("devices-map"), **self.auth)
        self.assertEqual(geo.status_code, status.HTTP_200_OK)
        self.assertEqual(len(geo.data["results"]), 1)
