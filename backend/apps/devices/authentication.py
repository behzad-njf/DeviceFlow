from rest_framework import authentication, exceptions

from apps.common.crypto import hash_secret
from apps.devices.models import Device


class DeviceUser:
    """Lightweight principal representing a paired Android agent."""

    is_authenticated = True
    is_anonymous = False

    def __init__(self, device: Device):
        self.device = device
        self.pk = device.id
        self.id = device.id

    def __str__(self) -> str:
        return f"device:{self.device.id}"


class DeviceTokenAuthentication(authentication.BaseAuthentication):
    """
    Authorization: Device <plaintext_token>
    """

    keyword = "Device"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header:
            return None
        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None
        token = parts[1]
        token_hash = hash_secret(token)
        try:
            device = Device.objects.select_related("tenant").get(
                device_token_hash=token_hash
            )
        except Device.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Invalid device token") from exc
        if device.status == Device.Status.DISABLED:
            raise exceptions.AuthenticationFailed("Device disabled")
        request.device = device
        request.tenant = device.tenant
        return (DeviceUser(device), token)
