"""Browser cookie extraction and management"""

import os
import shutil
import sqlite3
import tempfile
import configparser

from .utils import atomic_private_write
from .logging_setup import get_logger

log = get_logger(__name__)


def find_firefox_cookies_db():
    """Find Firefox's cookies.sqlite by reading profiles.ini"""
    for base in ["~/.mozilla/firefox", "~/.config/mozilla/firefox"]:
        profiles_ini = os.path.expanduser(os.path.join(base, "profiles.ini"))
        if not os.path.isfile(profiles_ini):
            continue
        base_expanded = os.path.expanduser(base)
        config = configparser.ConfigParser()
        config.read(profiles_ini)

        # Check [Install*] sections first — this is the actively used profile
        for section in config.sections():
            if section.startswith("Install"):
                path = config.get(section, "Default", fallback="")
                if path:
                    db = os.path.join(base_expanded, path, "cookies.sqlite")
                    if os.path.isfile(db):
                        return db

        # Then check [Profile*] sections with Default=1
        for section in config.sections():
            if not section.startswith("Profile"):
                continue
            if config.get(section, "Default", fallback="0") != "1":
                continue
            path = config.get(section, "Path", fallback="")
            is_relative = config.get(section, "IsRelative", fallback="1") == "1"
            if is_relative:
                profile_dir = os.path.join(base_expanded, path)
            else:
                profile_dir = path
            db = os.path.join(profile_dir, "cookies.sqlite")
            if os.path.isfile(db):
                return db

        # Fallback: find any profile with cookies.sqlite
        if os.path.isdir(base_expanded):
            for entry in os.listdir(base_expanded):
                db = os.path.join(base_expanded, entry, "cookies.sqlite")
                if os.path.isfile(db):
                    return db
    return None


def extract_browser_cookies(browser, cookies_out):
    """Extract cookies from browser's DB and save as cookies.txt.
    Returns the output path on success, or None on failure.
    """
    if not browser or browser == "none":
        return None

    if browser == "firefox":
        db_path = find_firefox_cookies_db()
        if not db_path:
            return None
        try:
            # Copy the database files to avoid lock issues with running browser
            # Use restrictive permissions on temp copies (contain sensitive cookies)
            with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                shutil.copy2(db_path, tmp_path)
                os.chmod(tmp_path, 0o600)
                for ext in ["-wal", "-shm"]:
                    src_file = db_path + ext
                    if os.path.isfile(src_file):
                        shutil.copy2(src_file, tmp_path + ext)
                        os.chmod(tmp_path + ext, 0o600)

                # Read cookies from the copy
                conn = sqlite3.connect(tmp_path)
                cursor = conn.execute(
                    "SELECT host, name, value, path, expiry, isSecure, isHttpOnly "
                    "FROM moz_cookies WHERE host LIKE '%youtube.com' "
                    "OR host LIKE '%google.com'"
                )
                rows = cursor.fetchall()
                conn.close()

                if not rows:
                    return None

                # Netscape cookie format, owner-only and written atomically.
                # A plain os.open(..., O_CREAT, 0o600) would leave an existing
                # cookies.txt on whatever mode it already had.
                with atomic_private_write(cookies_out) as f:
                    f.write("# Netscape HTTP Cookie File\n")
                    f.write("# Extracted from Firefox by Snatch\n\n")
                    for host, name, value, path, expiry, secure, _httponly in rows:
                        domain_flag = "TRUE" if host.startswith(".") else "FALSE"
                        secure_flag = "TRUE" if secure else "FALSE"
                        f.write(f"{host}\t{domain_flag}\t{path}\t{secure_flag}\t{expiry}\t{name}\t{value}\n")

                return cookies_out
            finally:
                os.unlink(tmp_path)
                for ext in ["-wal", "-shm"]:
                    p = tmp_path + ext
                    if os.path.isfile(p):
                        os.unlink(p)
        except Exception:
            # Was a print(), which reaches nobody in a windowed build and can
            # itself raise when there is no stdout to write to.
            log.warning("Cookie extraction failed", exc_info=True)
            return None
    else:
        # For non-Firefox browsers, fall back to yt-dlp's --cookies-from-browser
        return None


def get_cookie_args(cookies_file, browser):
    """Get the appropriate cookie arguments for yt-dlp."""
    # Prefer yt-dlp's built-in browser cookie handling — it decrypts properly
    if browser and browser != "none":
        return ["--cookies-from-browser", browser]

    if cookies_file and os.path.isfile(cookies_file):
        return ["--cookies", cookies_file]
    return []
