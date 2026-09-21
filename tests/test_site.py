"""The presentation site must stay true to the plugin it describes."""
from __future__ import annotations

import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import validate_plugin  # noqa: E402

FINDING_TYPES = ["spec-missing", "spec-partial", "spec-wrong", "out-of-scope", "rule-violated",
                 "acceptance-failed", "design-guideline", "smell"]
INBOX_TYPES = ["alert", "question", "approval", "acceptance", "proposal"]
EXECUTABLES = validate_plugin.BINARIES


def read(name):
    with open(os.path.join(SITE, name), encoding="utf-8") as handle:
        return handle.read()


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = read("index.html")
        cls.css = read("style.css")
        cls.js = read("loop.js")

    def test_every_local_asset_exists(self):
        refs = re.findall(r'(?:href|src)="([^"#:]+)"', self.html) + re.findall(r'url\("([^")]+)"\)', self.css)
        self.assertTrue(refs)
        for ref in refs:
            with self.subTest(ref=ref):
                self.assertTrue(os.path.isfile(os.path.join(SITE, ref)), ref)

    def test_every_in_page_link_has_a_target(self):
        ids = set(re.findall(r'\bid="([^"]+)"', self.html))
        for anchor in set(re.findall(r'href="#([^"]+)"', self.html)):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, ids)

    def test_the_models_table_matches_the_agent_definitions(self):
        rows = re.findall(r"<tr><th>(haiku|sonnet|opus)</th><td>(.*?)</td>", self.html, re.S)
        shown = {}
        for model, cell in rows:
            for name in re.findall(r"<code>([a-z-]+)</code>", cell):
                shown[name] = model
        defined = {}
        for filename in os.listdir(os.path.join(ROOT, "agents")):
            if filename.endswith(".md"):
                with open(os.path.join(ROOT, "agents", filename), encoding="utf-8") as handle:
                    defined[filename[:-3]] = validate_plugin.frontmatter(handle.read()).get("model")
        self.assertEqual(shown, defined)

    def test_the_walk_through_only_uses_real_actions(self):
        actions = set(re.findall(r'action: "([a-z-]+)"', self.js))
        self.assertTrue(actions)
        self.assertLessEqual(actions, set(validate_plugin.ACTIONS))
        for actor in set(re.findall(r'actor: "([a-z]+)"', self.js)):
            self.assertIn(actor, {"you", "agent", "script"})

    def test_every_station_of_the_loop_is_described(self):
        for action in ["init", "intention", "plan-epic", "spec", "ticket", "execute", "deliver", "close-epic"]:
            with self.subTest(action=action):
                self.assertRegex(self.html, r'<span class="station-id"><b>%s</b>' % re.escape(action))

    def test_vocabulary_matches_the_contract(self):
        for word in FINDING_TYPES + INBOX_TYPES + EXECUTABLES:
            with self.subTest(word=word):
                self.assertIn("<code>%s</code>" % word, self.html)

    def test_fonts_ship_with_their_licence(self):
        self.assertTrue(os.path.isfile(os.path.join(SITE, "fonts", "OFL.txt")))

    def test_no_third_party_requests(self):
        external = [u for u in re.findall(r'(?:src|href)="(https?://[^"]+)"', self.html)
                    if "<a " not in u]
        loaded = re.findall(r'<(?:script|link|img)[^>]+(?:src|href)="(https?://[^"]+)"', self.html)
        self.assertEqual(loaded, [], "the page must not load anything from another origin: %s" % external)


if __name__ == "__main__":
    unittest.main()
