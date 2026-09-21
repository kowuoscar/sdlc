"""Tests of the plugin hooks: the out-of-bounds guard and the session-start summary."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GUARD = os.path.join(ROOT, "hooks", "guard.py")
SESSION_START = os.path.join(ROOT, "hooks", "session_start.py")

sys.path.insert(0, os.path.join(ROOT, "hooks"))
import session_start  # noqa: E402


def run_hook(script, payload):
    return subprocess.run([sys.executable, script], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=30)


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        os.makedirs(os.path.join(self.repo, "docs", "agents"))
        self.write_config({"verify": "true"})

    def tearDown(self):
        self.tmp.cleanup()

    def write_config(self, config):
        with open(os.path.join(self.repo, "docs", "agents", "sdlc.json"), "w", encoding="utf-8") as handle:
            json.dump(config, handle)

    def guard(self, command, cwd=None):
        return run_hook(GUARD, {"cwd": cwd or self.repo, "tool_input": {"command": command}})

    def test_blocks_force_push_wherever_the_flag_sits(self):
        for command in ("git push --force", "git push -f origin main", "git push origin main --force",
                        "git push origin main --force-with-lease", "git push origin +main"):
            with self.subTest(command=command):
                result = self.guard(command)
                self.assertEqual(result.returncode, 2)
                self.assertIn("BLOCKED", result.stderr)

    def test_git_global_options_do_not_hide_the_verb(self):
        for command in ("git -C . push --force origin main", "git -c core.pager=cat push --force",
                        "git --no-pager push origin +main", "git -C sub filter-branch --tree-filter x HEAD",
                        "git -C . branch -D main", "git push -uf origin feature/x", "git push --mirror"):
            with self.subTest(command=command):
                self.assertEqual(self.guard(command).returncode, 2)

    def test_blocks_history_rewriting_and_deleting_main(self):
        for command in ("git filter-branch --tree-filter x HEAD", "git branch -D main",
                        "git push origin --delete feature/x"):
            with self.subTest(command=command):
                self.assertEqual(self.guard(command).returncode, 2)

    def test_allows_everyday_commands(self):
        for command in ("git push origin feature/x", "git status", "git branch -D ticket/charge-card",
                        "npm test -- --force", "echo git push is fine to mention"):
            with self.subTest(command=command):
                self.assertEqual(self.guard(command).returncode, 0)

    def test_main_branch_comes_from_the_config(self):
        self.write_config({"verify": "true", "main_branch": "trunk"})
        self.assertEqual(self.guard("git branch -D trunk").returncode, 2)
        self.assertEqual(self.guard("git branch -D main").returncode, 0)

    def test_pushing_main_is_blocked_only_where_the_human_merges(self):
        self.assertEqual(self.guard("git push origin main").returncode, 0)
        self.write_config({"verify": "true", "merge": "human"})
        for command in ("git push origin main", "git push origin HEAD:main", "git push -u origin main"):
            with self.subTest(command=command):
                self.assertEqual(self.guard(command).returncode, 2)
        self.assertEqual(self.guard("git push origin feature/maintenance-page").returncode, 0)
        self.assertEqual(self.guard("git push origin feature/x").returncode, 0)

    def test_forbidden_commands_from_the_config(self):
        self.write_config({"verify": "true", "forbidden_commands": [r"\bvercel\b", "("]})
        self.assertEqual(self.guard("vercel deploy --prod").returncode, 2)
        self.assertEqual(self.guard("git status").returncode, 0, "an invalid pattern is skipped, not fatal")

    def test_silent_outside_a_repository_run_by_the_loop(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            result = self.guard("git push --force", cwd=elsewhere)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_malformed_input_never_blocks(self):
        result = subprocess.run([sys.executable, GUARD], input="not json", capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)


class SessionStartTest(unittest.TestCase):
    def test_summary_orders_the_inbox_and_names_the_next_action(self):
        state = {"inbox": {"open": [{"id": "walk-card-checkout", "type": "acceptance", "blocks": []},
                                    {"id": "refund", "type": "question", "blocks": ["refunds"]},
                                    {"id": "currency", "type": "question", "blocks": ["refunds"]},
                                    {"id": "main-reverted", "type": "alert", "blocks": []}]},
                 "next": {"action": "execute", "target": "card-checkout"}}
        line = session_start.summarise(state)
        self.assertIn("Inbox: 1 alert, 2 question, 1 acceptance.", line)
        self.assertIn("Next action: execute card-checkout.", line)

    def test_summary_of_an_empty_inbox(self):
        line = session_start.summarise({"inbox": {"open": []}, "next": {"action": "idle", "target": ""}})
        self.assertIn("Inbox: empty.", line)
        self.assertIn("Next action: idle.", line)

    def test_silent_outside_a_repository_run_by_the_loop(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            result = run_hook(SESSION_START, {"cwd": elsewhere})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_end_to_end_against_the_real_state_script(self):
        """The summary must read the shape state.py really produces, not a shape invented here."""
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "docs", "agents"))
            os.makedirs(os.path.join(repo, "docs", "inbox"))
            with open(os.path.join(repo, "docs", "agents", "sdlc.json"), "w", encoding="utf-8") as handle:
                json.dump({"schema": 1, "verify": "true"}, handle)
            with open(os.path.join(repo, "docs", "inbox", "refund.md"), "w", encoding="utf-8") as handle:
                handle.write("---\nid: refund\ntype: question\nstatus: open\nblocks: []\n"
                             "created: 2026-01-31\n---\n\n## Question\nRefund in part?\n")
            result = run_hook(SESSION_START, {"cwd": repo})
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn("Inbox: 1 question.", output["additionalContext"])
        self.assertIn("Next action:", output["additionalContext"])


if __name__ == "__main__":
    unittest.main()
