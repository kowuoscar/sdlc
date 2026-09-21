"""Implements ``test_guard.py`` (contracts.md section 13).

Diagnostic codes produced here:

Fatal errors (exit 2):
    not-a-git-repo      --repo is not inside a git repository
    unknown-ref         base or head does not resolve to a commit
    test-guard-git-error  any other git failure

Errors (exit 1 when present -- "ok is false when anything is reported"):
    test-modified        an existing test file (matches test_globs, present
                          at base) was modified
    test-deleted          "                                    " was deleted
    test-renamed          "                                    " was renamed
    skip-marker-added    a '+' line in the diff adds a skip marker
"""
from __future__ import annotations

import re
from pathlib import Path

from . import gitutil
from .globs import matches_any_glob
from .result import Result

# contracts.md section 13. Whitespace around '.' and before '(' is ignored,
# so each marker is compiled as a small regex rather than matched as a
# plain substring.
_SKIP_MARKER_SOURCES = (
    (".skip(", r"\.\s*skip\s*\("),
    (".only(", r"\.\s*only\s*\("),
    (".todo(", r"\.\s*todo\s*\("),
    ("xit(", r"xit\s*\("),
    ("xtest(", r"xtest\s*\("),
    ("xdescribe(", r"xdescribe\s*\("),
    ("@Disabled", r"@Disabled"),
    (".Disabled", r"\.\s*Disabled"),
    ("@Ignore", r"@Ignore"),
    ("enabled = false", r"enabled\s*=\s*false"),
    ("t.Skip(", r"t\.\s*Skip\s*\("),
    ("t.Skipf(", r"t\.\s*Skipf\s*\("),
    ("t.SkipNow(", r"t\.\s*SkipNow\s*\("),
    ("@pytest.mark.skip", r"@pytest\.\s*mark\.\s*skip"),
    ("pytest.skip(", r"pytest\.\s*skip\s*\("),
    ("@unittest.skip", r"@unittest\.\s*skip"),
)
SKIP_MARKERS = tuple(
    (label, re.compile(pattern)) for label, pattern in _SKIP_MARKER_SOURCES
)


def check_test_guard(repo: Path, base: str, head: str, config: dict, result: Result) -> None:
    try:
        gitutil.check_repo(repo)
    except gitutil.GitError as exc:
        code = "not-a-git-repo" if exc.kind == "not-a-repo" else "test-guard-git-error"
        result.fail_fatal(code, str(exc))
        return

    test_globs = config.get("test_globs", [])

    try:
        entries = gitutil.name_status(repo, base, head)
    except gitutil.GitError as exc:
        code = "unknown-ref" if exc.kind == "unknown-ref" else "test-guard-git-error"
        result.fail_fatal(code, str(exc))
        return

    for status, paths in entries:
        if status.startswith("R"):
            if len(paths) < 2:
                continue
            old, new = paths[0], paths[1]
            if matches_any_glob(old, test_globs):
                result.error(
                    "test-renamed", "test file %s was renamed to %s" % (old, new), old
                )
        elif status == "M":
            path = paths[0] if paths else ""
            if path and matches_any_glob(path, test_globs):
                result.error("test-modified", "test file %s was modified" % path, path)
        elif status == "D":
            path = paths[0] if paths else ""
            if path and matches_any_glob(path, test_globs):
                result.error("test-deleted", "test file %s was deleted" % path, path)
        # 'A' (added), 'C' (copied) and other statuses are not reported.

    try:
        patch = gitutil.diff_patch(repo, base, head)
    except gitutil.GitError as exc:
        code = "unknown-ref" if exc.kind == "unknown-ref" else "test-guard-git-error"
        result.fail_fatal(code, str(exc))
        return

    current_path = None
    reported = set()
    for line in patch.split("\n"):
        if line.startswith("+++ "):
            p = line[4:]
            if p.startswith("b/"):
                p = p[2:]
            current_path = None if p == "/dev/null" else p
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:]
        for label, pattern in SKIP_MARKERS:
            if pattern.search(content):
                key = (current_path, content)
                if key not in reported:
                    reported.add(key)
                    result.error(
                        "skip-marker-added",
                        "added line with skip marker %r in %s" % (label, current_path or "?"),
                        current_path or "",
                    )
                break
