# Data contracts

The loop is stateless; the target repository is the state. This file is the
single definition of every machine-read file the plugin writes into a target
repository, and of the scripts that read them. Templates, agent prompts and
scripts must all agree with it. When they disagree, this file wins and the
other is a bug.

All paths below are relative to the root of the **target repository** (the
project being built), not of this plugin.

## 1. Frontmatter dialect

Markdown files carry a frontmatter block delimited by `---` lines at the very
top. Only this subset of YAML is allowed, so that it parses without a YAML
library and maps onto tracker fields without parsing prose:

- `key: scalar` — string, integer, `true`/`false`. Quotes optional; surrounding
  single or double quotes are stripped.
- `key: [a, b, c]` — inline list of scalars. `[]` is the empty list.
- `key:` with nothing after the colon is the empty string — agents write it
  that way, and a loop that halts on it helps nobody.
- No nesting, no multi-line values, no block lists, no comments. Blank lines
  inside the block are tolerated. A duplicate key is malformed.

Keys are lower-case `snake_case`. Unknown keys are preserved and ignored.

## 2. Layout

```
docs/agents/sdlc.json                  config (section 3)
docs/agents/README.md                  index of docs/agents/
docs/agents/*.md                       rule files
docs/journeys.md                       journeys and their state (section 4)
docs/roadmap/README.md                 ordered list of epics (section 5)
docs/roadmap/<epic>.md                 one epic (section 5)
docs/features/<feature>/spec.md        one feature spec (section 6)
docs/features/<feature>/tickets/<ticket>.md     (section 7)
docs/features/<feature>/findings.json  review findings (section 8)
docs/features/<feature>/acceptance.json  walkthrough results (section 9)
docs/features/<feature>/delivery.md    delivery report (prose, not machine-read)
docs/inbox/<item>.md                   one inbox item (section 10)
docs/tech-debt.md                      debt entries (section 11)
.sdlc/lock                             session lock, git-ignored (section 12)
```

`<epic>`, `<feature>`, `<ticket>` and `<item>` are kebab-case slugs matching
`^[a-z0-9]+(-[a-z0-9]+)*$` and starting with a letter. Never numeric prefixes. A file's `id` always equals
its filename without the extension.

## 3. Config — `docs/agents/sdlc.json`

```json
{
  "schema": 1,
  "verify": "npm run verify",
  "spec_gate": "always",
  "merge": "auto",
  "max_implementers": 3,
  "ticket_budget_turns": 60,
  "session_budget_features": 3,
  "max_pending_acceptance": 3,
  "debt_threshold_per_module": 5,
  "map_max_lines": 120,
  "module_roots": ["src"],
  "test_globs": ["**/*.test.*", "**/*.spec.*", "**/*_test.go", "**/src/test/**", "**/test_*.py", "**/*_test.py", "**/tests/**", "**/__tests__/**", "**/*Test.java", "**/*Tests.java", "**/*IT.java", "**/*_spec.rb", "**/*Tests.cs"],
  "main_branch": "main",
  "pull_requests": false,
  "forbidden_commands": [],
  "skills": {
    "interview": "bundled",
    "domain": "bundled",
    "tdd": "bundled",
    "debugging": "bundled",
    "design": "impeccable"
  }
}
```

