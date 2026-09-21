"""Reading ``docs/inbox/<item>.md`` (contracts.md section 10)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .frontmatter import parse_frontmatter
from .markdown import extract_level2_sections
from .paths import INBOX_DIR

TYPES = ("alert", "question", "approval", "acceptance", "proposal")
STATUSES = ("open", "answered", "closed")

TYPE_ORDER = {t: i for i, t in enumerate(TYPES)}


class InboxItem:
    def __init__(self, slug: str, frontmatter: dict, sections: Dict[str, str]) -> None:
        self.slug = slug
        self.frontmatter = frontmatter
        self.sections = sections

    @property
    def id(self):
        return self.frontmatter.get("id")

    @property
    def type(self):
        return self.frontmatter.get("type")

    @property
    def status(self):
        return self.frontmatter.get("status")

    @property
    def blocks(self) -> List[str]:
        v = self.frontmatter.get("blocks", [])
        return v if isinstance(v, list) else []


def load_inbox_item(path: Path) -> InboxItem:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    sections = extract_level2_sections(body)
    return InboxItem(path.stem, fm, sections)


def list_inbox_files(repo: Path) -> List[Path]:
    d = repo / INBOX_DIR
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.md") if p.is_file())


def sort_key(item: InboxItem):
    return (TYPE_ORDER.get(item.type, len(TYPES)), item.slug)
