#!/usr/bin/env python3
"""Check that every human-gate line in methods/ is accounted for.

The upstream methods under methods/ assume a human is present ("confirm them
with the user", "Quiz the user", "ask the user", ...). This plugin runs
unattended and replaces each of those gates with something else. A silent
upstream change that adds a new human gate must fail this check rather than
stall or mislead an agent, so every such line is either registered in
methods/gates.json (with what replaces it) or lives in a file that is exempt
because a human genuinely is present when it is loaded.

Regexes can never catch every phrasing a future upstream commit might use, so
they are only the aid. The hard guarantee is `gates.json`'s `"reviewed"` map:
one sha256 per tracked method, copied from methods/UPSTREAM.json the moment a
person has actually read that version's diff. Any upstream change to a
followed method -- caught by the regex or not -- changes that method's
sha256 in UPSTREAM.json and so fails this check (`method-unreviewed`) until
someone re-reads it and runs `--accept <method>`. `--accept-all` accepts
every tracked method at once.

Documented misses (regex tuning is deliberately conservative to avoid
flagging harmless prose -- see the "must NOT flag" list below -- so these
realistic phrasings pass undetected by the regex layer; `reviewed` still
catches any upstream change to the file they live in):
  - A verb from the list ("confirm", "tell", "ask", "loop ... in", ...)
    whose object is a bare pronoun rather than one of the fixed human nouns
    or the "ask for it" idiom: "Confirm with them before merging.", "Tell
    them what changed.", "Loop them in before shipping." Widening to bare
    "them"/"they" reflagged ordinary prose such as to-tickets' "let them
    share an integration branch that all block a final integrate-and-verify
    ticket" (not a gate: "them" is the tickets, not a human).
  - A question with no fixed leading auxiliary and no line-start anchor,
    e.g. a "?" deep inside a longer sentence with no trigger word nearby.
  - A first-person question ("Can I ...?", "Should we ...?") is
    deliberately excluded even though it starts with a listed auxiliary --
    diagnosing-bugs' Phase-1 checklist ("Can I make it faster?") is the
    agent questioning itself, not a human gate.

Standard library only. Prints one JSON document on stdout; human-readable
diagnostics on stderr. Exit 0 (ok), 1 (an unregistered gate, a stale
registry entry, a missing exempt file, or an unreviewed/stale method), 2
(methods/, gates.json or UPSTREAM.json could not be read at all).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Tuple

GATES_RELPATH = "gates.json"
NEVER_SCANNED = {"README.md", "gates.json", "UPSTREAM.json", "LICENSE"}
SHELL_EXTENSIONS = (".sh", ".bash")

# --- Human-gate detection -------------------------------------------------
#
# Each regex is one narrow idiom: an interaction verb or fixed phrase bound
# to a human noun, or a strong standalone marker (AskUserQuestion, HITL,
# "sign-off", a leading question word). Deliberately narrower than "any verb
# near any noun anywhere in the line", because that shape flags harmless
# prose such as "the user's exact symptom" (diagnosing-bugs), "confirm the
# fixed point resolves" (code-review), or "let them share an integration
# branch" (to-tickets, bare pronoun, not a fixed human noun). Each pattern
# is tuned against the real vendored files; see the module docstring for the
# documented misses this leaves.
#
# A shared negative lookbehind excludes a verb immediately preceded by a
# negation ("not "/"n't "/"never "), so a line that explicitly says no
# interaction happens -- to-spec's "Do NOT interview the user; just
# synthesize what you already know.", grilling's "don't ask the user for
# anything you could look up yourself" -- is not flagged as if it still
# needed a human gate.
_NEG = r"(?<!not )(?<!n't )(?<!never )"

# "the user", "a human", "a developer", ... "someone", "your human". Bare
# "them"/"they" are deliberately excluded here (see documented misses); the
# one place a bare pronoun stands in for the human is the fixed "ask for it"
# idiom, handled by its own pattern below.
_HUMAN = (
    r"(?:\b(?:the|a)\s+(?:user|human|developer|reviewer|requester|maintainer|"
    r"owner|product owner|person|colleague|teammate)\b"
    r"|\bsomeone\b|\byour human\b)"
)

_VERBS = (
    r"(?:ask(?:s|ed|ing)?|tell\w*|prompt\w*|confirm\w*|check\w*|show\w*|present\w*|surface\w*"
    r"|escalate\w*|hand[- ]off\w*|hand[- ]back\w*|interview\w*|quiz\w*|consult\w*"
    r"|wait for|iterate with)"
)

_NOUN_FIRST_VERBS = r"(?:approves?|confirms?|decides?|chooses?|signs? off|responds?|agrees?)"

GATE_PATTERNS: Dict[str, re.Pattern] = {
    # "ask the user", "Ask the user for", "Check with the user", "confirm
    # them with a developer", "Show the ranked list to the user", "Present
    # these candidates to the user", "Quiz the user", "tell the user to run"
    "verb_then_human": re.compile(_NEG + r"\b" + _VERBS + r"\b[^.\n]{0,60}" + _HUMAN, re.I),
    # "Iterate until the user approves the breakdown.", "Get sign-off from
    # the developer before merging" (human noun precedes the verb)
    "human_then_verb": re.compile(_HUMAN + r"[^.\n]{0,60}" + _NEG + r"\b" + _NOUN_FIRST_VERBS + r"\b", re.I),
    # code-review: "If they didn't specify one, ask for it." -- the one
    # place the bare pronoun stands in for the human, via this fixed idiom.
    "ask_for_it": re.compile(r"\bask for it\b", re.I),
    # "Get sign-off", "Request confirmation", "Approval must be obtained",
    # "Only proceed with the user's approval", "the go-ahead", "permission"
    "signoff_words": re.compile(r"\b(?:sign-?off|approval|confirmation|the go-ahead|permission)\b", re.I),
    # "Use AskUserQuestion to clarify", "This is a HITL step",
    # "a human in the loop only via `scripts/hitl-loop.template.sh`"
    "hitl_markers": re.compile(r"\bAskUserQuestion\b|\bHITL\b|\bhuman[- ]in[- ]the[- ]loop\b", re.I),
    # "Wait for approval before proceeding", "Pause and let the user
    # choose", "block until the human replies"
    "wait_for": re.compile(
        r"\b(?:wait for|pause|block until|hold off|check in)\b[^.\n]{0,40}"
        r"\b(?:approv|confirm|respon|answer|human|user|input|reply)", re.I,
    ),
    # "let the user choose" -- deliberately not bare "let them" (to-tickets:
    # "let them share an integration branch" must stay clean).
    "let_human": re.compile(_NEG + r"\blet (?:the user|the human|the developer)\b", re.I),
    # "Do you agree with this breakdown?", "Hand off to the user", "let me
    # know"
    "question_phrases": re.compile(r"\b(?:do you|would you|what do you|which do you|let me know)\b", re.I),
    # A line (or list item) that itself opens with a yes/no question word
    # and asks one: "Does the granularity feel right?", "Are the blocking
    # edges correct...?", "Should any tickets be merged or split further?".
    # Anchored to the start of the line (after an optional bullet marker) --
    # not "anywhere in the line" -- so an unrelated technical "is"/"are"
    # earlier in a sentence does not drag in an unrelated trailing "?".
    # (?!\s+(?:I|we)\b) excludes the agent's own first-person checklist
    # questions ("Can I make it faster?", diagnosing-bugs Phase 1) -- those
    # are the agent interrogating itself, not addressing a human.
    "question_leading": re.compile(
        r"^\s*(?:[-*]\s*)?(?:does|do|are|is|should|could|would|can)(?!\s+(?:I|we)\b)\b[^\n]*\?", re.I,
    ),
    # Sentence- or list-initial bare "ask": "Ask: \"What's the public
    # interface...\"", "If unclear, ask." -- not "ask yourself".
    "bare_ask": re.compile(r"^\s*(?:[-*\d.)#]+\s*)*ask\b(?!\s+yourself)|\bask\.\s*$", re.I),
    # "Prompt the user for the missing value", "This is interactive"
    "interactive": re.compile(r"\binteractive(?:ly)?\b|\bprompts?\s+for\b", re.I),
    # A show/present/ask/tell clause that itself introduces a list ("Present
    # the proposed breakdown as a numbered list. For each ticket, show:") --
    # the noun is the list that follows, not a named human, so
    # verb_then_human alone would miss it. The tight {0,3} gap (not
    # unbounded) means only the word immediately before the colon counts:
    # "Confirm:" as a bare checklist header (diagnosing-bugs, "verify these
    # yourself"), or a "show"/"present" far earlier in an unrelated longer
    # sentence (diagnosing-bugs' Phase-1 completion criterion), must not
    # match. "confirm" is deliberately excluded from this verb list for the
    # same reason "Confirm:" is a checklist header, not a request to a human.
    "colon_intro": re.compile(_NEG + r"\b(?:show|present|ask|tell)\w*\b[^.\n]{0,3}:\s*$", re.I),
    # Shell-only: an interactive prompt a human is meant to answer at a
    # terminal. Only applied to .sh/.bash files (see is_human_gate_line).
    "shell_read_prompt": re.compile(r"\bread\s+(?:-\w+\s+)*-p\b|\bselect\s+\w+\s+in\b", re.I),
}
# Must-not-flag examples this set was tuned against (kept here, not
# asserted, as documentation): "the user's exact symptom", "user
# story"/"user stories", "user-facing", "from the user's perspective",
# "confirm the fixed point resolves", "let them share an integration
# branch", frontmatter `description:` lines, fenced code, `createUser`.

_SHELL_ONLY = {"shell_read_prompt"}


def is_human_gate_line(line: str, shell: bool = False) -> bool:
    for name, rx in GATE_PATTERNS.items():
        if name in _SHELL_ONLY and not shell:
            continue
        if rx.search(line):
            return True
    return False


def frontmatter_line_range(lines: List[str]) -> range:
    """1-indexed line numbers covered by a leading --- ... --- frontmatter
    block, empty range if there is none."""
    if not lines or lines[0].rstrip("\n") != "---":
        return range(0)
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            return range(1, i + 2)  # both --- delimiter lines, 1-indexed
    return range(0)


def flagged_lines(path: str) -> List[Tuple[int, str]]:
    shell = path.endswith(SHELL_EXTENSIONS)
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
    skip = frontmatter_line_range(lines)
    out: List[Tuple[int, str]] = []
    in_fence = False
    for lineno, raw in enumerate(lines, start=1):
        if lineno in skip:
            continue
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if is_human_gate_line(raw, shell=shell):
            out.append((lineno, raw.rstrip("\n")))
    return out


def discover_scannable(methods_root: str) -> List[str]:
    """Relative (posix) paths of every text file under methods_root except
    the four hand-off files at its root."""
    out = []
    for folder, dirs, files in os.walk(methods_root):
        dirs[:] = sorted(dirs)
        for name in sorted(files):
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, methods_root).replace(os.sep, "/")
            if rel in NEVER_SCANNED:
                continue
            out.append(rel)
    return sorted(out)


def is_probably_text(path: str) -> bool:
    try:
        with open(path, "rb") as handle:
            chunk = handle.read(8192)
    except OSError:
        return False
    return b"\0" not in chunk


class Report:
    def __init__(self) -> None:
        self.errors: List[dict] = []
        self.warnings: List[dict] = []
        self.fatal: bool = False

    def error(self, code: str, path: str, message: str) -> None:
        self.errors.append({"code": code, "path": path, "message": message})

    def fail_fatal(self, code: str, path: str, message: str) -> None:
        self.error(code, path, message)
        self.fatal = True

    def warn(self, code: str, path: str, message: str) -> None:
        self.warnings.append({"code": code, "path": path, "message": message})


def _load_json(path: str):
    """Returns (data, error_kind). error_kind is None on success, "missing"
    or the exception text otherwise."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except FileNotFoundError:
        return None, "missing"
    except (OSError, ValueError) as exc:
        return None, str(exc)