| Key | Values | Meaning |
|---|---|---|
| `schema` | integer | Contract version. Scripts refuse a higher schema than they know. |
| `verify` | shell command | The single command that proves the repo is green: tests, lint, types. Exit 0 means green. The harness check is not part of it — the target repo's CI does not have this plugin — it is run by the merger and by the merge gate. |
| `spec_gate` | `always` \| `questions-only` | Whether every spec waits for approval, or only specs with open questions. |
| `merge` | `auto` \| `human` | Whether the orchestrator merges a delivered feature into `main_branch` itself. |
| `max_implementers` | integer ≥ 1 | Concurrent implementer subagents. |
| `ticket_budget_turns` | integer ≥ 1 | Soft turn budget told to one implementer; beyond it the implementer returns `failed`. The hard cap is `maxTurns` in `agents/implementer.md`. |
| `session_budget_features` | integer ≥ 1 | Features one session may deliver before it stops and reports. |
| `max_pending_acceptance` | integer ≥ 0 | The loop pauses once this many features are delivered and not yet accepted. `0` disables the cap. |
| `debt_threshold_per_module` | integer ≥ 1 | Debt entries on one module beyond which a refactoring epic is proposed. |
| `map_max_lines` | integer | Maximum length of the root agent map (`CLAUDE.md` or `AGENTS.md`). |
| `module_roots` | list of dirs | Every immediate subdirectory of each root must be named in `ARCHITECTURE.md`. Empty list disables the check. |
| `test_globs` | list of globs | What counts as a test file for the test guard. |
| `main_branch` | branch name | Integration branch. |
| `pull_requests` | `true` \| `false` | `true`: feature branches are pushed to `origin`, a draft pull request is opened, and delivery merges it with `gh`. `false`: everything stays local and delivery is a local `--no-ff` merge. |
| `forbidden_commands` | list of regular expressions | Bash commands the plugin's guard hook refuses in this repository, on top of its built-ins (force-push, history rewriting, deleting the main branch). For deploy and publish commands. |
| `skills` | object, slot → `bundled` or a skill name | Method slots. `bundled` means the copy of the upstream method shipped in the plugin's `methods/` directory, which the agent reads as a file. Any other value names an installed skill the agent loads with the Skill tool instead. An empty string disables a slot. `design` has no bundled copy: it names an installed skill or plugin (`impeccable` by default), required for projects with a user interface and only used on tickets labelled `frontend`. |

Missing keys take the defaults shown above, except `verify`, which is required.
Unknown keys are preserved and ignored. `skills` merges slot by slot: a config
naming one slot keeps the defaults of the others.

### Template markers

Every file instantiated from a template carries, on its own line,
`<!-- sdlc:template <name> <version> -->` (in JSON files: the key
`"template": "<name> <version>"`). `<version>` is an integer bumped when the
template's machine-read shape or rules change. `state.py` reports, under
`"outdated_templates"`, every marker older than the plugin's template of the
same name; the orchestrator turns that into one `proposal` inbox item.

## 4. Journeys — `docs/journeys.md`

One level-3 heading per journey, the state after an em dash or a plain hyphen:

```markdown
### Book a slot — exists
### Cancel a booking — partial
### Pay online — wanted
```

States: `exists`, `partial`, `wanted`. The journey slug is the kebab-case of its
title (`book-a-slot`). Prose under the heading is free.

## 5. Roadmap

`docs/roadmap/README.md` holds the epic order as a numbered list whose items
start with the epic slug in backticks:

```markdown
1. `online-payment` — take card payments end to end
2. `client-cancellation`
```

`docs/roadmap/<epic>.md`:

```markdown
---
id: online-payment
title: Pay online
status: planned
journeys: [pay-online]
---

## Intent
## Features

- [ ] `card-checkout` — pay a booking by card
- [x] `email-receipt` — receive a receipt
- [ ] ~`refunds`~ — dropped: out of scope for now

## Later
```

Epic `status`: `proposed` (awaiting the human), `planned`, `in-progress`,
`done`, `dropped`. Only `planned` and `in-progress` epics are worked on.

A feature line is `- [ ] \`slug\`` (not delivered), `- [x] \`slug\`` (delivered)
or wrapped in `~…~` (dropped). An epic with no feature line has not been planned
yet. Features are worked in list order. A line whose slug is not a valid slug
(a template placeholder) is ignored. Parsing is otherwise tolerant: any list
line with a checkbox and a backticked valid slug is a feature line, whatever
punctuation or emphasis surrounds it (`[X]` counts as ticked) — a line dropped
silently would let an epic close with work outstanding.

Only the frontmatter and `## Features` are machine-read; `## Intent`,
`## Journeys`, `## Reworked` and `## Later` are prose (see `templates/epic.md`).

## 6. Spec — `docs/features/<feature>/spec.md`

Frontmatter:

