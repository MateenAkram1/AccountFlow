import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from accountflow.core.security import redact_mapping, redact_text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = redact_text(record.getMessage())
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        if hasattr(record, "run_id"):
            payload["run_id"] = record.run_id
        if hasattr(record, "extra_data"):
            payload.update(redact_mapping(record.extra_data))
        if record.exc_info:
            payload["exc_info"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
