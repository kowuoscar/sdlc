# methods/

Vendored copies of a fixed set of engineering methods from Matt Pocock's
public repository, [mattpocock/skills](https://github.com/mattpocock/skills)
(MIT licence, copyright Matt Pocock — see `LICENSE` in this directory).

These are **reference files, not skills**: they live here, deliberately
outside `skills/`, so Claude Code never registers them for autonomous
invocation. Agents read them by path (see `docs/contracts.md` section 3 and
the `skills` slots in `docs/agents/sdlc.json`) exactly like any other file in
the target repository.

Nothing under this directory is edited by hand, except `gates.json` and this
`README.md`. Everything else — every method folder and `UPSTREAM.json` — is
overwritten wholesale by `tools/sync_methods.py`, run weekly by
`.github/workflows/sync-methods.yml` against upstream, and by nobody else.
Do not hand-edit a method file: the next sync will silently discard the edit.

`UPSTREAM.json` records exactly which upstream commit these files were
mirrored from, and the file list and checksum of each method.

`gates.json` is the one hand-maintained registry in this directory. The
upstream methods assume a human is present ("confirm them with the user",
"Quiz the user", "ask the user", …); this plugin runs unattended and
replaces each of those human gates with something else. `gates.json` records
every such line and what replaces it, so that `tools/check_method_gates.py`
can fail loudly the moment an upstream sync introduces a human gate nobody
has accounted for yet, instead of silently shipping a prompt that stalls or
misleads an unattended agent.

## The review workflow (`gates.json`'s `"reviewed"` map)

A regex can never catch every way a phrase might be worded, so it is only an
aid; the hard guarantee is `gates.json`'s `"reviewed"` object, one sha256 per
tracked method, copied from that method's `sha256` in `UPSTREAM.json` at the
moment a person actually read its diff. `tools/check_method_gates.py` fails
with `method-unreviewed` whenever a tracked method's current `UPSTREAM.json`
hash does not match its `reviewed` entry (or has none) — which means **every**
sync that changes a followed method fails the check, regardless of whether
the regex layer flagged anything, until a person reads the diff.

After a sync (typically via the `sync-methods` pull request):

1. For each method `check_method_gates.py` reports as `method-unreviewed`,
   read the diff between the old and new `methods/<name>/` (the pull request
   body links the upstream compare view).
2. If the diff adds, changes or drops a human-gate line, update `gates.json`
   accordingly — a new `gates` entry, an edited `replaced_by`, or a removed
   stale entry — and update whatever phase or agent file implements that
   replacement.
3. Once satisfied, run `python3 tools/check_method_gates.py --accept <name>`
   for that method (or `--accept-all` once every reported method has been
   read) to record its current hash as reviewed. This only ever edits
   `gates.json`'s `"reviewed"` map — nothing else in this directory.
4. Re-run `python3 tools/check_method_gates.py`; it now passes for that
   method.

A red `check_method_gates.py` on a fresh sync pull request is the normal,
expected state, not a bug: it is the review gate doing its job.
