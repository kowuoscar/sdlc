#!/usr/bin/env python3
"""CLI wrapper for state.py -- see sdlc_lib/checks_state.py for the logic
and docs/contracts.md section 13 for the contract."""
from __future__ import annotations

import sys
from pathlib import Path

from sdlc_lib.checks_state import compute_state
from sdlc_lib.cli import ArgError, make_parser
from sdlc_lib.result import Result, emit


def main(argv=None) -> int:
    parser = make_parser("sdlc-state", "Derive project state and the single next action.")
    try:
        args = parser.parse_args(argv)
    except ArgError as exc:
        result = Result()
        result.fail_fatal("usage-error", str(exc))
        return emit(result)

    repo = Path(args.repo).resolve()
    result = Result()
    try:
        compute_state(repo, result)
    except Exception as exc:  # noqa: BLE001 -- never let a bug become a traceback
        result = Result()
        result.fail_fatal("internal-error", "unexpected error: %s" % exc)
    return emit(result)


if __name__ == "__main__":
    sys.exit(main())
