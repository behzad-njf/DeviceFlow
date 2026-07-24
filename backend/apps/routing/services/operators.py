from apps.routing.models import OperatorPrefix


def normalize_number(number: str) -> str:
    cleaned = "".join(ch for ch in (number or "") if ch.isdigit() or ch == "+")
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if cleaned.startswith("09") and len(cleaned) == 11:
        cleaned = "+98" + cleaned[1:]
    if cleaned.startswith("9") and len(cleaned) == 10:
        cleaned = "+98" + cleaned
    return cleaned


def is_valid_phone_number(number: str) -> bool:
    """
    Accept numbers that normalize to international (+…) form with 8–15 digits.
    Iranian mobiles like 09XXXXXXXXX / 9XXXXXXXXX are accepted via normalize_number.
    """
    raw = (number or "").strip()
    if not raw:
        return False
    cleaned = normalize_number(raw)
    if not cleaned.startswith("+"):
        return False
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if not (8 <= len(digits) <= 15):
        return False
    # Reject obvious junk (e.g. +11111111)
    if len(set(digits)) == 1:
        return False
    return True


def resolve_operator(to_number: str) -> str | None:
    number = normalize_number(to_number)
    prefixes = list(
        OperatorPrefix.objects.filter(is_active=True).values_list("prefix", "operator")
    )
    prefixes.sort(key=lambda item: len(item[0]), reverse=True)
    for prefix, operator in prefixes:
        if number.startswith(prefix):
            return operator
    return None
