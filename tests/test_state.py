from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import helpers

from sdlc_lib.checks_state import compute_state
from sdlc_lib.result import Result


EMPTY_TEMPLATES = None  # resolved lazily to a shared empty temp dir per test


class StateTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = helpers.RepoBuilder(Path(self._tmp.name))
        self._templates_tmp = tempfile.TemporaryDirectory()
        # An empty-but-existing templates dir: outdated_templates checks are
        # exercised separately in test_templates.py, so keep this inert here.
        self.templates_dir = Path(self._templates_tmp.name)

    def tearDown(self):
        self._tmp.cleanup()
        self._templates_tmp.cleanup()

    def compute(self):
        result = Result()
        compute_state(self.repo.root, result, templates_dir=self.templates_dir)
        return result


class Rule1InitTests(StateTestCase):
    def test_missing_config_means_init(self):
        result = self.compute()
        self.assertTrue(result.ok)
        self.assertFalse(result.fatal)
        d = result.to_dict()
        self.assertFalse(d["initialized"])
        self.assertEqual(d["next"]["action"], "init")

    def test_malformed_config_is_fatal(self):
        self.repo.write("docs/agents/sdlc.json", "{not json")
        result = self.compute()
        self.assertEqual(result.exit_code(), 2)


class Rule2ApplyAnswersTests(StateTestCase):
    def test_answered_inbox_item_wins_over_everything(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "wanted")])
        self.repo.inbox_item("q1", status="answered", answer="Do X.")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "apply-answers")
        self.assertEqual(d["next"]["target"], "")
        self.assertEqual(
            d["inbox"]["answered"], [{"id": "q1", "type": "question", "blocks": []}]
        )

    def test_inbox_items_are_objects_sorted_by_type_then_id(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "wanted")])
        self.repo.inbox_item("z-question", item_type="question", status="open")
        self.repo.inbox_item("a-alert", item_type="alert", status="open", blocks=["f1"])
        self.repo.inbox_item("m-approval", item_type="approval", status="open")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(
            d["inbox"]["open"],
            [
                {"id": "a-alert", "type": "alert", "blocks": ["f1"]},
                {"id": "z-question", "type": "question", "blocks": []},
                {"id": "m-approval", "type": "approval", "blocks": []},
            ],
        )


class Rule3PauseTests(StateTestCase):
    def _delivered_feature(self, slug):
        self.repo.spec(slug, status="delivered")

    def test_pause_when_delivered_count_reaches_cap(self):
        self.repo.config(max_pending_acceptance=2)
        self._delivered_feature("f1")
        self._delivered_feature("f2")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "pause")
        self.assertEqual(sorted(d["pending_acceptance"]), ["f1", "f2"])

    def test_no_pause_below_cap(self):
        self.repo.config(max_pending_acceptance=2)
        self._delivered_feature("f1")
        result = self.compute()
        d = result.to_dict()
        self.assertNotEqual(d["next"]["action"], "pause")

    def test_cap_zero_disables_pause(self):
        self.repo.config(max_pending_acceptance=0)
        self._delivered_feature("f1")
        self._delivered_feature("f2")
        self._delivered_feature("f3")
        result = self.compute()
        d = result.to_dict()
        self.assertNotEqual(d["next"]["action"], "pause")


