"""Implements ``check_harness.py`` (contracts.md section 13).

Diagnostic codes produced here:

Errors:
    path-missing          a backticked path cited in a checked doc does not exist
    agent-doc-unlisted    a file in docs/agents/ is not named in its README.md
    module-undocumented   an immediate subdir of a module_roots entry is not
                           named in ARCHITECTURE.md
    map-too-long          the root map (CLAUDE.md/AGENTS.md) exceeds map_max_lines

Warnings:
    map-missing           no root map (CLAUDE.md or AGENTS.md) exists
    module-roots-empty    config's module_roots is empty

Ambiguity handled conservatively: if both CLAUDE.md and AGENTS.md exist, both
are treated as "the root map" and independently checked (path citations and
length), rather than picking one arbitrarily -- see the final report.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .markdown import extract_backticked
from .paths import AGENTS_DIR, AGENTS_README, ARCHITECTURE, ROOT_MAP_CANDIDATES, TECH_DEBT, relpath
from .result import Result

_LINECOL_RE = re.compile(r":\d+(:\d+)?$")
_EXCLUDE_CHARS = ("<", ">", "*", "$", "~")

# contracts.md section 13's exact list -- so that "3.9", "0.1.0" and
# "user.save" are not mistaken for paths.
_KNOWN_EXTENSIONS = {
    "md", "json", "yml", "yaml", "toml", "txt", "sh", "py", "js", "jsx",
    "ts", "tsx", "go", "java", "kt", "rb", "rs", "cs", "sql", "css", "html",
    "xml", "lock",
}


def normalize_path_token(token: str) -> Optional[str]:
    """Apply the path-token heuristic from contracts.md section 13.

    Returns the token with any trailing ``:line`` / ``:line:col`` stripped,
    or ``None`` if the token does not count as a path.
    """
    stripped = _LINECOL_RE.sub("", token)
    if not stripped:
        return None
    if " " in stripped:
        return None
    for ch in _EXCLUDE_CHARS:
        if ch in stripped:
            return None
    if "://" in stripped:
        return None
    if "/" in stripped:
        return stripped
    if "." in stripped and stripped.rsplit(".", 1)[-1].lower() in _KNOWN_EXTENSIONS:
        return stripped
    return None


def _scan_paths_in_file(repo: Path, file_rel: str, result: Result) -> None:
    path = repo / file_rel
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    seen = set()
    for token in extract_backticked(text):
        candidate = normalize_path_token(token)
        if candidate is None or candidate in seen:
            continue
        seen.add(candidate)
        target = repo / candidate
        if not target.exists():
            result.error(
                "path-missing",
                "path `%s` cited in %s does not exist" % (candidate, file_rel),
                file_rel,
            )


def check_harness(repo: Path, config: dict, result: Result) -> None:
    maps_found = [name for name in ROOT_MAP_CANDIDATES if (repo / name).is_file()]
    if not maps_found:
        result.warning("map-missing", "no root agent map (CLAUDE.md or AGENTS.md) found", "")

    map_max_lines = config.get("map_max_lines", 120)
    for name in maps_found:
        text = (repo / name).read_text(encoding="utf-8")
        n_lines = len(text.splitlines())
        if n_lines > map_max_lines:
            result.error(
                "map-too-long",
                "%s has %d lines, more than map_max_lines (%d)" % (name, n_lines, map_max_lines),
                name,
            )
        _scan_paths_in_file(repo, name, result)

    _scan_paths_in_file(repo, ARCHITECTURE, result)
    _scan_paths_in_file(repo, AGENTS_README, result)
    _scan_paths_in_file(repo, TECH_DEBT, result)

    agents_dir = repo / AGENTS_DIR
    readme_path = repo / AGENTS_README
    readme_text = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    if agents_dir.is_dir():
        for f in sorted(agents_dir.iterdir()):
            if not f.is_file():
                continue
            if f.name in ("README.md", "sdlc.json"):
                continue
            if f.name not in readme_text:
                result.error(
                    "agent-doc-unlisted",
                    "docs/agents/%s is not named in docs/agents/README.md" % f.name,
                    relpath(repo, f),
                )

    module_roots = config.get("module_roots", [])
    if not module_roots:
        result.warning("module-roots-empty", "module_roots is empty", "")
    else:
        arch_path = repo / ARCHITECTURE
        arch_text = arch_path.read_text(encoding="utf-8") if arch_path.is_file() else ""
        for root in module_roots:
            root_dir = repo / root
            if not root_dir.is_dir():
                continue
            for entry in sorted(root_dir.iterdir()):
                if not entry.is_dir():
                    continue
                if entry.name not in arch_text:
                    result.error(
                        "module-undocumented",
                        "subdirectory %s of module root %s is not named in ARCHITECTURE.md"
                        % (entry.name, root),
                        relpath(repo, entry),
                    )
