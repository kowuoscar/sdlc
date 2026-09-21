#!/usr/bin/env python3
"""CLI wrapper for merge_gate.py -- see sdlc_lib/checks_mergegate.py for the
logic and docs/contracts.md section 13 for the contract."""
from __future__ import annotations

import sys
from pathlib import Path

from sdlc_lib.checks_mergegate import check_merge_gate
from sdlc_lib.cli import ArgError, make_parser
from sdlc_lib.result import Result, emit


def main(argv=None) -> int:
    parser = make_parser("sdlc-merge-gate", "The merge verdict for one feature.")
    parser.add_argument("feature", help="feature slug")
    parser.add_argument("--no-verify", action="store_true", help="skip the config verify command")
    try:
        args = parser.parse_args(argv)
    except ArgError as exc:
        result = Result()
        result.fail_fatal("usage-error", str(exc))
        return emit(result)

    repo = Path(args.repo).resolve()
    result = Result()
    try:
        check_merge_gate(repo, args.feature, args.no_verify, result)
    except Exception as exc:  # noqa: BLE001
        result = Result()
        result.fail_fatal("internal-error", "unexpected error: %s" % exc)
    return emit(result)


if __name__ == "__main__":
    sys.exit(main())
