from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import helpers

from sdlc_lib.checks_tickets import check_tickets
from sdlc_lib.result import Result


class CheckTicketsTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = helpers.RepoBuilder(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def check(self, feature="f1"):
        result = Result()
        check_tickets(self.repo.root, feature, result)
        return result

    def codes(self, result, bucket="errors"):
        return [d.code for d in getattr(result, bucket)]


class FullyValidFeatureTests(CheckTicketsTestCase):
    def test_valid_feature_is_ok(self):
        self.repo.spec(
            "f1",
            stories=["As a user, I want A", "As a user, I want B"],
            walkthrough=[
                "[agent] does A (stories: 1)",
                "[human] does B (stories: 2)",
            ],
            execution_order=["t1", "t2"],
        )
        self.repo.ticket("f1", "t1", stories=[1])
        self.repo.ticket("f1", "t2", stories=[2], depends_on=["t1"])
        result = self.check()
        self.assertTrue(result.ok, result.to_dict())
        self.assertEqual(result.errors, [])


class SpecLevelTests(CheckTicketsTestCase):
    def test_spec_not_found_is_fatal(self):
        result = self.check("nope")
        self.assertEqual(result.exit_code(), 2)
        self.assertEqual(self.codes(result), ["spec-not-found"])

    def test_spec_frontmatter_invalid_is_fatal(self):
        self.repo.write("docs/features/f1/spec.md", "---\nfeature:\n  sub: value\n---\n")
        result = self.check()
        self.assertEqual(result.exit_code(), 2)
        self.assertEqual(self.codes(result), ["frontmatter-invalid"])


class PerTicketErrorTests(CheckTicketsTestCase):
    def _valid_spec(self, **kw):
        defaults = dict(
            stories=["story one"],
            walkthrough=["[agent] step (stories: 1)"],
            execution_order=["t1"],
        )
        defaults.update(kw)
        self.repo.spec("f1", **defaults)

    def test_ticket_frontmatter_invalid(self):
        self._valid_spec()
        self.repo.write(
            "docs/features/f1/tickets/t1.md",
            "---\nid:\n  sub: value\n---\n\n## Context\n\nx\n",
        )
        result = self.check()
        self.assertIn("frontmatter-invalid", self.codes(result))

    def test_ticket_slug_invalid(self):
        self._valid_spec(execution_order=["1bad"])
        self.repo.ticket("f1", "1bad", id="1bad", stories=[1])
        result = self.check()
        self.assertIn("ticket-slug-invalid", self.codes(result))

    def test_ticket_id_mismatch(self):
        self._valid_spec()
        self.repo.ticket("f1", "t1", id="other-id", stories=[1])
        result = self.check()
        self.assertIn("ticket-id-mismatch", self.codes(result))

    def test_ticket_status_unknown(self):
        self._valid_spec()
        self.repo.ticket("f1", "t1", status="bogus-status", stories=[1])
        result = self.check()
        self.assertIn("ticket-status-unknown", self.codes(result))

    def test_ticket_section_missing(self):
        self._valid_spec()
        self.repo.ticket("f1", "t1", stories=[1], omit_sections=["Observability"])
        result = self.check()
        self.assertIn("ticket-section-missing", self.codes(result))

    def test_ticket_section_empty(self):
        self._valid_spec()
        self.repo.ticket("f1", "t1", stories=[1], sections={"Observability": ""})
        result = self.check()
        self.assertIn("ticket-section-empty", self.codes(result))

    def test_dependency_missing(self):
        self._valid_spec()
        self.repo.ticket("f1", "t1", stories=[1], depends_on=["ghost"])
        result = self.check()
        self.assertIn("dependency-missing", self.codes(result))

    def test_dependency_self(self):
        self._valid_spec()
        self.repo.ticket("f1", "t1", stories=[1], depends_on=["t1"])
        result = self.check()
        self.assertIn("dependency-self", self.codes(result))

    def test_dependency_cycle(self):
        self._valid_spec(execution_order=["t1", "t2"])
        self.repo.ticket("f1", "t1", stories=[1], depends_on=["t2"])
        self.repo.ticket("f1", "t2", stories=[], labels=["enabler"], depends_on=["t1"])
        result = self.check()
        self.assertIn("dependency-cycle", self.codes(result))

    def test_stories_empty_without_enabler(self):
        self._valid_spec()
        self.repo.ticket("f1", "t1", stories=[])
        result = self.check()
        self.assertIn("stories-empty", self.codes(result))

    def test_stories_empty_with_enabler_is_fine(self):
        self._valid_spec()
        self.repo.ticket("f1", "t1", stories=[], labels=["enabler"])
        result = self.check()
        self.assertNotIn("stories-empty", self.codes(result))
        # But the spec story is still uncovered.
        self.assertIn("story-uncovered", self.codes(result))

    def test_story_unknown(self):
        self._valid_spec()
        self.repo.ticket("f1", "t1", stories=[99])
        result = self.check()
        self.assertIn("story-unknown", self.codes(result))

    def test_story_uncovered(self):
        self._valid_spec(stories=["one", "two"], walkthrough=["[agent] step (stories: 1, 2)"])
        self.repo.ticket("f1", "t1", stories=[1])
        result = self.check()
        self.assertIn("story-uncovered", self.codes(result))

    def test_walkthrough_missing_actor(self):
        self._valid_spec(walkthrough=["does something (stories: 1)"])
        self.repo.ticket("f1", "t1", stories=[1])
        result = self.check()
        self.assertIn("walkthrough-missing-actor", self.codes(result))

    def test_walkthrough_missing_stories(self):
        self._valid_spec(walkthrough=["[agent] does something"])
        self.repo.ticket("f1", "t1", stories=[1])
        result = self.check()
        self.assertIn("walkthrough-missing-stories", self.codes(result))

    def test_walkthrough_story_unknown(self):
        self._valid_spec(walkthrough=["[agent] does something (stories: 1, 5)"])
        self.repo.ticket("f1", "t1", stories=[1])
        result = self.check()
        self.assertIn("walkthrough-story-unknown", self.codes(result))

    def test_execution_order_omits_ticket(self):
        self._valid_spec(execution_order=[])
        self.repo.ticket("f1", "t1", stories=[1])
        result = self.check()
        self.assertIn("execution-order-incomplete", self.codes(result))

    def test_execution_order_names_unknown_ticket(self):
        self._valid_spec(execution_order=["t1", "ghost-ticket"])
        self.repo.ticket("f1", "t1", stories=[1])
        result = self.check()
        self.assertIn("execution-order-unknown", self.codes(result))

    def test_execution_order_violation(self):
        self._valid_spec(stories=["one", "two"], execution_order=["t2", "t1"])
        self.repo.ticket("f1", "t1", stories=[1])
        self.repo.ticket("f1", "t2", stories=[2], depends_on=["t1"])
        result = self.check()
        self.assertIn("execution-order-violation", self.codes(result))


class WarningTests(CheckTicketsTestCase):
    def test_too_many_acceptance_criteria(self):
        self.repo.spec(
            "f1",
            stories=["one"],
            walkthrough=["[agent] step (stories: 1)"],
            execution_order=["t1"],
        )
        criteria = "\n".join("- [ ] criterion %d" % i for i in range(8))
        self.repo.ticket("f1", "t1", stories=[1], sections={"Acceptance criteria": criteria})
        result = self.check()
        self.assertIn("ticket-too-many-criteria", self.codes(result, "warnings"))

    def test_redundant_dependency(self):
        self.repo.spec(
            "f1",
            stories=["one"],
            walkthrough=["[agent] step (stories: 1)"],
            execution_order=["t1", "t2", "t3"],
        )
        self.repo.ticket("f1", "t1", stories=[], labels=["enabler"])
        self.repo.ticket("f1", "t2", stories=[], labels=["enabler"], depends_on=["t1"])
        self.repo.ticket("f1", "t3", stories=[1], depends_on=["t1", "t2"])
        result = self.check()
        self.assertIn("dependency-redundant", self.codes(result, "warnings"))


class CycleCheckIsIterativeTests(CheckTicketsTestCase):
    def test_deep_dependency_chain_does_not_overflow_recursion(self):
        # A long chain (deeper than Python's default recursion limit) must
        # not raise RecursionError -- _check_cycles has to be iterative.
        #
        # dependency-graph traversal walks depends_on (not dependents), and
        # tickets are visited from `sorted(depends_map.keys())`. To force a
        # SINGLE unbroken recursive descent through the whole chain (rather
        # than many short ones bounded by nodes visited on earlier outer
        # iterations), the chain's tip is named so it sorts alphabetically
        # first -- its one dfs call then has to walk every other node before
        # any of them could have been marked visited another way.
        n = 3000
        base = ["m%05d" % i for i in range(n - 1)]  # m00000 .. depends on nothing
        # Execution order must list blockers first: base in dependency order,
        # then the tip last.
        self.repo.spec(
            "f1",
            stories=["one"],
            walkthrough=["[agent] step (stories: 1)"],
            execution_order=base + ["a-tip"],
        )
        # a-tip -> m(n-2) -> m(n-3) -> ... -> m1 -> m0 (no deps)
        self.repo.ticket("f1", "a-tip", stories=[], labels=["enabler"], depends_on=[base[-1]])
        for i, slug in enumerate(base):
            depends_on = [base[i - 1]] if i > 0 else []
            is_last = i == 0  # m0 has no deps; give the story-carrying job to it
            stories = [1] if is_last else []
            labels = [] if is_last else ["enabler"]
            self.repo.ticket("f1", slug, stories=stories, labels=labels, depends_on=depends_on)
        result = self.check()
        self.assertNotIn("dependency-cycle", self.codes(result))
        self.assertTrue(result.ok, [e.code for e in result.errors][:5])


if __name__ == "__main__":
    unittest.main()
