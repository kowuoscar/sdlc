#!/usr/bin/env python3
"""CLI wrapper for check_tickets.py -- see sdlc_lib/checks_tickets.py for the
logic and docs/contracts.md section 13 for the contract."""
from __future__ import annotations

import sys
from pathlib import Path

from sdlc_lib.checks_tickets import check_tickets
from sdlc_lib.cli import ArgError, make_parser
from sdlc_lib.result import Result, emit


def main(argv=None) -> int:
    parser = make_parser("sdlc-check-tickets", "Mechanical half of the ticket critic for one feature.")
    parser.add_argument("feature", help="feature slug")
    try:
        args = parser.parse_args(argv)
    except ArgError as exc:
        result = Result()
        result.fail_fatal("usage-error", str(exc))
        return emit(result)

    repo = Path(args.repo).resolve()
    result = Result()
    try:
        check_tickets(repo, args.feature, result)
    except Exception as exc:  # noqa: BLE001
        result = Result()
        result.fail_fatal("internal-error", "unexpected error: %s" % exc)
    return emit(result)


if __name__ == "__main__":
    sys.exit(main())
