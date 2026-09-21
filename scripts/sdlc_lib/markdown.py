"""Generic markdown helpers: level-2 section extraction, numbered lists,
checkbox lines and backticked-token extraction.

These are deliberately generic (contract-format-agnostic); the modules that
know about a specific file format (spec.md, ticket files, roadmap epics)
build on top of them.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_H1_RE = re.compile(r"^#\s+(.+?)\s*$")
_NUM_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")
_CHECKBOX_RE = re.compile(r"^-\s*\[([ xX])\]\s*(.*)$")
_BACKTICK_RE = re.compile(r"`([^`\n]+)`")


def extract_level2_sections(text: str) -> Dict[str, str]:
    """Split ``text`` into level-2 (``## Heading``) sections.

    Returns a dict of heading text -> section body (stripped). A level-1
    heading also closes whatever level-2 section is open (content before the
    first level-2 heading, and content directly under a level-1 heading, is
    not attached to any section). If the same level-2 heading appears more
    than once, the later occurrence's lines are appended to the earlier
    ones (sections are not silently overwritten or ignored).
    """
    sections: Dict[str, List[str]] = {}
    order: List[str] = []
    current = None
    for line in text.split("\n"):
        m2 = _H2_RE.match(line)
        if m2:
            current = m2.group(1)
            if current not in sections:
                sections[current] = []
                order.append(current)
            continue
        if _H1_RE.match(line):
            current = None
            continue
        if current is not None:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def parse_numbered_list(text: str) -> List[Tuple[int, str]]:
    """Return ``(number, rest-of-line)`` for every numbered-list line."""
    items: List[Tuple[int, str]] = []
    for line in text.split("\n"):
        m = _NUM_RE.match(line)
        if m:
            items.append((int(m.group(1)), m.group(2).strip()))
    return items


def parse_checkbox_lines(text: str) -> List[Tuple[bool, str]]:
    """Return ``(checked, rest-of-line)`` for every ``- [ ]``/``- [x]`` line."""
    items: List[Tuple[bool, str]] = []
    for line in text.split("\n"):
        m = _CHECKBOX_RE.match(line)
        if m:
            items.append((m.group(1).lower() == "x", m.group(2).strip()))
    return items


def extract_backticked(text: str) -> List[str]:
    """Return every backtick-delimited token's inner text, in order."""
    return _BACKTICK_RE.findall(text)