class Rule4FeatureTests(StateTestCase):
    def test_draft_feature_means_spec(self):
        self.repo.config()
        self.repo.spec("f1", status="draft")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "f1")

    def test_approved_no_tickets_means_ticket(self):
        self.repo.config()
        self.repo.spec("f1", status="approved")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "ticket")
        self.assertEqual(d["next"]["target"], "f1")

    def test_approved_all_done_means_deliver(self):
        self.repo.config()
        self.repo.spec("f1", status="approved", stories=["s"])
        self.repo.ticket("f1", "t1", status="done", stories=[1])
        self.repo.ticket("f1", "t2", status="wontfix", stories=[])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "deliver")
        self.assertEqual(d["next"]["target"], "f1")

    def test_approved_all_wontfix_means_stalled_not_deliver(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "wanted")])
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic("epic-a", status="done", features=[])
        self.repo.spec("f1", status="approved", stories=["s"])
        self.repo.ticket("f1", "t1", status="wontfix", stories=[])
        self.repo.ticket("f1", "t2", status="wontfix", stories=[])
        result = self.compute()
        d = result.to_dict()
        self.assertNotEqual(d["next"]["action"], "deliver")
        self.assertEqual(d["next"]["action"], "wait")
        self.assertIn("f1", d["stalled"])

    def test_approved_frontier_means_execute(self):
        self.repo.config()
        self.repo.spec("f1", status="approved", stories=["s"])
        self.repo.ticket("f1", "t1", status="ready-for-agent", stories=[1])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "execute")
        self.assertEqual(d["next"]["target"], "f1")
        feat = d["features"][0]
        self.assertEqual(feat["frontier"], ["t1"])

    def test_approved_in_progress_means_execute(self):
        self.repo.config()
        self.repo.spec("f1", status="approved", stories=["s"])
        self.repo.ticket("f1", "t1", status="in-progress", stories=[1])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "execute")

    def test_approved_blocked_ticket_means_stalled(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "wanted")])
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic("epic-a", status="done", features=[])
        self.repo.spec("f1", status="approved", stories=["s"])
        # ready-for-agent but its dependency is not done -> not in frontier,
        # not in-progress either -> stalled.
        self.repo.ticket("f1", "t1", status="ready-for-agent", depends_on=["t0"], stories=[1])
        self.repo.ticket("f1", "t0", status="needs-triage", stories=[])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "wait")
        self.assertIn("f1", d["stalled"])

    def test_stalled_feature_is_skipped_for_a_later_actionable_one(self):
        self.repo.config()
        self.repo.spec("f1", status="approved", stories=["s"])
        self.repo.ticket("f1", "t1", status="ready-for-agent", depends_on=["t0"], stories=[1])
        self.repo.ticket("f1", "t0", status="needs-triage", stories=[])
        self.repo.spec("f2", status="draft")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "f2")
        self.assertEqual(d["stalled"], ["f1"])

    def test_stalled_feature_after_the_chosen_action_is_still_reported(self):
        # f1 (draft) supplies the action; f2 (approved, stuck tickets) comes
        # after it in order but must still show up in `stalled` -- the whole
        # feature list is scanned before the action is chosen.
        self.repo.config()
        self.repo.spec("f1", status="draft")
        self.repo.spec("f2", status="approved", stories=["s"])
        self.repo.ticket("f2", "t1", status="ready-for-agent", depends_on=["t0"], stories=[1])
        self.repo.ticket("f2", "t0", status="needs-triage", stories=[])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "f1")
        self.assertEqual(d["stalled"], ["f2"])

    def test_delivered_accepted_dropped_are_skipped(self):
        self.repo.config()
        self.repo.spec("f1", status="delivered")
        self.repo.spec("f2", status="accepted")
        self.repo.spec("f3", status="dropped")
        self.repo.spec("f4", status="draft")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "f4")

    def test_open_inbox_block_skips_feature(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "wanted")])
        # An epic must exist for rule 6 ("no epic exists at all") to not
        # pre-empt rule 7 -- make it 'done' so it contributes no action.
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic("epic-a", status="done", features=[])
        self.repo.spec("f1", status="draft")
        self.repo.inbox_item("i1", status="open", blocks=["f1"])
        result = self.compute()
        d = result.to_dict()
        # f1 is blocked and nothing else exists -> falls through to wait.
        self.assertEqual(d["next"]["action"], "wait")
        feat = [f for f in d["features"] if f["feature"] == "f1"][0]
        self.assertEqual(feat["blocked_by"], ["i1"])

    def test_answered_inbox_block_does_not_skip_feature(self):
        self.repo.config()
        self.repo.spec("f1", status="draft")
        self.repo.inbox_item("i1", status="closed", blocks=["f1"])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "f1")

    def test_non_epic_features_come_before_epic_features(self):
        self.repo.config()
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic("epic-a", status="planned", features=[(False, False, "in-epic", "")])
        self.repo.spec("in-epic", epic="epic-a", status="draft")
        self.repo.spec("outside", epic="", status="draft")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "outside")


