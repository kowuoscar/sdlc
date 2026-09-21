from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import helpers

from sdlc_lib import templates as templates_mod
from sdlc_lib.checks_state import compute_state
from sdlc_lib.checks_tickets import check_tickets
from sdlc_lib.frontmatter import FrontmatterError, parse_frontmatter
from sdlc_lib.markdown import extract_level2_sections
from sdlc_lib.result import Result

REAL_TEMPLATES_DIR = helpers.PLUGIN_ROOT / "skills" / "sdlc" / "templates"


class TemplateMarkerParsingTests(unittest.TestCase):
    def test_find_markers_in_text(self):
        text = "before\n<!-- sdlc:template spec 3 -->\nafter\n"
        self.assertEqual(templates_mod.find_markers_in_text(text), [("spec", 3)])

    def test_find_marker_in_json(self):
        text = '{"template": "sdlc-config 2", "schema": 1}'
        self.assertEqual(templates_mod.find_marker_in_json(text), ("sdlc-config", 2))

    def test_find_marker_in_json_missing_key(self):
        self.assertIsNone(templates_mod.find_marker_in_json('{"schema": 1}'))


class OutdatedTemplatesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = helpers.RepoBuilder(Path(self._tmp.name))
        self._templates_tmp = tempfile.TemporaryDirectory()
        self.templates_dir = Path(self._templates_tmp.name)

    def tearDown(self):
        self._tmp.cleanup()
        self._templates_tmp.cleanup()

    def compute(self):
        result = Result()
        compute_state(self.repo.root, result, templates_dir=self.templates_dir)
        return result

    def test_missing_templates_tree_gives_empty_list_and_warning(self):
        # self.templates_dir exists but is empty -- simulate "missing" by
        # pointing at a path that does not exist at all.
        result = Result()
        compute_state(self.repo.root, result, templates_dir=self.templates_dir / "does-not-exist")
        d = result.to_dict()
        self.assertEqual(d["outdated_templates"], [])
        self.assertIn("templates-tree-missing", [w.code for w in result.warnings])

    def test_outdated_marker_is_reported(self):
        (self.templates_dir / "spec.md").write_text("<!-- sdlc:template spec 3 -->\n")
        self.repo.config()
        self.repo.spec("f1", status="draft", marker_version=1)
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(len(d["outdated_templates"]), 1)
        entry = d["outdated_templates"][0]
        self.assertEqual(entry["name"], "spec")
        self.assertEqual(entry["found"], 1)
        self.assertEqual(entry["current"], 3)
        self.assertEqual(entry["path"], "docs/features/f1/spec.md")

    def test_up_to_date_marker_is_not_reported(self):
        (self.templates_dir / "spec.md").write_text("<!-- sdlc:template spec 1 -->\n")
        self.repo.config()
        self.repo.spec("f1", status="draft", marker_version=1)
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(d["outdated_templates"], [])

    def test_json_marker_scanned_for_config(self):
        (self.templates_dir / "sdlc.json").write_text('{"template": "sdlc-config 5"}')
        self.repo.write_json(
            "docs/agents/sdlc.json",
            {"template": "sdlc-config 2", "schema": 1, "verify": "true"},
        )
        result = self.compute()
        d = result.to_dict()
        self.assertEqual(len(d["outdated_templates"]), 1)
        self.assertEqual(d["outdated_templates"][0]["name"], "sdlc-config")


