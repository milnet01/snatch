"""Diagnostic logging — off unless asked for, owner-only when on.

SNAT-0045: the app imported no logging module anywhere, so every
`except Exception: pass` site had nothing to record to and ruff's own
suggestion ("consider logging the exception") could not be followed. The
handlers were individually defensible -- best-effort cleanup, optional
feature paths -- but collectively they meant a failure that showed no
dialog left no trace at all.

Off by default is the whole point: the item required no change to anything
a user sees. Unconfigured, the package logger holds a NullHandler and every
call site costs a discarded record. Set SNATCH_LOG to turn it on.

    SNATCH_LOG=1 python3 snatch.py        # everything, DEBUG and up
    SNATCH_LOG=warning python3 snatch.py  # only what went wrong

The file lands beside config.json and history.json in app_data_dir(), at
0o600 like them -- it carries the URLs being downloaded and the text of
whatever failed, which is the same class of user data. It rotates, because
a log a user forgets they enabled must not grow without bound.
"""

import contextlib
import logging
import logging.handlers
import os

# Environment variable that enables logging, and the values that do not.
LOG_ENV = "SNATCH_LOG"
_OFF_VALUES = frozenset({"", "0", "false", "off", "no"})

LOGGER_NAME = "snatch"
LOG_FILENAME = "snatch.log"

# One megabyte per file, two old files kept: enough to cover a session that
# went wrong, bounded enough to leave behind unattended.
MAX_LOG_BYTES = 1024 * 1024
LOG_BACKUP_COUNT = 2

PRIVATE_MODE = 0o600

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# Silence by default. Without this, Python's last-resort handler prints
# WARNING and above to stderr, which is a user-visible change on the
# terminal and a write to a stream a frozen GUI build may not have.
logging.getLogger(LOGGER_NAME).addHandler(logging.NullHandler())


class _PrivateRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """RotatingFileHandler that keeps every file it opens owner-only.

    The mode has to be applied on each open rather than once at setup: a
    rollover creates a fresh file, and that one would otherwise be born at
    whatever the umask allows.
    """

    def _open(self):
        stream = super()._open()
        # Nowhere to report this to -- we are the reporting mechanism, and a
        # log whose permissions could not be tightened is still better than
        # an app that would not start. Windows reaches here too, where mode
        # bits are not the access control.
        with contextlib.suppress(OSError):
            os.chmod(self.baseFilename, PRIVATE_MODE)
        return stream


def _resolve_level(raw):
    """Map the environment value to a level, or None for "stay off"."""
    if raw is None:
        return None
    value = raw.strip()
    if value.lower() in _OFF_VALUES:
        return None
    named = logging.getLevelName(value.upper())
    # getLevelName returns the string "Level FOO" for anything it does not
    # know, so a truthy value that is not a level name means "on, verbose".
    return named if isinstance(named, int) else logging.DEBUG


def configure_logging(data_dir):
    """Install the log file handler if SNATCH_LOG asks for it.

    Returns True when logging is on. Never raises: a diagnostic must not be
    the reason the app fails to start, so an unwritable directory turns
    logging off rather than propagating.
    """
    level = _resolve_level(os.environ.get(LOG_ENV))
    if level is None:
        return False

    logger = logging.getLogger(LOGGER_NAME)
    if any(isinstance(h, _PrivateRotatingFileHandler) for h in logger.handlers):
        # Already configured. Stacking a second handler would double every
        # line rather than add anything.
        return True

    try:
        handler = _PrivateRotatingFileHandler(
            os.path.join(data_dir, LOG_FILENAME),
            maxBytes=MAX_LOG_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
    except OSError:
        return False

    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(level)
    return True


def get_logger(name):
    """The module logger for `name` -- call as get_logger(__name__)."""
    return logging.getLogger(name)
