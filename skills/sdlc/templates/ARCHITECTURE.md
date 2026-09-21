# Architecture

<!-- sdlc:template architecture 1 -->

This file **points**; it never **describes**. A route, a schema, a function
signature is read in the code, never copied here — a copy goes stale, a
pointer does not. It changes in the same merge as the code it maps: an
implementer who moves or adds a module updates this file in that ticket, or
declares the change for the merger to apply. Every path cited here is checked
mechanically by `sdlc-check-harness`; a path that stops existing is a build
error, not a nitpick.

## Modules

One line per top-level directory under each of `module_roots`
(`docs/agents/sdlc.json`): path in backticks, then its single responsibility.

- `<src/module>` · <its one responsibility, one sentence>
- `<src/other-module>` · <its one responsibility, one sentence>

## Dependency direction

<Which module may import which. State the rule, not every edge — e.g. "web
depends on domain, domain depends on nothing" or "handlers → services →
repositories, never the reverse".>

## Entry points

<Where execution starts: main functions, HTTP routers, CLI commands, queue
consumers — path in backticks, one line each.>

## Tests

<Where tests live relative to the code they cover, and the seams they run at
(unit, integration, end-to-end). Point at the directory or naming convention,
not at an example test.>

## Invariants

<A short list of properties that must stay true across any change — e.g.
"all writes go through the repository layer", "no HTTP call outside
services/". Each one is a fact a reviewer can check, not a preference.>
