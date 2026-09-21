#!/usr/bin/env python3
"""CLI wrapper for check_harness.py -- see sdlc_lib/checks_harness.py for the
logic and docs/contracts.md section 13 for the contract."""
from __future__ import annotations

import sys
from pathlib import Path

from sdlc_lib.checks_harness import check_harness
from sdlc_lib.cli import ArgError, make_parser
from sdlc_lib.config import load_config
from sdlc_lib.result import Result, emit


def main(argv=None) -> int:
    parser = make_parser(
        "sdlc-check-harness",
        "Check the root map, ARCHITECTURE.md, docs/agents/ and docs/tech-debt.md against reality.",
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
        config = load_config(repo, result, required=True)
        if config is not None:
            check_harness(repo, config, result)
    except Exception as exc:  # noqa: BLE001
        result = Result()
        result.fail_fatal("internal-error", "unexpected error: %s" % exc)
    return emit(result)


if __name__ == "__main__":
    sys.exit(main())
