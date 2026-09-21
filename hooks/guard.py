#!/usr/bin/env python3
"""PreToolUse hook on Bash: in a repository run by the sdlc loop, refuse the
commands that are out of bounds for an agent (escalation case 5). Permission
rules match command prefixes; this matches the whole command, so a force flag
at the end of a push is caught too. Exit 2 blocks the call and shows stderr to
the agent. Silent everywhere else."""
from __future__ import annotations

import json
import os
import re
import sys

# `git -C dir push`, `git -c k=v push`: global options sit between `git` and the verb.
GIT = r"\bgit\s+(?:(?:-[cC]|--git-dir|--work-tree|--namespace)(?:=\S+|\s+\S+)\s+|--\S+\s+|-p\s+)*"

BUILT_IN = [
    (GIT + r"push\b[^|;&]*\s(--force(-with-lease)?(=\S+)?|-f|-[a-zA-Z]*f[a-zA-Z]*)(\s|$)", "force-pushing"),
    (GIT + r"push\b[^|;&]*\s\+\S+", "force-pushing (+refspec)"),
    (GIT + r"(filter-branch|filter-repo)\b", "rewriting history"),
    (GIT + r"push\b[^|;&]*\s(--delete|-d)\b", "deleting a remote branch"),
    (GIT + r"push\b[^|;&]*\s--mirror\b", "mirror-pushing"),
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    repo = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    config_path = os.path.join(repo, "docs", "agents", "sdlc.json")
    if not os.path.isfile(config_path):
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0
    rules = list(BUILT_IN)
    try:
        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)
        main_branch = str(config.get("main_branch") or "main")
        rules.append((GIT + r"branch\s+(-D|-d|--delete)\b[^|;&]*\s%s(\s|$)" % re.escape(main_branch),
                      "deleting the main branch"))
        if config.get("merge") == "human":
            # Where the human merges, a push to the main branch may be a deploy.
            rules.append((GIT + r"push\b[^|;&]*\s(\S+:)?%s(\s|$)" % re.escape(main_branch),
                          "pushing the main branch while `merge` is `human`"))
        for pattern in config.get("forbidden_commands") or []:
            rules.append((str(pattern), "a command this repository forbids (forbidden_commands)"))
    except Exception:
        pass
    for pattern, what in rules:
        try:
            hit = re.search(pattern, command)
        except re.error:
            continue
        if hit:
            sys.stderr.write(
                "BLOCKED by sdlc: %s is out of bounds for an agent in this repository "
                "(docs/agents/escalation.md, case 5). Do not look for another route to the "
                "same effect: file a `question` inbox item and move to other work.\n" % what)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
