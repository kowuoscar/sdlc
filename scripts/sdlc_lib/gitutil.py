"""Thin wrapper around the ``git`` CLI for test_guard.py."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Tuple


class GitError(Exception):
    """kind is one of: 'not-a-repo', 'unknown-ref', 'other'."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def _run(repo: Path, args: List[str], timeout: int = 60) -> str:
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=str(repo),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise GitError("other", "git executable not found")
    except subprocess.TimeoutExpired:
        raise GitError("other", "git %s timed out" % " ".join(args))
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace")
        if _looks_like_not_a_repo(stderr):
            raise GitError("not-a-repo", stderr.strip())
        if _looks_like_unknown_ref(stderr):
            raise GitError("unknown-ref", stderr.strip())
        raise GitError("other", stderr.strip() or "git %s failed" % " ".join(args))
    return proc.stdout.decode("utf-8", "replace")


def _looks_like_not_a_repo(stderr: str) -> bool:
    return "not a git repository" in stderr.lower()


def _looks_like_unknown_ref(stderr: str) -> bool:
    s = stderr.lower()
    return (
        "unknown revision" in s
        or "bad revision" in s
        or "ambiguous argument" in s
        or "not a valid object name" in s
        or "invalid merge base" in s
        or "no merge base" in s
    )


def check_repo(repo: Path) -> None:
    _run(repo, ["rev-parse", "--git-dir"])


def name_status(repo: Path, base: str, head: str) -> List[Tuple[str, List[str]]]:
    out = _run(repo, ["diff", "--name-status", "-M", "%s...%s" % (base, head)])
    entries: List[Tuple[str, List[str]]] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        entries.append((parts[0], parts[1:]))
    return entries


def diff_patch(repo: Path, base: str, head: str) -> str:
    return _run(repo, ["diff", "%s...%s" % (base, head)])
