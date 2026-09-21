"""Glob matching shared by test_guard.py and state.py's test-globs sanity
check. Supports ``**`` (matches zero or more path segments, including
across ``/``) in addition to the usual ``*``/``?``.
"""
from __future__ import annotations

import re
from typing import Dict, List

_CACHE: Dict[str, "re.Pattern[str]"] = {}


def _glob_to_regex(glob: str):
    cached = _CACHE.get(glob)
    if cached is not None:
        return cached
    i = 0
    n = len(glob)
    out = []
    while i < n:
        c = glob[i]
        if c == "*" and glob[i : i + 2] == "**":
            if i + 2 < n and glob[i + 2] == "/":
                out.append("(?:.*/)?")
                i += 3
            else:
                out.append(".*")
                i += 2
            continue
        if c == "*":
            out.append("[^/]*")
            i += 1
            continue
        if c == "?":
            out.append("[^/]")
            i += 1
            continue
        out.append(re.escape(c))
        i += 1
    pattern = re.compile("^" + "".join(out) + "$")
    _CACHE[glob] = pattern
    return pattern


def matches_any_glob(path: str, globs: List[str]) -> bool:
    for g in globs:
        if _glob_to_regex(g).match(path):
            return True
    return False