class ShippedTemplatesConformTests(unittest.TestCase):
    """Instantiate the real shipped templates (after substituting their
    placeholders) into a temp repo, and check they parse under our own
    parsers: frontmatter dialect, required sections, and template markers.
    """

    def setUp(self):
        if not REAL_TEMPLATES_DIR.is_dir():
            self.skipTest("skills/sdlc/templates/ not present")
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = helpers.RepoBuilder(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    @staticmethod
    def _read(name):
        return (REAL_TEMPLATES_DIR / name).read_text(encoding="utf-8")

    def _substitute(self, text, mapping):
        for placeholder, value in mapping.items():
            text = text.replace(placeholder, value)
        return text

    def test_sdlc_json_template_parses_and_has_marker(self):
        import json

        text = self._read("sdlc.json")
        text = text.replace(
            "<set me: one command that runs tests, lint and types>", "true"
        )
        data = json.loads(text)
        self.assertIn("template", data)
        name, version = data["template"].rsplit(" ", 1)
        self.assertEqual(name, "sdlc-config")
        self.assertTrue(version.isdigit())
        self.assertIn("verify", data)
        self.assertEqual(data["verify"], "true")

    def test_spec_template_parses(self):
        text = self._read("spec.md")
        text = self._substitute(
            text,
            {
                "<feature-slug>": "card-checkout",
                "<epic-slug>": "online-payment",
                "<YYYY-MM-DD>": "2026-01-31",
            },
        )
        try:
            fm, body = parse_frontmatter(text)
        except FrontmatterError as exc:
            self.fail("spec.md template frontmatter did not parse: %s" % exc)
        self.assertEqual(fm["feature"], "card-checkout")
        self.assertEqual(fm["status"], "draft")
        sections = extract_level2_sections(body)
        for heading in ("User stories", "Open questions", "Acceptance walkthrough", "Execution order"):
            self.assertIn(heading, sections, heading)
        self.assertIn("sdlc:template spec", body)

    def test_ticket_template_parses_and_has_required_sections(self):
        text = self._read("ticket.md")
        text = self._substitute(
            text,
            {
                "<ticket-slug>": "charge-card",
                "<one line, imperative, in domain vocabulary>": "Charge a card",
                "<area>": "backend",
                "<n>": "1",
            },
        )
        try:
            fm, body = parse_frontmatter(text)
        except FrontmatterError as exc:
            self.fail("ticket.md template frontmatter did not parse: %s" % exc)
        self.assertEqual(fm["id"], "charge-card")
        self.assertEqual(fm["status"], "needs-triage")
        sections = extract_level2_sections(body)
        for heading in ("Context", "Acceptance criteria", "Tests", "Regression", "Observability"):
            self.assertIn(heading, sections, heading)

    def test_epic_template_parses(self):
        text = self._read("epic.md")
        text = self._substitute(
            text,
            {
                "<epic-slug>": "online-payment",
                "<Epic name>": "Pay online",
                "<journey-slug>": "pay-online",
                "<feature-slug>": "card-checkout",
            },
        )
        try:
            fm, body = parse_frontmatter(text)
        except FrontmatterError as exc:
            self.fail("epic.md template frontmatter did not parse: %s" % exc)
        self.assertEqual(fm["id"], "online-payment")
        self.assertEqual(fm["status"], "proposed")
        sections = extract_level2_sections(body)
        self.assertIn("Features", sections)

    def test_inbox_item_template_parses(self):
        text = self._read("inbox-item.md")
        text = self._substitute(
            text,
            {
                "<item-slug>": "refund-partial-amounts",
                "<feature-or-epic-slug>": "refunds",
                "<YYYY-MM-DD>": "2026-01-31",
            },
        )
        try:
            fm, body = parse_frontmatter(text)
        except FrontmatterError as exc:
            self.fail("inbox-item.md template frontmatter did not parse: %s" % exc)
        self.assertEqual(fm["id"], "refund-partial-amounts")
        self.assertEqual(fm["status"], "open")
        sections = extract_level2_sections(body)
        for heading in ("Question", "Recommendation", "Blocks", "Meanwhile", "Answer"):
            self.assertIn(heading, sections, heading)

    def test_instantiated_feature_is_readable_by_check_tickets(self):
        """End-to-end: write the templates (with placeholders filled) into a
        real temp repo via the same shapes our scripts expect, and confirm
        check_tickets can at least parse them without a fatal error."""
        spec_text = self._substitute(
            self._read("spec.md"),
            {
                "<feature-slug>": "card-checkout",
                "<epic-slug>": "",
                "<YYYY-MM-DD>": "2026-01-31",
                "1. As a <actor>, I want <capability>, so that <benefit>": "1. As a user, I want to pay by card",
                "1. [agent] <observable action and expected result> (stories: 1)": "1. [agent] pays (stories: 1)",
                "2. [human] <observable action and expected result> (stories: 2, 3)": "",
                "1. `<ticket-slug>` — one line on what it delivers\n2. `<ticket-slug>`": "1. `charge-card`",
            },
        )
        # empty epic must be a quoted empty string under our dialect
        spec_text = spec_text.replace("epic: \n", 'epic: ""\n')
        self.repo.write("docs/features/card-checkout/spec.md", spec_text)

        ticket_text = self._substitute(
            self._read("ticket.md"),
            {
                "<ticket-slug>": "charge-card",
                "<one line, imperative, in domain vocabulary>": "Charge a card",
                "depends_on: [<ticket-slug>]": "depends_on: []",
                "labels: [<area>]": "labels: []",
                "stories: [<n>]": "stories: [1]",
            },
        )
        self.repo.write("docs/features/card-checkout/tickets/charge-card.md", ticket_text)

        result = Result()
        check_tickets(self.repo.root, "card-checkout", result)
        self.assertFalse(result.fatal, result.to_dict())


if __name__ == "__main__":
    unittest.main()
