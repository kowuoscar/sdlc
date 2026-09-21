#!/usr/bin/env python3
"""Vendor copies of Matt Pocock's engineering methods into methods/.

Mirrors a fixed set of directories from the upstream repository
https://github.com/mattpocock/skills into methods/<name>/ in this plugin,
skipping any agents/ subdirectory (platform launcher metadata we do not use),
and writes methods/UPSTREAM.json describing exactly what was copied.

methods/gates.json and methods/README.md are hand-maintained and never
touched by this tool.

A commit that never touched any of the eleven tracked directories or LICENSE
leaves methods/UPSTREAM.json untouched, even though the upstream HEAD moved:
"changed"/"added"/"removed" all come back empty.

Standard library only. Prints one JSON document on stdout; human-readable
diagnostics on stderr. Exit 0 (ok / no changes), 1 (check found a difference,
a named upstream method directory is missing, or a method directory contains
a symlink -- nothing is written either way), 2 (usage error or the source
checkout could not be read, including an unreadable file hit while walking a
method directory).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

DEFAULT_REPO_URL = "https://github.com/mattpocock/skills"
DEFAULT_REF = "main"

# Our method name -> upstream directory (relative to the upstream repo root).
METHODS: Dict[str, str] = {
    "tdd": "skills/engineering/tdd",
    "diagnosing-bugs": "skills/engineering/diagnosing-bugs",
    "domain-modeling": "skills/engineering/domain-modeling",
    "grilling": "skills/productivity/grilling",
    "to-spec": "skills/engineering/to-spec",
    "to-tickets": "skills/engineering/to-tickets",
    "implement-spec": "skills/in-progress/implement-spec",
    "code-review": "skills/engineering/code-review",
    "resolving-merge-conflicts": "skills/engineering/resolving-merge-conflicts",
    "retro": "skills/in-progress/retro",
    "writing-for-agents": "skills/productivity/writing-for-agents",
}

# Files at the root of methods/ that this tool never reads, writes or removes.
HANDS_OFF = {"gates.json", "README.md"}

Tree = Dict[str, Tuple[bytes, bool]]  # relpath (posix) -> (content, executable)


class SourceError(Exception):
    """The upstream checkout could not be obtained or read (exit 2)."""


def git_capture(args: List[str], cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, check=True
        )
    except FileNotFoundError as exc:
        raise SourceError("git is not available: %s" % exc) from exc
    except subprocess.CalledProcessError as exc:
        raise SourceError(
            "git %s failed: %s" % (" ".join(args), exc.stderr.strip())
        ) from exc
    return result.stdout.strip()


def clone_shallow(repo_url: str, ref: str, dest: str) -> None:
    try:
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", ref, repo_url, dest],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError as exc:
        raise SourceError("git is not available: %s" % exc) from exc
    except subprocess.CalledProcessError as exc:
        raise SourceError(
            "could not clone %s at %s: %s" % (repo_url, ref, exc.stderr.strip())
        ) from exc


def source_commit_info(source_dir: str) -> Tuple[str, str]:
    if not os.path.isdir(os.path.join(source_dir, ".git")):
        raise SourceError("%s is not a git checkout" % source_dir)
    sha = git_capture(["rev-parse", "HEAD"], cwd=source_dir)
    date = git_capture(["log", "-1", "--format=%cI"], cwd=source_dir)
    return sha, date


def collect_tree(root: str) -> Tuple[Tree, List[str]]:
    """Walk a directory, skipping any 'agents' subdirectory at any depth.

    Returns (files, symlinks): symlinks (files or directories, dangling or
    not) are never opened -- a symlink can point outside the upstream tree
    -- and are reported by relative path so the caller can refuse the sync.
    """
    out: Tree = {}
    symlinks: List[str] = []
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            full = os.path.join(folder, name)
            if os.path.islink(full):
                symlinks.append(os.path.relpath(full, root).replace(os.sep, "/"))
        dirs[:] = sorted(d for d in dirs if d != "agents" and d != ".git")
        for name in sorted(files):
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if os.path.islink(full):
                symlinks.append(rel)
                continue
            try:
                with open(full, "rb") as handle:
                    content = handle.read()
                executable = bool(os.stat(full).st_mode & stat.S_IXUSR)
            except OSError as exc:
                raise SourceError("could not read %s: %s" % (rel, exc)) from exc
            out[rel] = (content, executable)
    return out, sorted(symlinks)


def method_sha256(files: Tree) -> str:
    hasher = hashlib.sha256()
    for path in sorted(files):
        content, _executable = files[path]
        hasher.update(path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(content)
        hasher.update(b"\0")
    return hasher.hexdigest()


def build_content_tree(source_root: str) -> Tuple[Optional[Tree], List[str], dict]:
    """Returns (content_tree, errors, methods_info).

    content_tree holds every method file plus LICENSE, keyed "<name>/<rel>"
    or "LICENSE" -- never UPSTREAM.json, which depends on the source commit
    and is decided by the caller. content_tree is None when errors is
    non-empty (a method's upstream directory is missing, or it contains a
    symlink): the sync is all-or-nothing.
    """
    errors: List[str] = []
    methods_info: dict = {}
    method_trees: Dict[str, Tree] = {}

    for name in sorted(METHODS):
        upstream_rel = METHODS[name]
        upstream_dir = os.path.join(source_root, upstream_rel)
        if not os.path.isdir(upstream_dir):
            errors.append(
                "missing-upstream-method: %s (upstream directory %s does not exist)"
                % (name, upstream_rel)
            )
            continue
        files, symlinks = collect_tree(upstream_dir)
        for link in symlinks:
            errors.append(
                "upstream-symlink: %s (%s/%s is a symlink; refusing to mirror it)"
                % (name, upstream_rel, link)
            )
        if symlinks:
            continue
        method_trees[name] = files
        methods_info[name] = {
            "path": upstream_rel,
            "files": sorted(files.keys()),
            "sha256": method_sha256(files),
        }

    license_path = os.path.join(source_root, "LICENSE")
    if not os.path.isfile(license_path):
        errors.append("missing-license: upstream LICENSE does not exist")

    if errors:
        return None, errors, {}

    content: Tree = {}
    for name, files in method_trees.items():
        for rel, (content_bytes, executable) in files.items():
            content["%s/%s" % (name, rel)] = (content_bytes, executable)

    try:
        with open(license_path, "rb") as handle:
            content["LICENSE"] = (handle.read(), False)
    except OSError as exc:
        return None, ["missing-license: could not read upstream LICENSE: %s" % exc], {}

    return content, [], methods_info


def build_upstream_json(repo_url: str, sha: str, date: str, methods_info: dict) -> bytes:
    upstream_json = {
        "repository": "mattpocock/skills",
        "url": repo_url,
        "commit": sha,
        "commit_date": date,
        "methods": methods_info,
    }
    return (json.dumps(upstream_json, indent=2, sort_keys=True) + "\n").encode("utf-8")


def collect_existing_tree(methods_root: str) -> Tree:
    out: Tree = {}
    if not os.path.isdir(methods_root):
        return out
    for folder, dirs, files in os.walk(methods_root):
        dirs[:] = sorted(dirs)
        for name in sorted(files):
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, methods_root).replace(os.sep, "/")
            if rel in HANDS_OFF:
                continue
            with open(full, "rb") as handle:
                content = handle.read()
            executable = bool(os.stat(full).st_mode & stat.S_IXUSR)
            out[rel] = (content, executable)
    return out


def diff_trees(old: Tree, new: Tree) -> Tuple[List[str], List[str], List[str]]:
    old_keys = set(old)
    new_keys = set(new)
    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed = sorted(k for k in (old_keys & new_keys) if old[k] != new[k])
    return changed, added, removed


def apply_tree(methods_root: str, new: Tree, removed: List[str]) -> None:
    for rel in removed:
        full = os.path.join(methods_root, *rel.split("/"))
        if os.path.isfile(full):
            os.remove(full)
    for rel, (content, executable) in new.items():
        full = os.path.join(methods_root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(content)
        os.chmod(full, 0o755 if executable else 0o644)
    # Prune directories left empty by removals.
    for folder, dirs, files in os.walk(methods_root, topdown=False):
        if folder == methods_root:
            continue
        if not dirs and not files:
            try:
                os.rmdir(folder)
            except OSError:
                pass


def read_previous_commit(methods_root: str) -> str:
    path = os.path.join(methods_root, "UPSTREAM.json")
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return ""
    return str(data.get("commit", ""))


def parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=None,
                        help="existing checkout of the upstream repository")
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL,
                        help="upstream repository URL, used when --source is not given")
    parser.add_argument("--ref", default=DEFAULT_REF,
                        help="branch or tag to clone, used when --source is not given")
    parser.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."),
                        help="root of this plugin repository (methods/ lives directly under it)")
    parser.add_argument("--check", action="store_true",
                        help="write nothing; exit 0 if methods/ already matches the source, 1 if it differs")
    return parser.parse_args(argv)


def run(args: argparse.Namespace, stdout, stderr) -> int:
    root = os.path.abspath(args.root)
    methods_root = os.path.join(root, "methods")

    tmp_clone = None
    try:
        if args.source:
            source_root = os.path.abspath(args.source)
            if not os.path.isdir(source_root):
                raise SourceError("--source %s does not exist" % args.source)
        else:
            tmp_clone = tempfile.mkdtemp(prefix="sync-methods-")
            clone_shallow(args.repo_url, args.ref, tmp_clone)
            source_root = tmp_clone

        content_tree, errors, methods_info = build_content_tree(source_root)

        if errors:
            for message in errors:
                stderr.write("error  %s\n" % message)
            payload = {
                "ok": False,
                "from_commit": read_previous_commit(methods_root),
                "to_commit": "",
                "changed": [],
                "added": [],
                "removed": [],
                "methods": sorted(METHODS),
                "errors": errors,
            }
            stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            return 1

        from_commit = read_previous_commit(methods_root)
        to_commit, to_date = source_commit_info(source_root)
        old_tree = collect_existing_tree(methods_root)
        old_content = {k: v for k, v in old_tree.items() if k != "UPSTREAM.json"}

        if old_content == content_tree:
            # Nothing this tool tracks changed, even though the upstream
            # HEAD moved: leave UPSTREAM.json untouched so a commit that
            # never touched our eleven directories produces no PR.
            new_tree = old_tree
            changed, added, removed = [], [], []
            effective_to_commit = from_commit
        else:
            upstream_bytes = build_upstream_json(args.repo_url, to_commit, to_date, methods_info)
            new_tree = dict(content_tree)
            new_tree["UPSTREAM.json"] = (upstream_bytes, False)
            changed, added, removed = diff_trees(old_tree, new_tree)
            effective_to_commit = to_commit

        if args.check:
            ok = not (changed or added or removed)
            if not ok:
                for path in changed:
                    stderr.write("changed  methods/%s\n" % path)
                for path in added:
                    stderr.write("added    methods/%s\n" % path)
                for path in removed:
                    stderr.write("removed  methods/%s\n" % path)
            payload = {
                "ok": ok,
                "from_commit": from_commit,
                "to_commit": effective_to_commit,
                "changed": changed,
                "added": added,
                "removed": removed,
                "methods": sorted(METHODS),
                "errors": [],
            }
            stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            return 0 if ok else 1

        if changed or added or removed:
            os.makedirs(methods_root, exist_ok=True)
            apply_tree(methods_root, new_tree, removed)

        stderr.write(
            "synced methods/ from %s (%s..%s): %d changed, %d added, %d removed\n"
            % (args.repo_url, from_commit[:12] or "(none)", effective_to_commit[:12],
               len(changed), len(added), len(removed))
        )
        payload = {
            "ok": True,
            "from_commit": from_commit,
            "to_commit": effective_to_commit,
            "changed": changed,
            "added": added,
            "removed": removed,
            "methods": sorted(METHODS),
            "errors": [],
        }
        stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0
    except SourceError as exc:
        stderr.write("error  %s\n" % exc)
        stdout.write(json.dumps({
            "ok": False, "from_commit": "", "to_commit": "", "changed": [],
            "added": [], "removed": [], "methods": sorted(METHODS), "errors": [str(exc)],
        }, indent=2, sort_keys=True) + "\n")
        return 2
    finally:
        if tmp_clone is not None:
            shutil.rmtree(tmp_clone, ignore_errors=True)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    return run(args, sys.stdout, sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
