from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.contacts.models import AutoReplyRule, Conversation
from apps.devices.models import Device
from apps.messaging.models import BulkCampaign, ExportJob, Message
from apps.messaging.services.scheduler import next_allowed_datetime
from apps.messaging.tasks import promote_scheduled_task
from apps.projects.models import Project, ProjectDevice
from apps.tenants.services import create_tenant_with_owner


class ConversationsBulkTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="ops6@example.com", password="securepass1", name="Ops6"
        )
        self.tenant = create_tenant_with_owner(
            owner=self.user, name="BulkCo", slug="bulkco"
        )
        login = self.client.post(
            reverse("auth-login"),
            {"email": "ops6@example.com", "password": "securepass1"},
            format="json",
        )
        self.token = login.data["access"]
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.project = Project.objects.create(
            tenant=self.tenant, name="Camp", slug="camp"
        )
        self.device = self._pair_device("bulk-phone")
        ProjectDevice.objects.create(project=self.project, device=self.device)

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
                    "agent_version": "0.6.0",
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

    def test_contacts_blacklist_blocks_send(self):
        create = self.client.post(
            reverse("contacts-list"),
            {
                "phone_number": "+989121111111",
                "name": "Blocked",
                "is_blacklisted": True,
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        send = self.client.post(
            reverse("messages-send"),
            {"to": "+989121111111", "text": "nope", "project": "camp"},
            format="json",
            **self.auth,
        )
        self.assertEqual(send.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_bulk_campaign_and_export(self):
        bulk = self.client.post(
            reverse("messages-send-bulk"),
            {
                "project": "camp",
                "name": "Test campaign",
                "messages": [
                    {"to": "+989121000001", "text": "A"},
                    {"to": "+989121000002", "text": "B"},
                ],
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(bulk.status_code, status.HTTP_202_ACCEPTED)
        campaign = BulkCampaign.objects.get(id=bulk.data["id"])
        self.assertEqual(campaign.total, 2)
        self.assertEqual(campaign.status, BulkCampaign.Status.COMPLETED)
        self.assertEqual(campaign.sent, 2)

        export = self.client.post(
            reverse("exports-create"),
            {"type": "messages", "format": "json"},
            format="json",
            **self.auth,
        )
        self.assertEqual(export.status_code, status.HTTP_202_ACCEPTED)
        job = ExportJob.objects.get(id=export.data["id"])
        self.assertEqual(job.status, ExportJob.Status.READY)
        self.assertGreaterEqual(job.row_count, 2)

    def test_scheduled_message_and_promote(self):
        future = timezone.now() + timedelta(hours=2)
        send = self.client.post(
            reverse("messages-send"),
            {
                "to": "+989121234567",
                "text": "later",
                "project": "camp",
                "scheduled_at": future.isoformat().replace("+00:00", "Z"),
            },
            format="json",
            **self.auth,
        )
        self.assertEqual(send.status_code, status.HTTP_202_ACCEPTED)
        msg = Message.objects.get(id=send.data["id"])
        self.assertEqual(msg.status, Message.Status.SCHEDULED)
        msg.scheduled_at = timezone.now() - timedelta(seconds=1)
        msg.save(update_fields=["scheduled_at"])
        promote_scheduled_task()
        msg.refresh_from_db()
        self.assertEqual(msg.status, Message.Status.ASSIGNED)

    def test_inbound_conversation_and_auto_reply(self):
        AutoReplyRule.objects.create(
            tenant=self.tenant,
            project=self.project,
            name="STOP",
            keyword="STOP",
            match_type="contains",
            reply_body="You are unsubscribed",
            priority=200,
        )
        pairing = self.client.post(
            reverse("devices-pairing-code"),
            {"name": "inbox-phone"},
            format="json",
            **self.auth,
        )
        pair = self.client.post(
            reverse("agent-pair"),
            {
                "pairing_code": pairing.data["code"],
                "device_info": {
                    "agent_version": "0.6.0",
                    "sims": [{"slot_index": 1}],
                },
            },
            format="json",
        )
        device_token = pair.data["device_token"]
        device = Device.objects.get(id=pair.data["device_id"])
        ProjectDevice.objects.create(project=self.project, device=device)
        device.status = Device.Status.ONLINE
        device.save()

        inbound = self.client.post(
            reverse("agent-inbound"),
            {"from": "+989129998887", "body": "Please STOP now"},
            format="json",
            HTTP_AUTHORIZATION=f"Device {device_token}",
        )
        self.assertEqual(inbound.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Conversation.objects.filter(
                tenant=self.tenant, phone_number="+989129998887"
            ).exists()
        )
        self.assertTrue(
            Message.objects.filter(
                to_number="+989129998887", body="You are unsubscribed"
            ).exists()
        )
        listing = self.client.get(reverse("conversations-list"), **self.auth)
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(listing.data["results"]), 1)

    def test_quiet_hours_defer(self):
        self.project.settings = {
            "quiet_hours": {
                "timezone": "UTC",
                "windows_allowed": [{"start": "08:00", "end": "09:00"}],
                "days": [0, 1, 2, 3, 4, 5, 6],
                "action": "defer",
            }
        }
        self.project.save()
        noon = datetime(2026, 7, 23, 12, 0, tzinfo=ZoneInfo("UTC"))
        nxt = next_allowed_datetime(project=self.project, from_dt=noon, mode="general")
        self.assertIsNotNone(nxt)
        self.assertEqual(nxt.astimezone(ZoneInfo("UTC")).hour, 8)
