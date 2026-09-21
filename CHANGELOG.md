# Changelog

All notable changes to this plugin. Versions follow semantic versioning; the
template markers (`sdlc:template <name> <version>`) version the files the plugin
writes into target repositories, independently of the plugin version.

## [0.1.0] - 2026-09-21

First version of the loop.

### Added

- `/sdlc` — a stateless orchestrator: reads the repository, takes the next
  action, writes the result back. Ten phases loaded on demand: init, intention,
  admission, inbox, plan-epic, spec, tickets, execute, deliver, close-epic.
- Ten subagents with a fixed model per role: haiku explores, sonnet builds,
  merges, fixes and plays walkthroughs, opus writes specs and reviews.
- Mechanical checks: `sdlc-state`, `sdlc-check-tickets`, `sdlc-check-harness`,
  `sdlc-test-guard`, `sdlc-merge-gate`, `sdlc-lock`.
- Templates, all at marker version 1, for every file the loop writes into a
  target repository, including per-stack coding standards for TypeScript/Next.js,
  Java/Spring Boot and Go.
- Hooks: a session-start summary of the inbox, and a guard that refuses
  out-of-bounds commands in repositories run by the loop.
