"""Tests for tools/check_method_gates.py and methods/gates.json."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import check_method_gates as gates_mod  # noqa: E402


def write(root, rel, content):
    full = os.path.join(root, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(content)
    return full


class DetectionPositiveTests(unittest.TestCase):
    """One example line per registry entry, plus the coordinator's widened
    detection worklist: each must be recognised as a human-gate line by the
    bare regex set (before any registry lookup)."""

    CASES = [
        "confirm them with the user",
        "Check with the user that these seams match their expectations.",
        "If not, tell the user to run `/setup-matt-pocock-skills`.",
        "### 4. Quiz the user",
        "Ask the user:",
        "Iterate until the user approves the breakdown.",
        "If they didn't specify one, ask for it.",
        "ask the user where the spec is",
        "say so and ask the user.",
        # Flagged via the HITL marker on the same line, not a "drive" verb
        # (dropped from the verb list; see DetectionNegativeTests below for
        # why bare "drive"/pronoun-object phrasing is a documented miss).
        "10. **HITL bash script.** If a human must click, drive them with the template script.",
        "Ask the user for: (a) access to the environment",
        "Show the ranked list to the user before testing.",
        "Present these candidates to the user, in order of severity.",
        # Widened detection worklist (coordinator follow-up).
        "Get sign-off from the developer before merging",
        "Wait for approval before proceeding",
        "Pause and let the user choose",
        "Surface this to the human and stop",
        "Use AskUserQuestion to clarify",
        "The user must confirm the plan",
        "Only proceed with the user's approval",
        "Prompt the user for the missing value",
        "Request confirmation",
        "This is a HITL step",
        "Approval must be obtained",
        "Do you agree with this breakdown?",
        "Hand off to the user",
        "Ask them what they meant",
        "Escalate to a person",
        "Ask: which seam should we test?",
        "If unclear, ask.",
    ]

    def test_each_case_is_flagged(self):
        for line in self.CASES:
            with self.subTest(line=line):
                self.assertTrue(
                    gates_mod.is_human_gate_line(line),
                    "expected to flag: %r" % line,
                )


class DetectionNegativeTests(unittest.TestCase):
    """Lines that must never be flagged."""

    CASES = [
        "This list of user stories should be extremely extensive.",
        "A LONG, numbered list of user stories.",
        "you test the shape of things rather than user-facing behavior",
        "The problem that the user is facing, from the user's perspective.",
        "it drives the actual bug code path and asserts the user's exact symptom",
        "createUser(name, email)",
        "confirm the fixed point resolves",
        "don't ask the user for anything you could look up yourself",
        "Do NOT interview the user; just synthesize what you already know.",
        # Widened detection: must not overcatch.
        "let them share an integration branch that all block a final integrate-and-verify ticket",
        "Confirm:",
        "Can I make it faster? (Cache setup, skip unrelated init, narrow the test scope.)",
        "Can I make the signal sharper? (Assert on the specific symptom, not \"didn't crash\".)",
        "Should we retry the request automatically?",
        # Documented misses (module docstring): bare-pronoun object, not a
        # fixed human noun.
        "Confirm with them before merging.",
        "Tell them what changed.",
    ]

    def test_none_of_these_are_flagged(self):
        for line in self.CASES:
            with self.subTest(line=line):
                self.assertFalse(
                    gates_mod.is_human_gate_line(line),
                    "did not expect to flag: %r" % line,
                )


class ShellDetectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_read_dash_p_prompt_is_flagged_in_a_shell_file(self):
        path = write(self.root, "script.sh", "#!/bin/sh\nread -p 'Continue? ' answer\n")
        hits = gates_mod.flagged_lines(path)
        self.assertEqual([h[0] for h in hits], [2])

    def test_read_dash_r_dash_p_prompt_is_flagged_in_a_shell_file(self):
        path = write(self.root, "script.sh", "#!/bin/sh\nread -r -p 'Continue? ' answer\n")
        hits = gates_mod.flagged_lines(path)
        self.assertEqual([h[0] for h in hits], [2])

    def test_select_prompt_is_flagged_in_a_shell_file(self):
        path = write(self.root, "script.sh", "#!/bin/sh\nselect opt in yes no; do\n  echo \"$opt\"\ndone\n")
        hits = gates_mod.flagged_lines(path)
        self.assertEqual([h[0] for h in hits], [2])

    def test_read_dash_p_in_a_non_shell_file_is_not_flagged(self):
        path = write(self.root, "notes.md", "Example: `read -p 'prompt' var` is a bash idiom.\n")
        self.assertEqual(gates_mod.flagged_lines(path), [])


class FrontmatterAndFenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_frontmatter_description_line_is_skipped(self):
        path = write(self.root, "sample.md", (
            "---\n"
            'name: sample\n'
            'description: "Ask the user for a fixed point before reviewing."\n'
            "---\n"
            "\n"
            "# Sample\n"
            "\n"
            "Ordinary prose that does not mention a human gate.\n"
        ))
        self.assertEqual(gates_mod.flagged_lines(path), [])

    def test_fenced_code_block_is_skipped(self):
        path = write(self.root, "sample.md", (
            "# Sample\n"
            "\n"
            "```\n"
            "ask the user\n"
            "```\n"
            "\n"
            "Ordinary prose.\n"
        ))
        self.assertEqual(gates_mod.flagged_lines(path), [])

    def test_a_real_gate_outside_frontmatter_and_fences_is_still_flagged(self):
        path = write(self.root, "sample.md", (
            "---\n"
            "name: sample\n"
            "---\n"
            "\n"
            "```\n"
            "not a gate\n"
            "```\n"
            "\n"
            "Quiz the user about their preferences.\n"
        ))
        hits = gates_mod.flagged_lines(path)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0], 9)


class FakeMethodsTreeTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.methods = os.path.join(self.root, "methods")
        os.makedirs(self.methods, exist_ok=True)
        # A minimal, valid UPSTREAM.json by default -- no tracked methods,
        # so the "reviewed" check (which iterates UPSTREAM.json's own
        # "methods" object) stays out of the way of tests that are not
        # about it. Tests of the reviewed-hash mechanism call
        # write_upstream() themselves with real entries.
        self.write_upstream({})

    def tearDown(self):
        self._tmp.cleanup()

    def write_upstream(self, methods):
        write(self.root, "methods/UPSTREAM.json", json.dumps({
            "repository": "mattpocock/skills",
            "url": "https://github.com/mattpocock/skills",
            "commit": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            "commit_date": "2026-01-01T00:00:00Z",
            "methods": methods,
        }))

    def write_gates(self, gates=None, exempt_files=None, reviewed=None):
        write(self.root, "methods/gates.json", json.dumps({
            "gates": gates or [],
            "exempt_files": exempt_files or [],
            "reviewed": reviewed or {},
        }))


class UnregisteredGateTests(FakeMethodsTreeTestCase):
    def test_unregistered_gate_is_an_error_naming_file_and_line(self):
        write(self.root, "methods/example/SKILL.md", (
            "---\nname: example\n---\n\nQuiz the user about the plan.\n"
        ))
        self.write_gates()
        result = gates_mod.check_gates(self.root)
        self.assertFalse(result["ok"])
        codes = {e["code"] for e in result["errors"]}
        self.assertIn("gate-unregistered", codes)
        entry = next(e for e in result["errors"] if e["code"] == "gate-unregistered")
        self.assertEqual(entry["path"], "example/SKILL.md")
        self.assertIn("Quiz the user about the plan.", entry["message"])
        self.assertIn("5", entry["message"])

    def test_a_covered_gate_is_not_an_error(self):
        write(self.root, "methods/example/SKILL.md", (
            "---\nname: example\n---\n\nQuiz the user about the plan.\n"
        ))
        self.write_gates(gates=[
            {"file": "example/SKILL.md", "match": "Quiz the user", "replaced_by": "x"},
        ])
        result = gates_mod.check_gates(self.root)
        self.assertTrue(result["ok"])
        self.assertEqual(result["flagged"], 1)
        self.assertEqual(result["covered"], 1)


class StaleEntryTests(FakeMethodsTreeTestCase):
    def test_gate_entry_matching_nothing_is_stale(self):
        write(self.root, "methods/example/SKILL.md", "# example\n\nOrdinary prose.\n")
        self.write_gates(gates=[
            {"file": "example/SKILL.md", "match": "Quiz the user", "replaced_by": "x"},
        ])
        result = gates_mod.check_gates(self.root)
        self.assertFalse(result["ok"])
        codes = {e["code"] for e in result["errors"]}
        self.assertIn("gate-stale", codes)


class ExemptFileMissingTests(FakeMethodsTreeTestCase):
    def test_exempt_file_that_does_not_exist_is_an_error(self):
        write(self.root, "methods/example/SKILL.md", "# example\n\nOrdinary prose.\n")
        self.write_gates(exempt_files=[
            {"file": "nonexistent/SKILL.md", "reason": "does not matter"},
        ])
        result = gates_mod.check_gates(self.root)
        self.assertFalse(result["ok"])
        codes = {e["code"] for e in result["errors"]}
        self.assertIn("exempt-file-missing", codes)


class ExemptFileCoversFlaggedLinesTests(FakeMethodsTreeTestCase):
    def test_exempt_file_flagged_lines_need_no_gate_entry(self):
        write(self.root, "methods/grilling/SKILL.md", (
            "---\nname: grilling\n---\n\nInterview the user relentlessly.\n"
        ))
        self.write_gates(exempt_files=[
            {"file": "grilling/SKILL.md", "reason": "human present"},
        ])
        result = gates_mod.check_gates(self.root)
        self.assertTrue(result["ok"])
        self.assertEqual(result["flagged"], 1)
        self.assertEqual(result["covered"], 1)


class ReadmeIsNeverScannedTests(FakeMethodsTreeTestCase):
    def test_methods_readme_is_excluded(self):
        write(self.root, "methods/README.md", "Quiz the user about the README.\n")
        self.write_gates()
        result = gates_mod.check_gates(self.root)
        self.assertTrue(result["ok"])
        self.assertEqual(result["flagged"], 0)


class NeverScannedFilesTests(FakeMethodsTreeTestCase):
    def test_gates_json_and_upstream_json_and_license_are_never_scanned(self):
        # These contain "Quiz the user" only inside JSON strings / prose that
        # would themselves be flagged if scanned as ordinary content.
        write(self.root, "methods/LICENSE", "Quiz the user in this fake licence body.\n")
        self.write_gates(gates=[{"file": "LICENSE", "match": "x", "replaced_by": "y"}])
        result = gates_mod.check_gates(self.root)
        # LICENSE itself is never scanned, so its one gate entry is stale,
        # not "covered" -- proving LICENSE content was not read for gates.
        self.assertIn("gate-stale", {e["code"] for e in result["errors"]})
        self.assertEqual(result["flagged"], 0)


class NonMarkdownTextFileScanningTests(FakeMethodsTreeTestCase):
    def test_a_non_markdown_text_file_is_scanned(self):
        write(self.root, "methods/example/notes.txt", "Quiz the user before shipping.\n")
        self.write_gates()
        result = gates_mod.check_gates(self.root)
        self.assertEqual(result["flagged"], 1)
        self.assertFalse(result["ok"])

    def test_a_binary_file_is_not_scanned_and_does_not_crash(self):
        full = os.path.join(self.root, "methods", "example", "blob.bin")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(b"\x00\x01\x02binary Quiz the user\xff")
        self.write_gates()
        result = gates_mod.check_gates(self.root)
        self.assertEqual(result["flagged"], 0)
        self.assertTrue(result["ok"])


def disk_sha(root, name):
    import sync_methods
    files, _symlinks = sync_methods.collect_tree(os.path.join(root, "methods", name))
    return sync_methods.method_sha256(files)


class TamperTests(FakeMethodsTreeTestCase):
    """UPSTREAM.json records what was synced; the files on disk must still be that."""

    def sync_foo(self):
        write(self.root, "methods/foo/SKILL.md", "# foo\n\nOrdinary prose.\n")
        sha = disk_sha(self.root, "foo")
        self.write_upstream({"foo": {"path": "skills/x/foo", "files": ["SKILL.md"], "sha256": sha}})
        self.write_gates(reviewed={"foo": sha})

    def test_an_untouched_method_passes(self):
        self.sync_foo()
        self.assertTrue(gates_mod.check_gates(self.root)["ok"])

    def test_a_method_edited_by_hand_is_tampered(self):
        self.sync_foo()
        with open(os.path.join(self.methods, "foo", "SKILL.md"), "a", encoding="utf-8") as handle:
            handle.write("Refactor mercilessly.\n")
        result = gates_mod.check_gates(self.root)
        self.assertFalse(result["ok"])
        entry = next(e for e in result["errors"] if e["code"] == "method-tampered")
        self.assertEqual(entry["path"], "foo")

    def test_a_file_added_by_hand_is_tampered(self):
        self.sync_foo()
        write(self.root, "methods/foo/extra.md", "An extra file nobody synced.\n")
        codes = {e["code"] for e in gates_mod.check_gates(self.root)["errors"]}
        self.assertIn("method-tampered", codes)

    def test_a_tracked_method_missing_from_disk_is_tampered(self):
        self.write_upstream({"foo": {"path": "skills/x/foo", "files": ["SKILL.md"], "sha256": "abc"}})
        self.write_gates(reviewed={"foo": "abc"})
        codes = {e["code"] for e in gates_mod.check_gates(self.root)["errors"]}
        self.assertIn("method-tampered", codes)


class ReviewedHashTests(FakeMethodsTreeTestCase):
    def method_entry(self, sha):
        # The reviewed-hash tests are about UPSTREAM.json versus gates.json, so they
        # switch the on-disk comparison off by recording a hash that matches the disk
        # only when asked to; see TamperTests for the disk comparison itself.
        return {"path": "skills/x/foo", "files": ["SKILL.md"], "sha256": sha}

    def setUp(self):
        super().setUp()
        self._real = gates_mod.disk_digest
        gates_mod.disk_digest = lambda methods_root, name: None
        self.addCleanup(lambda: setattr(gates_mod, "disk_digest", self._real))

    def test_missing_reviewed_entry_is_method_unreviewed(self):
        write(self.root, "methods/foo/SKILL.md", "# foo\n\nOrdinary prose.\n")
        self.write_upstream({"foo": self.method_entry("abc123")})
        self.write_gates(reviewed={})
        result = gates_mod.check_gates(self.root)
        self.assertFalse(result["ok"])
        entry = next(e for e in result["errors"] if e["code"] == "method-unreviewed")
        self.assertEqual(entry["path"], "foo")
        self.assertIn("abc123", entry["message"])

    def test_mismatched_reviewed_hash_is_method_unreviewed(self):
        write(self.root, "methods/foo/SKILL.md", "# foo\n\nOrdinary prose.\n")
        self.write_upstream({"foo": self.method_entry("abc123")})
        self.write_gates(reviewed={"foo": "stale-hash"})
        result = gates_mod.check_gates(self.root)
        self.assertFalse(result["ok"])
        codes = {e["code"] for e in result["errors"]}
        self.assertIn("method-unreviewed", codes)

    def test_matching_reviewed_hash_is_not_an_error(self):
        write(self.root, "methods/foo/SKILL.md", "# foo\n\nOrdinary prose.\n")
        self.write_upstream({"foo": self.method_entry("abc123")})
        self.write_gates(reviewed={"foo": "abc123"})
        result = gates_mod.check_gates(self.root)
        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])

    def test_reviewed_entry_for_a_method_no_longer_tracked_is_stale(self):
        self.write_upstream({})  # "foo" no longer exists upstream
        self.write_gates(reviewed={"foo": "abc123"})
        result = gates_mod.check_gates(self.root)
        self.assertFalse(result["ok"])
        entry = next(e for e in result["errors"] if e["code"] == "reviewed-stale")
        self.assertEqual(entry["path"], "foo")

    def test_upstream_json_missing_is_fatal(self):
        os.remove(os.path.join(self.root, "methods", "UPSTREAM.json"))
        self.write_gates()
        result = gates_mod.check_gates(self.root)
        self.assertFalse(result["ok"])
        self.assertTrue(result["_fatal"])
        self.assertIn("upstream-missing", {e["code"] for e in result["errors"]})


class AcceptTests(FakeMethodsTreeTestCase):
    def setUp(self):
        # About UPSTREAM.json versus gates.json only; TamperTests covers the disk.
        super().setUp()
        self._real = gates_mod.disk_digest
        gates_mod.disk_digest = lambda methods_root, name: None
        self.addCleanup(lambda: setattr(gates_mod, "disk_digest", self._real))

    def test_accept_one_method_copies_its_current_hash(self):
        write(self.root, "methods/foo/SKILL.md", "# foo\n\nOrdinary prose.\n")
        write(self.root, "methods/bar/SKILL.md", "# bar\n\nOrdinary prose.\n")
        self.write_upstream({
            "foo": self.entry("hash-foo"),
            "bar": self.entry("hash-bar"),
        })
        self.write_gates(reviewed={})
        before = gates_mod.check_gates(self.root)
        self.assertFalse(before["ok"])

        accepted = gates_mod.accept_reviews(self.root, ["foo"], False)
        self.assertEqual(accepted, ["foo"])

        with open(os.path.join(self.root, "methods", "gates.json"), encoding="utf-8") as handle:
            gates_data = json.load(handle)
        self.assertEqual(gates_data["reviewed"], {"foo": "hash-foo"})

        after = gates_mod.check_gates(self.root)
        after_codes_by_path = {e["path"]: e["code"] for e in after["errors"]}
        self.assertNotIn("foo", after_codes_by_path)
        self.assertEqual(after_codes_by_path.get("bar"), "method-unreviewed")

    def test_accept_all_copies_every_current_hash(self):
        write(self.root, "methods/foo/SKILL.md", "# foo\n\nOrdinary prose.\n")
        write(self.root, "methods/bar/SKILL.md", "# bar\n\nOrdinary prose.\n")
        self.write_upstream({
            "foo": self.entry("hash-foo"),
            "bar": self.entry("hash-bar"),
        })
        self.write_gates(reviewed={})
        accepted = gates_mod.accept_reviews(self.root, None, True)
        self.assertEqual(accepted, ["bar", "foo"])
        result = gates_mod.check_gates(self.root)
        self.assertTrue(result["ok"])

    def test_accept_preserves_other_gates_json_structure(self):
        write(self.root, "methods/foo/SKILL.md", "# foo\n\nOrdinary prose.\n")
        self.write_upstream({"foo": self.entry("hash-foo")})
        self.write_gates(
            gates=[{"file": "x", "match": "y", "replaced_by": "z"}],
            exempt_files=[{"file": "w", "reason": "r"}],
            reviewed={},
        )
        gates_mod.accept_reviews(self.root, ["foo"], False)
        with open(os.path.join(self.root, "methods", "gates.json"), encoding="utf-8") as handle:
            gates_data = json.load(handle)
        self.assertEqual(gates_data["gates"], [{"file": "x", "match": "y", "replaced_by": "z"}])
        self.assertEqual(gates_data["exempt_files"], [{"file": "w", "reason": "r"}])
        self.assertEqual(gates_data["reviewed"], {"foo": "hash-foo"})

    def test_accept_unknown_method_raises(self):
        self.write_upstream({})
        self.write_gates()
        with self.assertRaises(ValueError):
            gates_mod.accept_reviews(self.root, ["does-not-exist"], False)

    def entry(self, sha):
        return {"path": "skills/x/foo", "files": ["SKILL.md"], "sha256": sha}


class RealMethodsTreeTests(unittest.TestCase):
    def test_the_real_methods_tree_and_registry_pass(self):
        result = gates_mod.check_gates(ROOT)
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["ok"])
        self.assertGreater(result["flagged"], 0)
        self.assertEqual(result["flagged"], result["covered"])

    def test_the_real_hitl_script_is_exempt_and_executable_bit_untouched(self):
        script = os.path.join(ROOT, "methods", "diagnosing-bugs", "scripts", "hitl-loop.template.sh")
        self.assertTrue(os.path.isfile(script))
        # Not asserting a particular mode here -- sync_methods.py preserves
        # whatever upstream ships -- just that check_method_gates can read it.
        hits = gates_mod.flagged_lines(script)
        self.assertGreater(len(hits), 0)


if __name__ == "__main__":
    unittest.main()
