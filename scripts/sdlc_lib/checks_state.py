"""Implements ``state.py`` (contracts.md section 13). Pure read-only.

Diagnostic codes produced here:

Fatal errors (exit 2):
    frontmatter-invalid   a spec/ticket/epic/inbox file's frontmatter block
                           does not parse under the section-1 dialect

Warnings:
    epic-not-found          an epic listed in docs/roadmap/README.md has no
                             docs/roadmap/<epic>.md file
    templates-tree-missing  the plugin's skills/sdlc/templates/ tree could
                             not be found, so outdated_templates is empty

Policy on malformed input (documented in the final report as a judgment
call): a structural parse failure (frontmatter that does not parse) halts
the whole computation (fatal, exit 2), since state.py cannot safely read
that file's fields at all. A semantic/content problem that another script
is responsible for flagging (an unknown enum value, a dangling reference) is
NOT fatal here: it simply fails to match any next.action rule and the
computation continues, so one bad ticket status doesn't take down the whole
"what's next" oracle.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from . import config as config_mod
from . import inbox as inbox_mod
from . import roadmap as roadmap_mod
from . import spec as spec_mod
from . import templates as templates_mod
from .debt import is_stale, load_debt
from .frontmatter import FrontmatterError
from .globs import matches_any_glob
from .paths import FEATURES_DIR, JOURNEYS, epic_path, relpath, spec_path, tickets_dir
from .result import Result
from .ticket import list_ticket_files, load_ticket

_SCAN_SKIP_DIRS = {".git", "node_modules", "worktrees", ".sdlc"}


def _test_globs_ok(repo: Path, test_globs: List[str]) -> bool:
    """Walk the repo (pruning .git, node_modules, worktrees and .sdlc),
    stopping at the first file that matches any test_globs. Returns True as
    soon as a match is found, or if the repo has no files at all outside
    those directories (nothing to warn about)."""
    any_file = False
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in _SCAN_SKIP_DIRS]
        for fname in filenames:
            any_file = True
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, repo).replace(os.sep, "/")
            if matches_any_glob(rel, test_globs):
                return True
    return not any_file


def _item_key(item) -> str:
    return item.id if isinstance(item.id, str) and item.id else item.slug


def _item_obj(item) -> dict:
    return {
        "id": _item_key(item),
        "type": item.type,
        "blocks": [b for b in item.blocks if isinstance(b, str)],
    }


def compute_state(repo: Path, result: Result, templates_dir: Optional[Path] = None) -> None:
    config = config_mod.load_config(repo, result, required=False)
    if result.fatal:
        return
    initialized = config is not None
    effective_config = config if config is not None else dict(config_mod.DEFAULTS)

    # ---- inbox ----
    inbox_items = []
    for f in inbox_mod.list_inbox_files(repo):
        try:
            inbox_items.append(inbox_mod.load_inbox_item(f))
        except FrontmatterError as exc:
            rel = relpath(repo, f)
            result.fail_fatal("frontmatter-invalid", "%s: %s" % (rel, exc), rel)
            return

    open_blocks: Set[str] = set()
    for item in inbox_items:
        if item.status == "open":
            open_blocks.update(b for b in item.blocks if isinstance(b, str))

    inbox_open = sorted((i for i in inbox_items if i.status == "open"), key=inbox_mod.sort_key)
    inbox_answered = sorted((i for i in inbox_items if i.status == "answered"), key=inbox_mod.sort_key)

    # ---- roadmap: epics ----
    epic_order = roadmap_mod.list_epic_order(repo)
    epics: Dict[str, roadmap_mod.EpicData] = {}
    epic_feature_lines: Dict[str, List[roadmap_mod.FeatureLine]] = {}
    for slug in epic_order:
        p = epic_path(repo, slug)
        if not p.is_file():
            result.warning(
                "epic-not-found",
                "docs/roadmap/%s.md is listed in README.md but does not exist" % slug,
                relpath(repo, p),
            )
            continue
        try:
            epic = roadmap_mod.load_epic(repo, slug)
        except FrontmatterError as exc:
            rel = relpath(repo, p)
            result.fail_fatal("frontmatter-invalid", "%s: %s" % (rel, exc), rel)
            return
        epics[slug] = epic
        epic_feature_lines[slug] = roadmap_mod.epic_feature_lines(epic)

    # ---- features: discovery ----
    features_root = repo / FEATURES_DIR
    feature_slugs: List[str] = []
    if features_root.is_dir():
        for d in sorted(features_root.iterdir()):
            if d.is_dir() and (d / "spec.md").is_file():
                feature_slugs.append(d.name)
    feature_slugs_set = set(feature_slugs)

    feature_specs: Dict[str, spec_mod.SpecData] = {}
    for slug in feature_slugs:
        p = spec_path(repo, slug)
        try:
            feature_specs[slug] = spec_mod.load_spec(p)
        except FrontmatterError as exc:
            rel = relpath(repo, p)
            result.fail_fatal("frontmatter-invalid", "%s: %s" % (rel, exc), rel)
            return

    def feature_epic(slug: str) -> str:
        return feature_specs[slug].frontmatter.get("epic") or ""

    # ---- features: tickets / frontier ----
    feature_ticket_info: Dict[str, dict] = {}
    for slug in feature_slugs:
        t_dir = tickets_dir(repo, slug)
        tix = {}
        for f in list_ticket_files(t_dir):
            try:
                tix[f.stem] = load_ticket(f)
            except FrontmatterError as exc:
                rel = relpath(repo, f)
                result.fail_fatal("frontmatter-invalid", "%s: %s" % (rel, exc), rel)
                return
        total = len(tix)
        done = sum(1 for t in tix.values() if t.status == "done")
        all_done_or_wontfix = (
            total > 0
            and done > 0
            and all(t.status in ("done", "wontfix") for t in tix.values())
        )
        any_in_progress = any(t.status == "in-progress" for t in tix.values())
        frontier = []
        for tslug, t in tix.items():
            if t.status != "ready-for-agent":
                continue
            deps = t.depends_on
            if all(tix.get(d) is not None and tix[d].status == "done" for d in deps if isinstance(d, str)):
                frontier.append(tslug)
        feature_ticket_info[slug] = {
            "total": total,
            "done": done,
            "all_done_or_wontfix": all_done_or_wontfix,
            "any_in_progress": any_in_progress,
            "frontier": sorted(frontier),
        }

    if result.fatal:
        return

    # ---- feature ordering: outside-epic first (alpha), then per epic in
    # roadmap order and the epic's own Features list order, then leftovers ----
    ordered_slugs: List[str] = []
    assigned: Set[str] = set()

    non_epic = sorted(s for s in feature_slugs if not feature_epic(s))
    ordered_slugs.extend(non_epic)
    assigned.update(non_epic)

    for epic_slug in epic_order:
        for fl in epic_feature_lines.get(epic_slug, []):
            if fl.slug in feature_slugs_set and fl.slug not in assigned:
                ordered_slugs.append(fl.slug)
                assigned.add(fl.slug)

    leftovers = sorted(s for s in feature_slugs if s not in assigned)
    ordered_slugs.extend(leftovers)
    assigned.update(leftovers)

    def blocked_by_for(slug: str) -> List[str]:
        epic = feature_epic(slug)
        ids = set()
        for item in inbox_items:
            if item.status != "open":
                continue
            if slug in item.blocks or (epic and epic in item.blocks):
                ids.add(_item_key(item))
        return sorted(ids)

    features_out = []
    for slug in ordered_slugs:
        info = feature_ticket_info[slug]
        features_out.append(
            {
                "feature": slug,
                "epic": feature_epic(slug),
                "status": feature_specs[slug].frontmatter.get("status"),
                "tickets": {"total": info["total"], "done": info["done"]},
                "frontier": info["frontier"],
                "blocked_by": blocked_by_for(slug),
            }
        )

    pending_acceptance = [s for s in ordered_slugs if feature_specs[s].frontmatter.get("status") == "delivered"]

    # ---- debt ----
    debt_by_module = load_debt(repo)
    threshold = effective_config.get("debt_threshold_per_module", config_mod.DEFAULTS["debt_threshold_per_module"])
    stale_paths: Set[str] = set()
    over_threshold = []
    for module, entries in debt_by_module.items():
        fresh_count = 0
        for entry in entries:
            if is_stale(repo, entry):
                stale_paths.add(entry.path)
            else:
                fresh_count += 1
        if fresh_count > threshold:
            over_threshold.append(module)
    over_threshold.sort()
    stale = sorted(stale_paths)

    # ---- outdated templates ----
    t_dir = templates_dir if templates_dir is not None else templates_mod.default_templates_dir()
    current_versions, tree_exists = templates_mod.load_current_versions(t_dir)
    outdated: List[dict] = []
    if not tree_exists:
        result.warning(
            "templates-tree-missing",
            "plugin templates tree not found at %s" % t_dir,
            str(t_dir),
        )
    else:
        for path, name, found in templates_mod.scan_target_markers(repo):
            current = current_versions.get(name)
            if current is not None and found < current:
                outdated.append(
                    {"path": relpath(repo, path), "name": name, "found": found, "current": current}
                )
    outdated.sort(key=lambda d: (d["path"], d["name"]))

    # ---- test_globs sanity ----
    test_globs = effective_config.get("test_globs", config_mod.DEFAULTS["test_globs"])
    if not _test_globs_ok(repo, test_globs):
        result.warning(
            "test-globs-match-nothing",
            "no file in the repository matches any of the configured test_globs",
            "",
        )

    # ---- next.action ----
    stalled: List[str] = []
    any_blocked = False
    action: Optional[str] = None
    target = ""
    reason = ""

    if not initialized:
        action, target, reason = "init", "", "docs/agents/sdlc.json is missing"
    elif inbox_answered:
        action, target = "apply-answers", ""
        reason = "%d inbox item(s) are answered and awaiting application" % len(inbox_answered)
    else:
        max_pending = effective_config.get(
            "max_pending_acceptance", config_mod.DEFAULTS["max_pending_acceptance"]
        )
        if max_pending > 0 and len(pending_acceptance) >= max_pending:
            action, target = "pause", ""
            reason = "%d features are delivered, at or above max_pending_acceptance (%d)" % (
                len(pending_acceptance),
                max_pending,
            )
        else:
            # `stalled` is computed over every non-terminal, non-blocked
            # feature in one full pass -- the loop never breaks early, so a
            # stalled feature is reported even when an earlier or later
            # feature in roadmap order supplies the action (contracts.md
            # section 13: "stalled is computed over every feature before
            # the action is chosen").
            first_action = None
            for slug in ordered_slugs:
                status = feature_specs[slug].frontmatter.get("status")
                if status in ("delivered", "accepted", "dropped"):
                    continue
                epic = feature_epic(slug)
                if slug in open_blocks or (epic and epic in open_blocks):
                    any_blocked = True
                    continue
                info = feature_ticket_info[slug]

                candidate = None
                if status == "approved" and info["total"] > 0:
                    if info["all_done_or_wontfix"]:
                        candidate = ("deliver", slug, "all tickets are done or wontfix")
                    elif info["frontier"] or info["any_in_progress"]:
                        candidate = ("execute", slug, "tickets are ready to work or in progress")
                    else:
                        stalled.append(slug)
                elif status == "approved" and info["total"] == 0:
                    candidate = ("ticket", slug, "feature is approved but has no tickets yet")
                elif status == "draft":
                    candidate = ("spec", slug, "feature spec is still a draft")

                if candidate is not None and first_action is None:
                    first_action = candidate

            if first_action is not None:
                action, target, reason = first_action

            if action is None:
                for epic_slug in epic_order:
                    epic = epics.get(epic_slug)
                    if epic is None:
                        continue
                    if epic.status not in ("planned", "in-progress"):
                        continue
                    if epic_slug in open_blocks:
                        any_blocked = True
                        continue

                    lines = epic_feature_lines.get(epic_slug, [])
                    matched = False
                    if not lines:
                        action, target, reason = "plan-epic", epic_slug, "epic has no feature line yet"
                        matched = True
                    else:
                        first_pending = None
                        for fl in lines:
                            if not fl.checked and not fl.dropped:
                                first_pending = fl
                                break
                        if first_pending is None:
                            action, target, reason = (
                                "close-epic",
                                epic_slug,
                                "every feature line is delivered or dropped",
                            )
                            matched = True
                        else:
                            # A feature directory without spec.md still
                            # counts as "no spec" (contracts.md section 13).
                            if not spec_path(repo, first_pending.slug).is_file():
                                action, target, reason = (
                                    "spec",
                                    first_pending.slug,
                                    "epic %s's next feature has no spec yet" % epic_slug,
                                )
                                matched = True
                            # else: no rule-5 bullet matches this epic; move on

                    if matched:
                        break

            if action is None:
                journeys_exists = (repo / JOURNEYS).is_file()
                if not journeys_exists or not epic_order:
                    action, target = "intention", ""
                    reason = "docs/journeys.md is missing" if not journeys_exists else "no epic exists yet"
                elif stalled or any_blocked:
                    action, target, reason = "wait", "", "work exists but is stalled or blocked"
                else:
                    action, target, reason = "idle", "", "nothing left to do"

    result.set("initialized", initialized)
    result.set("config", config if config is not None else {})
    result.set(
        "inbox",
        {
            "open": [_item_obj(i) for i in inbox_open],
            "answered": [_item_obj(i) for i in inbox_answered],
        },
    )
    result.set("pending_acceptance", pending_acceptance)
    result.set("features", features_out)
    result.set("debt", {"over_threshold": over_threshold, "stale": stale})
    result.set("stalled", stalled)
    result.set("outdated_templates", outdated)
    result.set("next", {"action": action, "target": target, "reason": reason})
