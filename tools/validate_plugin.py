#!/usr/bin/env python3
"""Structural validation of this plugin, for CI and before a release.

Checks what no unit test of the scripts can: that the prose parts of the
plugin agree with each other. A phase the dispatcher names must exist; an agent
a phase spawns must be defined, with the model the dispatcher's table promises;
a template a phase instantiates must ship, parse and carry its marker.

Standard library only. Prints one JSON document; exit 0 ok, 1 failed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_method_gates  # noqa: E402
import sync_methods  # noqa: E402

METHODS_PATH = re.compile(r"`(methods/[A-Za-z0-9_./-]+)`")

ACTIONS = ["init", "intention", "apply-answers", "plan-epic", "spec", "ticket",
           "execute", "deliver", "close-epic", "pause", "wait", "idle"]
MODELS = {"haiku", "sonnet", "opus", "inherit"}
KNOWN_TOOLS = {"Read", "Write", "Edit", "Bash", "Grep", "Glob", "Skill", "WebFetch", "WebSearch"}
BINARIES = ["sdlc-state", "sdlc-check-tickets", "sdlc-check-harness",
            "sdlc-test-guard", "sdlc-merge-gate", "sdlc-lock"]
SEMVER = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
MARKER = re.compile(r"<!--\s*sdlc:template\s+([a-z0-9-]+)\s+(\d+)\s*-->")


class Report:
    def __init__(self) -> None:
        self.errors: list = []
        self.warnings: list = []

    def error(self, code: str, path: str, message: str) -> None:
        self.errors.append({"code": code, "path": path, "message": message})

    def warn(self, code: str, path: str, message: str) -> None:
        self.warnings.append({"code": code, "path": path, "message": message})


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    out = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load_json(root: str, rel: str, report: Report):
    try:
        return json.loads(read(os.path.join(root, rel)))
    except FileNotFoundError:
        report.error("file-missing", rel, "required file is missing")
    except ValueError as exc:
        report.error("json-invalid", rel, str(exc))
    return None


def check_manifests(root: str, report: Report) -> str:
    version = ""
    plugin = load_json(root, ".claude-plugin/plugin.json", report)
    if plugin is not None:
        name = plugin.get("name", "")
        if not KEBAB.match(str(name)):
            report.error("plugin-name", ".claude-plugin/plugin.json", "name must be kebab-case")
        version = str(plugin.get("version", ""))
        if not SEMVER.match(version):
            report.error("plugin-version", ".claude-plugin/plugin.json", "version must be semver")
        if not plugin.get("description"):
            report.error("plugin-description", ".claude-plugin/plugin.json", "description is required")
    market = load_json(root, ".claude-plugin/marketplace.json", report)
    if market is not None and plugin is not None:
        names = [p.get("name") for p in market.get("plugins", [])]
        if plugin.get("name") not in names:
            report.error("marketplace-plugin", ".claude-plugin/marketplace.json",
                         "marketplace does not list the plugin %r" % plugin.get("name"))
        for entry in market.get("plugins", []):
            source = entry.get("source")
            if isinstance(source, str) and not os.path.isdir(os.path.join(root, source)):
                report.error("marketplace-source", ".claude-plugin/marketplace.json",
                             "source %r is not a directory" % source)
    return version


def check_changelog(root: str, version: str, report: Report) -> None:
    path = os.path.join(root, "CHANGELOG.md")
    if not os.path.isfile(path):
        report.error("file-missing", "CHANGELOG.md", "required file is missing")
        return
    found = re.search(r"^## \[?(\d+\.\d+\.\d+[^\]\s]*)\]?", read(path), re.M)
    if not found:
        report.error("changelog-empty", "CHANGELOG.md", "no version heading found")
    elif version and found.group(1) != version:
        report.error("version-mismatch", "CHANGELOG.md",
                     "latest changelog entry is %s but plugin.json says %s" % (found.group(1), version))


def check_agents(root: str, report: Report) -> dict:
    models = {}
    folder = os.path.join(root, "agents")
    for filename in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not filename.endswith(".md"):
            continue
        rel = "agents/" + filename
        text = read(os.path.join(folder, filename))
        meta = frontmatter(text)
        name = meta.get("name", "")
        if name != filename[:-3]:
            report.error("agent-name", rel, "frontmatter name %r must equal the filename" % name)
        if len(meta.get("description", "")) < 40:
            report.error("agent-description", rel, "description is missing or too short to trigger on")
        model = meta.get("model", "")
        if model not in MODELS:
            report.error("agent-model", rel, "model %r is not one of %s" % (model, sorted(MODELS)))
        for tool in [t.strip() for t in meta.get("tools", "").split(",") if t.strip()]:
            if tool not in KNOWN_TOOLS:
                report.warn("agent-tool", rel, "unknown tool %r" % tool)
        if not meta.get("maxTurns", "").isdigit():
            report.error("agent-max-turns", rel, "maxTurns must bound every agent")
        if "```json" not in text:
            report.error("agent-result", rel, "an agent must specify the fenced json result it returns")
        models[name] = model
    if not models:
        report.error("agents-missing", "agents/", "no agent definitions found")
    return models


def check_links(root: str, rel: str, report: Report) -> None:
    base = os.path.dirname(os.path.join(root, rel))
    for target in MD_LINK.findall(read(os.path.join(root, rel))):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            continue
        target = target.split("#")[0]
        if target and not os.path.exists(os.path.join(base, target)):
            report.error("link-broken", rel, "relative link %r does not resolve" % target)


def check_skill(root: str, agent_models: dict, report: Report) -> None:
    rel = "skills/sdlc/SKILL.md"
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        report.error("file-missing", rel, "required file is missing")
        return
    text = read(path)
    meta = frontmatter(text)
    if meta.get("name") != "sdlc":
        report.error("skill-name", rel, "skill name must be sdlc")
    if not meta.get("description"):
        report.error("skill-description", rel, "description is required")
    for action in ACTIONS:
        if "`%s`" % action not in text:
            report.error("action-undispatched", rel, "next.action `%s` has no row in the dispatch table" % action)
    for name, model in re.findall(r"^\|\s*`([a-z-]+)`\s*\|\s*([a-z]+)\s*\|", text, re.M):
        if name in agent_models and agent_models[name] != model:
            report.error("model-mismatch", rel, "table says %s runs on %s, agents/%s.md says %s"
                         % (name, model, name, agent_models[name]))
    for name in agent_models:
        if "`%s`" % name not in text:
            report.error("agent-unlisted", rel, "agent %s is missing from the Subagents table" % name)
    phases = os.path.join(root, "skills/sdlc/phases")
    for filename in sorted(os.listdir(phases)) if os.path.isdir(phases) else []:
        if filename.endswith(".md") and "phases/%s" % filename not in text:
            report.error("phase-orphan", "skills/sdlc/phases/" + filename, "no pointer to this phase in SKILL.md")


def check_prose_references(root: str, agent_models: dict, report: Report) -> None:
    files = ["skills/sdlc/SKILL.md"]
    for folder in ("skills/sdlc/phases", "agents"):
        full = os.path.join(root, folder)
        if os.path.isdir(full):
            files += [folder + "/" + f for f in sorted(os.listdir(full)) if f.endswith(".md")]
    for rel in files:
        text = read(os.path.join(root, rel))
        check_links(root, rel, report)
        for template in set(re.findall(r"`templates/([A-Za-z0-9_./*-]+)`", text)):
            if "*" in template:
                continue
            if not os.path.exists(os.path.join(root, "skills/sdlc/templates", template)):
                report.error("template-missing", rel, "refers to templates/%s, which does not ship" % template)
        for agent in set(re.findall(r"`sdlc:([a-z-]+)`", text)):
            if agent not in agent_models:
                report.error("agent-undefined", rel, "spawns sdlc:%s, which is not defined" % agent)
        for binary in set(re.findall(r"`(sdlc-[a-z-]+)", text)):
            if binary not in BINARIES:
                report.error("binary-unknown", rel, "calls %s, which is not a shipped executable" % binary)
        for path in set(METHODS_PATH.findall(text)):
            if not os.path.exists(os.path.join(root, path)):
                report.error("methods-path-missing", rel, "refers to `%s`, which does not exist" % path)


def check_templates(root: str, report: Report) -> None:
    base = os.path.join(root, "skills/sdlc/templates")
    names = {}
    for folder, _dirs, filenames in os.walk(base):
        for filename in sorted(filenames):
            full = os.path.join(folder, filename)
            rel = os.path.relpath(full, root)
            text = read(full)
            if filename.endswith(".json"):
                try:
                    data = json.loads(text)
                except ValueError as exc:
                    report.error("json-invalid", rel, str(exc))
                    continue
                if not re.match(r"^[a-z0-9-]+ \d+$", str(data.get("template", ""))):
                    report.error("marker-missing", rel, 'JSON templates carry "template": "<name> <version>"')
                else:
                    names.setdefault(data["template"].split()[0], []).append(rel)
            elif filename.endswith(".md") and os.path.basename(folder) != "stacks":
                found = MARKER.search(text)
                if not found:
                    report.error("marker-missing", rel, "template has no <!-- sdlc:template name version --> marker")
                else:
                    names.setdefault(found.group(1), []).append(rel)
    for name, paths in sorted(names.items()):
        # Ready-made tickets are instances of the ticket shape and share its marker.
        paths = [p for p in paths if "/templates/tickets/" not in p.replace(os.sep, "/")] or paths[:1]
        if len(paths) > 1:
            report.error("marker-duplicate", paths[1], "marker name %r is also used by %s" % (name, paths[0]))


def check_methods(root: str, report: Report) -> None:
    methods_dir = os.path.join(root, "methods")

    upstream = load_json(root, "methods/UPSTREAM.json", report)
    if upstream is not None and not isinstance(upstream, dict):
        report.error("json-invalid", "methods/UPSTREAM.json", "must be a JSON object")

    for name in sorted(sync_methods.METHODS):
        skill_path = os.path.join(methods_dir, name, "SKILL.md")
        if not os.path.isfile(skill_path):
            report.error("method-missing", "methods/%s" % name,
                         "no SKILL.md found for method %r (upstream %s)" % (name, sync_methods.METHODS[name]))

    if not os.path.isfile(os.path.join(methods_dir, "LICENSE")):
        report.error("file-missing", "methods/LICENSE", "required file is missing")

    gate_result = check_method_gates.check_gates(root)
    if not gate_result["ok"]:
        for entry in gate_result["errors"]:
            path = "methods/" + entry["path"] if entry["path"] else "methods"
            report.error("method-gate-%s" % entry["code"], path, entry["message"])

    # A vendored method placed under skills/ (rather than methods/) would
    # register as a skill Claude Code invokes on its own -- the whole point
    # of vendoring under methods/ is to avoid that.
    skills_dir = os.path.join(root, "skills")
    for folder, _dirs, filenames in os.walk(skills_dir):
        for filename in filenames:
            if filename != "SKILL.md":
                continue
            rel = os.path.relpath(os.path.join(folder, filename), root).replace(os.sep, "/")
            if rel != "skills/sdlc/SKILL.md":
                report.error("skill-under-skills", rel,
                             "only skills/sdlc/SKILL.md may exist under skills/; "
                             "a vendored method here would register as a skill")


def check_shipped_text(root: str, report: Report) -> None:
    for top in ("skills", "agents", "hooks", "bin", "scripts", "methods"):
        for folder, _dirs, filenames in os.walk(os.path.join(root, top)):
            if "__pycache__" in folder:
                continue
            for filename in filenames:
                full = os.path.join(folder, filename)
                try:
                    text = read(full)
                except (UnicodeDecodeError, OSError):
                    continue
                if re.search(r"/Users/[A-Za-z]|/home/[a-z]+/", text):
                    report.error("absolute-path", os.path.relpath(full, root),
                                 "shipped file contains a machine-specific absolute path")


def check_hooks_and_bin(root: str, report: Report) -> None:
    hooks = load_json(root, "hooks/hooks.json", report)
    if hooks is not None:
        for script in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)", json.dumps(hooks)):
            if not os.path.isfile(os.path.join(root, script)):
                report.error("hook-script-missing", "hooks/hooks.json", "%s does not exist" % script)
    for binary in BINARIES:
        full = os.path.join(root, "bin", binary)
        if not os.path.isfile(full):
            report.error("binary-missing", "bin/" + binary, "executable does not exist")
        elif not os.stat(full).st_mode & stat.S_IXUSR:
            report.error("binary-not-executable", "bin/" + binary, "executable bit is not set")


def validate(root: str) -> Report:
    report = Report()
    version = check_manifests(root, report)
    check_changelog(root, version, report)
    agent_models = check_agents(root, report)
    check_skill(root, agent_models, report)
    check_prose_references(root, agent_models, report)
    check_templates(root, report)
    check_methods(root, report)
    check_shipped_text(root, report)
    check_hooks_and_bin(root, report)
    for rel in ("README.md", "LICENSE", "docs/contracts.md"):
        if not os.path.isfile(os.path.join(root, rel)):
            report.error("file-missing", rel, "required file is missing")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    args = parser.parse_args()
    report = validate(os.path.abspath(args.root))
    for entry in report.errors:
        sys.stderr.write("error  %-22s %s: %s\n" % (entry["code"], entry["path"], entry["message"]))
    for entry in report.warnings:
        sys.stderr.write("warn   %-22s %s: %s\n" % (entry["code"], entry["path"], entry["message"]))
    print(json.dumps({"ok": not report.errors, "errors": report.errors, "warnings": report.warnings}, indent=2))
    return 0 if not report.errors else 1


if __name__ == "__main__":
    sys.exit(main())
