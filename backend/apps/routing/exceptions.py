class RateLimitExceeded(Exception):
    """Raised when tenant/device/project/SIM send rate limits are exceeded."""

    def __init__(self, code: str = "RATE_LIMITED", message: str | None = None):
        self.code = code
        self.message = message or "Rate limit exceeded"
        super().__init__(self.message)


class RoutingError(Exception):
    """Raised when no suitable device can be selected."""

    def __init__(self, code: str = "NO_DEVICE_AVAILABLE", message: str | None = None):
        self.code = code
        self.message = message or "No device available"
        super().__init__(self.message)
