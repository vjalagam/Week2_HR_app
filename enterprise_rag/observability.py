from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from contextlib import contextmanager

from .config import SETTINGS

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": correlation_id.get(),
            "message": record.getMessage(),
        })


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(SETTINGS.log_level.upper())
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("pinecone_plugin_interface").setLevel(logging.WARNING)


def new_correlation_id(value: str | None = None) -> str:
    request_id = value or str(uuid.uuid4())
    correlation_id.set(request_id)
    return request_id


@contextmanager
def timed_operation(name: str):
    started = time.perf_counter()
    try:
        yield
        logging.getLogger("enterprise_rag.metrics").info(
            "operation=%s status=ok duration_ms=%.2f", name, (time.perf_counter() - started) * 1000
        )
    except Exception:
        logging.getLogger("enterprise_rag.metrics").exception(
            "operation=%s status=error duration_ms=%.2f", name, (time.perf_counter() - started) * 1000
        )
        raise