```yaml
feature: card-checkout
epic: online-payment
status: draft
date: 2026-01-31
```

`status`: `draft`, `approved`, `delivered`, `accepted`, `dropped`.
`epic` may be empty for a change admitted outside any epic.

Machine-read sections (level-2 headings, exact text):

- `## User stories` — a numbered list; the number is the story id.
- `## Open questions` — the literal `None` when empty.
- `## Acceptance walkthrough` — a numbered list; every step ends with
  `(stories: 1, 3)` and starts with `[agent]` or `[human]`, naming who can play it.
- `## Execution order` — a numbered list whose items start with a ticket slug in
  backticks.

Other sections are prose (see `templates/spec.md`).

## 7. Ticket — `docs/features/<feature>/tickets/<ticket>.md`

Frontmatter:

```yaml
id: charge-card
title: Charge a card for a booking
status: ready-for-agent
depends_on: [payment-schema]
labels: [backend]
stories: [1, 2]
```

`status`: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`,
`in-progress`, `done`, `wontfix`.

`stories` lists the spec story numbers the ticket carries. It may be empty only
when `labels` contains `enabler` (foundation, design system, prefactoring).

Required level-2 sections, each non-empty (`N/A — <reason>` is non-empty):
`## Context`, `## Acceptance criteria`, `## Tests`, `## Regression`,
`## Observability`.

The **frontier** is every ticket with status `ready-for-agent` whose
`depends_on` tickets are all `done`.

## 8. Findings — `docs/features/<feature>/findings.json`

```json
{
  "schema": 1,
  "feature": "card-checkout",
  "base": "main",
  "findings": [
    {
      "id": "F1",
      "type": "spec-partial",
      "citation": "spec.md ## User stories — 3. As a client, I want a receipt…",
      "where": "src/payments/receipt.ts:40",
      "note": "No receipt is sent when the charge is retried.",
      "state": "open",
      "raised_by": "reviewer-spec",
      "after_review": false,
      "in_changed_lines": true
    }
  ]
}
```

| `type` | Blocks merge |
|---|---|
| `spec-missing` | yes |
| `spec-partial` | yes |
| `spec-wrong` | yes |
| `out-of-scope` | yes |
| `rule-violated` | yes |
| `acceptance-failed` | yes |
| `design-guideline` | yes |
| `smell` | no |

`in_changed_lines` is carried on `smell` findings only: a smell sitting in
lines the feature changed is fixed, any other becomes debt. Unknown keys on a
finding are preserved and ignored.

**No citation, no block.** `citation` is a string; any other JSON type makes
the finding malformed (an error, never a downgrade). A blocking type whose
`citation` is empty or whitespace is *downgraded*: it counts as a `smell`. The gate reports every
downgrade.

`state`: `open` → `fixed` (set by the fixer) → `confirmed` (set by a reviewer
only). A reviewer may also set `dismissed`, with the reason appended to `note`.
A finding blocks while its state is `open` or `fixed`.

## 9. Acceptance — `docs/features/<feature>/acceptance.json`

```json
{
  "schema": 1,
  "feature": "card-checkout",
  "steps": [
    {"step": 1, "actor": "agent", "status": "passed", "evidence": "evidence/step-1.txt"},
    {"step": 2, "actor": "human", "status": "pending", "evidence": ""}
  ]
}
```

`actor`: `agent`, `human`. `status`: `passed`, `failed`, `pending`. Every
walkthrough step of the spec has exactly one entry. A `passed` agent step must
name an `evidence` file **inside the feature directory**: a relative path with
no `..` segment that, once symlinks are resolved, is still under it. Anything
else is an error — evidence that can point anywhere proves nothing.

## 10. Inbox — `docs/inbox/<item>.md`

```yaml
id: refund-partial-amounts
type: question
status: open
blocks: [refunds]
created: 2026-01-31
```

`type`: `alert`, `question`, `approval`, `acceptance`, `proposal` — also the
display order. `status`: `open`, `answered`, `closed`. `blocks` lists feature or
epic slugs that cannot advance while the item is `open`.

