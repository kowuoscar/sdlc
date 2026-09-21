from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import helpers

from sdlc_lib.checks_mergegate import check_merge_gate
from sdlc_lib.result import Result


class MergeGateTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = helpers.RepoBuilder(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def gate(self, feature="f1", no_verify=False, timeout=None):
        result = Result()
        kwargs = {} if timeout is None else {"timeout": timeout}
        check_merge_gate(self.repo.root, feature, no_verify, result, **kwargs)
        return result

    def codes(self, result, bucket="errors"):
        return [d.code for d in getattr(result, bucket)]

    def _basic_feature(self, walkthrough_steps=1):
        walkthrough = ["[agent] does step %d (stories: 1)" % i for i in range(1, walkthrough_steps + 1)]
        self.repo.spec("f1", status="delivered", stories=["one"], walkthrough=walkthrough)
        self.repo.config()
        self.repo.agent_map()
        self.repo.architecture()
        self.repo.agents_readme([])


class HappyPathTests(MergeGateTestCase):
    def test_clean_gate_passes_with_no_verify(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt", "proof\n")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertTrue(result.ok, result.to_dict())
        d = result.to_dict()
        self.assertEqual(d["verify"], "skipped")
        self.assertEqual(d["harness"], "passed")
        self.assertEqual(d["blocking"], [])
        self.assertEqual(d["downgraded"], [])


class FindingBlockingTests(MergeGateTestCase):
    def _acceptance_ok(self):
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )

    def test_blocking_open_finding_blocks(self):
        self._basic_feature()
        self._acceptance_ok()
        self.repo.findings(
            "f1",
            findings=[
                {
                    "id": "F1",
                    "type": "spec-partial",
                    "citation": "spec.md ## User stories -- 1",
                    "where": "src/x.ts:1",
                    "note": "n",
                    "state": "open",
                    "raised_by": "reviewer",
                    "after_review": False,
                }
            ],
        )
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("finding-blocking", self.codes(result))
        self.assertEqual(result.to_dict()["blocking"], ["F1"])

    def test_fixed_still_blocks(self):
        self._basic_feature()
        self._acceptance_ok()
        self.repo.findings(
            "f1",
            findings=[
                {
                    "id": "F1",
                    "type": "spec-wrong",
                    "citation": "spec.md ## Solution",
                    "where": "src/x.ts:1",
                    "note": "n",
                    "state": "fixed",
                    "raised_by": "fixer",
                    "after_review": False,
                }
            ],
        )
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertEqual(result.to_dict()["blocking"], ["F1"])

    def test_confirmed_does_not_block(self):
        self._basic_feature()
        self._acceptance_ok()
        self.repo.findings(
            "f1",
            findings=[
                {
                    "id": "F1",
                    "type": "spec-wrong",
                    "citation": "spec.md ## Solution",
                    "where": "src/x.ts:1",
                    "note": "n",
                    "state": "confirmed",
                    "raised_by": "reviewer",
                    "after_review": False,
                }
            ],
        )
        result = self.gate(no_verify=True)
        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.to_dict()["blocking"], [])

    def test_dismissed_does_not_block(self):
        self._basic_feature()
        self._acceptance_ok()
        self.repo.findings(
            "f1",
            findings=[
                {
                    "id": "F1",
                    "type": "rule-violated",
                    "citation": "docs/agents/coding-standards.md",
                    "where": "src/x.ts:1",
                    "note": "n -- dismissed: not applicable",
                    "state": "dismissed",
                    "raised_by": "reviewer",
                    "after_review": False,
                }
            ],
        )
        result = self.gate(no_verify=True)
        self.assertTrue(result.ok, result.to_dict())

    def test_smell_never_blocks(self):
        self._basic_feature()
        self._acceptance_ok()
        self.repo.findings(
            "f1",
            findings=[
                {
                    "id": "F1",
                    "type": "smell",
                    "citation": "",
                    "where": "src/x.ts:1",
                    "note": "n",
                    "state": "open",
                    "raised_by": "reviewer",
                    "after_review": False,
                }
            ],
        )
        result = self.gate(no_verify=True)
        self.assertTrue(result.ok, result.to_dict())

    def test_no_citation_downgrades_blocking_type(self):
        self._basic_feature()
        self._acceptance_ok()
        self.repo.findings(
            "f1",
            findings=[
                {
                    "id": "F1",
                    "type": "spec-partial",
                    "citation": "   ",
                    "where": "src/x.ts:1",
                    "note": "n",
                    "state": "open",
                    "raised_by": "reviewer",
                    "after_review": False,
                }
            ],
        )
        result = self.gate(no_verify=True)
        self.assertTrue(result.ok, result.to_dict())
        d = result.to_dict()
        self.assertEqual(d["downgraded"], ["F1"])
        self.assertEqual(d["blocking"], [])
        self.assertIn("finding-downgraded", self.codes(result, "warnings"))


