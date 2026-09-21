"""Slug validation shared across epics, features, tickets and inbox items.

contracts.md section 2: kebab-case matching ``^[a-z0-9]+(-[a-z0-9]+)*$`` and
starting with a letter. Never numeric prefixes.
"""
from __future__ import annotations

import re

SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def is_valid_slug(value: str) -> bool:
    return bool(SLUG_RE.match(value))
