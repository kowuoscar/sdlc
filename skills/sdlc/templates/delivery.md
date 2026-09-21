# Delivery report — <feature-slug>

<!-- sdlc:template delivery 1 -->

Prose, not machine-read — `findings.json` and `acceptance.json` carry the
data this report narrates. Filed once, at delivery, alongside the inbox item
of type `acceptance` that points here.

## What was built

Story by story (from `spec.md`'s `## User stories`): what shipped, and the
ticket(s) that carried it. One paragraph or a few lines per story — the
`git log` for this feature has the detail; this is the summary a human reads
once.

## Acceptance walkthrough

The spec's `## Acceptance walkthrough`, replayed, one line per step:

1. <step, copied from the spec> — played — evidence: `<path>`
2. <step, copied from the spec> — yours

An `[agent]` step is marked `played — evidence: <path>` (the path exists,
relative to this feature's directory) or `failed`. A `[human]` step is
marked `yours` — the human plays it and records the result through the
`acceptance` inbox item, not by editing this file.

## Decisions taken alone

Copied from the spec's `## Decisions taken`, plus any made during
implementation or review — those are flagged `(after review)`. The human may
veto any entry; a veto reopens it as a new open question on the next spec.

## Debt recorded

Entries this feature added to `docs/tech-debt.md`, one line each: module,
smell, note. `None` when this feature left no debt.

## How to undo

The exact command to revert this feature's merge commit:

```
git revert -m 1 <merge-commit-sha>
```

Reverts code, not data — a migration with no safe rollback was already
flagged as an open question at spec time, not discovered here.

## What happens next

The next feature or epic the orchestrator moves to while this delivery
awaits the human's walkthrough, and what changes if the human vetoes a
decision above.
