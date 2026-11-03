"""Every app-side network fetch goes through version._open_https.

SNAT-0074. urllib follows redirects and permits an https -> http downgrade,
so a startswith("https://") check on the URL asserts what was asked for, not
what arrived. _open_https checks resp.geturl() as well (STANDARDS.md 5.2).
The thumbnail fetch and the GitHub release check each called urlopen
directly and skipped that second check.

SNAT-0038: checking the final URL is not enough either. An https -> http ->
https chain ends on HTTPS, but its middle hop was readable and rewritable by
anyone on the path. So _open_https uses its own opener, whose redirect
handler refuses each hop before following it.

Asserted structurally, over every module, so a new fetch written the old way
fails here rather than waiting for a review to notice it.
"""

import ast
import email.message
import io
import pathlib
import urllib.request
import urllib.response

import pytest

from snatch import version

PACKAGE = pathlib.Path(__file__).resolve().parent.parent / "snatch"


def _openers():
    """Every call that opens a URL, as "file:function"."""
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(func):
                if not isinstance(node, ast.Call):
                    continue
                callee = ast.unparse(node.func)
                if callee.endswith(("urlopen", "OPENER.open")):
                    yield f"{path.relative_to(PACKAGE.parent)}:{func.name}", callee


def test_only_open_https_opens_a_url():
    assert sorted(set(_openers())) == [
        ("snatch/version.py:_open_https", "_HTTPS_OPENER.open")]


def test_a_final_url_off_https_is_refused(monkeypatch):
    class _Downgraded:
        closed = False

        def geturl(self):
            return "http://example.com/thumb.jpg"

        def close(self):
            self.closed = True

    resp = _Downgraded()
    monkeypatch.setattr(version._HTTPS_OPENER, "open", lambda *a, **k: resp)

    with pytest.raises(ValueError):
        version._open_https("https://example.com/thumb.jpg", 5)
    assert resp.closed


def _reply(url, code, location=None):
    headers = email.message.Message()
    if location:
        headers["Location"] = location
    resp = urllib.response.addinfourl(io.BytesIO(b"body"), headers, url, code)
    resp.msg = "Found" if location else "OK"
    return resp


def test_a_redirect_hop_off_https_is_refused(monkeypatch):
    plain_hops = []

    def https_open(_handler, req):
        if req.full_url == "https://example.com/start":
            return _reply(req.full_url, 302, "http://example.com/middle")
        return _reply(req.full_url, 200)

    def http_open(_handler, req):
        plain_hops.append(req.full_url)
        return _reply(req.full_url, 302, "https://example.com/end")

    monkeypatch.setattr(urllib.request.HTTPSHandler, "https_open", https_open)
    monkeypatch.setattr(urllib.request.HTTPHandler, "http_open", http_open)

    with pytest.raises(ValueError):
        version._open_https("https://example.com/start", 5)
    assert plain_hops == []
