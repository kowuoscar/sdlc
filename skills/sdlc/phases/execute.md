# Phase: execute

Work the **frontier** of one feature until every ticket is `done`. You hold the
graph and write the statuses; implementers write code; the merger alone touches
the feature branch.

The orchestration method is `methods/implement-spec/SKILL.md` under `METHODS` —
one branch, a task graph, implementers in worktrees, a merger, the frontier
re-derived after every merge. Read it once. This file adds what it leaves
open because it assumes a real tracker and a human at the end: who writes
statuses, the four outcomes, the merger's guarantees. Its review and "ready for
review" steps belong to the deliver phase. Two of its lines do not apply: there
are no tracker issues for the pull request to close, and exploration notes are
never saved outside the repository — an explorer's findings come back in its
result and you pass them on as part of the pointers.

## Every time this phase starts

1. **The branch.** `feature/<feature>` exists: switch the primary working tree
   to it. It does not: create it from the main branch; with
   `pull_requests: true`, push it and open a draft pull request titled with the
   spec title.
2. **Orphans.** A ticket that is `in-progress` while you have no live
   implementer for it belonged to a session that is gone. Its `ticket/<id>`
   branch has commits: hand the ticket to a fresh implementer with that branch
   as its starting point. It has none: set it back to `ready-for-agent`.
   Done when every `in-progress` ticket has a live implementer.

## The cycle

1. Take the frontier from `sdlc-state`. For up to `max_implementers` tickets:
   set `status: in-progress`, commit, then spawn `sdlc:implementer` **in the
   background** with pointers to the ticket, the spec section it implements,
   `ARCHITECTURE.md`, `CONTEXT.md`, `docs/agents/coding-standards.md`, the
   feature branch name, `BIN`, `METHODS`, the `tdd`, `debugging` and `domain`
   slot values, and the soft budget `ticket_budget_turns`.
   Tickets labelled `frontend` also get `docs/agents/frontend.md` and the
   `design` slot.
2. As each implementer returns, act on its `outcome`:

   | Outcome | It returns | You do |
   |---|---|---|
   | `done` | branch, commits, `verify` output, declared harness changes, tests it touched | spawn `sdlc:merger`, **one at a time**, with the feature branch, the ticket file, the implementer's result block, `BIN` and `METHODS` |
   | `too-big` | a proposed split | replace the ticket file with the split tickets (`depends_on`, `stories`, status `ready-for-agent`), repoint tickets that depended on it, rewrite the spec's `## Execution order`, run `sdlc-check-tickets`, continue |
   | `blocked` | what is missing, or "the spec says X, the code makes X wrong" | a *how*: decide, record it in `## Decisions taken`, respawn. A *what*, or irreversible: `question` item naming the ticket, ticket `needs-info`. `blocks` lists the feature only when the answer could change other tickets |
   | `failed` | a diagnosis | **one** retry by a fresh implementer holding the diagnosis — a fresh context sees what a stuck one cannot. Second failure: escalation case 4 — a `question` item naming the ticket and carrying both diagnoses, ticket `needs-info` |

3. When the merger reports `merged: true` with a green `verify`: set the ticket
   `done`, commit with the merger's proof in the message body, take the new
   frontier, spawn again. `merged: false`: the reason decides — `test-weakening`
   and `verify-red` send the ticket back to a fresh implementer with the
   merger's report; `conflict` does the same, starting from the new branch tip.
   Either counts as the ticket's one retry.

Tickets that depend on nothing stuck keep moving throughout.

A `ready-for-human` ticket gets a `question` item naming it, with empty
`blocks`; the rest of the frontier proceeds, and `sdlc-state` reports the
feature stalled once only human work remains. The inbox phase puts an answered
ticket back on the frontier.

## What the merger guarantees

The feature branch is green after every merge, or the merge did not happen.
Existing tests are only modified when the ticket's `## Regression` says why.
`ARCHITECTURE.md` and `CONTEXT.md` change in the merge that changes what they
map, written by one hand. You do not re-check these; you read the merger's
proof.

Done when every ticket is `done` or `wontfix` and `sdlc-state` answers
`deliver`.
