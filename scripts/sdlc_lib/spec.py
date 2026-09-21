"""Reading ``docs/features/<feature>/spec.md`` (contracts.md section 6)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from .frontmatter import parse_frontmatter
from .markdown import extract_level2_sections, parse_numbered_list

STORIES_SECTION = "User stories"
QUESTIONS_SECTION = "Open questions"
WALKTHROUGH_SECTION = "Acceptance walkthrough"
EXEC_ORDER_SECTION = "Execution order"

STATUSES = ("draft", "approved", "delivered", "accepted", "dropped")

_ACTOR_RE = re.compile(r"\[(agent|human)\]")
_STORIES_RE = re.compile(r"\(stories:\s*([0-9,\s]*)\)")
_TICKET_SLUG_RE = re.compile(r"^`([a-z0-9]+(?:-[a-z0-9]+)*)`")


class SpecData:
    def __init__(self, frontmatter: dict, body: str, sections: Dict[str, str]) -> None:
        self.frontmatter = frontmatter
        self.body = body
        self.sections = sections


def load_spec(path: Path) -> SpecData:
    """Raises FrontmatterError if the frontmatter block is malformed."""
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    sections = extract_level2_sections(body)
    return SpecData(fm, body, sections)


def story_numbers(spec: SpecData) -> List[int]:
    text = spec.sections.get(STORIES_SECTION, "")
    return sorted(set(n for n, _ in parse_numbered_list(text)))


class WalkthroughStep:
    def __init__(self, step: int, text: str, actor: Optional[str], stories: Optional[List[int]]) -> None:
        self.step = step
        self.text = text
        self.actor = actor
        self.stories = stories


def walkthrough_steps(spec: SpecData) -> List[WalkthroughStep]:
    text = spec.sections.get(WALKTHROUGH_SECTION, "")
    steps = []
    for num, line in parse_numbered_list(text):
        actor_m = _ACTOR_RE.search(line)
        stories_m = _STORIES_RE.search(line)
        stories: Optional[List[int]] = None
        if stories_m:
            raw = stories_m.group(1)
            stories = [int(x.strip()) for x in raw.split(",") if x.strip() != ""]
        steps.append(WalkthroughStep(num, line, actor_m.group(1) if actor_m else None, stories))
    return steps


def execution_order(spec: SpecData) -> List[Optional[str]]:
    """Return the listed ticket slugs in order. An entry is ``None`` where
    the line did not start with a backticked slug (the line is then simply
    not counted as "listing" any ticket)."""
    text = spec.sections.get(EXEC_ORDER_SECTION, "")
    out: List[Optional[str]] = []
    for _, line in parse_numbered_list(text):
        m = _TICKET_SLUG_RE.match(line.strip())
        out.append(m.group(1) if m else None)
    return out
