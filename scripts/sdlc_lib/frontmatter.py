"""Parser for the minimal frontmatter dialect defined in contracts.md section 1.

Only this subset of YAML is allowed:

- ``key: scalar`` -- string, integer, ``true``/``false``. Surrounding single
  or double quotes are optional and are stripped.
- ``key: [a, b, c]`` -- inline list of scalars. ``[]`` is the empty list.
- ``key:`` with nothing after the colon is the empty string.
- No nesting, no multi-line values, no block lists, no comments. Blank lines
  inside the block are tolerated. A duplicate key is malformed.

Keys are expected to be lower-case snake_case by convention, but this parser
does not enforce key naming -- callers that know the expected schema for a
given file validate individual keys themselves.
"""
from __future__ import annotations

import re
from typing import Any, List, Tuple

_KEY_LINE_RE = re.compile(r"^([A-Za-z0-9_]+):(.*)$")
_INT_RE = re.compile(r"^-?\d+$")
_BLOCK_SCALAR_RE = re.compile(r"^[|>][+-]?\d*$")
_BOOL = {"true": True, "false": False}


class FrontmatterError(Exception):
    """Raised when a frontmatter block is present but malformed."""


def parse_frontmatter(text: str) -> Tuple[dict, str]:
    """Parse a leading frontmatter block.

    Returns ``(data, body)``. If ``text`` does not begin with a ``---``
    delimiter line, there is no frontmatter block at all: returns
    ``({}, text)`` unchanged -- it is up to the caller to decide whether a
    frontmatter block was required for this kind of file.

    Raises ``FrontmatterError`` if a block is opened (starts with ``---``)
    but is malformed or never closed.
    """
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        return {}, text

    data: dict = {}
    i = 1
    closed = False
    while i < len(lines):
        raw_line = lines[i].rstrip("\r")
        if raw_line == "---":
            closed = True
            i += 1
            break
        if raw_line.strip() == "":
            i += 1
            continue
        if raw_line[:1] in (" ", "\t"):
            raise FrontmatterError(
                "line %d: indented line inside frontmatter is not allowed "
                "(no nesting, no multi-line values): %r" % (i + 1, raw_line)
            )
        if raw_line.lstrip().startswith("-"):
            raise FrontmatterError(
                "line %d: block-list syntax is not allowed: %r" % (i + 1, raw_line)
            )
        m = _KEY_LINE_RE.match(raw_line)
        if not m:
            raise FrontmatterError(
                "line %d: malformed frontmatter line (expected 'key: value'): %r"
                % (i + 1, raw_line)
            )
        key = m.group(1)
        raw_val = m.group(2).strip()
        if key in data:
            raise FrontmatterError("line %d: duplicate key %r" % (i + 1, key))
        data[key] = _parse_value(raw_val, key, i + 1)
        i += 1

    if not closed:
        raise FrontmatterError("unterminated frontmatter block (missing closing '---')")

    body = "\n".join(lines[i:])
    return data, body


def _parse_value(raw: str, key: str, lineno: int) -> Any:
    if raw == "":
        return ""
    if _BLOCK_SCALAR_RE.match(raw):
        raise FrontmatterError(
            "line %d: multi-line block scalars are not allowed for key %r"
            % (lineno, key)
        )
    if raw.startswith("["):
        if not raw.endswith("]"):
            raise FrontmatterError(
                "line %d: malformed list value for key %r: %r" % (lineno, key, raw)
            )
        inner = raw[1:-1].strip()
        if inner == "":
            return []
        return [_parse_scalar(part.strip()) for part in _split_list(inner)]
    return _parse_scalar(raw)


def _split_list(inner: str) -> List[str]:
    parts: List[str] = []
    cur: List[str] = []
    in_quote = ""
    for ch in inner:
        if in_quote:
            cur.append(ch)
            if ch == in_quote:
                in_quote = ""
        elif ch in ("'", '"'):
            in_quote = ch
            cur.append(ch)
        elif ch == ",":
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def _parse_scalar(raw: str) -> Any:
    if raw in _BOOL:
        return _BOOL[raw]
    if _INT_RE.match(raw):
        return int(raw)
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        return raw[1:-1]
    return raw
