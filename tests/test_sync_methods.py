"""Tests for tools/sync_methods.py: vendoring upstream methods into methods/.

Builds a fake upstream (a real, local git repository) and a fake destination
root, and drives the tool via subprocess so it never touches the real
methods/ directory of this plugin.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TOOL = os.path.join(ROOT, "tools", "sync_methods.py")


def git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True, capture_output=True, text=True)


def init_git_repo(path):
    os.makedirs(path, exist_ok=True)
    git(["init", "--quiet"], cwd=path)
    git(["config", "user.email", "upstream@example.com"], cwd=path)
    git(["config", "user.name", "Upstream Test"], cwd=path)
    git(["config", "commit.gpgsign", "false"], cwd=path)
    # Default branch name varies by git version/config; pin it.
    git(["checkout", "--quiet", "-B", "main"], cwd=path)


def commit_all(path, message):
    git(["add", "-A"], cwd=path)
    git(["commit", "--quiet", "-m", message], cwd=path)
    return git_rev(path)


def git_rev(path):
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, check=True,
                             capture_output=True, text=True)
    return result.stdout.strip()


def write(path, rel, content):
    full = os.path.join(path, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(content)
    return full


LICENSE_TEXT = "MIT License\n\nCopyright (c) 2026 Matt Pocock\n"


def build_minimal_upstream(root):
    """A fake upstream repo carrying just enough of each METHODS entry to
    exercise the sync: one file per method, one method with an agents/
    subdir to skip, and LICENSE."""
    write(root, "LICENSE", LICENSE_TEXT)
    write(root, "skills/engineering/tdd/SKILL.md", "# tdd v1\n")
    write(root, "skills/engineering/tdd/agents/openai.yaml", "should-be-skipped: true\n")
    write(root, "skills/engineering/diagnosing-bugs/SKILL.md", "# diagnosing-bugs v1\n")
    write(root, "skills/engineering/domain-modeling/SKILL.md", "# domain-modeling v1\n")
    write(root, "skills/productivity/grilling/SKILL.md", "# grilling v1\n")
    write(root, "skills/engineering/to-spec/SKILL.md", "# to-spec v1\n")
    write(root, "skills/engineering/to-tickets/SKILL.md", "# to-tickets v1\n")
    write(root, "skills/in-progress/implement-spec/SKILL.md", "# implement-spec v1\n")
    write(root, "skills/engineering/code-review/SKILL.md", "# code-review v1\n")
    write(root, "skills/engineering/resolving-merge-conflicts/SKILL.md", "# resolving-merge-conflicts v1\n")
    write(root, "skills/in-progress/retro/SKILL.md", "# retro v1\n")
    write(root, "skills/productivity/writing-for-agents/SKILL.md", "# writing-for-agents v1\n")


def run_tool(args):
    result = subprocess.run(
        [sys.executable, TOOL] + args, capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
    except ValueError:
        data = None
    return result.returncode, data, result.stdout, result.stderr


class SyncMethodsTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.upstream = os.path.join(self._tmp.name, "upstream")
        self.dest = os.path.join(self._tmp.name, "dest")
        os.makedirs(self.dest, exist_ok=True)
        init_git_repo(self.upstream)
        build_minimal_upstream(self.upstream)
        self.sha1 = commit_all(self.upstream, "initial methods")

    def tearDown(self):
        self._tmp.cleanup()

    def sync(self, extra=None):
        args = ["--source", self.upstream, "--root", self.dest]
        if extra:
            args += extra
        return run_tool(args)


class FirstSyncTests(SyncMethodsTestCase):
    def test_first_sync_writes_all_methods_and_license(self):
        code, data, _out, _err = self.sync()
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["from_commit"], "")
        self.assertEqual(data["to_commit"], self.sha1)
        for name in ("tdd", "diagnosing-bugs", "domain-modeling", "grilling",
                      "to-spec", "to-tickets", "implement-spec", "code-review",
                      "resolving-merge-conflicts", "retro", "writing-for-agents"):
            self.assertIn(name, data["methods"])
            self.assertTrue(
                os.path.isfile(os.path.join(self.dest, "methods", name, "SKILL.md")),
                "methods/%s/SKILL.md should exist" % name,
            )
        self.assertTrue(os.path.isfile(os.path.join(self.dest, "methods", "LICENSE")))
        with open(os.path.join(self.dest, "methods", "LICENSE"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), LICENSE_TEXT)

    def test_upstream_json_shape(self):
        self.sync()
        with open(os.path.join(self.dest, "methods", "UPSTREAM.json"), encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data["repository"], "mattpocock/skills")
        self.assertEqual(data["commit"], self.sha1)
        self.assertIn("commit_date", data)
        self.assertIn("tdd", data["methods"])
        self.assertEqual(data["methods"]["tdd"]["path"], "skills/engineering/tdd")
        self.assertEqual(data["methods"]["tdd"]["files"], ["SKILL.md"])
        self.assertTrue(data["methods"]["tdd"]["sha256"])

    def test_agents_subdirectory_is_skipped(self):
        self.sync()
        self.assertFalse(
            os.path.exists(os.path.join(self.dest, "methods", "tdd", "agents"))
        )


class IdempotenceTests(SyncMethodsTestCase):
    def test_second_run_reports_no_change_and_is_byte_identical(self):
        self.sync()
        with open(os.path.join(self.dest, "methods", "UPSTREAM.json"), "rb") as handle:
            first_upstream_json = handle.read()
        code, data, _out, _err = self.sync()
        self.assertEqual(code, 0)
        self.assertEqual(data["changed"], [])
        self.assertEqual(data["added"], [])
        self.assertEqual(data["removed"], [])
        with open(os.path.join(self.dest, "methods", "UPSTREAM.json"), "rb") as handle:
            second_upstream_json = handle.read()
        self.assertEqual(first_upstream_json, second_upstream_json)


class UpstreamChangeTests(SyncMethodsTestCase):
    def test_changed_file_is_reflected(self):
        self.sync()
        write(self.upstream, "skills/engineering/tdd/SKILL.md", "# tdd v2\n")
        sha2 = commit_all(self.upstream, "update tdd")
        code, data, _out, _err = self.sync()
        self.assertEqual(code, 0)
        self.assertEqual(data["from_commit"], self.sha1)
        self.assertEqual(data["to_commit"], sha2)
        self.assertIn("tdd/SKILL.md", data["changed"])
        with open(os.path.join(self.dest, "methods", "tdd", "SKILL.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "# tdd v2\n")

    def test_added_file_is_reflected(self):
        self.sync()
        write(self.upstream, "skills/engineering/tdd/tests.md", "# extra guidance\n")
        commit_all(self.upstream, "add tests.md")
        code, data, _out, _err = self.sync()
        self.assertEqual(code, 0)
        self.assertIn("tdd/tests.md", data["added"])
        self.assertTrue(os.path.isfile(os.path.join(self.dest, "methods", "tdd", "tests.md")))

    def test_removed_file_is_reflected(self):
        self.sync()
        write(self.upstream, "skills/engineering/tdd/tests.md", "# extra guidance\n")
        commit_all(self.upstream, "add tests.md")
        self.sync()
        os.remove(os.path.join(self.upstream, "skills/engineering/tdd/tests.md"))
        commit_all(self.upstream, "remove tests.md")
        code, data, _out, _err = self.sync()
        self.assertEqual(code, 0)
        self.assertIn("tdd/tests.md", data["removed"])
        self.assertFalse(os.path.exists(os.path.join(self.dest, "methods", "tdd", "tests.md")))


class ExecutableBitTests(SyncMethodsTestCase):
    def test_executable_bit_is_preserved(self):
        script = write(self.upstream, "skills/engineering/tdd/run.sh", "#!/bin/sh\necho hi\n")
        os.chmod(script, 0o755)
        commit_all(self.upstream, "add executable script")
        self.sync()
        dest_script = os.path.join(self.dest, "methods", "tdd", "run.sh")
        self.assertTrue(os.stat(dest_script).st_mode & stat.S_IXUSR)

    def test_non_executable_file_is_not_made_executable(self):
        self.sync()
        dest_file = os.path.join(self.dest, "methods", "tdd", "SKILL.md")
        self.assertFalse(os.stat(dest_file).st_mode & stat.S_IXUSR)


class MissingUpstreamMethodTests(SyncMethodsTestCase):
    def test_missing_upstream_directory_is_an_error_and_nothing_is_written(self):
        import shutil
        shutil.rmtree(os.path.join(self.upstream, "skills/engineering/tdd"))
        commit_all(self.upstream, "remove tdd upstream")
        code, data, _out, err = self.sync()
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertTrue(any("tdd" in e for e in data["errors"]))
        self.assertIn("tdd", err)
        self.assertFalse(os.path.exists(os.path.join(self.dest, "methods")))


class HandsOffFilesTests(SyncMethodsTestCase):
    def test_gates_json_and_readme_are_never_touched(self):
        self.sync()
        methods_dir = os.path.join(self.dest, "methods")
        write(self.dest, "methods/gates.json", '{"gates": [], "exempt_files": []}')
        write(self.dest, "methods/README.md", "hand maintained\n")
        code, data, _out, _err = self.sync()
        self.assertEqual(code, 0)
        self.assertEqual(data["changed"], [])
        self.assertEqual(data["added"], [])
        self.assertEqual(data["removed"], [])
        with open(os.path.join(methods_dir, "gates.json"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), '{"gates": [], "exempt_files": []}')
        with open(os.path.join(methods_dir, "README.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "hand maintained\n")

        # A further sync with an upstream change must still leave them alone.
        write(self.upstream, "skills/engineering/tdd/SKILL.md", "# tdd v2\n")
        commit_all(self.upstream, "update tdd again")
        self.sync()
        with open(os.path.join(methods_dir, "gates.json"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), '{"gates": [], "exempt_files": []}')
        with open(os.path.join(methods_dir, "README.md"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "hand maintained\n")


class CheckModeTests(SyncMethodsTestCase):
    def test_check_exits_zero_when_up_to_date(self):
        self.sync()
        code, data, _out, _err = self.sync(["--check"])
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])

    def test_check_exits_one_when_out_of_date_and_writes_nothing(self):
        code, data, _out, err = self.sync(["--check"])
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertIn("tdd/SKILL.md", data["added"])
        self.assertFalse(os.path.exists(os.path.join(self.dest, "methods")))
        self.assertTrue(err.strip())

    def test_check_detects_upstream_change(self):
        self.sync()
        write(self.upstream, "skills/engineering/tdd/SKILL.md", "# tdd v2\n")
        commit_all(self.upstream, "update tdd")
        code, data, _out, _err = self.sync(["--check"])
        self.assertEqual(code, 1)
        self.assertIn("tdd/SKILL.md", data["changed"])

    def test_check_against_a_locally_modified_methods_file(self):
        self.sync()
        write(self.dest, "methods/tdd/SKILL.md", "# locally hacked\n")
        code, data, _out, err = self.sync(["--check"])
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertIn("tdd/SKILL.md", data["changed"])
        self.assertTrue(err.strip())

    def test_unrelated_upstream_commit_causes_no_reported_change(self):
        self.sync()
        with open(os.path.join(self.dest, "methods", "UPSTREAM.json"), "rb") as handle:
            before = handle.read()
        write(self.upstream, "unrelated-top-level-file.txt", "nothing to do with us\n")
        commit_all(self.upstream, "unrelated change outside tracked methods")
        code, data, _out, _err = self.sync(["--check"])
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["changed"], [])
        self.assertEqual(data["added"], [])
        self.assertEqual(data["removed"], [])
        with open(os.path.join(self.dest, "methods", "UPSTREAM.json"), "rb") as handle:
            after = handle.read()
        self.assertEqual(before, after)


class SymlinkTests(SyncMethodsTestCase):
    def test_symlink_inside_a_method_directory_is_refused(self):
        target = write(self.upstream, "skills/engineering/tdd/target.md", "real file\n")
        link = os.path.join(self.upstream, "skills/engineering/tdd/link.md")
        os.symlink(target, link)
        commit_all(self.upstream, "add a symlink inside tdd")
        code, data, _out, err = self.sync()
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertTrue(any("upstream-symlink" in e and "tdd" in e for e in data["errors"]))
        self.assertIn("upstream-symlink", err)
        self.assertFalse(os.path.exists(os.path.join(self.dest, "methods")))

    def test_broken_symlink_inside_a_method_directory_is_refused_not_a_crash(self):
        link = os.path.join(self.upstream, "skills/engineering/tdd/broken.md")
        os.symlink(os.path.join(self.upstream, "skills/engineering/tdd/does-not-exist.md"), link)
        commit_all(self.upstream, "add a broken symlink inside tdd")
        code, data, out, err = self.sync()
        self.assertEqual(code, 1)
        # Stdout must still be valid JSON, not a traceback.
        self.assertIsNotNone(data, "stdout was not valid JSON: %r" % out)
        self.assertFalse(data["ok"])
        self.assertTrue(any("upstream-symlink" in e for e in data["errors"]))
        self.assertIn("upstream-symlink", err)
        self.assertFalse(os.path.exists(os.path.join(self.dest, "methods")))


class CRLFTests(SyncMethodsTestCase):
    def test_crlf_content_is_preserved_byte_for_byte(self):
        full = os.path.join(self.upstream, "skills/engineering/tdd", "crlf.md")
        with open(full, "wb") as handle:
            handle.write(b"line one\r\nline two\r\n")
        commit_all(self.upstream, "add a CRLF file")
        self.sync()
        with open(os.path.join(self.dest, "methods", "tdd", "crlf.md"), "rb") as handle:
            self.assertEqual(handle.read(), b"line one\r\nline two\r\n")


class EmptyDirectoryPruningTests(SyncMethodsTestCase):
    def test_a_subdirectory_left_empty_by_removal_is_pruned(self):
        write(self.upstream, "skills/engineering/tdd/nested/deep.md", "deep content\n")
        commit_all(self.upstream, "add a nested file")
        self.sync()
        self.assertTrue(os.path.isdir(os.path.join(self.dest, "methods", "tdd", "nested")))
        os.remove(os.path.join(self.upstream, "skills/engineering/tdd/nested/deep.md"))
        os.rmdir(os.path.join(self.upstream, "skills/engineering/tdd/nested"))
        commit_all(self.upstream, "remove the nested file")
        self.sync()
        self.assertFalse(os.path.exists(os.path.join(self.dest, "methods", "tdd", "nested")))


if __name__ == "__main__":
    unittest.main()
