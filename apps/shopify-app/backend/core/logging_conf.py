from __future__ import annotations

import logging
import os
from typing import Any, Dict

try:
    from pythonjsonlogger import jsonlogger
    _JSONLOGGER_AVAILABLE = True
    _BaseFormatter = jsonlogger.JsonFormatter
except Exception:  # pragma: no cover - optional dependency
    jsonlogger = None
    _JSONLOGGER_AVAILABLE = False
    _BaseFormatter = logging.Formatter

from app.utils.logging import PIISafeFormatter


class RedactingJsonFormatter(_BaseFormatter):
    """JSON formatter that redacts sensitive fields from log records."""

    def _sanitize_value(self, value: Any):
        if isinstance(value, str):
            return PIISafeFormatter.sanitize(value)
        if isinstance(value, dict):
            return {k: self._sanitize_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._sanitize_value(v) for v in value]
        return value

    def add_fields(self, log_record, record, message_dict):
        if not _JSONLOGGER_AVAILABLE:
            return
        super().add_fields(log_record, record, message_dict)
        for key, value in list(log_record.items()):
            log_record[key] = self._sanitize_value(value)

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        if not hasattr(record, "shop_domain"):
            record.shop_domain = "-"
        record.msg = PIISafeFormatter.sanitize(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: (PIISafeFormatter.sanitize(v) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    PIISafeFormatter.sanitize(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        if record.exc_text:
            record.exc_text = PIISafeFormatter.sanitize(record.exc_text)
        formatted = super().format(record)
        if _JSONLOGGER_AVAILABLE:
            return formatted
        return PIISafeFormatter.sanitize(formatted)


def configure_logging(level: str | None = None) -> None:
    """Configure global structured JSON logging with a request-aware formatter.

    This sets a JSON formatter that includes timestamp, level, message and any
    extra context (e.g., shop_domain, request_id) provided by `LoggerAdapter`.
    """
    log_level = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    handler = logging.StreamHandler()
    formatter = RedactingJsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(shop_domain)s')
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))
    # Clear existing handlers to avoid duplicate logs in some environments
    root.handlers = []
    root.addHandler(handler)


def get_structured_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
