"""Reading ``docs/roadmap/README.md`` and ``docs/roadmap/<epic>.md``
(contracts.md section 5)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .frontmatter import parse_frontmatter
from .markdown import extract_level2_sections, parse_checkbox_lines, parse_numbered_list
from .paths import ROADMAP_README, epic_path
from .slugs import is_valid_slug

EPIC_STATUSES = ("proposed", "planned", "in-progress", "done", "dropped")

FEATURES_SECTION = "Features"

_EPIC_SLUG_RE = re.compile(r"^`([a-z0-9]+(?:-[a-z0-9]+)*)`")
_BACKTICKED_RE = re.compile(r"`([^`]+)`")


def list_epic_order(repo: Path) -> List[str]:
    """Epic slugs in roadmap order, from the numbered list in
    docs/roadmap/README.md. Lines that do not start with a backticked slug
    are ignored."""
    path = repo / ROADMAP_README
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    slugs: List[str] = []
    for _, line in parse_numbered_list(text):
        m = _EPIC_SLUG_RE.match(line.strip())
        if m:
            slugs.append(m.group(1))
    return slugs


class EpicData:
    def __init__(self, slug: str, frontmatter: dict, sections: dict) -> None:
        self.slug = slug
        self.frontmatter = frontmatter
        self.sections = sections

    @property
    def status(self):
        return self.frontmatter.get("status")


def load_epic(repo: Path, slug: str) -> EpicData:
    """Raises FrontmatterError if the frontmatter block is malformed."""
    path = epic_path(repo, slug)
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    sections = extract_level2_sections(body)
    return EpicData(slug, fm, sections)


class FeatureLine:
    def __init__(self, slug: str, checked: bool, dropped: bool, note: str) -> None:
        self.slug = slug
        self.checked = checked
        self.dropped = dropped
        self.note = note


def epic_feature_lines(epic: EpicData) -> List[FeatureLine]:
    """Parse the ``## Features`` checkbox list of an epic file.

    contracts.md section 5: "any list line with a checkbox and a backticked
    valid slug is a feature line, whatever punctuation or emphasis surrounds
    it" -- so this searches for the first backticked, valid-slug token on
    the line rather than anchoring to a fixed shape. A line whose only
    backticked token is not a valid slug (a template placeholder) is
    ignored, as if absent. Strike-through (``~...~``, tolerating whitespace
    and emphasis markers immediately around the backticks) still means
    dropped.
    """
    text = epic.sections.get(FEATURES_SECTION, "")
    out: List[FeatureLine] = []
    for checked, rest in parse_checkbox_lines(text):
        slug = None
        span = None
        for m in _BACKTICKED_RE.finditer(rest):
            if is_valid_slug(m.group(1)):
                slug = m.group(1)
                span = m.span()
                break
        if slug is None:
            continue

        before, after = rest[: span[0]], rest[span[1] :]
        dropped = before.rstrip().endswith("~") and after.lstrip().startswith("~")

        note = after.lstrip()
        if dropped and note.startswith("~"):
            note = note[1:].lstrip()
        for sep in ("—", "-", ":"):
            if note.startswith(sep):
                note = note[len(sep) :].strip()
                break

        out.append(FeatureLine(slug, checked, dropped, note))
    return out
