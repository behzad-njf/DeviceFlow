from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    """Wrap DRF errors in DeviceFlow envelope: { error: { code, message, details } }."""
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        message = str(data["detail"])
        details = None
    else:
        message = "Validation error" if response.status_code == 400 else "Request failed"
        details = data

    code = getattr(exc, "default_code", None) or _status_to_code(response.status_code)
    if hasattr(exc, "get_codes"):
        codes = exc.get_codes()
        if isinstance(codes, str):
            code = codes

    response.data = {
        "error": {
            "code": str(code).upper() if code else "ERROR",
            "message": message,
            "details": details,
        }
    }
    return response


def _status_to_code(status: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        429: "RATE_LIMITED",
        500: "SERVER_ERROR",
    }
    return mapping.get(status, "ERROR")
