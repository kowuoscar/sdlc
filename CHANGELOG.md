# Changelog

All notable changes to this plugin. Versions follow semantic versioning; the
template markers (`sdlc:template <name> <version>`) version the files the plugin
writes into target repositories, independently of the plugin version.

## [Unreleased]

### Added

- `site/`: a presentation of the loop — the inversion, the one rule, an
  interactive walk through one feature, every station, the human's side, the
  mechanical guarantees, the methods and the models. Static, no third-party
  request, fonts self-hosted. `tests/test_site.py` keeps it true to the plugin;
  `pages.yml` deploys it once the repository variable `PAGES_ENABLED` is set.

## [0.2.0] - 2026-09-21

### Changed

- Methods are now **bundled**: `methods/` holds verbatim copies of eleven of
  Matt Pocock's skills (MIT), read by agents as files. The agents' paraphrases
  and "skill missing" fallbacks are gone; phases and agents name the method
  file they follow and what replaces each of its human gates.
- The `interview`, `domain`, `tdd` and `debugging` slots default to `bundled`;
  a skill name still overrides. `design` stays an installed dependency
  (`impeccable`), checked at init.

### Added

- `tools/sync_methods.py` and a weekly workflow that syncs `methods/` with
  upstream through a pull request carrying the diff and the check results.
- `methods/gates.json` and `tools/check_method_gates.py`: a registry of every
  human gate in the methods and what replaces it; an unregistered gate fails
  the tests.

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
