"""
Structured (JSON) logging setup.

Every log line is a single-line JSON object so it can be shipped straight
into any log aggregator (CloudWatch, Datadog, ELK, etc.) without a custom
parser. A request_id is threaded through via contextvars so every log line
emitted while handling a given HTTP request / webhook can be correlated.
"""
import json
import logging
import sys
import time
from contextvars import ContextVar

from app.config import get_settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Allow callers to attach arbitrary structured fields via `extra`.
        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                payload[key[4:]] = value
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    # Avoid duplicate handlers on reload
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
