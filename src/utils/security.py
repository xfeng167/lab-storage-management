import base64
import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{base64.b64encode(salt).decode()}:{base64.b64encode(password_hash).decode()}"


def verify_password(password: str, stored_password: str) -> bool:
    try:
        salt_text, hash_text = stored_password.split(":", maxsplit=1)
        salt = base64.b64decode(salt_text)
        expected_hash = base64.b64decode(hash_text)
    except ValueError:
        return False

    actual_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return secrets.compare_digest(actual_hash, expected_hash)


def create_demo_token() -> str:
    return secrets.token_urlsafe(32)
