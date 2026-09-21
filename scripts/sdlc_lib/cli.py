"""Argparse plumbing shared by every script's ``main()``.

Scripts must always print a JSON document, even on a usage error, so we
never let argparse call ``sys.exit()`` directly on a parse error -- we turn
it into a normal fatal ``Result`` instead.
"""
from __future__ import annotations

import argparse
from typing import List, Optional, Sequence


class ArgError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise ArgError(message)


def make_parser(prog: str, description: str = "") -> Parser:
    parser = Parser(prog=prog, description=description)
    parser.add_argument(
        "--repo",
        default=".",
        help="path to the target repository (default: current directory)",
    )
    return parser


def parse_args(parser: Parser, argv: Optional[Sequence[str]]) -> List[str]:
    return parser.parse_args(argv)
