from __future__ import annotations

import unittest

import helpers  # noqa: F401  -- sets up sys.path

from sdlc_lib.frontmatter import FrontmatterError, parse_frontmatter


class FrontmatterTests(unittest.TestCase):
    def test_no_frontmatter_block(self):
        data, body = parse_frontmatter("# Just a doc\n")
        self.assertEqual(data, {})
        self.assertEqual(body, "# Just a doc\n")

    def test_basic_scalars(self):
        text = "---\nfeature: card-checkout\nstatus: draft\n---\nbody\n"
        data, body = parse_frontmatter(text)
        self.assertEqual(data, {"feature": "card-checkout", "status": "draft"})
        self.assertEqual(body, "body\n")

    def test_quoted_strings(self):
        text = '---\na: "hello world"\nb: \'single quoted\'\n---\n'
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["a"], "hello world")
        self.assertEqual(data["b"], "single quoted")

    def test_int_and_bool(self):
        text = "---\ncount: 42\nneg: -3\nflag_t: true\nflag_f: false\n---\n"
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["count"], 42)
        self.assertEqual(data["neg"], -3)
        self.assertIs(data["flag_t"], True)
        self.assertIs(data["flag_f"], False)

    def test_inline_list(self):
        text = "---\ndepends_on: [a, b, c]\n---\n"
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["depends_on"], ["a", "b", "c"])

    def test_empty_list(self):
        text = "---\ndepends_on: []\n---\n"
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["depends_on"], [])

    def test_list_of_ints_and_quoted(self):
        text = '---\nstories: [1, 2, "3"]\n---\n'
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["stories"], [1, 2, "3"])

    def test_list_with_quoted_comma(self):
        text = '---\nvals: ["a, b", c]\n---\n'
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["vals"], ["a, b", "c"])

    def test_unterminated_block_rejected(self):
        with self.assertRaises(FrontmatterError):
            parse_frontmatter("---\nfeature: x\n")

    def test_nested_mapping_rejected(self):
        text = "---\nfeature:\n  sub: value\n---\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_bare_key_is_empty_string(self):
        text = "---\nfeature:\nstatus: draft\n---\n"
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["feature"], "")
        self.assertEqual(data["status"], "draft")

    def test_bare_key_with_trailing_space_is_empty_string(self):
        text = "---\nepic: \n---\n"
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["epic"], "")

    def test_multiline_block_scalar_rejected(self):
        text = "---\nnote: |\n  line one\n  line two\n---\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_multiline_block_scalar_gt_rejected(self):
        text = "---\nnote: >\n  folded text\n---\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_block_list_rejected(self):
        text = "---\ndepends_on:\n- a\n- b\n---\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_malformed_line_rejected(self):
        text = "---\nthis is not key value\n---\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_duplicate_key_rejected(self):
        text = "---\na: 1\na: 2\n---\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_blank_line_inside_block_tolerated(self):
        text = "---\na: 1\n\nb: 2\n---\nbody\n"
        data, body = parse_frontmatter(text)
        self.assertEqual(data, {"a": 1, "b": 2})
        self.assertEqual(body, "body\n")

    def test_comment_hash_not_stripped(self):
        # No comment support: a literal '#' in a value is part of the string.
        text = "---\ntitle: fix #123\n---\n"
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["title"], "fix #123")

    def test_unicode_em_dash_value_literal(self):
        text = "---\ntitle: pay — online\n---\n"
        data, _ = parse_frontmatter(text)
        self.assertEqual(data["title"], "pay — online")


if __name__ == "__main__":
    unittest.main()