class Rule5EpicTests(StateTestCase):
    def test_no_feature_line_means_plan_epic(self):
        self.repo.config()
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic("epic-a", status="planned", features=[])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "plan-epic")
        self.assertEqual(d["next"]["target"], "epic-a")

    def test_first_undelivered_feature_without_spec_dir_means_spec(self):
        self.repo.config()
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic(
            "epic-a",
            status="planned",
            features=[(False, False, "feat-a", "first"), (False, False, "feat-b", "second")],
        )
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "feat-a")

    def test_empty_feature_directory_without_spec_md_still_means_spec(self):
        self.repo.config()
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic(
            "epic-a",
            status="planned",
            features=[(False, False, "feat-a", "first")],
        )
        # The directory exists (e.g. a stray findings.json was created) but
        # spec.md itself does not -- must still count as "no spec".
        (self.repo.root / "docs" / "features" / "feat-a").mkdir(parents=True, exist_ok=True)
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "feat-a")

    def test_every_feature_delivered_or_dropped_means_close_epic(self):
        self.repo.config()
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic(
            "epic-a",
            status="in-progress",
            features=[(True, False, "feat-a", ""), (False, True, "feat-b", "dropped: n/a")],
        )
        self.repo.spec("feat-a", epic="epic-a", status="accepted")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "close-epic")
        self.assertEqual(d["next"]["target"], "epic-a")

    def test_proposed_epic_is_not_worked(self):
        self.repo.config()
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic("epic-a", status="proposed", features=[])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "intention")

    def test_blocked_epic_is_skipped(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "wanted")])
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic("epic-a", status="planned", features=[])
        self.repo.inbox_item("i1", status="open", blocks=["epic-a"])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "wait")

    def test_placeholder_feature_line_is_ignored(self):
        self.repo.config()
        self.repo.roadmap_readme(["epic-a"])
        # Hand-craft an epic file with a template-placeholder feature line.
        self.repo.write(
            "docs/roadmap/epic-a.md",
            "---\n"
            "id: epic-a\n"
            "title: Epic A\n"
            "status: planned\n"
            "journeys: []\n"
            "---\n\n"
            "## Intent\n\nText.\n\n"
            "## Features\n\n"
            "- [ ] `<feature-slug>`\n"
            "- [ ] `real-feature`\n\n"
            "## Later\n",
        )
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "real-feature")

    def test_feature_line_with_colon_and_bold_punctuation_is_tolerated(self):
        self.repo.config()
        self.repo.roadmap_readme(["epic-a"])
        self.repo.write(
            "docs/roadmap/epic-a.md",
            "---\n"
            "id: epic-a\n"
            "title: Epic A\n"
            "status: planned\n"
            "journeys: []\n"
            "---\n\n"
            "## Intent\n\nText.\n\n"
            "## Features\n\n"
            "- [ ] `a`: note about a\n"
            "- [ ] **`b`**\n\n"
            "## Later\n",
        )
        result = self.compute()
        d = result.to_dict()
        # Both 'a' and 'b' must be recognized as feature lines (not dropped
        # silently), so the epic does not close early; the first one with no
        # spec.md wins.
        self.assertEqual(d["next"]["action"], "spec")
        self.assertEqual(d["next"]["target"], "a")

    def test_strikethrough_around_slug_still_means_dropped_despite_punctuation(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "exists")])
        self.repo.roadmap_readme(["epic-a"])
        self.repo.write(
            "docs/roadmap/epic-a.md",
            "---\n"
            "id: epic-a\n"
            "title: Epic A\n"
            "status: planned\n"
            "journeys: []\n"
            "---\n\n"
            "## Intent\n\nText.\n\n"
            "## Features\n\n"
            "- [ ] ~`a`~: dropped, out of scope\n\n"
            "## Later\n",
        )
        result = self.compute()
        d = result.to_dict()
        # The only feature line is dropped -> every feature line delivered
        # or dropped -> close-epic.
        self.assertEqual(d["next"]["action"], "close-epic")
        self.assertEqual(d["next"]["target"], "epic-a")


class Rule6IntentionTests(StateTestCase):
    def test_missing_journeys_means_intention(self):
        self.repo.config()
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "intention")

    def test_no_epics_means_intention(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "wanted")])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "intention")


