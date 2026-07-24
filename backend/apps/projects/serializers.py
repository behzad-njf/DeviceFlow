from rest_framework import serializers

from apps.projects.models import Project, ProjectDevice


class ProjectDeviceBriefSerializer(serializers.Serializer):
    device_id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    agent_version = serializers.CharField(allow_blank=True)
    health_score = serializers.IntegerField()
    last_seen_at = serializers.DateTimeField(allow_null=True)
    priority = serializers.IntegerField()
    exclusive = serializers.BooleanField()


class ProjectSerializer(serializers.ModelSerializer):
    devices = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "slug",
            "mode_default",
            "settings",
            "is_active",
            "device_count",
            "devices",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "device_count",
            "devices",
            "created_at",
            "updated_at",
        )

    def get_device_count(self, obj) -> int:
        # Prefetched in list/detail views when available.
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "project_devices" in obj._prefetched_objects_cache
        ):
            return len(obj.project_devices.all())
        return obj.project_devices.count()

    def get_devices(self, obj):
        links = obj.project_devices.all()
        # Use prefetched relation when present.
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "project_devices" in obj._prefetched_objects_cache
        ):
            links = obj.project_devices.all()
        else:
            links = obj.project_devices.select_related("device").all()

        results = []
        for link in links:
            device = link.device
            results.append(
                {
                    "device_id": str(device.id),
                    "name": device.name,
                    "status": device.status,
                    "agent_version": device.agent_version or "",
                    "health_score": device.health_score,
                    "last_seen_at": device.last_seen_at,
                    "priority": link.priority,
                    "exclusive": link.exclusive,
                }
            )
        # Stable order: priority then name
        results.sort(key=lambda row: (row["priority"], row["name"].lower()))
        return results


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("name", "slug", "mode_default", "settings")

    def create(self, validated_data):
        tenant = self.context["tenant"]
        return Project.objects.create(tenant=tenant, **validated_data)


class ProjectDeviceSerializer(serializers.Serializer):
    device_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=True
    )
    priorities = serializers.DictField(
        child=serializers.IntegerField(), required=False
    )
