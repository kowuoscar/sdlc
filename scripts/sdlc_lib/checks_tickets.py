"""Implements ``check_tickets.py``: the mechanical half of the ticket critic
(contracts.md section 13).

Diagnostic codes produced here:

Fatal errors (exit 2 -- the feature cannot be evaluated at all):
    spec-not-found          docs/features/<feature>/spec.md does not exist
    frontmatter-invalid     spec.md's frontmatter block is malformed

Errors (exit 1 when present):
    frontmatter-invalid     a ticket's frontmatter block is malformed
    ticket-slug-invalid     ticket filename is not a valid kebab-case slug
    ticket-id-mismatch      frontmatter id != filename
    ticket-status-unknown   status is not one of the defined values
    ticket-section-missing  a required level-2 section is absent
    ticket-section-empty    a required level-2 section is present but empty
    dependency-missing      depends_on names a ticket that does not exist
    dependency-self         a ticket depends on itself
    dependency-cycle        a dependency cycle exists
    stories-empty           stories is empty and the ticket is not 'enabler'
    story-unknown           a ticket cites a story number not in spec.md
    story-uncovered         a spec user story is carried by no ticket
    walkthrough-missing-actor    a walkthrough step has no [agent]/[human] tag
    walkthrough-missing-stories  a walkthrough step has no (stories: ...) tag
    walkthrough-story-unknown    a walkthrough step cites an unknown story
    execution-order-incomplete   a ticket is missing from Execution order
    execution-order-unknown      Execution order names a ticket that does not exist
    execution-order-violation    a ticket is listed before one of its blockers

Warnings:
    ticket-too-many-criteria     more than 7 acceptance criteria
    dependency-redundant         a dependency already implied transitively
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

from . import spec as spec_mod
from . import ticket as ticket_mod
from .frontmatter import FrontmatterError
from .paths import relpath, spec_path, tickets_dir
from .result import Result
from .slugs import is_valid_slug


def _count_list_items(text: str) -> int:
    count = 0
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("- ") or s == "-" or s.startswith("-\t"):
            count += 1
            continue
        i = 0
        while i < len(s) and s[i].isdigit():
            i += 1
        if i > 0 and s[i : i + 1] == ".":
            count += 1
    return count


def check_tickets(repo: Path, feature: str, result: Result) -> None:
    spec_file = spec_path(repo, feature)
    if not spec_file.is_file():
        result.fail_fatal(
            "spec-not-found",
            "spec.md not found for feature %r" % feature,
            relpath(repo, spec_file),
        )
        return

    try:
        spec = spec_mod.load_spec(spec_file)
    except FrontmatterError as exc:
        result.fail_fatal(
            "frontmatter-invalid", "spec.md: %s" % exc, relpath(repo, spec_file)
        )
        return
    except OSError as exc:
        result.fail_fatal(
            "spec-not-found", "could not read spec.md: %s" % exc, relpath(repo, spec_file)
        )
        return

    spec_stories = spec_mod.story_numbers(spec)
    spec_rel = relpath(repo, spec_file)

    t_dir = tickets_dir(repo, feature)
    files = ticket_mod.list_ticket_files(t_dir)

    tickets: Dict[str, ticket_mod.TicketData] = {}
    known_slugs: Set[str] = set()

    for f in files:
        slug = f.stem
        rel = relpath(repo, f)
        known_slugs.add(slug)

        if not is_valid_slug(slug):
            result.error(
                "ticket-slug-invalid", "ticket filename is not a valid slug: %r" % slug, rel
            )

        try:
            t = ticket_mod.load_ticket(f)
        except FrontmatterError as exc:
            result.error("frontmatter-invalid", str(exc), rel)
            continue

        tickets[slug] = t

        fm_id = t.frontmatter.get("id")
        if fm_id != slug:
            result.error(
                "ticket-id-mismatch",
                "id %r does not match filename %r" % (fm_id, slug),
                rel,
            )

        if t.status not in ticket_mod.STATUSES:
            result.error("ticket-status-unknown", "unknown status %r" % (t.status,), rel)

        for section in ticket_mod.REQUIRED_SECTIONS:
            heading = "## " + section
            if section not in t.sections:
                result.error(
                    "ticket-section-missing", "missing required section %s" % heading, rel
                )
            elif not t.sections[section].strip():
                result.error(
                    "ticket-section-empty", "required section %s is empty" % heading, rel
                )

        n_criteria = _count_list_items(t.sections.get("Acceptance criteria", ""))
        if n_criteria > 7:
            result.warning(
                "ticket-too-many-criteria",
                "%d acceptance criteria (more than 7)" % n_criteria,
                rel,
            )

        stories = t.stories
        if not stories and "enabler" not in t.labels:
            result.error(
                "stories-empty",
                "stories is empty and ticket is not labeled 'enabler'",
                rel,
            )
        for sn in stories:
            if sn not in spec_stories:
                result.error(
                    "story-unknown",
                    "story %s is not in spec.md's User stories" % sn,
                    rel,
                )

    depends_map: Dict[str, List[str]] = {}
    for slug, t in tickets.items():
        rel = relpath(repo, t_dir / (slug + ".md"))
        deps = [d for d in t.depends_on if isinstance(d, str)]
        depends_map[slug] = deps
        for d in deps:
            if d == slug:
                result.error("dependency-self", "ticket depends on itself", rel)
            elif d not in known_slugs:
                result.error(
                    "dependency-missing",
                    "depends_on references missing ticket %r" % d,
                    rel,
                )

    _check_cycles(depends_map, t_dir, repo, result)
    _check_redundant(depends_map, t_dir, repo, result)

    covered: Set[int] = set()
    for t in tickets.values():
        covered.update(s for s in t.stories if isinstance(s, int))
    for sn in spec_stories:
        if sn not in covered:
            result.error(
                "story-uncovered",
                "spec user story %d is carried by no ticket" % sn,
                spec_rel,
            )

    for step in spec_mod.walkthrough_steps(spec):
        if step.actor is None:
            result.error(
                "walkthrough-missing-actor",
                "walkthrough step %d has no [agent]/[human] actor tag" % step.step,
                spec_rel,
            )
        if step.stories is None:
            result.error(
                "walkthrough-missing-stories",
                "walkthrough step %d has no (stories: ...) tag" % step.step,
                spec_rel,
            )
        else:
            for sn in step.stories:
                if sn not in spec_stories:
                    result.error(
                        "walkthrough-story-unknown",
                        "walkthrough step %d cites story %d, not in spec.md's User stories"
                        % (step.step, sn),
                        spec_rel,
                    )

    listed: List[str] = []
    seen: Set[str] = set()
    for slug in spec_mod.execution_order(spec):
        if slug and slug not in seen:
            listed.append(slug)
            seen.add(slug)
    position = {slug: i for i, slug in enumerate(listed)}

    for slug in sorted(known_slugs):
        if slug not in position:
            result.error(
                "execution-order-incomplete",
                "ticket %r is not listed in spec.md's Execution order" % slug,
                spec_rel,
            )

    for slug in listed:
        if slug not in known_slugs:
            result.error(
                "execution-order-unknown",
                "spec.md's Execution order names ticket %r, which does not exist" % slug,
                spec_rel,
            )

    for slug, deps in depends_map.items():
        if slug not in position:
            continue
        for d in deps:
            if d in position and position[slug] < position[d]:
                result.error(
                    "execution-order-violation",
                    "ticket %r is listed before its blocker %r" % (slug, d),
                    spec_rel,
                )


def _path_for(t_dir: Path, repo: Path, slug: str) -> str:
    return relpath(repo, t_dir / (slug + ".md"))


def _check_cycles(depends_map: Dict[str, List[str]], t_dir: Path, repo: Path, result: Result) -> None:
    """Iterative DFS cycle detection (an explicit frame stack, not Python's
    call stack, so an arbitrarily long dependency chain cannot overflow the
    interpreter's recursion limit)."""
    reported_keys: Set[frozenset] = set()
    visited: Set[str] = set()

    for start in sorted(depends_map.keys()):
        if start in visited:
            continue

        path: List[str] = [start]
        path_set: Set[str] = {start}
        frames = [iter(depends_map.get(start, []))]

        while frames:
            try:
                d = next(frames[-1])
            except StopIteration:
                finished = path.pop()
                path_set.discard(finished)
                visited.add(finished)
                frames.pop()
                continue

            node = path[-1]
            if d == node or d not in depends_map:
                continue
            if d in path_set:
                idx = path.index(d)
                cycle = path[idx:] + [d]
                key = frozenset(cycle)
                if key not in reported_keys:
                    reported_keys.add(key)
                    result.error(
                        "dependency-cycle",
                        "dependency cycle: %s" % " -> ".join(cycle),
                        _path_for(t_dir, repo, path[idx]),
                    )
                continue
            if d not in visited:
                path.append(d)
                path_set.add(d)
                frames.append(iter(depends_map.get(d, [])))


def _reachable_from(node: str, depends_map: Dict[str, List[str]]) -> Set[str]:
    seen: Set[str] = set()
    stack = list(depends_map.get(node, []))
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(depends_map.get(n, []))
    return seen


def _check_redundant(depends_map: Dict[str, List[str]], t_dir: Path, repo: Path, result: Result) -> None:
    for node, deps in depends_map.items():
        for d in deps:
            if d == node:
                continue
            for d2 in deps:
                if d2 == d or d2 == node:
                    continue
                if d in _reachable_from(d2, depends_map):
                    result.warning(
                        "dependency-redundant",
                        "depends_on %r is already implied transitively via %r" % (d, d2),
                        _path_for(t_dir, repo, node),
                    )
                    break
