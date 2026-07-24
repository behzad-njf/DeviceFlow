from dataclasses import dataclass

from apps.devices.models import Device, SimSlot
from apps.messaging.models import Message
from apps.projects.models import Project, ProjectDevice
from apps.routing.models import RoutingRule, TenantRoutingConfig
from apps.routing.services import load_balancer
from apps.routing.services import modes as mode_policy
from apps.routing.services import operators
from apps.routing.services import rate_limit
from apps.routing.services import throttle


@dataclass
class RouteResult:
    device: Device | None
    sim_slot: SimSlot | None
    strategy: str
    operator: str | None
    reason: str | None = None
    forced: bool = False


def get_or_create_config(tenant) -> TenantRoutingConfig:
    config, _ = TenantRoutingConfig.objects.get_or_create(tenant=tenant)
    return config


def _rule_matches(rule: RoutingRule, *, to_number: str, mode: str, project: Project | None) -> bool:
    match = rule.match or {}
    prefixes = match.get("to_prefix") or []
    if prefixes and not any(to_number.startswith(p) for p in prefixes):
        return False
    modes = match.get("mode") or []
    if modes and mode not in modes:
        return False
    project_ids = match.get("project_id") or match.get("project_ids") or []
    if project_ids:
        if project is None or str(project.id) not in [str(x) for x in project_ids]:
            return False
    operators_match = match.get("operator") or []
    if operators_match:
        op = operators.resolve_operator(to_number)
        if op not in operators_match:
            return False
    return True


def _is_healthy(device: Device, config: TenantRoutingConfig) -> bool:
    if device.health_score < config.min_health_score:
        return False
    health = device.health or {}
    battery = health.get("battery")
    charging = bool(health.get("charging"))
    if battery is not None and int(battery) < config.min_battery_percent and not charging:
        return False
    perms = health.get("permissions") or {}
    if "sms" in perms and not perms.get("sms", True):
        return False
    return True


def _base_candidates(*, tenant, project: Project | None, prefer_online: bool = True) -> list[Device]:
    qs = Device.objects.filter(tenant=tenant).exclude(
        status__in=[Device.Status.DISABLED, Device.Status.PENDING]
    )
    if project is not None:
        linked_ids = ProjectDevice.objects.filter(project=project).values_list(
            "device_id", flat=True
        )
        qs = qs.filter(id__in=linked_ids)
    devices = list(qs.prefetch_related("sims"))
    if prefer_online:
        online = [d for d in devices if d.status == Device.Status.ONLINE and d.is_paired]
        if online:
            return online
    return [d for d in devices if d.is_paired]


def _select_sim(
    device: Device,
    *,
    preferred_operator: str | None,
    sim_slot_index: int | None,
    tenant_default_quota: int = 1000,
) -> SimSlot | None:
    """Pick an active SIM with remaining daily quota; rotate to least-used."""
    sims = list(device.sims.filter(is_active=True))
    if not sims:
        return None
    if sim_slot_index is not None:
        for sim in sims:
            if sim.slot_index == sim_slot_index:
                if not sim.is_quota_exhausted(tenant_default_quota):
                    return sim
                break

    available = [s for s in sims if not s.is_quota_exhausted(tenant_default_quota)]
    if not available:
        return None

    if preferred_operator:
        matched = [
            s for s in available if s.operator.lower() == preferred_operator.lower()
        ]
        if matched:
            return sorted(matched, key=lambda s: (s.daily_sent, s.slot_index))[0]
    return sorted(available, key=lambda s: (s.daily_sent, s.slot_index))[0]


def _limits_for_device(config: TenantRoutingConfig, device_id: str) -> dict:
    base = {
        "per_minute": config.rate_limit_per_minute,
        "per_hour": config.rate_limit_per_hour,
        "per_day": config.rate_limit_per_day,
        "project_per_minute": config.project_rate_limit_per_minute,
    }
    return throttle.apply_adaptive_limits(
        device_id=device_id,
        limits=base,
        enabled=config.adaptive_throttle_enabled,
        threshold=float(config.adaptive_failure_threshold),
    )


