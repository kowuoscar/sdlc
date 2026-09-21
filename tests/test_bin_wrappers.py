from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import helpers

BIN_DIR = helpers.BIN_DIR

WRAPPER_NAMES = [
    "sdlc-state",
    "sdlc-check-tickets",
    "sdlc-check-harness",
    "sdlc-test-guard",
    "sdlc-merge-gate",
    "sdlc-lock",
]


class BinWrapperTests(unittest.TestCase):
    def test_all_wrappers_exist_and_are_executable(self):
        for name in WRAPPER_NAMES:
            p = BIN_DIR / name
            self.assertTrue(p.is_file(), name)
            mode = p.stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR, "%s is not executable" % name)

    def test_sdlc_state_runs_and_emits_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = helpers.RepoBuilder(Path(tmp))
            proc = subprocess.run(
                [str(BIN_DIR / "sdlc-state"), "--repo", str(repo.root)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            data = json.loads(proc.stdout.decode())
            self.assertEqual(data["next"]["action"], "init")

    def test_exit_code_2_on_usage_error(self):
        # 'feature' is a required positional argument.
        proc = subprocess.run(
            [str(BIN_DIR / "sdlc-check-tickets")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(proc.returncode, 2)
        data = json.loads(proc.stdout.decode())
        self.assertFalse(data["ok"])

    def test_exit_code_1_on_check_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = helpers.RepoBuilder(Path(tmp))
            repo.config()
            repo.git_init()
            repo.write("src/foo.test.ts", "test('a', () => {});\n")
            base = repo.git_commit_all("base")
            repo.write("src/foo.test.ts", "test('a', () => { expect(1).toBe(1); });\n")
            repo.git_commit_all("modify test")
            proc = subprocess.run(
                [str(BIN_DIR / "sdlc-test-guard"), "--repo", str(repo.root), base],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 1, proc.stderr.decode())
            data = json.loads(proc.stdout.decode())
            self.assertFalse(data["ok"])

    def test_works_through_a_symlinked_path_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            link_dir = Path(tmp) / "linkbin"
            link_dir.mkdir()
            link = link_dir / "sdlc-state"
            os.symlink(str(BIN_DIR / "sdlc-state"), str(link))

            repo = helpers.RepoBuilder(Path(tmp) / "repo")
            proc = subprocess.run(
                [str(link), "--repo", str(repo.root)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
            data = json.loads(proc.stdout.decode())
            self.assertEqual(data["next"]["action"], "init")

    def test_default_repo_is_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = helpers.RepoBuilder(Path(tmp))
            proc = subprocess.run(
                [str(BIN_DIR / "sdlc-state")],
                cwd=str(repo.root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())

    def test_sdlc_lock_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = helpers.RepoBuilder(Path(tmp))
            acquire = subprocess.run(
                [str(BIN_DIR / "sdlc-lock"), "--repo", str(repo.root), "acquire", "--session", "s"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(acquire.returncode, 0, acquire.stderr.decode())
            status = subprocess.run(
                [str(BIN_DIR / "sdlc-lock"), "--repo", str(repo.root), "status"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(status.returncode, 0)
            self.assertTrue(json.loads(status.stdout.decode())["locked"])
            release = subprocess.run(
                [str(BIN_DIR / "sdlc-lock"), "--repo", str(repo.root), "release", "--session", "s"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(release.returncode, 0, release.stderr.decode())


if __name__ == "__main__":
    unittest.main()