def load_gates(methods_root: str):
    data, err = _load_json(os.path.join(methods_root, GATES_RELPATH))
    if err == "missing":
        return None
    if err is not None:
        return {"__fatal__": "methods/gates.json is not valid JSON: %s" % err}
    if not isinstance(data, dict) or not isinstance(data.get("gates"), list) \
            or not isinstance(data.get("exempt_files"), list):
        return {"__fatal__": 'methods/gates.json must be {"gates": [...], "exempt_files": [...]}'}
    return data


def load_upstream(methods_root: str):
    data, err = _load_json(os.path.join(methods_root, "UPSTREAM.json"))
    if err == "missing":
        return None, "missing"
    if err is not None:
        return None, err
    if not isinstance(data, dict) or not isinstance(data.get("methods"), dict):
        return None, 'methods/UPSTREAM.json must have a "methods" object'
    return data, None


def disk_digest(methods_root: str, name: str):
    """Digest of methods/<name>/ as it is on disk, computed exactly as the sync
    tool computes the one it records; None when it cannot be computed here."""
    folder = os.path.join(methods_root, name)
    if not os.path.isdir(folder):
        return ""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sync_methods
    files, _symlinks = sync_methods.collect_tree(folder)
    return sync_methods.method_sha256(files)


def check(root: str) -> Tuple[Report, int, int]:
    """Returns (report, flagged_count, covered_count)."""
    report = Report()
    methods_root = os.path.join(root, "methods")

    if not os.path.isdir(methods_root):
        report.fail_fatal("methods-missing", "methods", "methods/ directory does not exist")
        return report, 0, 0

    gates_data = load_gates(methods_root)
    if gates_data is None:
        report.fail_fatal("gates-missing", GATES_RELPATH, "methods/gates.json is missing")
        return report, 0, 0
    if "__fatal__" in gates_data:
        report.fail_fatal("gates-invalid", GATES_RELPATH, gates_data["__fatal__"])
        return report, 0, 0

    upstream, upstream_err = load_upstream(methods_root)
    if upstream is None:
        code = "upstream-missing" if upstream_err == "missing" else "upstream-invalid"
        report.fail_fatal(code, "UPSTREAM.json", "methods/UPSTREAM.json: %s" % upstream_err)
        return report, 0, 0
    current_methods = upstream["methods"]

    gates = gates_data.get("gates", [])
    exempt_files = gates_data.get("exempt_files", [])
    reviewed = gates_data.get("reviewed", {})
    if not isinstance(reviewed, dict):
        report.fail_fatal("gates-invalid", GATES_RELPATH, '"reviewed" must be an object mapping method name to sha256')
        return report, 0, 0

    exempt_names = set()
    for entry in exempt_files:
        rel = entry.get("file", "")
        exempt_names.add(rel)
        if not rel or not os.path.isfile(os.path.join(methods_root, rel)):
            report.error("exempt-file-missing", rel or "<empty>",
                         "exempt_files entry names a file that does not exist under methods/")

    by_file: Dict[str, List[dict]] = {}
    for entry in gates:
        by_file.setdefault(entry.get("file", ""), []).append(entry)

    flagged_total = 0
    covered_total = 0
    gate_matched: Dict[Tuple[str, str], bool] = {}
    for entry in gates:
        gate_matched[(entry.get("file", ""), entry.get("match", ""))] = False

    for rel in discover_scannable(methods_root):
        full = os.path.join(methods_root, rel)
        if not is_probably_text(full):
            continue
        try:
            hits = flagged_lines(full)
        except (OSError, UnicodeDecodeError) as exc:
            report.error("gate-unregistered", rel, "could not read file: %s" % exc)
            continue
        if not hits:
            continue
        flagged_total += len(hits)
        if rel in exempt_names:
            covered_total += len(hits)
            continue
        entries = by_file.get(rel, [])
        for lineno, text in hits:
            covering = [e for e in entries if e.get("match", "") and e.get("match", "") in text]
            if covering:
                covered_total += 1
                for e in covering:
                    gate_matched[(rel, e.get("match", ""))] = True
            else:
                report.error(
                    "gate-unregistered", rel,
                    "line %d is not covered by methods/gates.json and %s is not exempt: %s"
                    % (lineno, rel, text),
                )

    for entry in gates:
        key = (entry.get("file", ""), entry.get("match", ""))
        if not gate_matched.get(key, False):
            report.error(
                "gate-stale", entry.get("file", ""),
                "gates.json entry with match %r does not match any flagged line" % entry.get("match", ""),
            )

    for name, info in sorted(current_methods.items()):
        current_hash = info.get("sha256", "") if isinstance(info, dict) else ""
        on_disk = disk_digest(methods_root, name)
        if on_disk is not None and on_disk != current_hash:
            report.error(
                "method-tampered", name,
                "methods/%s/ on disk does not match the digest recorded in UPSTREAM.json -- vendored "
                "methods are never edited by hand; restore it with `python3 tools/sync_methods.py`"
                % name,
            )
        reviewed_hash = reviewed.get(name)
        if reviewed_hash is None or reviewed_hash != current_hash:
            report.error(
                "method-unreviewed", name,
                "current sha256 %s, reviewed sha256 %s -- read the diff, update gates.json (and "
                "the phase or agent that replaces any new gate), then run "
                "`python3 tools/check_method_gates.py --accept %s`"
                % (current_hash, reviewed_hash or "(none)", name),
            )

    for name in sorted(reviewed):
        if name not in current_methods:
            report.error(
                "reviewed-stale", name,
                "gates.json \"reviewed\" names %r, which no longer exists in UPSTREAM.json" % name,
            )

    return report, flagged_total, covered_total


