# Issue tracker

<!-- sdlc:template agents-issue-tracker 1 -->

**Tracker type:** local markdown, custom layout.

This file overrides the default output shape of any spec-writing or
ticket-writing skill. Draft a spec or a ticket in the layout below instead
of that skill's built-in default; follow the skill's method, not its format.

## Layout

```
docs/features/<feature-slug>/
  spec.md
  tickets/
    <ticket-slug>.md
  findings.json
  acceptance.json
  delivery.md
```

- `<feature-slug>` and `<ticket-slug>` are kebab-case and descriptive
  (`password-reset`, not `03`). Never prefix a filename with a number — it
  goes stale the moment a ticket is inserted, and renaming loses git
  history.
- A ticket's `id` always equals its filename without the extension.
- Execution order lives in `spec.md` under `## Execution order`. Dependencies
  live in each ticket's `depends_on`. The two must agree.

## spec.md shape

```markdown
---
feature: <feature-slug>
epic: <epic-slug>
status: draft
date: YYYY-MM-DD
---

## Problem
## Journeys
## Goals / Non-goals
## User stories
## Solution
## Design direction
## Constraints
## Testing decisions
## Decisions taken
## Open questions
## Acceptance walkthrough
## Execution order
```

`status`: `draft`, `approved`, `delivered`, `accepted`, `dropped`. `epic` may
be empty for a change admitted outside any epic. `## User stories` is a
numbered list — the number is the story id, cited by tickets and by the
walkthrough. `## Acceptance walkthrough` is numbered, every step starting
with `[agent]` or `[human]` and ending with `(stories: 1, 3)`. Full section
guidance lives in the file itself — see `templates/spec.md` in the plugin.

## ticket.md shape

```markdown
---
id: <ticket-slug>
title: <one line, imperative, in domain vocabulary>
status: needs-triage
depends_on: [<ticket-slug>]
labels: [<area>]
stories: [<n>]
---

## Context
## Acceptance criteria
## Tests
## Regression
## Observability
```

`stories` lists the spec story numbers this ticket carries. Leave it empty
only when `labels` contains `enabler` (foundation, design system,
prefactoring) — an enabler earns its place by unblocking stories, not by
carrying one.

## Conditional sections

`## Regression`, `## Observability` (tickets) and `## Open questions`
(spec) are **always present**. When one does not apply, write
`N/A — <reason>` — an absent section cannot be told apart from a forgotten
one; one line proves the question was asked.

## Status lifecycle

`status` is the only record of where a ticket stands; write it as the work
moves, never reconstruct it afterwards.

| Value | Set when |
|---|---|
| `needs-triage` | Ticket drafted, not yet assessed |
| `needs-info` | Blocked on an answer — name what is missing in `## Context` |
| `ready-for-agent` | Unambiguous enough to implement without further input |
| `ready-for-human` | Needs a person: judgement call, credentials, external action |
| `in-progress` | An implementer picked it up — set it **before** the first edit |
| `done` | Definition of Done met and the work is merged |
| `wontfix` | Dropped — say why in `## Context` |

The **frontier** is every `ready-for-agent` ticket whose `depends_on`
tickets are all `done`. Commits reference the ticket id:
`<type>(<ticket-id>): <subject>`.

## Definition of Done

Global, never restated inside a ticket:

- Every acceptance criterion is checked.
- Tests listed in the ticket exist and pass.
- The full test suite passes — not only the new tests.
- Lint and type checks pass.
- Observability described in the ticket is in place, or justified as `N/A`.
- A harness change (a module added, moved or renamed; a domain term
  introduced, renamed or narrowed) is **declared** in the implementer's
  result, never edited by the implementer directly — the merger applies it
  to `ARCHITECTURE.md` / `CONTEXT.md` in the merge commit. One writer keeps
  concurrent tickets from producing conflicting harness edits.
- An ADR is recorded **only** if a decision is hard to reverse, surprising
  without context, and the result of a genuine trade-off. All three, or no
  ADR.
- `stories` in the frontmatter is filled with every story number this
  ticket carries (empty only for a ticket labelled `enabler`).
- Changes are committed referencing the ticket id, and `status` is `done`.

A ticket labelled `frontend` additionally satisfies the frontend DoD in
`docs/agents/frontend.md`.

## Rules

1. **No tickets while a spec's `## Open questions` is non-empty.** A ticket
   built on an unvalidated assumption gets implemented, then thrown away.
2. **The spec is authoritative on constraints.** A ticket that needs a
   constraint cites the spec; it never redefines one.
3. **Tickets are vertical slices**, each a narrow but complete path through
   every layer, demoable on its own. See `docs/agents/ticket-critic.md` for
   what makes a slice healthy.
4. **One ticket fits one fresh context window.** An implementer that finds a
   ticket too big returns a proposed split instead of forcing it through.
5. **`status` uses the triage vocabulary above**, so it maps onto
   Linear/Jira states without translation.
6. **The domain model is maintained inline, not in batches.** When a term is
   challenged or resolved while writing a spec, a ticket or code, the
   implementer declares the change in its result at that moment — it does
   not edit `CONTEXT.md` itself. Create `CONTEXT.md` and `docs/adr/` lazily,
   only when there is something to write.
7. **Every visual change either conforms to `DESIGN.md`, or changes
   `DESIGN.md` in the same commit.** Read `docs/agents/frontend.md` before
   any UI work.
8. **Frontmatter is the migration contract.** Keep `id`, `title`, `status`,
   `depends_on`, `labels` and `stories` machine-readable: no prose, no free
   text in those fields.
