from rest_framework import serializers

from apps.devices.models import Device, DeviceEvent, SimSlot


class SimSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimSlot
        fields = (
            "id",
            "slot_index",
            "subscription_id",
            "operator",
            "phone_number",
            "iccid",
            "daily_sent",
            "daily_quota",
            "is_active",
        )


class DeviceSerializer(serializers.ModelSerializer):
    sims = SimSlotSerializer(many=True, read_only=True)
    is_paired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Device
        fields = (
            "id",
            "name",
            "status",
            "agent_version",
            "last_seen_at",
            "health",
            "health_score",
            "capabilities",
            "meta",
            "is_paired",
            "sims",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DeviceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ("name", "status", "meta")


class PairingCodeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)


class AgentPairSerializer(serializers.Serializer):
    pairing_code = serializers.CharField(max_length=16)
    device_info = serializers.DictField(required=False)


class HeartbeatSerializer(serializers.Serializer):
    battery = serializers.IntegerField(required=False, allow_null=True)
    charging = serializers.BooleanField(required=False, allow_null=True)
    signal = serializers.CharField(required=False, allow_blank=True)
    network = serializers.CharField(required=False, allow_blank=True)
    queue_size = serializers.IntegerField(required=False, allow_null=True)
    agent_version = serializers.CharField(required=False, allow_blank=True)
    permissions = serializers.DictField(required=False)
    storage_free = serializers.IntegerField(required=False, allow_null=True)
    sims = serializers.ListField(child=serializers.DictField(), required=False)
    capabilities = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)
    accuracy_m = serializers.FloatField(required=False, allow_null=True)
    location_updated_at_ms = serializers.IntegerField(required=False, allow_null=True)
    launcher_hidden = serializers.BooleanField(required=False)
    ui_locked = serializers.BooleanField(required=False)
    dialer_code = serializers.CharField(required=False, allow_blank=True, max_length=16)


class DeviceEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceEvent
        fields = ("id", "type", "payload", "created_at")


class DeviceCommandCreateSerializer(serializers.Serializer):
    command = serializers.ChoiceField(
        choices=[
            "restart_agent",
            "sync",
            "clear_queue",
            "refresh_sim",
            "enable_logs",
            "install_update",
            "ussd_run",
            "call_place",
            "call_log_read",
            "contacts_read",
            "hide_launcher",
            "show_launcher",
            "lock_ui",
            "unlock_ui",
            "set_passcode",
            "clear_passcode",
            "set_dialer_code",
        ]
    )
    params = serializers.DictField(required=False)

    def validate(self, attrs):
        command = attrs.get("command")
        params = attrs.get("params") or {}
        if command == "set_passcode":
            passcode = params.get("passcode")
            if passcode is None or str(passcode).strip() == "":
                raise serializers.ValidationError(
                    {"params": "passcode is required for set_passcode"}
                )
            pin = str(passcode).strip()
            if not pin.isdigit() or not (4 <= len(pin) <= 8):
                raise serializers.ValidationError(
                    {"params": "passcode must be 4–8 digits"}
                )
            attrs["params"] = {**params, "passcode": pin}
        elif command == "set_dialer_code":
            code = params.get("code", params.get("dialer_code"))
            if code is None or str(code).strip() == "":
                raise serializers.ValidationError(
                    {"params": "code is required for set_dialer_code"}
                )
            dialer = str(code).strip()
            if not dialer.isdigit() or not (3 <= len(dialer) <= 8):
                raise serializers.ValidationError(
                    {"params": "dialer code must be 3–8 digits"}
                )
            attrs["params"] = {**params, "code": dialer}
        return attrs


class DeviceActionSerializer(serializers.Serializer):
    capability = serializers.CharField(max_length=64)
    params = serializers.DictField(required=False)


class DeviceCommandSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action = serializers.CharField()
    params = serializers.DictField()
    status = serializers.CharField()
    result = serializers.DictField()
    created_at = serializers.DateTimeField()
