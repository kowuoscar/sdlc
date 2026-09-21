---
feature: <feature-slug>
epic: <epic-slug>
status: draft
date: <YYYY-MM-DD>
---

<!-- sdlc:template spec 1 -->

# <Feature name>

## Problem

The problem being solved, and for whom. From the user's perspective. No
solution here.

## Journeys

Which epic this advances (from `docs/roadmap/<epic>.md`) and which journeys
(from `docs/journeys.md`) it moves toward `exists`. Empty `epic` in the
frontmatter is only for a change admitted outside any epic — say so here.

## Goals / Non-goals

What the feature does. And explicitly what it does NOT do — the guardrail
against scope drift, so be specific rather than exhaustive.

## User stories

A numbered list covering every aspect of the feature; the number is the
story id, cited elsewhere in this spec and in tickets.

1. As a <actor>, I want <capability>, so that <benefit>

## Solution

The chosen approach and why it beat the alternatives that were rejected.
Include implementation decisions: modules built or modified, their
interfaces, schema changes, API contracts, specific interactions.

No file paths, no code snippets — they go stale fast. Exception: a snippet
that encodes a decision more precisely than prose can (state machine,
reducer, schema, type shape). Keep only the decision-rich part.

## Design direction

UI features only — write `N/A — no user interface` otherwise.

The committed visual world, and the references it was pinned against. One
line per surface naming its mode: Persuade (the visitor decides and acts),
Operate (the visitor completes a task), Read (the visitor understands), or
Experience (the visitor is inside the work). The mode comes from the
surface, not the product. See `docs/agents/frontend.md`.

## Constraints

Technical, performance, security and compatibility constraints, with exact
values. This section is authoritative: tickets inherit it and must not
restate or redefine it.

## Testing decisions

The seams at which this feature is tested. Prefer existing seams to new
ones, and place them as high as possible — the fewer seams across the
codebase, the better. Name the prior art: similar tests already in the repo.

Tests assert external behaviour, never implementation details.

## Decisions taken

Decisions made alone because they are about HOW, not WHAT, and easy to
undo — one line each, with the reason. The human may veto any entry after
the fact; a veto reopens it as an open question. An entry added once review
has started is flagged `(after review)` so a re-reader knows it was not part
of the original plan.

- <decision> — <reason> [(after review)]

## Open questions

Only questions about WHAT the user sees, or about an irreversible choice.
Each entry carries a recommendation — the human answers or accepts it. If
you cannot write how the human will check the answer, keep asking rather
than guessing.

Leave the section present and write `None` when empty.

## Acceptance walkthrough

The manual script that proves this feature works, written now — if it
cannot be written at spec time, the spec is not clear enough yet. Replayed
at delivery, with proof, as the delivery report.

Numbered steps, each starting with `[agent]` or `[human]` (who plays it) and
ending with `(stories: <n>, <n>)`:

1. [agent] <observable action and expected result> (stories: 1)
2. [human] <observable action and expected result> (stories: 2, 3)

## Execution order

Tickets in dependency order, blockers first:

1. `<ticket-slug>` — one line on what it delivers
2. `<ticket-slug>`
