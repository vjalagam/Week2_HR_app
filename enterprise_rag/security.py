from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque

from .config import SETTINGS

ROLE_NAMESPACES = {
    "admin": {"hr", "technical", "compliance"},
    "hr": {"hr"},
    "engineer": {"technical"},
    "compliance": {"compliance"},
    "employee": {"hr", "technical", "compliance"},
}
_requests: dict[str, deque[float]] = defaultdict(deque)


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, expected = encoded.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hash_password(password, salt).rsplit("$", 1)[1]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str) -> dict[str, str] | None:
    user = SETTINGS.auth_users.get(username)
    if not user or not verify_password(password, user.get("password_hash", "")):
        return None
    return {"username": username, "role": user.get("role", "employee")}


def allowed_namespaces(role: str) -> set[str]:
    return ROLE_NAMESPACES.get(role, set())


def validate_question(question: str) -> str:
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", question).strip()
    if not normalized:
        raise ValueError("Question cannot be empty.")
    if len(normalized) > SETTINGS.max_question_length:
        raise ValueError(f"Question exceeds {SETTINGS.max_question_length} characters.")
    return normalized


def check_rate_limit(identity: str) -> None:
    now = time.monotonic()
    entries = _requests[identity]
    while entries and now - entries[0] >= 60:
        entries.popleft()
    if len(entries) >= SETTINGS.rate_limit_per_minute:
        raise RuntimeError("Rate limit exceeded. Try again in one minute.")
    entries.append(now)