class Rule7WaitRule8IdleTests(StateTestCase):
    def test_idle_when_everything_is_finished(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "exists")])
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic("epic-a", status="done", features=[(True, False, "feat-a", "")])
        self.repo.spec("feat-a", epic="epic-a", status="accepted")
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "idle")
        self.assertEqual(d["stalled"], [])

    def test_wait_when_stalled_feature_exists_and_nothing_else_does(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "partial")])
        self.repo.roadmap_readme(["epic-a"])
        self.repo.epic("epic-a", status="done", features=[])
        self.repo.spec("f1", status="approved", stories=["s"])
        self.repo.ticket("f1", "t1", status="ready-for-agent", depends_on=["t0"], stories=[1])
        self.repo.ticket("f1", "t0", status="needs-triage", stories=[])
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["next"]["action"], "wait")


class OutputShapeTests(StateTestCase):
    def test_deterministic_output_for_same_input(self):
        self.repo.config()
        self.repo.journeys([("Book a slot", "wanted")])
        r1 = self.compute().to_dict()
        r2 = self.compute().to_dict()
        self.assertEqual(r1, r2)

    def test_ticket_totals_and_done_counts(self):
        self.repo.config()
        self.repo.spec("f1", status="approved", stories=["a", "b"])
        self.repo.ticket("f1", "t1", status="done", stories=[1])
        self.repo.ticket("f1", "t2", status="needs-triage", stories=[2])
        result = self.compute()
        d = result.to_dict()
        feat = d["features"][0]
        self.assertEqual(feat["tickets"], {"total": 2, "done": 1})

    def test_debt_over_threshold(self):
        self.repo.config(debt_threshold_per_module=1)
        self.repo.module_dir("src", "payments", files=["a.ts", "b.ts"])
        self.repo.tech_debt(
            [
                ("src/payments", "src/payments/a.ts", "Duplicated Code", "note", "f1", "2026-01-01"),
                ("src/payments", "src/payments/b.ts", "Duplicated Code", "note", "f1", "2026-01-01"),
            ]
        )
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["debt"]["over_threshold"], ["src/payments"])
        self.assertEqual(d["debt"]["stale"], [])

    def test_debt_stale_entries_excluded_from_threshold_and_listed(self):
        self.repo.config(debt_threshold_per_module=1)
        self.repo.module_dir("src", "payments", files=["a.ts"])
        self.repo.tech_debt(
            [
                ("src/payments", "src/payments/a.ts", "Duplicated Code", "note", "f1", "2026-01-01"),
                ("src/payments", "src/payments/ghost.ts", "Duplicated Code", "note", "f1", "2026-01-01"),
            ]
        )
        result = self.compute()
        d = result.to_dict()
        # Only one fresh entry remains for src/payments (threshold 1) -> not over.
        self.assertEqual(d["debt"]["over_threshold"], [])
        self.assertEqual(d["debt"]["stale"], ["src/payments/ghost.ts"])


class TestGlobsMatchNothingTests(StateTestCase):
    def test_warns_when_no_file_matches_any_test_glob(self):
        self.repo.config(test_globs=["**/*.doesnotmatchanything"])
        self.repo.write("src/foo.py", "print('hi')\n")
        result = self.compute()
        self.assertEqual(
            [w.code for w in result.warnings], ["test-globs-match-nothing"]
        )

    def test_no_warning_when_a_file_matches(self):
        self.repo.config()
        self.repo.write("src/foo.test.ts", "test\n")
        result = self.compute()
        self.assertNotIn("test-globs-match-nothing", [w.code for w in result.warnings])

    def test_no_warning_when_repo_has_no_files_at_all(self):
        # A truly empty repo (not even a config file) has nothing to warn
        # about; use the DEFAULTS test_globs since load_config never runs.
        result = self.compute()
        self.assertNotIn("test-globs-match-nothing", [w.code for w in result.warnings])

    def test_skip_dirs_are_not_scanned(self):
        # A file that would match, but only inside a skipped directory --
        # plus an ordinary source file so the repo isn't considered empty.
        self.repo.write("node_modules/pkg/index.test.js", "test\n")
        self.repo.write("src/main.py", "print('hi')\n")
        self.repo.config(test_globs=["**/*.test.js"])
        result = self.compute()
        self.assertEqual(
            [w.code for w in result.warnings], ["test-globs-match-nothing"]
        )


if __name__ == "__main__":
    unittest.main()
