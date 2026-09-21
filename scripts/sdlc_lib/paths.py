"""Layout constants from contracts.md section 2, and small path helpers.

All paths are relative to the root of the *target* repository.
"""
from __future__ import annotations

from pathlib import Path

CONFIG_PATH = "docs/agents/sdlc.json"
AGENTS_DIR = "docs/agents"
AGENTS_README = "docs/agents/README.md"
JOURNEYS = "docs/journeys.md"
ROADMAP_DIR = "docs/roadmap"
ROADMAP_README = "docs/roadmap/README.md"
FEATURES_DIR = "docs/features"
INBOX_DIR = "docs/inbox"
TECH_DEBT = "docs/tech-debt.md"
LOCK_DIR = ".sdlc"
LOCK_FILE = ".sdlc/lock"
ARCHITECTURE = "ARCHITECTURE.md"
ROOT_MAP_CANDIDATES = ("CLAUDE.md", "AGENTS.md")


def feature_dir(repo: Path, feature: str) -> Path:
    return repo / FEATURES_DIR / feature


def spec_path(repo: Path, feature: str) -> Path:
    return feature_dir(repo, feature) / "spec.md"


def tickets_dir(repo: Path, feature: str) -> Path:
    return feature_dir(repo, feature) / "tickets"


def findings_path(repo: Path, feature: str) -> Path:
    return feature_dir(repo, feature) / "findings.json"


def acceptance_path(repo: Path, feature: str) -> Path:
    return feature_dir(repo, feature) / "acceptance.json"


def epic_path(repo: Path, epic: str) -> Path:
    return repo / ROADMAP_DIR / (epic + ".md")


def relpath(repo: Path, path: Path) -> str:
    """Best-effort path relative to repo, using '/' separators, for
    diagnostics -- falls back to the absolute path if it is not inside
    repo."""
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
