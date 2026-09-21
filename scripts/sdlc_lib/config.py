"""Loading and validating ``docs/agents/sdlc.json`` (contracts.md section 3)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import CONFIG_PATH
from .result import Result

DEFAULTS: Dict[str, Any] = {
    "schema": 1,
    "spec_gate": "always",
    "merge": "auto",
    "max_implementers": 3,
    "ticket_budget_turns": 60,
    "session_budget_features": 3,
    "max_pending_acceptance": 3,
    "debt_threshold_per_module": 5,
    "map_max_lines": 120,
    "module_roots": ["src"],
    "test_globs": [
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
    "main_branch": "main",
    "pull_requests": False,
    "forbidden_commands": [],
    "skills": {
        "interview": "bundled",
        "domain": "bundled",
        "tdd": "bundled",
        "debugging": "bundled",
        "design": "impeccable",
    },
}

SUPPORTED_SCHEMA = 1

_MIN_BOUNDS = {
    "max_implementers": 1,
    "ticket_budget_turns": 1,
    "session_budget_features": 1,
    "max_pending_acceptance": 0,
    "debt_threshold_per_module": 1,
}


def config_file_path(repo: Path) -> Path:
    return repo / CONFIG_PATH


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def load_config(repo: Path, result: Result, required: bool = True) -> Optional[Dict[str, Any]]:
    """Load and validate the config file.

    If the file is missing and ``required`` is False, returns ``None``
    without recording any error (the caller -- state.py -- treats a missing
    config as "not initialized", not as a malformed-input failure).

    If the file is missing and ``required`` is True, or if it exists but is
    malformed / fails validation, records a fatal error on ``result`` and
    returns ``None``.

    On success, returns the config merged with defaults.
    """
    path = config_file_path(repo)
    if not path.is_file():
        if required:
            result.fail_fatal(
                "config-missing", "docs/agents/sdlc.json not found", CONFIG_PATH
            )
        return None

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        result.fail_fatal(
            "config-missing",
            "could not read docs/agents/sdlc.json: %s" % exc,
            CONFIG_PATH,
        )
        return None

    try:
        raw = json.loads(raw_text)
    except ValueError as exc:
        result.fail_fatal(
            "config-invalid-json",
            "docs/agents/sdlc.json is not valid JSON: %s" % exc,
            CONFIG_PATH,
        )
        return None

    if not isinstance(raw, dict):
        result.fail_fatal(
            "config-invalid-json",
            "docs/agents/sdlc.json must contain a JSON object",
            CONFIG_PATH,
        )
        return None

    schema = raw.get("schema", DEFAULTS["schema"])
    if not _is_int(schema):
        result.fail_fatal(
            "config-invalid-value", "schema must be an integer", CONFIG_PATH
        )
        return None
    if schema > SUPPORTED_SCHEMA:
        result.fail_fatal(
            "config-unsupported-schema",
            "config schema %s is newer than supported (%s)" % (schema, SUPPORTED_SCHEMA),
            CONFIG_PATH,
        )
        return None

    verify = raw.get("verify")
    if not isinstance(verify, str) or not verify.strip():
        result.fail_fatal(
            "config-missing-verify", "verify is required and must be a non-empty string", CONFIG_PATH
        )
        return None

    cfg = dict(DEFAULTS)
    cfg.update(raw)

    # skills merges slot by slot: a config naming one slot keeps the
    # defaults of the others, rather than replacing the whole object.
    raw_skills = raw.get("skills")
    if isinstance(raw_skills, dict):
        merged_skills = dict(DEFAULTS["skills"])
        merged_skills.update(raw_skills)
        cfg["skills"] = merged_skills

    errs = []
    if cfg.get("spec_gate") not in ("always", "questions-only"):
        errs.append(("spec_gate", "must be 'always' or 'questions-only'"))
    if cfg.get("merge") not in ("auto", "human"):
        errs.append(("merge", "must be 'auto' or 'human'"))
    for key, minimum in _MIN_BOUNDS.items():
        v = cfg.get(key)
        if not _is_int(v) or v < minimum:
            errs.append((key, "must be an integer >= %d" % minimum))
    if not _is_int(cfg.get("map_max_lines")):
        errs.append(("map_max_lines", "must be an integer"))
    if not isinstance(cfg.get("module_roots"), list) or not all(
        isinstance(x, str) for x in cfg.get("module_roots", [])
    ):
        errs.append(("module_roots", "must be a list of strings"))
    if not isinstance(cfg.get("test_globs"), list) or not all(
        isinstance(x, str) for x in cfg.get("test_globs", [])
    ):
        errs.append(("test_globs", "must be a list of strings"))
    if not isinstance(cfg.get("main_branch"), str) or not cfg.get("main_branch", "").strip():
        errs.append(("main_branch", "must be a non-empty string"))
    if not isinstance(cfg.get("pull_requests"), bool):
        errs.append(("pull_requests", "must be a boolean"))
    forbidden = cfg.get("forbidden_commands")
    if not isinstance(forbidden, list) or not all(isinstance(x, str) for x in forbidden):
        errs.append(("forbidden_commands", "must be a list of strings"))
    else:
        for pattern in forbidden:
            try:
                re.compile(pattern)
            except re.error:
                errs.append(("forbidden_commands", "invalid regular expression: %r" % pattern))
                break
    skills = cfg.get("skills")
    if not isinstance(skills, dict) or not all(isinstance(v, str) for v in skills.values()):
        errs.append(("skills", "must be an object mapping slot name to skill name"))

    if errs:
        for key, msg in errs:
            result.error("config-invalid-value", "%s: %s" % (key, msg), CONFIG_PATH)
        result.fatal = True
        return None

    return cfg
