from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone

from apps.devices.models import Device, DeviceEvent, SimSlot
from apps.messaging.models import InboundMessage, Message, MessageAttempt
from apps.projects.models import Project
from apps.routing.exceptions import RateLimitExceeded, RoutingError
from apps.messaging.services.templates import IdempotencyConflict
from apps.routing.services.engine import get_or_create_config, route_message
from apps.routing.services import modes as mode_policy
from apps.routing.services import rate_limit
from apps.routing.services import throttle


RETRY_BACKOFF_SECONDS = [30, 60, 300, 600, 1800]


class MessageService:
    @staticmethod
    def resolve_project(*, tenant, project_ref: str | None) -> Project | None:
        if not project_ref:
            return None
        qs = Project.objects.filter(tenant=tenant, is_active=True)
        project = qs.filter(slug=project_ref).first() or qs.filter(id=project_ref).first()
        if project is None:
            raise ValueError("Project not found")
        return project

    @staticmethod
    def resolve_device(*, tenant, device_ref: str | None, project: Project | None) -> Device | None:
        """Legacy helper kept for explicit device pin validation in views."""
        if not device_ref:
            return None
        result = route_message(
            tenant=tenant,
            to_number="",
            project=project,
            device_ref=device_ref,
        )
        if result.device is None:
            raise ValueError(result.reason or "Device not found")
        return result.device

    @staticmethod
    @transaction.atomic
    def enqueue(
        *,
        tenant,
        to_number: str,
        body: str,
        project: Project | None = None,
        device: Device | None = None,
        device_ref: str | None = None,
        sim_slot_index: int | None = None,
        mode: str = Message.Mode.GENERAL,
        client_ref: str = "",
        meta: dict | None = None,
        scheduled_at=None,
    ) -> Message:
        from apps.contacts.services import is_send_allowed, touch_conversation
        from apps.messaging.services.scheduler import next_allowed_datetime
        from apps.routing.services.operators import normalize_number

        to_number = normalize_number(to_number)
        allowed_send, block_code = is_send_allowed(
            tenant=tenant, phone_number=to_number, project=project
        )
        if not allowed_send:
            raise ValueError(block_code or "NUMBER_BLOCKED")

        resolved_mode = mode or (
            project.mode_default if project else Message.Mode.GENERAL
        )
        priority = mode_policy.priority_for_mode(resolved_mode)
        config = get_or_create_config(tenant)

        # Quiet hours may defer
        try:
            quiet_at = next_allowed_datetime(
                project=project, from_dt=scheduled_at or timezone.now(), mode=resolved_mode
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if quiet_at is not None:
            scheduled_at = quiet_at

        # Marketing pacing: inject random jitter so OTP path stays ahead
        if (
            resolved_mode == Message.Mode.MARKETING
            and (scheduled_at is None or scheduled_at <= timezone.now())
        ):
            jitter_at = mode_policy.marketing_jitter_deadline(config)
            if jitter_at is not None:
                scheduled_at = jitter_at

        if scheduled_at and scheduled_at > timezone.now():
            message_meta = {
                **(meta or {}),
                "scheduled": True,
                "mode_priority": priority,
            }
            message = Message.objects.create(
                tenant=tenant,
                project=project,
                to_number=to_number,
                body=body,
                status=Message.Status.SCHEDULED,
                mode=resolved_mode,
                priority=priority,
                client_ref=client_ref or "",
                meta=message_meta,
                scheduled_at=scheduled_at,
            )
            touch_conversation(
                tenant=tenant,
                phone_number=to_number,
                preview=body,
                when=timezone.now(),
                project=project,
            )
            from apps.realtime.events import publish_message_updated

            publish_message_updated(message)
            return message

        pin = device_ref or (str(device.id) if device is not None else None)
        result = route_message(
            tenant=tenant,
            to_number=to_number,
            mode=resolved_mode,
            project=project,
            device_ref=pin,
            sim_slot_index=sim_slot_index,
        )
        if result.device is None:
            raise RoutingError(
                code=result.reason or "NO_DEVICE_AVAILABLE",
                message=result.reason or "No device available to send message",
            )

        limits = throttle.apply_adaptive_limits(
            device_id=str(result.device.id),
            limits={
                "per_minute": config.rate_limit_per_minute,
                "per_hour": config.rate_limit_per_hour,
                "per_day": config.rate_limit_per_day,
                "project_per_minute": config.project_rate_limit_per_minute,
            },
            enabled=config.adaptive_throttle_enabled,
            threshold=float(config.adaptive_failure_threshold),
        )
        allowed, limit_code = rate_limit.check_and_consume(
            device_id=str(result.device.id),
            project_id=str(project.id) if project else None,
            sim_id=str(result.sim_slot.id) if result.sim_slot else None,
            limits=limits,
        )
        if not allowed:
            raise RateLimitExceeded(code=limit_code or "RATE_LIMITED")

        if client_ref and project is not None:
            existing = Message.objects.filter(
                project=project, client_ref=client_ref
            ).first()
            if existing:
                if existing.to_number != to_number or existing.body != body:
                    raise IdempotencyConflict(
                        "Idempotent client_ref reused with a different payload"
                    )
                return existing

        message_meta = {
            **(meta or {}),
            "mode_priority": priority,
            "queue_weight": mode_policy.queue_weight_for_mode(resolved_mode, config),
            "routing": {
                "strategy": result.strategy,
                "operator": result.operator,
                "forced": result.forced,
                "reason": result.reason,
            },
        }
        message = Message.objects.create(
            tenant=tenant,
            project=project,
            device=result.device,
            sim_slot=result.sim_slot,
            to_number=to_number,
            body=body,
            status=Message.Status.ASSIGNED,
            mode=resolved_mode,
            priority=priority,
            client_ref=client_ref or "",
            meta=message_meta,
            scheduled_at=scheduled_at,
        )
        MessageAttempt.objects.create(
            message=message,
            device=result.device,
            result="assigned",
            detail=f"Routed via {result.strategy}",
        )
        touch_conversation(
            tenant=tenant,
            phone_number=to_number,
            preview=body,
            when=timezone.now(),
            project=project,
        )
        from apps.common.metrics import MESSAGES_ENQUEUED
        from apps.realtime.events import publish_message_updated

        publish_message_updated(message)
        MESSAGES_ENQUEUED.labels(mode=resolved_mode).inc()
        return message

    @staticmethod
    def pending_for_device(device: Device, limit: int = 20) -> list[Message]:
        return list(
            Message.objects.filter(
                device=device,
                status__in=[
                    Message.Status.ASSIGNED,
                    Message.Status.RETRYING,
                ],
            )
            .select_related("sim_slot")
            .order_by("priority", "created_at")[:limit]
        )

    @staticmethod
    @transaction.atomic
    def update_status(
        *,
        message: Message,
        status: str,
        error_code: str = "",
        error_message: str = "",
        latency_ms: int | None = None,
        sim_slot_index: int | None = None,
    ) -> Message:
        now = timezone.now()
        message.status = status
        if latency_ms is not None:
            message.latency_ms = latency_ms
        if sim_slot_index is not None:
            slot = SimSlot.objects.filter(
                device=message.device, slot_index=sim_slot_index
            ).first()
            if slot:
                message.sim_slot = slot

        if status == Message.Status.SENDING:
            pass
        elif status == Message.Status.SENT:
            message.sent_at = now
            message.error_code = ""
            message.error_message = ""
            from apps.common.metrics import MESSAGES_SENT

            MESSAGES_SENT.inc()
            if message.sim_slot_id:
                SimSlot.objects.filter(id=message.sim_slot_id).update(
                    daily_sent=models.F("daily_sent") + 1
                )
            if message.device_id:
                throttle.record_outcome(device_id=str(message.device_id), success=True)
        elif status == Message.Status.DELIVERED:
            message.delivered_at = now
            if not message.sent_at:
                message.sent_at = now
            if message.device_id:
                throttle.record_outcome(device_id=str(message.device_id), success=True)
        elif status == Message.Status.FAILED:
            message.failed_at = now
            message.error_code = error_code or "SEND_FAILED"
            message.error_message = error_message or "Send failed"
            from apps.common.metrics import MESSAGES_FAILED

            MESSAGES_FAILED.inc()
            if message.device_id:
                throttle.record_outcome(device_id=str(message.device_id), success=False)
            MessageAttempt.objects.create(
                message=message,
                device=message.device,
                finished_at=now,
                result=status,
                detail=error_message or status,
            )
            if message.device_id:
                DeviceEvent.objects.create(
                    device=message.device,
                    type=f"sms.{status}",
                    payload={"message_id": str(message.id), "to": message.to_number},
                )
            from apps.routing.services.ha import maybe_failover_on_failure

            rerouted = maybe_failover_on_failure(message)
            if rerouted is not None:
                return rerouted
            MessageService._schedule_retry(message)
            message.save()
            from apps.realtime.events import publish_message_updated

            publish_message_updated(message)
            return message
        elif status == Message.Status.CANCELLED:
            pass

        message.save()
        MessageAttempt.objects.create(
            message=message,
            device=message.device,
            finished_at=now,
            result=status,
            detail=error_message or status,
        )
        if message.device_id:
            DeviceEvent.objects.create(
                device=message.device,
                type=f"sms.{status}",
                payload={"message_id": str(message.id), "to": message.to_number},
            )
        from apps.realtime.events import publish_message_updated

        publish_message_updated(message)
        return message

    @staticmethod
    def _schedule_retry(message: Message) -> None:
        if message.retry_count >= message.max_retries:
            message.status = Message.Status.DEAD_LETTER
            message.next_retry_at = None
            return
        delay = RETRY_BACKOFF_SECONDS[
            min(message.retry_count, len(RETRY_BACKOFF_SECONDS) - 1)
        ]
        message.retry_count += 1
        message.status = Message.Status.RETRYING
        message.next_retry_at = timezone.now() + timedelta(seconds=delay)

    @staticmethod
    @transaction.atomic
    def promote_retries() -> int:
        due = Message.objects.select_for_update().filter(
            status=Message.Status.RETRYING,
            next_retry_at__lte=timezone.now(),
        )
        count = 0
        for message in due:
            # Re-route on promote so retries can land on healthier devices
            result = route_message(
                tenant=message.tenant,
                to_number=message.to_number,
                mode=message.mode,
                project=message.project,
            )
            if result.device is not None:
                message.device = result.device
                message.sim_slot = result.sim_slot
            message.status = Message.Status.ASSIGNED
            message.next_retry_at = None
            message.save(
                update_fields=[
                    "device",
                    "sim_slot",
                    "status",
                    "next_retry_at",
                    "updated_at",
                ]
            )
            count += 1
        return count

    @staticmethod
    @transaction.atomic
    def cancel(message: Message) -> Message:
        if message.status in {
            Message.Status.SENT,
            Message.Status.DELIVERED,
            Message.Status.CANCELLED,
            Message.Status.DEAD_LETTER,
        }:
            raise ValueError("Message cannot be cancelled in its current state")
        message.status = Message.Status.CANCELLED
        message.save(update_fields=["status", "updated_at"])
        from apps.realtime.events import publish_message_updated

        publish_message_updated(message)
        return message

    @staticmethod
    @transaction.atomic
    def retry(message: Message) -> Message:
        if message.status not in {
            Message.Status.FAILED,
            Message.Status.DEAD_LETTER,
            Message.Status.CANCELLED,
        }:
            raise ValueError("Only failed/dead/cancelled messages can be retried")
        result = route_message(
            tenant=message.tenant,
            to_number=message.to_number,
            mode=message.mode,
            project=message.project,
        )
        if result.device is not None:
            message.device = result.device
            message.sim_slot = result.sim_slot
        message.status = Message.Status.ASSIGNED
        message.error_code = ""
        message.error_message = ""
        message.next_retry_at = None
        message.failed_at = None
        message.save()
        MessageAttempt.objects.create(
            message=message,
            device=message.device,
            result="manual_retry",
            detail="Manual retry from dashboard/API",
        )
        from apps.realtime.events import publish_message_updated

        publish_message_updated(message)
        return message

    @staticmethod
    def create_inbound(
        *,
        device: Device,
        from_number: str,
        body: str,
        received_at,
        sim_slot_index: int | None = None,
        meta: dict | None = None,
    ) -> InboundMessage:
        from apps.contacts.services import (
            find_auto_reply,
            touch_conversation,
            upsert_contact,
        )
        from apps.routing.services.operators import normalize_number

        from_number = normalize_number(from_number)
        sim_slot = None
        if sim_slot_index is not None:
            sim_slot = SimSlot.objects.filter(
                device=device, slot_index=sim_slot_index
            ).first()
        link = device.project_links.select_related("project").first()
        project = link.project if link else None
        inbound = InboundMessage.objects.create(
            tenant=device.tenant,
            project=project,
            device=device,
            from_number=from_number,
            body=body,
            received_at=received_at,
            sim_slot=sim_slot,
            meta=meta or {},
        )
        DeviceEvent.objects.create(
            device=device,
            type="sms.inbound",
            payload={"inbound_id": str(inbound.id), "from": from_number},
        )
        upsert_contact(tenant=device.tenant, phone_number=from_number)
        touch_conversation(
            tenant=device.tenant,
            phone_number=from_number,
            preview=body,
            when=received_at,
            project=project,
            inbound=True,
        )
        if project:
            from apps.webhooks.services.delivery import enqueue_event

            enqueue_event(
                project=project,
                event_type="inbound.received",
                payload={
                    "id": str(inbound.id),
                    "from_number": from_number,
                    "body": body,
                    "device_id": str(device.id),
                    "received_at": received_at.isoformat()
                    if hasattr(received_at, "isoformat")
                    else str(received_at),
                },
            )

        try:
            from apps.automations.services.engine import run_automations

            run_automations(
                tenant=device.tenant,
                event="inbound.received",
                body=body,
                project=project,
                meta={
                    "from_number": from_number,
                    "inbound_id": str(inbound.id),
                    "device_id": str(device.id),
                },
            )
        except Exception:
            pass

        try:
            from apps.plugins.services.events import emit_plugin_event

            emit_plugin_event(
                tenant=device.tenant,
                event_type="inbound.received",
                payload={
                    "from_number": from_number,
                    "body": body,
                    "inbound_id": str(inbound.id),
                },
                project_id=str(project.id) if project else None,
            )
        except Exception:
            pass

        rule = find_auto_reply(tenant=device.tenant, body=body, project=project)
        if rule:
            try:
                MessageService.enqueue(
                    tenant=device.tenant,
                    to_number=from_number,
                    body=rule.reply_body,
                    project=project,
                    mode=Message.Mode.GENERAL,
                    meta={"auto_reply_rule_id": str(rule.id)},
                )
            except Exception:
                # Auto-reply must not break inbound ingest
                pass
        return inbound
