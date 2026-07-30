from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from dataforge.backend.app.core.config import settings


class ContextAdapter(logging.LoggerAdapter):
    """LoggerAdapter that preserves per-call extra kwargs alongside adapter-level context."""

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = kwargs.get("extra", {})
        if isinstance(extra, dict):
            merged = dict(self.extra)
            merged.update(extra)
            kwargs["extra"] = merged
        return msg, kwargs


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, "source"):
            log_entry["source"] = record.source
        if hasattr(record, "job_id"):
            log_entry["job_id"] = record.job_id
        if hasattr(record, "run_id"):
            log_entry["run_id"] = record.run_id
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(
                    traceback.format_exception(*record.exc_info)
                ),
            }
        # Collect any extra fields from the record
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            for k, v in extra.items():
                if k not in log_entry:
                    log_entry[k] = v
        return json.dumps(log_entry, default=str)


def get_logger(
    name: str,
    level: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> ContextAdapter:
    logger = logging.getLogger(name)
    log_level = level or settings.log_level
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

        if settings.log_file:
            file_handler = logging.FileHandler(settings.log_file)
            file_handler.setFormatter(JsonFormatter())
            logger.addHandler(file_handler)

    return ContextAdapter(logger, {"correlation_id": correlation_id or str(uuid4())})


class LogManager:
    def __init__(self) -> None:
        self._loggers: dict[str, ContextAdapter] = {}

    def get_logger(self, name: str) -> ContextAdapter:
        if name not in self._loggers:
            self._loggers[name] = get_logger(name)
        return self._loggers[name]

    def set_correlation_id(self, name: str, correlation_id: str) -> None:
        logger = self.get_logger(name)
        logger.extra["correlation_id"] = correlation_id
