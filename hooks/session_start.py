#!/usr/bin/env python3
"""SessionStart hook: in a repository run by the sdlc loop, tell the session
what waits for the human and what the loop would do next. Silent everywhere
else, and silent on any error: a hook must never break a session."""
from __future__ import annotations

import json
import os
import subprocess
import sys

INBOX_ORDER = ["alert", "question", "approval", "acceptance", "proposal"]


def summarise(state: dict) -> str:
    counts: dict = {}
    for item in state.get("inbox", {}).get("open", []):
        kind = item.get("type", "item") if isinstance(item, dict) else "item"
        counts[kind] = counts.get(kind, 0) + 1
    ordered = [k for k in INBOX_ORDER if k in counts] + sorted(k for k in counts if k not in INBOX_ORDER)
    inbox = ", ".join("%d %s" % (counts[k], k) for k in ordered) or "empty"
    nxt = state.get("next", {})
    action = nxt.get("action", "unknown")
    target = nxt.get("target", "")
    line = "This repository is run by the sdlc delivery loop. Inbox: %s. Next action: %s%s." % (
        inbox, action, (" " + target) if target else "")
    return line + " The user continues the loop with /sdlc; rules for agents are indexed in docs/agents/README.md."


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    repo = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not os.path.isfile(os.path.join(repo, "docs", "agents", "sdlc.json")):
        return 0
    state_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "state.py")
    try:
        proc = subprocess.run([sys.executable, state_py, "--repo", repo],
                              capture_output=True, text=True, timeout=8)
        state = json.loads(proc.stdout)
    except Exception:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": summarise(state),
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
