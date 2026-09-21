"""Implements ``lock.py`` (contracts.md sections 12 and 13).

The lock is a lease, not a pid file: the processes that take it are
short-lived shell calls, so a pid proves nothing. The JSON shape is
``{"session": "<token>", "started": "<ISO-8601 UTC>", "refreshed": "<ISO-8601
UTC>"}``. It is *held* while ``refreshed`` is less than two hours old.

Diagnostic codes produced here:

Fatal errors (exit 2, for ``acquire``/``release``):
    lock-invalid    .sdlc/lock exists but is not a well-formed lease file
                    (bad JSON, not an object, missing/invalid session or
                    timestamps)

Errors (exit 1):
    lock-held       acquire or release by a non-holding session while the
                    lease is held by someone else, without --force

``status`` always exits 0 (per contract): a malformed lock file there is
reported as a warning, not a fatal error.

Rules, from section 12:
- ``acquire`` by the holding session (same non-empty ``session`` token)
  refreshes the lease (``refreshed`` moves, ``started`` is kept).
- ``acquire`` by anyone else fails while the lease is held, unless
  ``--force``.
- An empty token never matches -- two anonymous sessions exclude each other.
- ``release`` succeeds for the holder, or with ``--force``.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .paths import LOCK_DIR, LOCK_FILE
from .result import Result

LEASE_SECONDS = 2 * 60 * 60

Clock = Callable[[], datetime]


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _lock_path(repo: Path) -> Path:
    return repo / LOCK_FILE


def _format_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(ts: str) -> Optional[datetime]:
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _read_lease(repo: Path, result: Result, strict: bool = True) -> Optional[dict]:
    """Read and validate the lease file. On a validation failure, records a
    fatal error (``strict=True``, for acquire/release) or a warning
    (``strict=False``, for status, which must always exit 0) and returns
    ``None``. Returns ``None`` without any diagnostic when the file is
    simply absent."""
    path = _lock_path(repo)
    if not path.is_file():
        return None

    def fail(message: str) -> None:
        if strict:
            result.fail_fatal("lock-invalid", message, LOCK_FILE)
        else:
            result.warning("lock-invalid", message, LOCK_FILE)

    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, ValueError) as exc:
        fail(".sdlc/lock is not valid JSON: %s" % exc)
        return None
    if not isinstance(data, dict):
        fail(".sdlc/lock must contain a JSON object")
        return None

    session = data.get("session")
    if not isinstance(session, str):
        fail(".sdlc/lock is missing a valid 'session'")
        return None
    started = data.get("started")
    if not isinstance(started, str) or _parse_iso(started) is None:
        fail(".sdlc/lock is missing a valid 'started' timestamp")
        return None
    refreshed = data.get("refreshed")
    if not isinstance(refreshed, str) or _parse_iso(refreshed) is None:
        fail(".sdlc/lock is missing a valid 'refreshed' timestamp")
        return None
    return {"session": session, "started": started, "refreshed": refreshed}


def _write_lease(repo: Path, session: str, started: str, refreshed: str) -> dict:
    (repo / LOCK_DIR).mkdir(parents=True, exist_ok=True)
    data = {"session": session, "started": started, "refreshed": refreshed}
    _lock_path(repo).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def _is_held(lease: dict, now: datetime) -> bool:
    refreshed = _parse_iso(lease["refreshed"])
    if refreshed is None:
        return False
    return (now - refreshed).total_seconds() < LEASE_SECONDS


def _report_lease(result: Result, lease: dict, action: str) -> None:
    result.set("session", lease["session"])
    result.set("started", lease["started"])
    result.set("refreshed", lease["refreshed"])
    result.set("action", action)


def acquire(
    repo: Path,
    session: str,
    result: Result,
    force: bool = False,
    clock: Clock = _default_clock,
) -> None:
    session = session or ""
    existing = _read_lease(repo, result)
    if result.fatal:
        return

    now = clock()
    now_iso = _format_iso(now)
    currently_held = existing is not None and _is_held(existing, now)
    is_holder = currently_held and session != "" and existing["session"] == session

    if currently_held and not is_holder and not force:
        result.error(
            "lock-held",
            "lock is held by session %r (refreshed %s)" % (existing["session"], existing["refreshed"]),
            LOCK_FILE,
        )
        result.set("locked", True)
        _report_lease(result, existing, "held-by-other")
        return

    if is_holder:
        started = existing["started"]
        action = "refreshed"
    elif currently_held:
        started = now_iso
        action = "taken-over"
    else:
        started = now_iso
        action = "acquired"

    data = _write_lease(repo, session, started, now_iso)
    result.set("locked", True)
    _report_lease(result, data, action)


def release(
    repo: Path,
    session: str,
    result: Result,
    force: bool = False,
    clock: Clock = _default_clock,
) -> None:
    session = session or ""
    existing = _read_lease(repo, result)
    if result.fatal:
        return

    if existing is None:
        result.set("locked", False)
        result.set("action", "not-held")
        return

    now = clock()
    currently_held = _is_held(existing, now)
    is_holder = currently_held and session != "" and existing["session"] == session

    if currently_held and not is_holder and not force:
        result.error(
            "lock-held",
            "lock is held by session %r (refreshed %s)" % (existing["session"], existing["refreshed"]),
            LOCK_FILE,
        )
        result.set("locked", True)
        _report_lease(result, existing, "held-by-other")
        return

    try:
        _lock_path(repo).unlink()
    except OSError as exc:
        result.fail_fatal("lock-invalid", "could not remove .sdlc/lock: %s" % exc, LOCK_FILE)
        return
    result.set("locked", False)
    result.set("action", "released")


def status(repo: Path, result: Result, clock: Clock = _default_clock) -> None:
    existing = _read_lease(repo, result, strict=False)
    if existing is None:
        result.set("locked", _lock_path(repo).is_file())
        result.set("held", False)
        return
    now = clock()
    held = _is_held(existing, now)
    result.set("locked", True)
    result.set("held", held)
    result.set("session", existing["session"])
    result.set("started", existing["started"])
    result.set("refreshed", existing["refreshed"])