def check_gates(root: str) -> dict:
    """Importable entry point: returns the same dict the CLI prints, plus a
    private ``_fatal`` flag the CLI uses to pick exit code 2 over 1."""
    report, flagged, covered = check(root)
    return {
        "ok": not report.errors,
        "errors": report.errors,
        "warnings": report.warnings,
        "flagged": flagged,
        "covered": covered,
        "_fatal": report.fatal,
    }


def accept_reviews(root: str, methods: List[str], accept_all: bool) -> List[str]:
    """Copies the current UPSTREAM.json sha256 of the given methods (or
    every tracked method, with accept_all) into gates.json's "reviewed" map.

    Preserves the rest of gates.json's structure and key order; only
    "reviewed" is replaced, with its own keys sorted. Returns the list of
    method names accepted. Raises ValueError for an unknown method name,
    OSError if a file cannot be read or written.
    """
    methods_root = os.path.join(root, "methods")
    gates_path = os.path.join(methods_root, GATES_RELPATH)
    with open(gates_path, encoding="utf-8") as handle:
        gates_data = json.load(handle)
    upstream, err = load_upstream(methods_root)
    if upstream is None:
        raise ValueError("methods/UPSTREAM.json: %s" % err)
    current_methods = upstream["methods"]

    targets = sorted(current_methods) if accept_all else list(methods or [])
    unknown = [m for m in targets if m not in current_methods]
    if unknown:
        raise ValueError("unknown method(s), not in UPSTREAM.json: %s" % ", ".join(sorted(unknown)))

    reviewed = dict(gates_data.get("reviewed", {}))
    for name in targets:
        reviewed[name] = current_methods[name]["sha256"]
    gates_data["reviewed"] = {name: reviewed[name] for name in sorted(reviewed)}

    with open(gates_path, "w", encoding="utf-8") as handle:
        json.dump(gates_data, handle, indent=2)
        handle.write("\n")

    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    parser.add_argument("--accept", nargs="+", metavar="METHOD", default=None,
                        help="record the current UPSTREAM.json sha256 as reviewed for the given method(s)")
    parser.add_argument("--accept-all", action="store_true",
                        help="record the current UPSTREAM.json sha256 as reviewed for every tracked method")
    args = parser.parse_args()
    root = os.path.abspath(args.root)

    if args.accept or args.accept_all:
        try:
            targets = accept_reviews(root, args.accept, args.accept_all)
        except (OSError, ValueError) as exc:
            sys.stderr.write("error  accept-failed  methods/gates.json: %s\n" % exc)
            print(json.dumps({"ok": False, "accepted": [], "error": str(exc)}, indent=2))
            return 2
        sys.stderr.write("accepted review for: %s\n" % ", ".join(targets))
        print(json.dumps({"ok": True, "accepted": targets}, indent=2))
        return 0

    result = check_gates(root)
    fatal = result.pop("_fatal")
    for entry in result["errors"]:
        sys.stderr.write("error  %-22s %s: %s\n" % (entry["code"], entry["path"], entry["message"]))
    for entry in result["warnings"]:
        sys.stderr.write("warn   %-22s %s: %s\n" % (entry["code"], entry["path"], entry["message"]))
    print(json.dumps(result, indent=2))
    if fatal:
        return 2
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
