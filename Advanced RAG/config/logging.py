import json
import logging
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from threading import local

from config.settings import get_settings


_thread_local = local()


@dataclass
class RequestContext:
    request_id: str = ""
    ticket_id: str = ""
    stage: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = getattr(_thread_local, "context", RequestContext())

        log_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "level": record.levelname,
            "service": "advanced-rag",
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": ctx.request_id,
            "ticket_id": ctx.ticket_id,
            "stage": ctx.stage,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms

        # Merge call-site metadata (extra={"metadata": {...}}) with thread-local
        # context metadata.  Call-site metadata takes precedence for overlapping keys.
        call_site_metadata = getattr(record, "metadata", None)
        if call_site_metadata or ctx.metadata:
            log_data["metadata"] = {**(ctx.metadata or {}), **(call_site_metadata or {})}

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    settings = get_settings()
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


def set_context(**kwargs) -> None:
    if not hasattr(_thread_local, "context"):
        _thread_local.context = RequestContext()
    for key, value in kwargs.items():
        setattr(_thread_local.context, key, value)


def clear_context() -> None:
    if hasattr(_thread_local, "context"):
        delattr(_thread_local, "context")


@contextmanager
def log_stage(stage: str, request_id: str = "", ticket_id: str = ""):
    old_context = getattr(_thread_local, "context", None)
    _thread_local.context = RequestContext(
        request_id=request_id,
        ticket_id=ticket_id,
        stage=stage,
    )
    logger = get_logger("stage")
    logger.info(f"Starting stage: {stage}")
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"Completed stage: {stage}", extra={"latency_ms": elapsed_ms})
        if old_context:
            _thread_local.context = old_context
        else:
            clear_context()


def setup_logging() -> None:
    settings = get_settings()
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(handler)