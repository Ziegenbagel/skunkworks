import logging
import sys

from src.diagnostics import configure_diagnostics, diagnostic_log_directory, log_handled_error


def test_diagnostic_directory_is_user_scoped():
    assert diagnostic_log_directory().is_absolute()
    assert diagnostic_log_directory().name in {"Skunkworks", "skunkworks", "state"}


def test_diagnostic_log_rotates_and_redacts_credentials(tmp_path):
    logger = logging.getLogger("skunkworks")
    previous_handlers = list(logger.handlers)
    for handler in previous_handlers:
        logger.removeHandler(handler)
    try:
        path = configure_diagnostics(tmp_path)
        log_handled_error("API key=super-secret token=also-secret")
        for handler in logger.handlers:
            handler.flush()
        content = path.read_text(encoding="utf-8")
        assert "Operator-visible error" in content
        assert "super-secret" not in content
        assert "also-secret" not in content
        assert content.count("[REDACTED]") == 2
    finally:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        for handler in previous_handlers:
            logger.addHandler(handler)
