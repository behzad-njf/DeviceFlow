import hashlib
import secrets


def generate_pairing_code(length: int = 8) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_device_token() -> str:
    return f"dfdev_{secrets.token_urlsafe(32)}"


def generate_api_key() -> str:
    return f"df_live_{secrets.token_urlsafe(32)}"


def generate_webhook_secret() -> str:
    return f"whsec_{secrets.token_urlsafe(24)}"


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def api_key_prefix(plaintext: str) -> str:
    return plaintext[:16]
