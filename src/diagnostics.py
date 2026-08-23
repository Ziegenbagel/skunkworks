"""Privacy-conscious rotating diagnostic logging for support reports."""

from __future__ import annotations

import logging
import logging.handlers
import os
import platform
import re
import sys
import threading
from pathlib import Path

from src.application.paths import application_paths


LOGGER_NAME = "skunkworks"
_configured_path: Path | None = None


def diagnostic_log_directory() -> Path:
    """Return the conventional per-user log directory for this platform."""

    return application_paths().state


class _CredentialRedactionFilter(logging.Filter):
    _patterns = (
        re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
        re.compile(r"(?i)((?:api[-_ ]?key|token|secret)\s*[:=]\s*)[^\s,;]+"),
        re.compile(r"(?i)([?&](?:api[-_]?key|token)=)[^&\s]+"),
    )

    @classmethod
    def redact(cls, value):
        text = str(value)
        for pattern in cls._patterns:
            text = pattern.sub(r"\1[REDACTED]", text)
        return text

    def filter(self, record):
        record.msg = self.redact(record.getMessage())
        record.args = ()
        return True


def configure_diagnostics(log_directory=None) -> Path:
    """Configure a 1 MiB, five-backup rotating application error log."""

    global _configured_path
    directory = Path(log_directory) if log_directory else diagnostic_log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "skunkworks-errors.log"
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        handler.addFilter(_CredentialRedactionFilter())
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            "%Y-%m-%dT%H:%M:%S%z",
        ))
        logger.addHandler(handler)
    _configured_path = log_path
    logger.info(
        "Session started | Skunkworks | Python %s | %s %s",
        platform.python_version(), platform.system(), platform.release(),
    )
    return log_path


def install_exception_hooks() -> None:
    """Record otherwise uncaught main-thread and worker-thread exceptions."""

    logger = logging.getLogger(LOGGER_NAME)
    previous_sys_hook = sys.excepthook

    def exception_hook(exception_type, exception, traceback):
        logger.critical(
            "Uncaught application exception",
            exc_info=(exception_type, exception, traceback),
        )
        previous_sys_hook(exception_type, exception, traceback)

    sys.excepthook = exception_hook
    previous_thread_hook = threading.excepthook

    def thread_exception_hook(arguments):
        logger.critical(
            "Uncaught worker-thread exception in %s",
            arguments.thread.name if arguments.thread else "unknown",
            exc_info=(arguments.exc_type, arguments.exc_value, arguments.exc_traceback),
        )
        previous_thread_hook(arguments)

    threading.excepthook = thread_exception_hook


def log_handled_error(message: str) -> None:
    """Record an error presented to the operator, retaining active traceback."""

    if not message:
        return
    logging.getLogger(LOGGER_NAME).error(
        "Operator-visible error: %s",
        message,
        exc_info=sys.exc_info()[0] is not None,
    )
