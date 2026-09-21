from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import helpers

from sdlc_lib.checks_testguard import check_test_guard
from sdlc_lib.config import DEFAULTS
from sdlc_lib.result import Result


def _git_available() -> bool:
    return shutil.which("git") is not None


@unittest.skipUnless(_git_available(), "git is required for test_guard tests")
class TestGuardTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = helpers.RepoBuilder(Path(self._tmp.name))
        self.repo.git_init()
        self.config = dict(DEFAULTS)

    def tearDown(self):
        self._tmp.cleanup()

    def check(self, base, head="HEAD"):
        result = Result()
        check_test_guard(self.repo.root, base, head, self.config, result)
        return result

    def codes(self, result, bucket="errors"):
        return [d.code for d in getattr(result, bucket)]


class NotAGitRepoTests(unittest.TestCase):
    def test_not_a_git_repo_is_fatal(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            repo = helpers.RepoBuilder(Path(tmp.name))
            result = Result()
            check_test_guard(repo.root, "main", "HEAD", dict(DEFAULTS), result)
            self.assertEqual(result.exit_code(), 2)
            self.assertEqual([d.code for d in result.errors], ["not-a-git-repo"])
        finally:
            tmp.cleanup()


class UnknownRefTests(TestGuardTestCase):
    def test_unknown_ref_is_fatal(self):
        self.repo.write("README.md", "hello\n")
        self.repo.git_commit_all("init")
        result = self.check("does-not-exist-ref")
        self.assertEqual(result.exit_code(), 2)
        self.assertEqual(self.codes(result), ["unknown-ref"])


class DiffTests(TestGuardTestCase):
    def _base_commit(self):
        self.repo.write("src/foo.test.ts", "test('a', () => {});\n")
        self.repo.write("src/foo.ts", "export const a = 1;\n")
        return self.repo.git_commit_all("base")

    def test_clean_diff_is_ok(self):
        base = self._base_commit()
        self.repo.write("src/foo.ts", "export const a = 2;\n")
        self.repo.git_commit_all("tweak non-test file")
        result = self.check(base)
        self.assertTrue(result.ok, result.to_dict())

    def test_modified_test_file_is_reported(self):
        base = self._base_commit()
        self.repo.write("src/foo.test.ts", "test('a', () => { expect(1).toBe(1); });\n")
        self.repo.git_commit_all("modify test")
        result = self.check(base)
        self.assertIn("test-modified", self.codes(result))
        self.assertFalse(result.ok)

    def test_deleted_test_file_is_reported(self):
        base = self._base_commit()
        self.repo.git("rm", "-q", "src/foo.test.ts")
        self.repo.git_commit_all("delete test")
        result = self.check(base)
        self.assertIn("test-deleted", self.codes(result))

    def test_renamed_test_file_is_reported(self):
        base = self._base_commit()
        self.repo.git("mv", "src/foo.test.ts", "src/bar.test.ts")
        self.repo.git_commit_all("rename test")
        result = self.check(base)
        self.assertIn("test-renamed", self.codes(result))

    def test_added_test_file_is_not_reported(self):
        base = self._base_commit()
        self.repo.write("src/new.test.ts", "test('b', () => {});\n")
        self.repo.git_commit_all("add new test")
        result = self.check(base)
        self.assertNotIn("test-modified", self.codes(result))
        self.assertNotIn("test-deleted", self.codes(result))
        self.assertNotIn("test-renamed", self.codes(result))
        self.assertTrue(result.ok, result.to_dict())

    def test_skip_marker_added_is_reported(self):
        base = self._base_commit()
        self.repo.write("src/foo.test.ts", "test.skip('a', () => {});\n")
        self.repo.git_commit_all("skip a test")
        result = self.check(base)
        self.assertIn("skip-marker-added", self.codes(result))
        # This also counts as a modification of an existing test file.
        self.assertIn("test-modified", self.codes(result))

    def test_pytest_mark_skip_is_reported(self):
        self.repo.write("tests/test_foo.py", "def test_a():\n    assert 1 == 1\n")
        base = self.repo.git_commit_all("base py")
        self.repo.write(
            "tests/test_foo.py",
            "import pytest\n\n@pytest.mark.skip\ndef test_a():\n    assert 1 == 1\n",
        )
        self.repo.git_commit_all("skip py test")
        result = self.check(base)
        self.assertIn("skip-marker-added", self.codes(result))

    def test_globs_support_double_star(self):
        self.config["test_globs"] = ["**/src/test/**"]
        self.repo.write("a/src/test/foo.ts", "test\n")
        base = self.repo.git_commit_all("base globs")
        self.repo.write("a/src/test/foo.ts", "test 2\n")
        self.repo.git_commit_all("modify")
        result = self.check(base)
        self.assertIn("test-modified", self.codes(result))

    def test_todo_marker_is_reported(self):
        base = self._base_commit()
        self.repo.write("src/foo.test.ts", "test.todo('a');\n")
        self.repo.git_commit_all("todo a test")
        result = self.check(base)
        self.assertIn("skip-marker-added", self.codes(result))

    def test_xtest_marker_is_reported(self):
        base = self._base_commit()
        self.repo.write("src/foo.test.ts", "xtest('a', () => {});\n")
        self.repo.git_commit_all("xtest a test")
        result = self.check(base)
        self.assertIn("skip-marker-added", self.codes(result))

    def test_go_skipf_marker_is_reported(self):
        self.repo.write("pkg/foo_test.go", "func TestA(t *testing.T) {}\n")
        base = self.repo.git_commit_all("base go")
        self.repo.write("pkg/foo_test.go", "func TestA(t *testing.T) { t.Skipf(\"reason\") }\n")
        self.repo.git_commit_all("skipf go test")
        result = self.check(base)
        self.assertIn("skip-marker-added", self.codes(result))

    def test_go_skipnow_marker_is_reported(self):
        self.repo.write("pkg/foo_test.go", "func TestA(t *testing.T) {}\n")
        base = self.repo.git_commit_all("base go")
        self.repo.write("pkg/foo_test.go", "func TestA(t *testing.T) { t.SkipNow() }\n")
        self.repo.git_commit_all("skipnow go test")
        result = self.check(base)
        self.assertIn("skip-marker-added", self.codes(result))

    def test_dotnet_disabled_property_marker_is_reported(self):
        self.repo.write("Tests/FooTests.cs", "public class FooTests {}\n")
        base = self.repo.git_commit_all("base cs")
        self.repo.write("Tests/FooTests.cs", "public class FooTests { test.Disabled = true; }\n")
        self.repo.git_commit_all("disable cs test")
        result = self.check(base)
        self.assertIn("skip-marker-added", self.codes(result))

    def test_enabled_equals_false_marker_is_reported(self):
        self.repo.write("Tests/FooTests.cs", "public class FooTests {}\n")
        base = self.repo.git_commit_all("base cs enabled")
        self.repo.write("Tests/FooTests.cs", "public class FooTests { enabled = false; }\n")
        self.repo.git_commit_all("disable via enabled flag")
        result = self.check(base)
        self.assertIn("skip-marker-added", self.codes(result))

    def test_whitespace_around_dot_and_before_paren_is_tolerated(self):
        base = self._base_commit()
        self.repo.write("src/foo.test.ts", "test . skip ('a', () => {});\n")
        self.repo.git_commit_all("skip with whitespace")
        result = self.check(base)
        self.assertIn("skip-marker-added", self.codes(result))


if __name__ == "__main__":
    unittest.main()
