---
id: foundation
title: Stand up the verify command and the architecture map
status: ready-for-agent
depends_on: []
labels: [enabler]
stories: []
---

<!-- sdlc:template ticket 1 -->

## Context

The very first ticket of an empty project. Nothing else can be trusted green
until one command proves it, so every later ticket depends on this one
transitively through `docs/agents/sdlc.json`.

## Acceptance criteria

- [ ] A single command runs tests, lint and type checks, and exits 0 on a
      clean checkout
- [ ] That command is recorded as `verify` in `docs/agents/sdlc.json`,
      replacing the placeholder
- [ ] `ARCHITECTURE.md` exists at the repo root, naming every directory
      under each `module_roots` entry with its single responsibility
- [ ] `sdlc-check-harness` passes
- [ ] The `verify` command has run green at least once and its output is
      referenced in the commit

## Tests

N/A — this ticket builds the tooling other tickets are tested with, not
product behaviour.

## Regression

N/A — nothing shipped yet.

## Observability

N/A — no runtime behaviour yet.
