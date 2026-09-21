"""Reading ``docs/tech-debt.md`` (contracts.md section 11)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .markdown import extract_level2_sections
from .paths import TECH_DEBT


class DebtEntry:
    def __init__(self, module: str, raw_line: str, path: str) -> None:
        self.module = module
        self.raw_line = raw_line
        self.path = path


def is_stale(repo: Path, entry: "DebtEntry") -> bool:
    """A debt entry is stale when its cited path no longer exists. An entry
    whose path could not even be parsed out of the line is not considered
    stale (there is nothing to check existence of), though it still counts
    toward the module's threshold."""
    if not entry.path:
        return False
    return not (repo / entry.path).exists()


def load_debt(repo: Path) -> Dict[str, List[DebtEntry]]:
    """Returns module heading -> list of entries. A line is an entry when
    it starts with ``-`` (after stripping) and has a backticked path as its
    first field."""
    path = repo / TECH_DEBT
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    sections = extract_level2_sections(text)
    out: Dict[str, List[DebtEntry]] = {}
    for module, body in sections.items():
        entries: List[DebtEntry] = []
        for line in body.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("-"):
                continue
            rest = stripped[1:].strip()
            entry_path = ""
            if rest.startswith("`"):
                end = rest.find("`", 1)
                if end != -1:
                    entry_path = rest[1:end]
            entries.append(DebtEntry(module, stripped, entry_path))
        if entries:
            out[module] = entries
    return out
