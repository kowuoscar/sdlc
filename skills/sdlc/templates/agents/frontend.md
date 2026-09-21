# Frontend playbook

<!-- sdlc:template agents-frontend 1 -->

Read this whenever a feature has UI. It decides **which tool speaks when**,
so the agent never averages several opinionated systems into one incoherent
page.

## The problem this solves

AI-looking design is what an agent produces when **no direction is
committed**: it falls back on the category's defaults — same-size
icon/heading/text cards as page structure, gradient text, decorative glass,
eyebrow kickers, section numbers, sparklines standing in for content,
monospace as a costume, emoji standing in for icons, a system font as the
display voice (see impeccable's `reference/craft-floor.md`).

The fix is not a style checklist. It is a **committed `DESIGN.md` written
before the first line of UI**, plus a hook that checks mechanically on every
edit.

## Drift vs evolution

> **Every visual change either conforms to `DESIGN.md`, or changes
> `DESIGN.md` in the same commit.**

A screenshot golden updated on its own is drift. Updated alongside
`DESIGN.md` it is a decided evolution. The difference is visible in a diff,
so it can be reviewed. This is what keeps the design alive without letting
it wander.

## Who speaks when

| Stage | Tool | Role |
|---|---|---|
| Understand | a reference library of real `DESIGN.md` files, if the project has one configured | The user **points at** a stance instead of describing it — far more reliable than extracting adjectives in conversation |
| Understand | `design-taste-frontend`, if installed | Taste input, **landing pages, portfolios and redesigns only** — its own declared scope. Never during implementation, where its rules would fight the craft floor |
| Direction | `impeccable new-work` | Composes a world of the project's own, informed by what was pinned. Writes `DESIGN.md` |
| Context | `impeccable init` | Writes `PRODUCT.md` — durable product context |
| Build | `impeccable` + `reference/craft-floor.md` | The only system active during implementation |
| Build | design detector hook | Mechanical checks on every UI file write. Act on its findings instead of re-auditing |
| Verify | `playwright-cli` | Three distinct roles — see below |
| Review | `impeccable audit` · `impeccable critique` · `web-design-guidelines` | Technical quality · UX judgement · mechanical rules |
| Drift | `impeccable doctor` | Reports drift between artifacts. Never repair drift as a side effect of a design task |

**One system decides during implementation.** Taste-input tools are
consulted *before* the direction is committed, never after. Loading two
opinionated systems at build time does not produce a synthesis; it produces
an average, and an average of stances is exactly the AI look.

## Playwright's three roles

Do not conflate them — they happen at different moments.

| Role | When | How |
|---|---|---|
| **Validation** | Inside the `tdd` loop | Acceptance criteria checked in a real browser, at the seam agreed in the spec. `playwright-cli snapshot` gives the accessibility tree; assert against it, not against pixels |
| **Visual regression** | In the Definition of Done | Committed goldens, `toHaveScreenshot()`, one per surface × theme × breakpoint. A golden changes only with `DESIGN.md` |
| **Design review** | At the gates | `playwright-cli show --annotate` — the user draws on the live page and types notes; you get the annotated screenshot, the snapshot of the marked region, and their comments. Use it whenever feedback is "I don't like it" and you need it localised |

Impeccable verifies in **bounded passes, not a loop**: build fully, inspect
once with a batched round (desktop and mobile together), fix everything it
shows in one batch, confirm with at most one more round, then stop.
Open-ended self-QA costs money and does worse what the review stage does
properly.

## The design-system ticket

The first frontend ticket of a project, always. Copy the plugin's
`tickets/design-system.md` template into the feature's ticket list —
`depends_on: []`, and every other frontend ticket depends on it, so the
blocking graph is what makes the anchor real rather than a convention.
Choosing a visual world is a taste decision, so it is taken by the human —
as the answer to the spec's open question on design direction, before any
ticket exists. Committing the chosen world is then an agent's ticket.

## Frontend additions to the Definition of Done

On top of the global DoD in `docs/agents/issue-tracker.md`, a ticket
labelled `frontend`:

- Visual goldens pass, or were updated **in the same commit as
  `DESIGN.md`**.
- `craft-floor.md` checks are green on the built result — contrast, depth,
  spacing, type, motion, states, browser surfaces, copy, coverage.
- `web-design-guidelines` reports no finding on the changed files.
- Browser surfaces are themed: selection, caret, scrollbars, focus rings,
  underline offset, tabular numerals. These ship with defaults belonging to
  no design system, and are the cheapest signal a page was built rather
  than assembled.