class AcceptanceTests(MergeGateTestCase):
    def test_missing_walkthrough_entry_is_an_error(self):
        self._basic_feature(walkthrough_steps=2)
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("acceptance-step-missing", self.codes(result))

    def test_agent_step_without_evidence_file_is_an_error(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/missing.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("acceptance-evidence-missing", self.codes(result))

    def test_human_pending_step_does_not_need_evidence(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "human", "status": "pending", "evidence": ""}],
        )
        result = self.gate(no_verify=True)
        self.assertTrue(result.ok, result.to_dict())


class VerifyTests(MergeGateTestCase):
    def test_verify_pass(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        self.repo.config(verify="true")
        result = self.gate()
        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.to_dict()["verify"], "passed")

    def test_verify_fail_blocks(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        self.repo.config(verify="false")
        result = self.gate()
        self.assertFalse(result.ok)
        self.assertEqual(result.to_dict()["verify"], "failed")
        self.assertIn("verify-failed", self.codes(result))

    def test_no_verify_flag_skips_and_passes(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        self.repo.config(verify="false")
        result = self.gate(no_verify=True)
        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.to_dict()["verify"], "skipped")


class EvidencePathSafetyTests(MergeGateTestCase):
    def _acceptance_with_evidence(self, evidence):
        self.repo.acceptance(
            "f1", steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": evidence}]
        )

    def test_absolute_evidence_path_is_rejected(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self._acceptance_with_evidence("/etc/hosts")
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("acceptance-evidence-missing", self.codes(result))

    def test_dotdot_evidence_path_is_rejected(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self._acceptance_with_evidence("../../../docs/agents/sdlc.json")
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("acceptance-evidence-missing", self.codes(result))

    def test_symlink_escaping_feature_dir_is_rejected(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        feature_dir = self.repo.root / "docs" / "features" / "f1"
        feature_dir.mkdir(parents=True, exist_ok=True)
        link = feature_dir / "evil.txt"
        try:
            link.symlink_to("/etc/hosts")
        except OSError:
            self.skipTest("symlinks not supported in this environment")
        self._acceptance_with_evidence("evil.txt")
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("acceptance-evidence-missing", self.codes(result))

    def test_ordinary_relative_evidence_inside_feature_dir_is_accepted(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self._acceptance_with_evidence("evidence/step-1.txt")
        result = self.gate(no_verify=True)
        self.assertTrue(result.ok, result.to_dict())


class CitationTypeTests(MergeGateTestCase):
    def _finding(self, citation):
        return {
            "id": "F1",
            "type": "spec-missing",
            "citation": citation,
            "where": "src/x.ts:1",
            "note": "n",
            "state": "open",
            "raised_by": "reviewer",
            "after_review": False,
        }

    def test_list_citation_is_finding_invalid_not_downgrade(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[self._finding(["x"])])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("finding-invalid", self.codes(result))
        self.assertNotIn("finding-downgraded", self.codes(result, "warnings"))
        d = result.to_dict()
        self.assertEqual(d["downgraded"], [])

    def test_number_citation_is_finding_invalid(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[self._finding(3)])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertIn("finding-invalid", self.codes(result))

    def test_null_citation_is_finding_invalid(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[self._finding(None)])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertIn("finding-invalid", self.codes(result))

    def test_object_citation_is_finding_invalid(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[self._finding({"a": 1})])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertIn("finding-invalid", self.codes(result))

    def test_missing_citation_key_still_downgrades(self):
        self._basic_feature()
        finding = self._finding("")
        del finding["citation"]
        self.repo.findings("f1", findings=[finding])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.to_dict()["downgraded"], ["F1"])


class WalkthroughEmptyTests(MergeGateTestCase):
    def test_no_walkthrough_section_is_an_error(self):
        self.repo.spec("f1", status="delivered", stories=["one"], walkthrough=[])
        self.repo.config()
        self.repo.agent_map()
        self.repo.architecture()
        self.repo.agents_readme([])
        self.repo.findings("f1", findings=[])
        self.repo.acceptance("f1", steps=[])
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("walkthrough-empty", self.codes(result))

    def test_renamed_heading_yields_walkthrough_empty(self):
        # Spec text with the wrong heading -- extract_level2_sections finds
        # no "Acceptance walkthrough" section at all.
        self.repo.spec("f1", status="delivered", stories=["one"])
        raw = (self.repo.root / "docs/features/f1/spec.md").read_text()
        raw = raw.replace("## Acceptance walkthrough", "## Walkthrough (renamed)")
        (self.repo.root / "docs/features/f1/spec.md").write_text(raw)
        self.repo.config()
        self.repo.agent_map()
        self.repo.architecture()
        self.repo.agents_readme([])
        self.repo.findings("f1", findings=[])
        self.repo.acceptance("f1", steps=[])
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("walkthrough-empty", self.codes(result))


class FatalPathStillEmitsKeysTests(MergeGateTestCase):
    def test_missing_config_fatal_path_still_has_all_four_keys(self):
        result = self.gate()
        self.assertEqual(result.exit_code(), 2)
        d = result.to_dict()
        for key in ("blocking", "downgraded", "harness", "verify"):
            self.assertIn(key, d, key)

    def test_spec_not_found_fatal_path_still_has_all_four_keys(self):
        self.repo.config()
        result = self.gate(feature="does-not-exist")
        self.assertEqual(result.exit_code(), 2)
        d = result.to_dict()
        for key in ("blocking", "downgraded", "harness", "verify"):
            self.assertIn(key, d, key)


class MoreFindingsValidationTests(MergeGateTestCase):
    def test_findings_missing(self):
        self._basic_feature()
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("findings-missing", self.codes(result))

    def test_findings_not_a_list(self):
        self._basic_feature()
        self.repo.write_json(
            "docs/features/f1/findings.json", {"schema": 1, "feature": "f1", "findings": "nope"}
        )
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertIn("findings-invalid", self.codes(result))

    def test_unknown_finding_type(self):
        self._basic_feature()
        self.repo.findings(
            "f1",
            findings=[
                {
                    "id": "F1",
                    "type": "not-a-real-type",
                    "citation": "spec.md",
                    "where": "x",
                    "note": "n",
                    "state": "open",
                    "raised_by": "r",
                    "after_review": False,
                }
            ],
        )
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertIn("finding-invalid", self.codes(result))

    def test_unknown_finding_state(self):
        self._basic_feature()
        self.repo.findings(
            "f1",
            findings=[
                {
                    "id": "F1",
                    "type": "smell",
                    "citation": "spec.md",
                    "where": "x",
                    "note": "n",
                    "state": "not-a-real-state",
                    "raised_by": "r",
                    "after_review": False,
                }
            ],
        )
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertIn("finding-invalid", self.codes(result))

    def test_duplicate_finding_id(self):
        self._basic_feature()
        entry = {
            "id": "F1",
            "type": "smell",
            "citation": "spec.md",
            "where": "x",
            "note": "n",
            "state": "confirmed",
            "raised_by": "r",
            "after_review": False,
        }
        self.repo.findings("f1", findings=[dict(entry), dict(entry)])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertIn("finding-invalid", self.codes(result))

    def test_findings_unsupported_schema(self):
        self._basic_feature()
        self.repo.write_json(
            "docs/features/f1/findings.json", {"schema": 2, "feature": "f1", "findings": []}
        )
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        result = self.gate(no_verify=True)
        self.assertIn("findings-unsupported-schema", self.codes(result))

    def test_acceptance_unsupported_schema(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.write_json(
            "docs/features/f1/acceptance.json", {"schema": 2, "feature": "f1", "steps": []}
        )
        result = self.gate(no_verify=True)
        self.assertIn("acceptance-unsupported-schema", self.codes(result))

    def test_acceptance_step_duplicate(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[
                {"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"},
                {"step": 1, "actor": "human", "status": "pending", "evidence": ""},
            ],
        )
        result = self.gate(no_verify=True)
        self.assertIn("acceptance-step-duplicate", self.codes(result))

    def test_acceptance_step_unknown(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[
                {"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"},
                {"step": 99, "actor": "human", "status": "pending", "evidence": ""},
            ],
        )
        result = self.gate(no_verify=True)
        self.assertIn("acceptance-step-unknown", self.codes(result))

    def test_harness_failure_propagates_into_gate(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        self.repo.architecture(extra_paths=["src/ghost.ts"])
        result = self.gate(no_verify=True)
        self.assertFalse(result.ok)
        self.assertIn("path-missing", self.codes(result))
        self.assertEqual(result.to_dict()["harness"], "failed")

    def test_verify_timeout_with_injectable_timeout(self):
        self._basic_feature()
        self.repo.findings("f1", findings=[])
        self.repo.evidence("f1", "evidence/step-1.txt")
        self.repo.acceptance(
            "f1",
            steps=[{"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"}],
        )
        self.repo.config(verify='python3 -c "import time; time.sleep(2)"')
        result = self.gate(timeout=0.1)
        self.assertFalse(result.ok)
        self.assertEqual(result.to_dict()["verify"], "failed")
        self.assertIn("verify-timeout", self.codes(result))


if __name__ == "__main__":
    unittest.main()