Body sections: `## Question`, `## Recommendation`, `## Blocks`,
`## Meanwhile`, `## Answer`. An item is `answered` once `## Answer` is non-empty
and its status says so; the orchestrator then applies it and sets `closed`.

## 11. Debt — `docs/tech-debt.md`

One level-2 heading per module path, one list line per entry:

```markdown
## src/payments

- `src/payments/receipt.ts` · smell: Duplicated Code · retry and first-charge paths format the receipt twice · card-checkout · 2026-01-31
```

Fields are separated by ` · `: path in backticks, `smell: <name>`, note,
origin feature, date. An entry whose path no longer exists is stale: reported,
and left out of the per-module threshold count.

## 12. Lock — `.sdlc/lock`

JSON: `{"session": "<token>", "started": "<ISO-8601 UTC>", "refreshed": "<ISO-8601 UTC>"}`.

The processes that take the lock are short-lived shell calls, so a pid proves
nothing; the lock is a lease. It is **held** while `refreshed` is less than two
hours old. `acquire` by the holding session (same non-empty `session` token)
refreshes the lease — the orchestrator does so on every turn of the loop.
`acquire` by anyone else fails while the lease is held, unless `--force`. An
empty token never matches, so two anonymous sessions exclude each other.
`release` succeeds for the holder, or with `--force`. `.sdlc/` is git-ignored.

## 13. Scripts

All scripts live in `scripts/`, are Python 3.9+ with the standard library only,
and share `scripts/sdlc_lib/`. Each has a thin executable wrapper in `bin/`
(`sdlc-state`, `sdlc-check-tickets`, `sdlc-check-harness`, `sdlc-test-guard`,
`sdlc-merge-gate`, `sdlc-lock`); Claude Code puts a plugin's `bin/` on `PATH`,
so agents call them by name. They
take the target repository as `--repo` (default: current directory), print one
JSON document on stdout, human-readable diagnostics on stderr, and exit `0`
(ok), `1` (check failed) or `2` (malformed input or usage error).

Every JSON result has `"ok": true|false`, `"errors": [...]` and
`"warnings": [...]`, each entry `{"code": "...", "path": "...", "message": "..."}`.

### `state.py`

Derives the project state and the single next action. Never writes.

Output adds:

```json
{
  "initialized": true,
  "config": {},
  "inbox": {"open": [{"id": "", "type": "", "blocks": []}], "answered": [{"id": "", "type": "", "blocks": []}]},
  "pending_acceptance": ["feature-slug"],
  "features": [{"feature": "", "epic": "", "status": "", "tickets": {"total": 0, "done": 0}, "frontier": [], "blocked_by": []}],
  "debt": {"over_threshold": ["src/payments"], "stale": ["<entry path>"]},
  "stalled": ["feature-slug"],
  "outdated_templates": [{"path": "", "name": "", "found": 1, "current": 2}],
  "next": {"action": "", "target": "", "reason": ""}
}
```

Inbox items are listed by `type` in the order of section 10, then by `id`.
`stalled` is computed over every feature before the action is chosen, so a
stalled feature is reported even when another feature supplies the action.

`next.action` is decided by the first rule that matches:

