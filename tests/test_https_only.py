"""Every app-side network fetch goes through version._open_https.

SNAT-0074. urllib follows redirects and permits an https -> http downgrade,
so a startswith("https://") check on the URL asserts what was asked for, not
what arrived. _open_https checks resp.geturl() as well (STANDARDS.md 5.2).
The thumbnail fetch and the GitHub release check each called urlopen
directly and skipped that second check.

Asserted structurally, over every module, so a new fetch written the old way
fails here rather than waiting for a review to notice it.
"""

import ast
import pathlib

import pytest

from snatch import version

PACKAGE = pathlib.Path(__file__).resolve().parent.parent / "snatch"


def _urlopen_callers():
    for path in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for node in ast.walk(func):
                if (isinstance(node, ast.Call)
                        and ast.unparse(node.func).endswith("urlopen")):
                    yield f"{path.relative_to(PACKAGE.parent)}:{func.name}"


def test_only_open_https_calls_urlopen():
    assert sorted(set(_urlopen_callers())) == ["snatch/version.py:_open_https"]


def test_a_redirect_off_https_is_refused(monkeypatch):
    class _Downgraded:
        closed = False

        def geturl(self):
            return "http://example.com/thumb.jpg"

        def close(self):
            self.closed = True

    resp = _Downgraded()
    monkeypatch.setattr(version.urllib.request, "urlopen", lambda *a, **k: resp)

    with pytest.raises(ValueError):
        version._open_https("https://example.com/thumb.jpg", 5)
    assert resp.closed
