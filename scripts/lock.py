#!/usr/bin/env python3
"""CLI wrapper for lock.py -- see sdlc_lib/checks_lock.py for the logic and
docs/contracts.md sections 12 and 13 for the contract."""
from __future__ import annotations

import sys
from pathlib import Path

from sdlc_lib.checks_lock import acquire, release, status
from sdlc_lib.cli import ArgError, make_parser
from sdlc_lib.result import Result, emit


def main(argv=None) -> int:
    parser = make_parser("sdlc-lock", "Acquire, release or report the session lease.")
    parser.add_argument("action", choices=["acquire", "release", "status"])
    parser.add_argument("--session", default="", help="session token")
    parser.add_argument(
        "--force", action="store_true", help="acquire or release even if held by another session"
    )
    try:
        args = parser.parse_args(argv)
    except ArgError as exc:
        result = Result()
        result.fail_fatal("usage-error", str(exc))
        return emit(result)

    repo = Path(args.repo).resolve()
    result = Result()
    try:
        if args.action == "acquire":
            acquire(repo, args.session, result, force=args.force)
        elif args.action == "release":
            release(repo, args.session, result, force=args.force)
        else:
            status(repo, result)
    except Exception as exc:  # noqa: BLE001
        result = Result()
        result.fail_fatal("internal-error", "unexpected error: %s" % exc)
    return emit(result)


if __name__ == "__main__":
    sys.exit(main())
