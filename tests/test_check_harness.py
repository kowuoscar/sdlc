from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import helpers

from sdlc_lib.checks_harness import check_harness, normalize_path_token
from sdlc_lib.config import DEFAULTS
from sdlc_lib.result import Result


class PathTokenHeuristicTests(unittest.TestCase):
    def test_slash_is_a_path(self):
        self.assertEqual(normalize_path_token("src/foo.ts"), "src/foo.ts")

    def test_extension_without_slash_is_a_path(self):
        self.assertEqual(normalize_path_token("README.md"), "README.md")

    def test_bare_word_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("verify"))

    def test_placeholder_with_angle_brackets_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("<feature>/spec.md"))

    def test_glob_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("src/**/*.ts"))

    def test_url_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("https://example.com/readme.md"))

    def test_home_relative_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("~/foo/bar.txt"))

    def test_token_with_spaces_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("npm run verify"))

    def test_trailing_line_suffix_is_stripped(self):
        self.assertEqual(normalize_path_token("src/foo.ts:42"), "src/foo.ts")

    def test_trailing_line_col_suffix_is_stripped(self):
        self.assertEqual(normalize_path_token("src/foo.ts:42:7"), "src/foo.ts")

    def test_dollar_sign_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("$HOME/foo.ts"))

    def test_version_number_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("3.9"))

    def test_semver_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("0.1.0"))

    def test_unknown_extension_is_not_a_path(self):
        self.assertIsNone(normalize_path_token("user.save"))

    def test_known_extension_lock_is_a_path(self):
        self.assertEqual(normalize_path_token("package.lock"), "package.lock")

    def test_known_extension_yaml_is_a_path(self):
        self.assertEqual(normalize_path_token("config.yaml"), "config.yaml")


class CheckHarnessTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = helpers.RepoBuilder(Path(self._tmp.name))
        self.config = dict(DEFAULTS)

    def tearDown(self):
        self._tmp.cleanup()

    def check(self):
        result = Result()
        check_harness(self.repo.root, self.config, result)
        return result

    def codes(self, result, bucket="errors"):
        return [d.code for d in getattr(result, bucket)]


class ValidHarnessTests(CheckHarnessTestCase):
    def test_fully_valid_harness_is_ok(self):
        self.repo.agent_map(extra_paths=["docs/agents/sdlc.json"])
        self.repo.architecture(modules=[("src/payments", "handles payments")])
        self.repo.agents_readme(["coding-standards.md"])
        self.repo.agent_doc("coding-standards.md")
        self.repo.config()
        self.repo.module_dir("src", "payments")
        self.config["module_roots"] = ["src"]
        result = self.check()
        self.assertTrue(result.ok, result.to_dict())


class PathMissingTests(CheckHarnessTestCase):
    def test_path_missing_in_root_map(self):
        self.repo.agent_map(extra_paths=["src/does-not-exist.ts"])
        result = self.check()
        self.assertIn("path-missing", self.codes(result))

    def test_path_missing_in_architecture(self):
        self.repo.architecture(extra_paths=["src/ghost.ts"])
        result = self.check()
        self.assertIn("path-missing", self.codes(result))

    def test_placeholder_path_is_not_flagged(self):
        self.repo.architecture(modules=[("<src/module>", "placeholder")])
        result = self.check()
        self.assertNotIn("path-missing", self.codes(result))


class AgentDocUnlistedTests(CheckHarnessTestCase):
    def test_unlisted_doc_is_an_error(self):
        self.repo.agents_readme([])
        self.repo.agent_doc("review.md")
        result = self.check()
        self.assertIn("agent-doc-unlisted", self.codes(result))

    def test_listed_doc_is_fine(self):
        self.repo.agents_readme(["review.md"])
        self.repo.agent_doc("review.md")
        result = self.check()
        self.assertNotIn("agent-doc-unlisted", self.codes(result))


class ModuleRootsTests(CheckHarnessTestCase):
    def test_undocumented_module_is_an_error(self):
        self.repo.module_dir("src", "payments")
        self.repo.architecture(modules=[])
        self.config["module_roots"] = ["src"]
        result = self.check()
        self.assertIn("module-undocumented", self.codes(result))

    def test_documented_module_is_fine(self):
        self.repo.module_dir("src", "payments")
        self.repo.architecture(modules=[("src/payments", "does payments")])
        self.config["module_roots"] = ["src"]
        result = self.check()
        self.assertNotIn("module-undocumented", self.codes(result))

    def test_empty_module_roots_is_a_warning(self):
        self.config["module_roots"] = []
        result = self.check()
        self.assertIn("module-roots-empty", self.codes(result, "warnings"))


class MapLengthTests(CheckHarnessTestCase):
    def test_map_too_long_is_an_error(self):
        self.config["map_max_lines"] = 5
        self.repo.agent_map(filler_lines=20)
        result = self.check()
        self.assertIn("map-too-long", self.codes(result))

    def test_map_missing_is_a_warning(self):
        result = self.check()
        self.assertIn("map-missing", self.codes(result, "warnings"))


if __name__ == "__main__":
    unittest.main()
