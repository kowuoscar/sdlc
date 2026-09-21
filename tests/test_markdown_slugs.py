from __future__ import annotations

import unittest

import helpers  # noqa: F401

from sdlc_lib.markdown import (
    extract_backticked,
    extract_level2_sections,
    parse_checkbox_lines,
    parse_numbered_list,
)
from sdlc_lib.slugs import is_valid_slug


class MarkdownTests(unittest.TestCase):
    def test_extract_level2_sections(self):
        text = "# Title\n\n## Context\n\nfoo\nbar\n\n## Tests\n\nbaz\n"
        sections = extract_level2_sections(text)
        self.assertEqual(sections["Context"], "foo\nbar")
        self.assertEqual(sections["Tests"], "baz")

    def test_level1_heading_closes_section(self):
        text = "## A\n\nfoo\n\n# Interlude\n\nignored\n\n## B\n\nbar\n"
        sections = extract_level2_sections(text)
        self.assertEqual(sections["A"], "foo")
        self.assertEqual(sections["B"], "bar")
        self.assertNotIn("Interlude", sections)

    def test_missing_section_absent(self):
        sections = extract_level2_sections("no headings here\n")
        self.assertEqual(sections, {})

    def test_parse_numbered_list(self):
        text = "1. first\n2. second\nnot numbered\n3. third\n"
        items = parse_numbered_list(text)
        self.assertEqual(items, [(1, "first"), (2, "second"), (3, "third")])

    def test_parse_checkbox_lines(self):
        text = "- [ ] `a`\n- [x] `b`\n- [X] `c`\nnot a checkbox\n"
        items = parse_checkbox_lines(text)
        self.assertEqual(
            items, [(False, "`a`"), (True, "`b`"), (True, "`c`")]
        )

    def test_extract_backticked(self):
        text = "see `src/foo.ts` and `README.md` and plain text"
        self.assertEqual(extract_backticked(text), ["src/foo.ts", "README.md"])


class SlugTests(unittest.TestCase):
    def test_valid_slugs(self):
        for s in ("card-checkout", "a", "a1", "a-b-c", "abc123"):
            self.assertTrue(is_valid_slug(s), s)

    def test_invalid_slugs(self):
        for s in ("", "Card-Checkout", "card_checkout", "-card", "card-", "card--checkout", "1-card", "card checkout"):
            self.assertFalse(is_valid_slug(s), s)


if __name__ == "__main__":
    unittest.main()
