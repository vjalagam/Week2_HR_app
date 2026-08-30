from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from .config import SETTINGS

_requests: dict[str, deque[float]] = defaultdict(deque)


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
