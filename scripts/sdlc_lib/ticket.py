"""Reading ``docs/features/<feature>/tickets/<ticket>.md`` (contracts.md section 7)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .frontmatter import parse_frontmatter
from .markdown import extract_level2_sections

STATUSES = (
    "needs-triage",
    "needs-info",
    "ready-for-agent",
    "ready-for-human",
    "in-progress",
    "done",
    "wontfix",
)

REQUIRED_SECTIONS = (
    "Context",
    "Acceptance criteria",
    "Tests",
    "Regression",
    "Observability",
)


class TicketData:
    def __init__(self, slug: str, frontmatter: dict, sections: Dict[str, str]) -> None:
        self.slug = slug
        self.frontmatter = frontmatter
        self.sections = sections

    @property
    def status(self):
        return self.frontmatter.get("status")

    @property
    def depends_on(self) -> List[str]:
        v = self.frontmatter.get("depends_on", [])
        return v if isinstance(v, list) else []

    @property
    def labels(self) -> List[str]:
        v = self.frontmatter.get("labels", [])
        return v if isinstance(v, list) else []

    @property
    def stories(self) -> List[int]:
        v = self.frontmatter.get("stories", [])
        return v if isinstance(v, list) else []


def load_ticket(path: Path) -> TicketData:
    """Raises FrontmatterError if the frontmatter block is malformed."""
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    sections = extract_level2_sections(body)
    return TicketData(path.stem, fm, sections)


def list_ticket_files(tickets_dir: Path) -> List[Path]:
    if not tickets_dir.is_dir():
        return []
    return sorted(p for p in tickets_dir.glob("*.md") if p.is_file())
