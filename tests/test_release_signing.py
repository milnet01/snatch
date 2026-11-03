"""The release key stays private, and nothing unverifiable is published
(SNAT-0038 INV-14).

sign-release.py runs on the maintainer's PC against a real GitHub release, so
here `gh` is replaced by a recorder on PATH that serves a valid draft and
writes down every call it gets.
"""

import hashlib
import importlib.util
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "sign-release.py"
PRIVATE_KEY = re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
GIT_TIMEOUT_SEC = 30
SIGN_TIMEOUT_SEC = 60

FAKE_GH = textwrap.dedent("""\
    #!/usr/bin/env python3
    import fnmatch, os, shutil, sys
    with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as log:
        log.write(" ".join(sys.argv[1:]) + "\\n")
    args = sys.argv[1:]
    if args[:2] == ["release", "download"]:
        patterns = [args[i + 1] for i, a in enumerate(args) if a == "--pattern"]
        out = args[args.index("--dir") + 1]
        os.makedirs(out, exist_ok=True)
        assets = os.environ["FAKE_GH_ASSETS"]
        for name in os.listdir(assets):
            if any(fnmatch.fnmatch(name, p) for p in patterns):
                shutil.copy(os.path.join(assets, name), out)
    elif args[:2] == ["release", "upload"]:
        for path in args[3:args.index("--repo")]:
            if not path.startswith("--"):
                shutil.copy(path, os.environ["FAKE_GH_ASSETS"])
    """)


def _tracked_files():
    """Every tracked file, or every file present where git cannot answer.

    The pre-push gate runs the suite in a container over a fresh worktree,
    whose .git points at a repository the container cannot see, so `git
    ls-files` exits 128 there. Every file present is a superset of the
    tracked ones, so the fallback is stricter, never weaker.
    """
    try:
        listed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                                check=True, capture_output=True,
                                timeout=GIT_TIMEOUT_SEC)
    except (OSError, subprocess.CalledProcessError):
        return [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                if ".git" not in p.relative_to(ROOT).parts]
    return [name for name in listed.stdout.decode().split("\0") if name]


def test_no_private_key_is_tracked():
    leaks = []
    for name in _tracked_files():
        path = ROOT / name
        if path.is_file() and PRIVATE_KEY.search(path.read_bytes()):
            leaks.append(name)
    assert leaks == []


def _draft(folder):
    """The three platform assets and a SHA256SUMS that matches them."""
    folder.mkdir()
    sums = []
    for name in ("Snatch-x86_64.AppImage", "snatch.exe", "Snatch-arm64.dmg"):
        body = f"build of {name}".encode()
        (folder / name).write_bytes(body)
        sums.append(f"{hashlib.sha256(body).hexdigest()}  {name}\n")
    (folder / "SHA256SUMS").write_text("".join(sums), encoding="ascii")


def _setup(tmp_path):
    """A key file, a draft, and the fake gh; returns (key, env, log)."""
    key = Ed25519PrivateKey.generate()
    key_file = tmp_path / "signing.key"
    key_file.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    key_file.chmod(0o600)
    _draft(tmp_path / "assets")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH, encoding="utf-8")
    gh.chmod(0o755)
    log = tmp_path / "gh.log"
    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
           "SNATCH_SIGNING_KEY": str(key_file),
           "FAKE_GH_LOG": str(log),
           "FAKE_GH_ASSETS": str(tmp_path / "assets")}
    return key, env, log


def test_sign_refuses_a_key_that_does_not_match(tmp_path):
    _foreign, env, log = _setup(tmp_path)
    env = dict(os.environ, **env)
    done = subprocess.run([sys.executable, str(SCRIPT), "v1.4.0"], env=env,
                          check=False,
                          capture_output=True, text=True,
                          timeout=SIGN_TIMEOUT_SEC)

    calls = log.read_text(encoding="utf-8").splitlines()
    assert done.returncode != 0, done.stdout + done.stderr
    assert any(c.startswith("release download") for c in calls), calls
    assert not [c for c in calls
                if c.startswith(("release upload", "release edit"))]
    assert "does not match the public key committed" in done.stderr


def test_sign_publishes_a_manifest_the_app_accepts(tmp_path, monkeypatch):
    key, env, log = _setup(tmp_path)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    spec = importlib.util.spec_from_file_location("sign_release", SCRIPT)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    monkeypatch.setattr(script, "public_key", key.public_key)
    monkeypatch.setattr(script.sys, "argv", ["sign-release.py", "v1.4.0"])

    script.main()

    assets = tmp_path / "assets"
    manifest = (assets / "SNATCH-UPDATE").read_bytes()
    key.public_key().verify((assets / "SNATCH-UPDATE.sig").read_bytes(),
                            manifest)
    version, digests = script.parse_manifest(manifest)
    assert version == "1.4.0"
    assert digests["snatch.exe"] == hashlib.sha256(
        (assets / "snatch.exe").read_bytes()).hexdigest()
    calls = log.read_text(encoding="utf-8").splitlines()
    assert [c.split()[1] for c in calls] == [
        "download", "download", "upload", "edit", "download"]
    assert "--draft=false" in calls[3]
