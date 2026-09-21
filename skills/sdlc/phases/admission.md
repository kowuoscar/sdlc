# Phase: admission

The human passed text to `/sdlc`. It is free text; classify it, act, then let
the loop continue. When two readings are plausible, ask one question.

| The text is | Do |
|---|---|
| **An answer** to an open inbox item | Write it under the item's `## Answer`, set `status: answered`. The loop applies it. |
| **A verdict on a delivered feature** — "accepted", or what failed | Accepted: spec `status: accepted`, close its `acceptance` item. Failed: below, as feedback. |
| **A veto** of a decision taken alone | Treat as feedback on that feature; quote the vetoed line of `## Decisions taken`. |
| **Feedback or a bug** on something delivered | A new feature, `epic` set to the original's, whose spec `## Problem` quotes the feedback. For a bug, the ticket's first test reproduces it and fails. |
| **An idea the size of a feature** inside an existing epic | Add its line to that epic's `## Features` at the position that respects dependencies. |
| **An idea the size of a journey or more** | A new journey (`wanted`) in `docs/journeys.md` and a new epic file, `status: proposed`. Ask where it goes in `docs/roadmap/README.md` — what to work on next is theirs. Set `planned` once placed. |
| **A change with no journey behind it** (tooling, upgrade, refactor) | A feature with an empty `epic`. |
| **A setting** ("stop asking me to approve specs") | Edit `docs/agents/sdlc.json`, say what changed. |

Sizing: a feature is one deliverable, demoable alone, a handful of tickets. An
idea whose honest description contains "and then" twice is an epic.

An idea that contradicts `PRODUCT.md` non-goals or an existing journey is
escalation case 3: say so now, while the human is here, rather than filing it.

Done when the text is recorded in the state and `sdlc-state` reflects it.
Commit: `docs(sdlc): admit <slug>`.
