---
id: design-system
title: Commit the visual world and its guardrails
status: ready-for-agent
depends_on: []
labels: [enabler, frontend]
stories: []
---

<!-- sdlc:template ticket 1 -->

## Context

The first frontend ticket of a project, always — no UI is written before
the direction is committed. Every other frontend ticket depends on this one,
so the blocking graph makes the anchor real rather than a convention.
Implements the spec's `## Design direction`: the direction itself is a taste
decision the human took when answering the spec's open question; committing it
is this ticket. See `docs/agents/frontend.md`.

## Acceptance criteria

- [ ] `PRODUCT.md` records durable product context (`impeccable init`)
- [ ] `DESIGN.md` and its sidecar commit the visual world (`impeccable
      new-work`)
- [ ] A surface brief exists for each surface, naming its mode (Persuade /
      Operate / Read / Experience)
- [ ] The design detector hook is on (`/impeccable hooks on`)
- [ ] A golden baseline is committed for each surface × theme × breakpoint
- [ ] Fonts are self-hosted — the nearest installed font is a failure, not a
      fallback

## Tests

`impeccable audit` passes. The golden baseline renders identically on a
second run.

## Regression

N/A — nothing shipped yet.

## Observability

N/A — no runtime behaviour.
