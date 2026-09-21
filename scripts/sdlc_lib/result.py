"""Diagnostic / result model shared by every sdlc script.

Every script prints exactly one JSON document on stdout, shaped as
``{"ok": bool, ...extra fields..., "errors": [...], "warnings": [...]}``.
Each diagnostic entry is ``{"code": str, "path": str, "message": str}``.

Exit codes:

- 0: ``ok`` is true.
- 1: ``ok`` is false because a check genuinely failed (errors present, but
  the input itself was well-formed enough to evaluate).
- 2: the input could not be evaluated at all (malformed config, bad CLI
  usage, a referenced file that is not parseable, an internal bug caught
  before it could turn into a traceback). ``Result.fatal`` drives this.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List


class Diagnostic:
    __slots__ = ("code", "message", "path")

    def __init__(self, code: str, message: str, path: str = "") -> None:
        self.code = code
        self.message = message
        self.path = path

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class Result:
    """Accumulates diagnostics and extra output fields for one script run."""

    def __init__(self) -> None:
        self.errors: List[Diagnostic] = []
        self.warnings: List[Diagnostic] = []
        self.extra: Dict[str, Any] = {}
        self.fatal: bool = False

    def error(self, code: str, message: str, path: str = "") -> None:
        self.errors.append(Diagnostic(code, message, path))

    def warning(self, code: str, message: str, path: str = "") -> None:
        self.warnings.append(Diagnostic(code, message, path))

    def fail_fatal(self, code: str, message: str, path: str = "") -> None:
        """Record an error that also means the input could not be evaluated
        at all (drives exit code 2 instead of 1)."""
        self.error(code, message, path)
        self.fatal = True

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def set(self, key: str, value: Any) -> None:
        self.extra[key] = value

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"ok": self.ok}
        d.update(self.extra)
        d["errors"] = [e.to_dict() for e in self.errors]
        d["warnings"] = [w.to_dict() for w in self.warnings]
        return d

    def exit_code(self) -> int:
        if self.fatal:
            return 2
        return 0 if self.ok else 1


def emit(result: Result, stdout=None, stderr=None) -> int:
    """Print the JSON document and human diagnostics, return the exit code."""
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    payload = result.to_dict()
    out.write(json.dumps(payload, indent=2, sort_keys=True))
    out.write("\n")
    for d in result.errors:
        _print_diag(err, "error", d)
    for d in result.warnings:
        _print_diag(err, "warning", d)
    return result.exit_code()


def _print_diag(stream, level: str, d: Diagnostic) -> None:
    loc = " " + d.path if d.path else ""
    stream.write("%s: %s:%s %s\n" % (level, d.code, loc, d.message))
