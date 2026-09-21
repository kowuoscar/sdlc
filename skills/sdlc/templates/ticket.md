---
id: <ticket-slug>
title: <one line, imperative, in domain vocabulary>
status: needs-triage
depends_on: [<ticket-slug>]
labels: [<area>]
stories: [<n>]
---

<!-- sdlc:template ticket 1 -->

## Context

Why this ticket exists, in 1-3 sentences. Point at the section of `spec.md`
it implements rather than restating it.

## Acceptance criteria

- [ ] Observable behaviour, never implementation

## Tests

The cases to cover: happy path, boundaries, errors. Written BEFORE the code.
Name the seam from the spec's `## Testing decisions`.

## Regression

What already-shipped behaviour this ticket puts at risk, and which test
protects it. For a bugfix: the test reproducing the bug is written first and
must fail. `N/A — <reason>` when nothing is at risk.

## Observability

Logs, metrics and traces to add. `N/A — <reason>` when none apply.
