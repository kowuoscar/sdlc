"""Implements ``merge_gate.py`` (contracts.md section 13).

Diagnostic codes produced here:

Fatal errors (exit 2 -- config problems reuse the config-* codes from
config.py). Even on a fatal path, "blocking", "downgraded", "harness" and
"verify" are still present in the output (as empty/"failed" placeholders),
per contract.
    spec-not-found        docs/features/<feature>/spec.md does not exist
    frontmatter-invalid   spec.md's frontmatter block is malformed

Errors (contribute to ok=false / exit 1). check_harness's own codes (e.g.
path-missing) are also merged straight in when the harness check fails.
    findings-missing            findings.json does not exist
    findings-invalid-json       findings.json is not valid JSON / not an object
    findings-unsupported-schema findings.json schema is newer than supported
    findings-invalid            'findings' is not a list
    finding-invalid              a finding entry is malformed, including a
                                  non-string 'citation' (never a downgrade)
    finding-blocking             a blocking-type finding is open or fixed
    walkthrough-empty            spec.md has no ## Acceptance walkthrough
                                  section, or it has zero steps
    acceptance-missing           acceptance.json does not exist
    acceptance-invalid-json      acceptance.json is not valid JSON / not an object
    acceptance-unsupported-schema acceptance.json schema is newer than supported
    acceptance-invalid           'steps' is not a list
    acceptance-step-invalid      a step entry is malformed
    acceptance-step-missing      a spec walkthrough step has no entry
    acceptance-step-duplicate    more than one entry for the same step
    acceptance-step-unknown      an entry's step is not in spec.md's walkthrough
    acceptance-evidence-missing  a passed agent step's evidence path is empty,
                                  absolute, contains '..', escapes the feature
                                  directory (symlinks resolved), or does not
                                  exist
    verify-failed                the config verify command exited non-zero
    verify-timeout                the config verify command exceeded the timeout

Warnings:
    finding-downgraded    a blocking-type finding with no citation, downgraded
                           to a smell (does not block)
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Tuple

from . import checks_harness
from . import config as config_mod
from . import spec as spec_mod
from .frontmatter import FrontmatterError
from .paths import acceptance_path, feature_dir, findings_path, relpath, spec_path
from .result import Result

BLOCKING_TYPES = {
    "spec-missing",
    "spec-partial",
    "spec-wrong",
    "out-of-scope",
    "rule-violated",
    "acceptance-failed",
    "design-guideline",
}
NONBLOCKING_TYPES = {"smell"}
ALL_FINDING_TYPES = BLOCKING_TYPES | NONBLOCKING_TYPES
FINDING_STATES = {"open", "fixed", "confirmed", "dismissed"}
BLOCKING_STATES = {"open", "fixed"}

VERIFY_TIMEOUT_SECONDS = 30 * 60


def _load_json_object(path: Path, rel: str, result: Result, missing_code: str, invalid_code: str):
    import json

    if not path.is_file():
        result.error(missing_code, "%s not found" % path.name, rel)
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        result.error(missing_code, "could not read %s: %s" % (path.name, exc), rel)
        return None
    try:
        data = json.loads(text)
    except ValueError as exc:
        result.error(invalid_code, "%s is not valid JSON: %s" % (path.name, exc), rel)
        return None
    if not isinstance(data, dict):
        result.error(invalid_code, "%s must contain a JSON object" % path.name, rel)
        return None
    return data


def _validate_findings(rel: str, data: dict, result: Result) -> Tuple[List[str], List[str]]:
    schema = data.get("schema", 1)
    if not isinstance(schema, int) or isinstance(schema, bool) or schema > 1:
        result.error(
            "findings-unsupported-schema", "findings.json schema %r is not supported" % (schema,), rel
        )
        return [], []
    findings = data.get("findings")
    if not isinstance(findings, list):
        result.error("findings-invalid", "findings.json 'findings' must be a list", rel)
        return [], []

    blocking_ids: List[str] = []
    downgraded_ids: List[str] = []
    seen_ids = set()
    for entry in findings:
        if not isinstance(entry, dict):
            result.error("finding-invalid", "finding entry is not an object", rel)
            continue
        fid = entry.get("id")
        if not isinstance(fid, str) or not fid:
            result.error("finding-invalid", "finding is missing a valid 'id'", rel)
            fid = fid if isinstance(fid, str) and fid else "?"
        elif fid in seen_ids:
            result.error("finding-invalid", "duplicate finding id %r" % fid, rel)
        seen_ids.add(fid)

        ftype = entry.get("type")
        state = entry.get("state")

        if ftype not in ALL_FINDING_TYPES:
            result.error("finding-invalid", "finding %s has unknown type %r" % (fid, ftype), rel)
            continue
        if state not in FINDING_STATES:
            result.error("finding-invalid", "finding %s has unknown state %r" % (fid, state), rel)
            continue

        raw_citation = entry.get("citation", "")
        if not isinstance(raw_citation, str):
            result.error(
                "finding-invalid",
                "finding %s has a non-string citation (%s)" % (fid, type(raw_citation).__name__),
                rel,
            )
            continue
        citation = raw_citation

        effective_type = ftype
        if ftype in BLOCKING_TYPES and not (isinstance(citation, str) and citation.strip()):
            effective_type = "smell"
            downgraded_ids.append(fid)
            result.warning(
                "finding-downgraded",
                "finding %s (%s) has no citation; downgraded to smell" % (fid, ftype),
                rel,
            )

        if effective_type in BLOCKING_TYPES and state in BLOCKING_STATES:
            blocking_ids.append(fid)
            result.error(
                "finding-blocking",
                "finding %s (%s) is %s and blocks merge" % (fid, ftype, state),
                rel,
            )

    return blocking_ids, downgraded_ids


def _evidence_path_is_safe(feature_root: Path, evidence: str) -> bool:
    """contracts.md section 9: a passed agent step's evidence must name a
    relative path with no '..' segment that, once symlinks are resolved, is
    still under the feature directory."""
    raw = Path(evidence)
    if raw.is_absolute():
        return False
    if ".." in raw.parts:
        return False
    resolved_root = feature_root.resolve()
    resolved_target = (feature_root / raw).resolve()
    return resolved_target.is_relative_to(resolved_root)


def _validate_acceptance(repo: Path, feature: str, rel: str, data: dict, spec: spec_mod.SpecData, result: Result) -> None:
    schema = data.get("schema", 1)
    if not isinstance(schema, int) or isinstance(schema, bool) or schema > 1:
        result.error(
            "acceptance-unsupported-schema", "acceptance.json schema %r is not supported" % (schema,), rel
        )
        return
    steps = data.get("steps")
    if not isinstance(steps, list):
        result.error("acceptance-invalid", "acceptance.json 'steps' must be a list", rel)
        return

    spec_steps = set(s.step for s in spec_mod.walkthrough_steps(spec))
    by_step = {}
    for entry in steps:
        if not isinstance(entry, dict):
            result.error("acceptance-step-invalid", "step entry is not an object", rel)
            continue
        num = entry.get("step")
        actor = entry.get("actor")
        status = entry.get("status")
        evidence = entry.get("evidence", "")
        if not isinstance(num, int) or isinstance(num, bool):
            result.error("acceptance-step-invalid", "step entry has a non-integer 'step'", rel)
            continue
        if actor not in ("agent", "human"):
            result.error(
                "acceptance-step-invalid", "step %d has unknown actor %r" % (num, actor), rel
            )
        if status not in ("passed", "failed", "pending"):
            result.error(
                "acceptance-step-invalid", "step %d has unknown status %r" % (num, status), rel
            )
        if num in by_step:
            result.error("acceptance-step-duplicate", "step %d has more than one entry" % num, rel)
        else:
            by_step[num] = entry
        if num not in spec_steps:
            result.error(
                "acceptance-step-unknown",
                "step %d is not a walkthrough step in spec.md" % num,
                rel,
            )
        if actor == "agent" and status == "passed":
            ev = evidence if isinstance(evidence, str) else ""
            if not ev.strip():
                result.error(
                    "acceptance-evidence-missing", "step %d is passed but has no evidence path" % num, rel
                )
            elif not _evidence_path_is_safe(feature_dir(repo, feature), ev):
                result.error(
                    "acceptance-evidence-missing",
                    "step %d evidence %r is not inside the feature directory" % (num, ev),
                    rel,
                )
            elif not (feature_dir(repo, feature) / ev).is_file():
                result.error(
                    "acceptance-evidence-missing",
                    "step %d evidence %r does not exist" % (num, ev),
                    rel,
                )

    for sn in sorted(spec_steps):
        if sn not in by_step:
            result.error(
                "acceptance-step-missing", "walkthrough step %d has no acceptance entry" % sn, rel
            )


def check_merge_gate(
    repo: Path,
    feature: str,
    no_verify: bool,
    result: Result,
    timeout: float = VERIFY_TIMEOUT_SECONDS,
) -> None:
    # These four keys must be present on every path, fatal ones included.
    result.set("blocking", [])
    result.set("downgraded", [])
    result.set("harness", "failed")
    result.set("verify", "failed")

    config = config_mod.load_config(repo, result, required=True)
    if config is None:
        return

    spec_file = spec_path(repo, feature)
    if not spec_file.is_file():
        result.fail_fatal(
            "spec-not-found", "spec.md not found for feature %r" % feature, relpath(repo, spec_file)
        )
        return
    try:
        spec = spec_mod.load_spec(spec_file)
    except FrontmatterError as exc:
        result.fail_fatal("frontmatter-invalid", "spec.md: %s" % exc, relpath(repo, spec_file))
        return
    except OSError as exc:
        result.fail_fatal("spec-not-found", "could not read spec.md: %s" % exc, relpath(repo, spec_file))
        return

    if not spec_mod.walkthrough_steps(spec):
        result.error(
            "walkthrough-empty",
            "spec.md's ## Acceptance walkthrough is missing or has no steps",
            relpath(repo, spec_file),
        )

    blocking_ids: List[str] = []
    downgraded_ids: List[str] = []

    f_path = findings_path(repo, feature)
    f_rel = relpath(repo, f_path)
    f_data = _load_json_object(f_path, f_rel, result, "findings-missing", "findings-invalid-json")
    if f_data is not None:
        blocking_ids, downgraded_ids = _validate_findings(f_rel, f_data, result)

    a_path = acceptance_path(repo, feature)
    a_rel = relpath(repo, a_path)
    a_data = _load_json_object(a_path, a_rel, result, "acceptance-missing", "acceptance-invalid-json")
    if a_data is not None:
        _validate_acceptance(repo, feature, a_rel, a_data, spec, result)

    harness_result = Result()
    checks_harness.check_harness(repo, config, harness_result)
    result.errors.extend(harness_result.errors)
    result.warnings.extend(harness_result.warnings)
    result.set("harness", "passed" if harness_result.ok else "failed")

    if no_verify:
        result.set("verify", "skipped")
    else:
        verify_cmd = config["verify"]
        try:
            proc = subprocess.run(
                verify_cmd,
                shell=True,
                cwd=str(repo),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            result.set("verify", "failed")
            result.error(
                "verify-timeout",
                "verify command %r timed out after %s seconds" % (verify_cmd, timeout),
                "",
            )
        except OSError as exc:
            result.set("verify", "failed")
            result.error("verify-failed", "verify command %r failed to start: %s" % (verify_cmd, exc), "")
        else:
            if proc.returncode == 0:
                result.set("verify", "passed")
            else:
                result.set("verify", "failed")
                result.error(
                    "verify-failed",
                    "verify command %r exited %d" % (verify_cmd, proc.returncode),
                    "",
                )

    result.set("blocking", sorted(blocking_ids))
    result.set("downgraded", sorted(downgraded_ids))