1. `init` — `docs/agents/sdlc.json` is missing.
2. `apply-answers` — at least one inbox item is `answered`.
3. `pause` — `max_pending_acceptance` > 0 and that many features are `delivered`.
4. For each feature not `delivered`/`accepted`/`dropped`, in roadmap order
   (features outside any epic first), skipping any feature or epic named in the
   `blocks` of an `open` inbox item:
   - `approved`, has tickets, all `done` or `wontfix`, at least one `done` →
     `deliver`. (Every ticket `wontfix`: stalled — dropping a feature is the
     human's call.)
   - `approved`, has tickets, non-empty frontier or any `in-progress` → `execute`.
   - `approved`, has tickets, otherwise → skip it (stalled; listed in `stalled`).
   - `approved`, no tickets → `ticket`.
   - `draft` → `spec`.
5. For each `planned`/`in-progress` epic in roadmap order, not blocked:
   - no feature line → `plan-epic`.
   - first undelivered, undropped feature line with no `spec.md` → `spec`
     (a feature directory without a spec counts as no spec).
   - every feature line delivered or dropped → `close-epic`.
6. `intention` — `docs/journeys.md` is missing, or no epic exists at all.
7. `wait` — something exists but everything is blocked or stalled.
8. `idle` — nothing left to do.

`target` is the feature or epic slug, empty otherwise.

A spec or an epic whose `status` is outside its vocabulary matches no rule, so
the loop cannot see it. That is never fatal, and never silent: `state.py` warns
with `spec-status-unknown` or `epic-status-unknown`, naming the file and the
statuses that exist.

### `check_tickets.py <feature>`

Mechanical half of the ticket critic. Errors: invalid frontmatter or slug,
`id` ≠ filename, unknown status, missing or empty required section,
`depends_on` naming a missing ticket, self-dependency, cycle, empty `stories`
without the `enabler` label, a story number absent from the spec, a spec story
carried by no ticket, a walkthrough step without `(stories: …)` or without an
actor tag, a walkthrough story number absent from the spec, an
`## Execution order` that lists a ticket before one of its blockers, omits a
ticket, or names a ticket that does not exist. Warnings: more than 7 acceptance criteria in one ticket; a dependency
already implied transitively (it serialises work for nothing).

### `check_harness.py`

Errors: a path cited in backticks in the root map, `ARCHITECTURE.md`,
`docs/agents/README.md` or `docs/tech-debt.md` that does not exist; a file in
`docs/agents/` not named in `docs/agents/README.md`; an immediate subdirectory
of a `module_roots` entry not named in `ARCHITECTURE.md`; a root map longer than
`map_max_lines`. A backticked token counts as a path when it contains `/`, or
ends with a known source or document extension (`md`, `json`, `yml`, `yaml`,
`toml`, `txt`, `sh`, `py`, `js`, `jsx`, `ts`, `tsx`, `go`, `java`, `kt`, `rb`,
`rs`, `cs`, `sql`, `css`, `html`, `xml`, `lock`) — so that `3.9`, `0.1.0` and
`user.save` are not paths — and contains no space, `<`, `>`, `*`, `$`, `~` or
`://`. A trailing `:line` or `:line:col` is stripped first. Warnings: no root
map; `module_roots` empty.

### `test_guard.py <base> [<head>]`

Reports, for the diff `base...head` (head defaults to `HEAD`): existing test
files (matching `test_globs`, present at `base`) that were modified, renamed or
deleted, and skip markers added on `+` lines (`.skip(`, `.only(`, `.todo(`,
`xit(`, `xtest(`, `xdescribe(`, `@Disabled`, `.Disabled`, `@Ignore`,
`enabled = false`, `t.Skip(`, `t.Skipf(`, `t.SkipNow(`, `@pytest.mark.skip`,
`pytest.skip(`, `@unittest.skip`; whitespace around `.` and before `(` is
ignored). `ok` is false when anything is reported; the merger then
requires each reported file to be justified in the ticket's `## Regression`.

### `merge_gate.py <feature> [--no-verify]`

The verdict. `ok` is true only when: `findings.json` and `acceptance.json` are
valid; the spec has a non-empty `## Acceptance walkthrough` (a renamed heading
or a bulleted list must not make acceptance vacuous); no blocking finding is `open` or `fixed`; every spec walkthrough step has
an entry; every `agent` step is `passed` with existing evidence; the harness
check passes; and the config `verify` command exits 0 (skipped with `--no-verify`, which sets
`"verify": "skipped"` in the output). Output — on every path, fatal ones included — adds `"blocking": [ids]`,
`"downgraded": [ids]`, `"harness": "passed|failed"`,
`"verify": "passed|failed|skipped"`.

### `lock.py acquire|release|status [--session <token>] [--force]`

Implements section 12. `acquire` and `release` exit 1 with `lock-held` when
another session holds a fresh lease. `status` prints the lock and whether it is
held, and always exits 0.
