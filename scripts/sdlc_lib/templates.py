"""Template markers (contracts.md section 3, "Template markers").

A file instantiated from a template carries `<!-- sdlc:template <name>
<version> -->` on its own line (or, in JSON files, a top-level
``"template": "<name> <version>"`` key). This module finds those markers,
both in the plugin's own `skills/sdlc/templates/` tree (the "current"
versions) and in a target repository (what's actually there), so state.py
can report outdated ones.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_MARKER_RE = re.compile(r"<!--\s*sdlc:template\s+([A-Za-z0-9_-]+)\s+(\d+)\s*-->")


def find_markers_in_text(text: str) -> List[Tuple[str, int]]:
    return [(m.group(1), int(m.group(2))) for m in _MARKER_RE.finditer(text)]


def find_marker_in_json(text: str) -> Optional[Tuple[str, int]]:
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    v = data.get("template")
    if not isinstance(v, str):
        return None
    parts = v.rsplit(" ", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    return (parts[0], int(parts[1]))


def _markers_in_file(path: Path) -> List[Tuple[str, int]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    if path.suffix == ".json":
        m = find_marker_in_json(text)
        return [m] if m else []
    return find_markers_in_text(text)


def default_templates_dir() -> Path:
    """The plugin's own templates tree, resolved relative to this file's
    location (scripts/sdlc_lib/templates.py -> <plugin root>/skills/sdlc/templates)."""
    return Path(__file__).resolve().parents[2] / "skills" / "sdlc" / "templates"


def load_current_versions(templates_dir: Path) -> Tuple[Dict[str, int], bool]:
    """Scan the plugin's templates tree. Returns (name -> current version,
    whether the tree exists at all)."""
    if not templates_dir.is_dir():
        return {}, False
    versions: Dict[str, int] = {}
    for path in sorted(templates_dir.rglob("*")):
        if not path.is_file():
            continue
        for name, version in _markers_in_file(path):
            if name not in versions or version > versions[name]:
                versions[name] = version
    return versions, True


def scan_target_markers(repo: Path) -> List[Tuple[Path, str, int]]:
    """Scan the target repo for template markers, per contracts.md: the root
    map (CLAUDE.md/AGENTS.md), PRODUCT.md, ARCHITECTURE.md, docs/**/*.md and
    docs/agents/sdlc.json."""
    candidates: List[Path] = []
    for name in ("CLAUDE.md", "AGENTS.md", "PRODUCT.md", "ARCHITECTURE.md"):
        p = repo / name
        if p.is_file():
            candidates.append(p)
    docs_dir = repo / "docs"
    if docs_dir.is_dir():
        candidates.extend(sorted(docs_dir.rglob("*.md")))
    sdlc_json = repo / "docs" / "agents" / "sdlc.json"
    if sdlc_json.is_file():
        candidates.append(sdlc_json)

    seen = set()
    results: List[Tuple[Path, str, int]] = []
    for path in candidates:
        rp = path.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        for name, version in _markers_in_file(path):
            results.append((path, name, version))
    return results
