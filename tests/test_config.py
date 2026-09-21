from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import helpers

from sdlc_lib.config import DEFAULTS, load_config
from sdlc_lib.result import Result


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = helpers.RepoBuilder(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_not_required_returns_none_without_error(self):
        result = Result()
        cfg = load_config(self.repo.root, result, required=False)
        self.assertIsNone(cfg)
        self.assertFalse(result.fatal)
        self.assertEqual(result.errors, [])

    def test_missing_required_is_fatal(self):
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertIsNone(cfg)
        self.assertTrue(result.fatal)
        self.assertEqual(result.errors[0].code, "config-missing")

    def test_defaults_applied(self):
        self.repo.config()
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertFalse(result.fatal)
        self.assertEqual(cfg["schema"], 1)
        self.assertEqual(cfg["max_implementers"], DEFAULTS["max_implementers"])
        self.assertEqual(cfg["module_roots"], DEFAULTS["module_roots"])
        self.assertEqual(cfg["skills"], DEFAULTS["skills"])
        self.assertEqual(cfg["pull_requests"], False)
        self.assertEqual(cfg["forbidden_commands"], [])

    def test_default_test_globs_matches_contract_section_3(self):
        self.repo.config()
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertFalse(result.fatal)
        self.assertEqual(
            cfg["test_globs"],
            [
                "**/*.test.*",
                "**/*.spec.*",
                "**/*_test.go",
                "**/src/test/**",
                "**/test_*.py",
                "**/*_test.py",
                "**/tests/**",
                "**/__tests__/**",
                "**/*Test.java",
                "**/*Tests.java",
                "**/*IT.java",
                "**/*_spec.rb",
                "**/*Tests.cs",
            ],
        )

    def test_verify_missing_is_fatal(self):
        self.repo.write_json("docs/agents/sdlc.json", {"schema": 1})
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertIsNone(cfg)
        self.assertTrue(result.fatal)
        self.assertEqual(result.errors[0].code, "config-missing-verify")

    def test_bad_json_is_fatal(self):
        self.repo.write("docs/agents/sdlc.json", "{not json")
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertIsNone(cfg)
        self.assertTrue(result.fatal)
        self.assertEqual(result.errors[0].code, "config-invalid-json")

    def test_unsupported_schema_is_fatal(self):
        self.repo.config(schema=2)
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertIsNone(cfg)
        self.assertTrue(result.fatal)
        self.assertEqual(result.errors[0].code, "config-unsupported-schema")

    def test_unknown_keys_preserved_and_ignored(self):
        self.repo.config(template="sdlc-config 1", some_future_key="x")
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertFalse(result.fatal)
        self.assertEqual(cfg["template"], "sdlc-config 1")
        self.assertEqual(cfg["some_future_key"], "x")

    def test_invalid_enum_is_fatal(self):
        self.repo.config(spec_gate="sometimes")
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertIsNone(cfg)
        self.assertTrue(result.fatal)
        self.assertEqual(result.errors[0].code, "config-invalid-value")

    def test_forbidden_commands_bad_regex_is_fatal(self):
        self.repo.config(forbidden_commands=["(unclosed"])
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertIsNone(cfg)
        self.assertTrue(result.fatal)

    def test_skills_partial_override_merges_slot_by_slot(self):
        self.repo.config(skills={"tdd": "other-tdd-skill"})
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertFalse(result.fatal)
        expected = dict(DEFAULTS["skills"])
        expected["tdd"] = "other-tdd-skill"
        self.assertEqual(cfg["skills"], expected)

    def test_max_implementers_below_minimum_is_fatal(self):
        self.repo.config(max_implementers=0)
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertIsNone(cfg)
        self.assertTrue(result.fatal)

    def test_max_pending_acceptance_zero_is_valid(self):
        self.repo.config(max_pending_acceptance=0)
        result = Result()
        cfg = load_config(self.repo.root, result, required=True)
        self.assertFalse(result.fatal)
        self.assertEqual(cfg["max_pending_acceptance"], 0)


if __name__ == "__main__":
    unittest.main()
