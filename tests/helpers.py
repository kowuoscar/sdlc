"""Test helpers: sys.path setup, a RepoBuilder for programmatic fixtures,
and small utilities for invoking a script's main() in-process."""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TESTS_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = TESTS_DIR.parent
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
BIN_DIR = PLUGIN_ROOT / "bin"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def run_main(main_func, argv: List[str]) -> Tuple[int, Optional[Any], str, str]:
    """Call a script's main(argv) in-process, capturing stdout/stderr.

    Returns (exit_code, parsed_json_or_None, stdout_text, stderr_text).
    """
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main_func(argv)
    stdout_text = out.getvalue()
    try:
        data = json.loads(stdout_text)
    except ValueError:
        data = None
    return code, data, stdout_text, err.getvalue()


class RepoBuilder:
    """Writes a target-repository fixture tree under `root`."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- generic ----
    def write(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def write_json(self, rel: str, data: Any) -> Path:
        return self.write(rel, json.dumps(data, indent=2))

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def remove(self, rel: str) -> None:
        (self.root / rel).unlink()

    # ---- config ----
    def config(self, **overrides: Any) -> Path:
        cfg: Dict[str, Any] = {"schema": 1, "verify": "true"}
        cfg.update(overrides)
        return self.write_json("docs/agents/sdlc.json", cfg)

    # ---- journeys ----
    def journeys(self, entries: List[Tuple[str, str]]) -> Path:
        lines = ["### %s — %s" % (title, state) for title, state in entries]
        return self.write("docs/journeys.md", "\n".join(lines) + "\n")

    # ---- roadmap ----
    def roadmap_readme(self, epic_slugs: List[str]) -> Path:
        lines = ["%d. `%s`" % (i, slug) for i, slug in enumerate(epic_slugs, 1)]
        return self.write("docs/roadmap/README.md", "\n".join(lines) + "\n")

    def epic(
        self,
        slug: str,
        title: Optional[str] = None,
        status: str = "planned",
        journeys: Optional[List[str]] = None,
        features: Optional[List[Tuple[bool, bool, str, str]]] = None,
        marker_version: int = 1,
    ) -> Path:
        journeys = journeys or []
        features = features if features is not None else []
        lines = [
            "---",
            "id: %s" % slug,
            "title: %s" % (title or slug),
            "status: %s" % status,
            "journeys: [%s]" % ", ".join(journeys),
            "---",
            "",
            "<!-- sdlc:template epic %d -->" % marker_version,
            "",
            "## Intent",
            "",
            "Intent text.",
            "",
            "## Features",
            "",
        ]
        for checked, dropped, fslug, note in features:
            box = "x" if checked else " "
            if dropped:
                line = "- [%s] ~`%s`~" % (box, fslug)
                if note:
                    line += " — %s" % note
            else:
                line = "- [%s] `%s`" % (box, fslug)
                if note:
                    line += " — %s" % note
            lines.append(line)
        lines.extend(["", "## Later", ""])
        return self.write("docs/roadmap/%s.md" % slug, "\n".join(lines) + "\n")

    # ---- feature spec ----
    def spec(
        self,
        feature: str,
        epic: str = "",
        status: str = "draft",
        date: str = "2026-01-01",
        stories: Optional[List[str]] = None,
        walkthrough: Optional[List[str]] = None,
        execution_order: Optional[List[str]] = None,
        open_questions: str = "None",
        marker_version: int = 1,
    ) -> Path:
        stories = stories if stories is not None else ["As a user, I want X, so that Y"]
        walkthrough = walkthrough if walkthrough is not None else []
        execution_order = execution_order if execution_order is not None else []
        lines = [
            "---",
            "feature: %s" % feature,
            "epic: %s" % epic,
            "status: %s" % status,
            "date: %s" % date,
            "---",
            "",
            "<!-- sdlc:template spec %d -->" % marker_version,
            "",
            "# %s" % feature,
            "",
            "## User stories",
            "",
        ]
        for i, s in enumerate(stories, 1):
            lines.append("%d. %s" % (i, s))
        lines += ["", "## Open questions", "", open_questions, "", "## Acceptance walkthrough", ""]
        for i, step in enumerate(walkthrough, 1):
            lines.append("%d. %s" % (i, step))
        lines += ["", "## Execution order", ""]
        for i, t in enumerate(execution_order, 1):
            lines.append("%d. `%s`" % (i, t))
        lines.append("")
        return self.write("docs/features/%s/spec.md" % feature, "\n".join(lines))

    def ticket(
        self,
        feature: str,
        slug: str,
        id: Optional[str] = None,
        title: str = "Do a thing",
        status: str = "ready-for-agent",
        depends_on: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        stories: Optional[List[int]] = None,
        sections: Optional[Dict[str, str]] = None,
        omit_sections: Optional[List[str]] = None,
        marker_version: int = 1,
    ) -> Path:
        depends_on = depends_on or []
        labels = labels or []
        stories = stories if stories is not None else [1]
        omit_sections = omit_sections or []
        lines = [
            "---",
            "id: %s" % (id if id is not None else slug),
            "title: %s" % title,
            "status: %s" % status,
            "depends_on: [%s]" % ", ".join(depends_on),
            "labels: [%s]" % ", ".join(labels),
            "stories: [%s]" % ", ".join(str(s) for s in stories),
            "---",
            "",
            "<!-- sdlc:template ticket %d -->" % marker_version,
            "",
        ]
        default_sections = {
            "Context": "Why this exists.",
            "Acceptance criteria": "- [ ] It works",
            "Tests": "Happy path.",
            "Regression": "N/A — nothing at risk",
            "Observability": "N/A — none",
        }
        if sections:
            default_sections.update(sections)
        for heading in list(default_sections.keys()):
            if heading in omit_sections:
                continue
            lines.append("## %s" % heading)
            lines.append("")
            lines.append(default_sections[heading])
            lines.append("")
        return self.write("docs/features/%s/tickets/%s.md" % (feature, slug), "\n".join(lines))

    def findings(self, feature: str, findings: Optional[List[dict]] = None, base: str = "main") -> Path:
        data = {"schema": 1, "feature": feature, "base": base, "findings": findings or []}
        return self.write_json("docs/features/%s/findings.json" % feature, data)

    def acceptance(self, feature: str, steps: Optional[List[dict]] = None) -> Path:
        data = {"schema": 1, "feature": feature, "steps": steps or []}
        return self.write_json("docs/features/%s/acceptance.json" % feature, data)

    def evidence(self, feature: str, rel: str, content: str = "ok\n") -> Path:
        return self.write("docs/features/%s/%s" % (feature, rel), content)

    def inbox_item(
        self,
        slug: str,
        item_type: str = "question",
        status: str = "open",
        blocks: Optional[List[str]] = None,
        created: str = "2026-01-01",
        answer: str = "",
        marker_version: int = 1,
    ) -> Path:
        blocks = blocks or []
        lines = [
            "---",
            "id: %s" % slug,
            "type: %s" % item_type,
            "status: %s" % status,
            "blocks: [%s]" % ", ".join(blocks),
            "created: %s" % created,
            "---",
            "",
            "<!-- sdlc:template inbox-item %d -->" % marker_version,
            "",
            "## Question",
            "",
            "Q?",
            "",
            "## Recommendation",
            "",
            "R.",
            "",
            "## Blocks",
            "",
            "Nothing.",
            "",
            "## Meanwhile",
            "",
            "None — nothing else to work on.",
            "",
            "## Answer",
            "",
            answer,
            "",
        ]
        return self.write("docs/inbox/%s.md" % slug, "\n".join(lines))

    def tech_debt(self, entries: List[Tuple[str, str, str, str, str, str]]) -> Path:
        """entries: list of (module, path, smell, note, origin_feature, date)."""
        by_module: Dict[str, List[str]] = {}
        for module, path, smell, note, feature, date in entries:
            by_module.setdefault(module, []).append(
                "- `%s` · smell: %s · %s · %s · %s" % (path, smell, note, feature, date)
            )
        lines: List[str] = []
        for module, entry_lines in by_module.items():
            lines.append("## %s" % module)
            lines.append("")
            lines.extend(entry_lines)
            lines.append("")
        return self.write("docs/tech-debt.md", "\n".join(lines))

    def agent_map(
        self,
        name: str = "CLAUDE.md",
        extra_paths: Optional[List[str]] = None,
        filler_lines: int = 0,
        marker_version: int = 1,
    ) -> Path:
        parts = [
            "<!-- sdlc:map:start -->",
            "# Project",
            "",
            "<!-- sdlc:template agent-map %d -->" % marker_version,
            "",
            "Verify: `docs/agents/sdlc.json`.",
        ]
        for p in extra_paths or []:
            parts.append("See `%s`." % p)
        for i in range(filler_lines):
            parts.append("filler line %d" % i)
        parts.append("<!-- sdlc:map:end -->")
        return self.write(name, "\n".join(parts) + "\n")

    def architecture(
        self, modules: Optional[List[Tuple[str, str]]] = None, extra_paths: Optional[List[str]] = None
    ) -> Path:
        lines = ["# Architecture", "", "<!-- sdlc:template architecture 1 -->", "", "## Modules", ""]
        for path, resp in modules or []:
            lines.append("- `%s` · %s" % (path, resp))
        for p in extra_paths or []:
            lines.append("See `%s`." % p)
        return self.write("ARCHITECTURE.md", "\n".join(lines) + "\n")

    def agents_readme(self, doc_names: List[str]) -> Path:
        lines = ["# Agent docs", ""]
        for n in doc_names:
            lines.append("- `docs/agents/%s`" % n)
        return self.write("docs/agents/README.md", "\n".join(lines) + "\n")

    def agent_doc(self, name: str, content: str = "Rules.\n") -> Path:
        return self.write("docs/agents/%s" % name, content)

    def module_dir(self, root: str, module: str, files: Optional[List[str]] = None) -> Path:
        d = self.root / root / module
        d.mkdir(parents=True, exist_ok=True)
        for f in files or ["index.py"]:
            (d / f).write_text("# code\n", encoding="utf-8")
        return d

    # ---- git ----
    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + list(args),
            cwd=str(self.root),
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def git_init(self, branch: str = "main") -> "RepoBuilder":
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/%s" % branch)
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")
        return self

    def git_commit_all(self, message: str = "commit") -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").stdout.decode().strip()
