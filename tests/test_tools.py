"""Tests of the repository tools: the plugin validator and the packager."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import validate_plugin  # noqa: E402

SHIPPED = [".claude-plugin", "skills", "agents", "hooks", "bin", "scripts", "docs",
           "README.md", "CHANGELOG.md", "LICENSE"]


def copy_plugin(destination):
    for entry in SHIPPED:
        source = os.path.join(ROOT, entry)
        target = os.path.join(destination, entry)
        if os.path.isdir(source):
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, target)


def codes(report):
    return {entry["code"] for entry in report.errors}


class ValidatePluginTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        copy_plugin(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, rel, old, new):
        path = os.path.join(self.root, rel)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(old, text, "fixture drifted: %r not in %s" % (old, rel))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, new, 1))

    def test_the_plugin_as_shipped_is_valid(self):
        report = validate_plugin.validate(ROOT)
        self.assertEqual(report.errors, [])

    def test_an_agent_on_an_unknown_model_is_an_error(self):
        self.edit("agents/explorer.md", "model: haiku", "model: gpt-4")
        self.assertIn("agent-model", codes(validate_plugin.validate(self.root)))

    def test_the_models_table_must_match_the_agent_definitions(self):
        self.edit("agents/explorer.md", "model: haiku", "model: opus")
        self.assertIn("model-mismatch", codes(validate_plugin.validate(self.root)))

    def test_a_phase_that_spawns_an_undefined_agent_is_an_error(self):
        self.edit("skills/sdlc/phases/tickets.md", "`sdlc:ticket-critic`", "`sdlc:ticket-judge`")
        self.assertIn("agent-undefined", codes(validate_plugin.validate(self.root)))

    def test_a_phase_that_names_a_missing_template_is_an_error(self):
        os.remove(os.path.join(self.root, "skills/sdlc/templates/tickets/foundation.md"))
        self.assertIn("template-missing", codes(validate_plugin.validate(self.root)))

    def test_a_template_without_its_marker_is_an_error(self):
        self.edit("skills/sdlc/templates/spec.md", "sdlc:template", "sdlc:tmpl")
        self.assertIn("marker-missing", codes(validate_plugin.validate(self.root)))

    def test_a_dispatched_phase_file_must_exist(self):
        os.remove(os.path.join(self.root, "skills/sdlc/phases/deliver.md"))
        self.assertIn("link-broken", codes(validate_plugin.validate(self.root)))

    def test_an_unlinked_phase_file_is_an_orphan(self):
        with open(os.path.join(self.root, "skills/sdlc/phases/extra.md"), "w", encoding="utf-8") as handle:
            handle.write("# Phase: extra\n")
        self.assertIn("phase-orphan", codes(validate_plugin.validate(self.root)))

    def test_changelog_and_manifest_versions_must_agree(self):
        self.edit(".claude-plugin/plugin.json", '"version": "', '"version": "9.')
        self.assertIn("version-mismatch", codes(validate_plugin.validate(self.root)))

    def test_machine_specific_paths_are_refused(self):
        with open(os.path.join(self.root, "agents/explorer.md"), "a", encoding="utf-8") as handle:
            handle.write("\nSee /Users/someone/notes.md\n")
        self.assertIn("absolute-path", codes(validate_plugin.validate(self.root)))

    def test_a_non_executable_binary_is_an_error(self):
        os.chmod(os.path.join(self.root, "bin/sdlc-state"), 0o644)
        self.assertIn("binary-not-executable", codes(validate_plugin.validate(self.root)))


class PackageTest(unittest.TestCase):
    def test_the_archive_ships_the_runtime_and_is_reproducible(self):
        def build():
            result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "package.py")],
                                    capture_output=True, text=True, check=True)
            return json.loads(result.stdout)

        dist = os.path.join(ROOT, "dist")
        existed = os.path.isdir(dist)
        try:
            first = build()
            second = build()
            self.assertEqual(first["sha256"], second["sha256"])
            with zipfile.ZipFile(os.path.join(ROOT, first["archive"])) as bundle:
                names = set(bundle.namelist())
                mode = bundle.getinfo("sdlc/bin/sdlc-state").external_attr >> 16
            self.assertIn("sdlc/.claude-plugin/plugin.json", names)
            self.assertIn("sdlc/skills/sdlc/SKILL.md", names)
            self.assertIn("sdlc/scripts/state.py", names)
            self.assertFalse([n for n in names if n.startswith(("sdlc/tests/", "sdlc/tools/", "sdlc/.github/"))])
            self.assertFalse([n for n in names if "__pycache__" in n])
            self.assertTrue(mode & 0o100, "executables keep their executable bit")
        finally:
            if not existed:
                shutil.rmtree(dist, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