def route_message(
    *,
    tenant,
    to_number: str,
    mode: str = Message.Mode.GENERAL,
    project: Project | None = None,
    device_ref: str | None = None,
    sim_slot_index: int | None = None,
    exclude_device_ids: set | None = None,
) -> RouteResult:
    config = get_or_create_config(tenant)
    number = operators.normalize_number(to_number)
    operator = operators.resolve_operator(number)
    exclude_device_ids = exclude_device_ids or set()
    strategy = config.lb_strategy
    preferred_operator = operator
    forced_device_id = None
    prefer_ids: list[str] = []
    exclude_ids = {str(x) for x in exclude_device_ids}
    sim_quota_default = int(config.sim_daily_quota_default or 0)

    if device_ref:
        qs = Device.objects.filter(tenant=tenant).exclude(status=Device.Status.DISABLED)
        device = qs.filter(name=device_ref).first() or qs.filter(id=device_ref).first()
        if device is None or not device.is_paired:
            return RouteResult(None, None, strategy, operator, "DEVICE_NOT_FOUND")
        sim = _select_sim(
            device,
            preferred_operator=preferred_operator,
            sim_slot_index=sim_slot_index,
            tenant_default_quota=sim_quota_default,
        )
        return RouteResult(device, sim, strategy, operator, forced=True)

    rules = RoutingRule.objects.filter(tenant=tenant, enabled=True).order_by("-priority")
    for rule in rules:
        if rule.project_id and (project is None or rule.project_id != project.id):
            continue
        if not _rule_matches(rule, to_number=number, mode=mode, project=project):
            continue
        action = rule.action or {}
        action_type = action.get("type")
        if action_type == "force_device":
            forced_device_id = str(
                action.get("device_id") or (action.get("device_ids") or [None])[0]
            )
            break
        if action_type == "prefer_devices":
            prefer_ids = [str(x) for x in (action.get("device_ids") or [])]
        if action_type == "exclude_devices":
            exclude_ids.update(str(x) for x in (action.get("device_ids") or []))
        if action.get("sim_operator"):
            preferred_operator = action["sim_operator"]
        if action.get("lb_strategy"):
            strategy = action["lb_strategy"]
        if action_type == "set_mode":
            mode = action.get("mode") or mode

    candidates = _base_candidates(tenant=tenant, project=project, prefer_online=True)
    candidates = [d for d in candidates if str(d.id) not in exclude_ids]
    candidates = [d for d in candidates if _is_healthy(d, config)]

    candidates = [
        d
        for d in candidates
        if rate_limit.has_headroom(
            device_id=str(d.id), limits=_limits_for_device(config, str(d.id))
        )
    ]

    with_sim = []
    for d in candidates:
        if _select_sim(
            d,
            preferred_operator=preferred_operator,
            sim_slot_index=None,
            tenant_default_quota=sim_quota_default,
        ):
            with_sim.append(d)
    if with_sim:
        candidates = with_sim

    if forced_device_id:
        forced = next((d for d in candidates if str(d.id) == forced_device_id), None)
        if forced is None:
            all_devs = _base_candidates(tenant=tenant, project=project, prefer_online=False)
            forced = next((d for d in all_devs if str(d.id) == forced_device_id), None)
        if forced is None:
            return RouteResult(None, None, strategy, operator, "FORCED_DEVICE_UNAVAILABLE")
        sim = _select_sim(
            forced,
            preferred_operator=preferred_operator,
            sim_slot_index=sim_slot_index,
            tenant_default_quota=sim_quota_default,
        )
        return RouteResult(forced, sim, strategy, operator, forced=True)

    if prefer_ids:
        preferred = [d for d in candidates if str(d.id) in prefer_ids]
        if preferred:
            candidates = preferred

    if not candidates:
        fallback = _base_candidates(tenant=tenant, project=project, prefer_online=False)
        fallback = [d for d in fallback if str(d.id) not in exclude_ids]
        if not fallback:
            return RouteResult(None, None, strategy, operator, "NO_DEVICE_AVAILABLE")
        strategy = mode_policy.prefer_strategy_for_mode(mode, strategy)
        device = load_balancer.select_device(
            candidates=fallback,
            strategy=strategy,
            tenant_id=tenant.id,
            project=project,
            mode=mode,
            mode_weight=mode_policy.queue_weight_for_mode(mode, config),
        )
        sim = (
            _select_sim(
                device,
                preferred_operator=preferred_operator,
                sim_slot_index=sim_slot_index,
                tenant_default_quota=sim_quota_default,
            )
            if device
            else None
        )
        return RouteResult(device, sim, strategy, operator, "ASSIGNED_OFFLINE_FALLBACK")

    strategy = mode_policy.prefer_strategy_for_mode(mode, strategy)

    device = load_balancer.select_device(
        candidates=candidates,
        strategy=strategy,
        tenant_id=tenant.id,
        project=project,
        mode=mode,
        mode_weight=mode_policy.queue_weight_for_mode(mode, config),
    )
    if device is None:
        return RouteResult(None, None, strategy, operator, "NO_DEVICE_AVAILABLE")

    sim = _select_sim(
        device,
        preferred_operator=preferred_operator,
        sim_slot_index=sim_slot_index,
        tenant_default_quota=sim_quota_default,
    )
    if sim is None:
        remaining = [d for d in candidates if d.id != device.id]
        for alt in remaining:
            sim = _select_sim(
                alt,
                preferred_operator=preferred_operator,
                sim_slot_index=None,
                tenant_default_quota=sim_quota_default,
            )
            if sim is not None:
                return RouteResult(alt, sim, strategy, operator, "SIM_ROTATED")
        return RouteResult(None, None, strategy, operator, "SIM_QUOTA_EXHAUSTED")

    return RouteResult(device, sim, strategy, operator)
