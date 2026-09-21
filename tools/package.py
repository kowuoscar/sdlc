#!/usr/bin/env python3
"""Build the release artefact: dist/sdlc-<version>.zip and dist/SHA256SUMS.

Only what a Claude Code installation needs at runtime is shipped. The archive
is reproducible: sorted entries, fixed timestamps, fixed permissions.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SHIPPED = [".claude-plugin", "skills", "agents", "hooks", "bin", "scripts", "methods",
           "README.md", "CHANGELOG.md", "LICENSE"]
SKIP_DIRS = {"__pycache__"}
FIXED_TIME = (2020, 1, 1, 0, 0, 0)


def shipped_files() -> list:
    out = []
    for entry in SHIPPED:
        full = os.path.join(ROOT, entry)
        if os.path.isfile(full):
            out.append(entry)
        for folder, dirs, files in os.walk(full):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in files:
                if name.endswith(".pyc") or name == ".DS_Store":
                    continue
                out.append(os.path.relpath(os.path.join(folder, name), ROOT))
    return sorted(set(out))


def main() -> int:
    with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
        version = json.load(handle)["version"]
    dist = os.path.join(ROOT, "dist")
    os.makedirs(dist, exist_ok=True)
    archive = os.path.join(dist, "sdlc-%s.zip" % version)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for rel in shipped_files():
            full = os.path.join(ROOT, rel)
            info = zipfile.ZipInfo("sdlc/" + rel.replace(os.sep, "/"), FIXED_TIME)
            executable = os.stat(full).st_mode & stat.S_IXUSR
            info.external_attr = (0o755 if executable else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(full, "rb") as handle:
                bundle.writestr(info, handle.read())
    with open(archive, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    with open(os.path.join(dist, "SHA256SUMS"), "w", encoding="utf-8") as handle:
        handle.write("%s  %s\n" % (digest, os.path.basename(archive)))
    print(json.dumps({"archive": os.path.relpath(archive, ROOT), "sha256": digest,
                      "files": len(shipped_files()), "version": version}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
