"""Diagnostic logging: off by default, owner-only when on.

SNAT-0045 filed the gap: the app imported no logging module anywhere, so the
six `except Exception: pass` sites had nothing to record to and ruff's own
suggestion ("consider logging the exception") could not be followed.

The two properties that matter are that an unconfigured app writes nothing --
the item required no user-visible change -- and that the file it does write
is owner-only, because it carries URLs and error text and CLAUDE.md makes
0o600 a guarantee for every user data file.
"""

import logging
import os
import stat

import pytest

from snatch import logging_setup


@pytest.fixture(autouse=True)
def _detach_handlers():
    """Each test starts from an unconfigured root logger and leaves one.

    configure_logging() installs a handler on the package logger, which is
    process-global; without this the first test that enables logging decides
    the state for every test after it.
    """
    logger = logging.getLogger(logging_setup.LOGGER_NAME)
    original = list(logger.handlers)
    yield
    for handler in logger.handlers:
        if handler not in original:
            handler.close()
    logger.handlers = original


def test_disabled_by_default_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.delenv(logging_setup.LOG_ENV, raising=False)

    enabled = logging_setup.configure_logging(str(tmp_path))

    assert enabled is False
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize("value", ["", "0", "false", "off", "no"])
def test_falsey_env_values_stay_disabled(tmp_path, monkeypatch, value):
    monkeypatch.setenv(logging_setup.LOG_ENV, value)

    assert logging_setup.configure_logging(str(tmp_path)) is False
    assert os.listdir(tmp_path) == []


def test_enabled_writes_the_record_to_the_log_file(tmp_path, monkeypatch):
    monkeypatch.setenv(logging_setup.LOG_ENV, "1")

    assert logging_setup.configure_logging(str(tmp_path)) is True
    logging_setup.get_logger("snatch.probe").warning("teardown failed")

    log_path = tmp_path / logging_setup.LOG_FILENAME
    assert log_path.is_file()
    assert "teardown failed" in log_path.read_text(encoding="utf-8")


def test_named_level_is_honoured(tmp_path, monkeypatch):
    monkeypatch.setenv(logging_setup.LOG_ENV, "warning")

    logging_setup.configure_logging(str(tmp_path))
    log = logging_setup.get_logger("snatch.probe")
    log.debug("below the bar")
    log.warning("at the bar")

    text = (tmp_path / logging_setup.LOG_FILENAME).read_text(encoding="utf-8")
    assert "below the bar" not in text
    assert "at the bar" in text


def test_unrecognised_truthy_value_falls_back_to_debug(tmp_path, monkeypatch):
    monkeypatch.setenv(logging_setup.LOG_ENV, "yes-please")

    logging_setup.configure_logging(str(tmp_path))
    logging_setup.get_logger("snatch.probe").debug("verbose detail")

    text = (tmp_path / logging_setup.LOG_FILENAME).read_text(encoding="utf-8")
    assert "verbose detail" in text


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits are not the access control on Windows")
def test_log_file_is_owner_only(tmp_path, monkeypatch):
    monkeypatch.setenv(logging_setup.LOG_ENV, "1")

    logging_setup.configure_logging(str(tmp_path))
    logging_setup.get_logger("snatch.probe").warning("anything")

    mode = os.stat(tmp_path / logging_setup.LOG_FILENAME).st_mode
    assert stat.S_IMODE(mode) == 0o600


def test_configure_is_idempotent(tmp_path, monkeypatch):
    """A second call must not stack a second handler and double every line."""
    monkeypatch.setenv(logging_setup.LOG_ENV, "1")

    logging_setup.configure_logging(str(tmp_path))
    logging_setup.configure_logging(str(tmp_path))
    logging_setup.get_logger("snatch.probe").warning("once")

    text = (tmp_path / logging_setup.LOG_FILENAME).read_text(encoding="utf-8")
    assert text.count("once") == 1


def test_unwritable_directory_does_not_raise(tmp_path, monkeypatch):
    """Logging is a diagnostic; it must never be the reason the app fails to start."""
    monkeypatch.setenv(logging_setup.LOG_ENV, "1")

    assert logging_setup.configure_logging(str(tmp_path / "does" / "not" / "exist")) is False
