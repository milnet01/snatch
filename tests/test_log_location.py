"""The app can say where its diagnostic log is (SNAT-0022).

Logging is off unless SNATCH_LOG is set, and even when on the file stays
absent until something is written. So the description must treat "off" and
"nothing yet" as ordinary states, never as faults, and offer to open a
folder only when there is one to open.
"""

import logging

import pytest

from snatch import logging_setup
from snatch.logging_setup import describe_log, log_path


@pytest.fixture(autouse=True)
def _no_handlers():
    """Each test starts and ends with logging off."""
    logger = logging.getLogger(logging_setup.LOGGER_NAME)
    saved = list(logger.handlers)
    for h in saved:
        logger.removeHandler(h)
    yield
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    for h in saved:
        logger.addHandler(h)


def test_off_says_how_to_turn_it_on(tmp_path, monkeypatch):
    monkeypatch.delenv(logging_setup.LOG_ENV, raising=False)

    text, folder = describe_log(str(tmp_path))

    assert "off" in text.lower()
    assert logging_setup.LOG_ENV in text
    assert log_path(str(tmp_path)) in text
    assert folder is None


def test_on_but_empty_is_not_a_fault(tmp_path, monkeypatch):
    monkeypatch.setenv(logging_setup.LOG_ENV, "warning")
    assert logging_setup.configure_logging(str(tmp_path))

    text, folder = describe_log(str(tmp_path))

    assert log_path(str(tmp_path)) in text
    assert "error" not in text.lower()
    assert folder == str(tmp_path)


def test_on_with_a_file_offers_its_folder(tmp_path, monkeypatch):
    monkeypatch.setenv(logging_setup.LOG_ENV, "1")
    assert logging_setup.configure_logging(str(tmp_path))
    logging_setup.get_logger("snatch.test").warning("something went wrong")

    text, folder = describe_log(str(tmp_path))

    assert log_path(str(tmp_path)) in text
    assert folder == str(tmp_path)
