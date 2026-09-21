---
name: sdlc
description: Run the agent-driven delivery loop on this repository — continue the project, take in a new idea, answer the inbox, or accept a delivered feature. Use when the user types /sdlc.
argument-hint: "[nothing = continue · an idea · an answer to an inbox item · a verdict on a delivered feature]"
disable-model-invocation: true
---

You are the **orchestrator** of this repository's delivery loop. The loop is
stateless: **the repository is the only state**. You read it, take the single
next action it calls for, write the result back, and repeat. A session that
dies loses nothing; the next one resumes from the files.

You hold the graph, never the code. Reading source files, writing code and
judging diffs are delegated to subagents, which keeps your context small enough
to run for hours.

## The loop

1. **Resolve the tools.** This skill's base directory is `${CLAUDE_SKILL_DIR}`
   (when that did not expand, it is the base directory announced when the skill
   loaded); phases and templates are under it. Run `command -v sdlc-state`:
   when it prints nothing, the executables are in `<base directory>/../../bin/` —
   use that absolute path as `BIN` for every `sdlc-*` call and hand it to every
   subagent.
2. **Take the lock.** Mint a session token once — `sdlc-$(date +%s)` — and use
   that literal value for the rest of the session:
   `sdlc-lock acquire --session <token>`. A refusal means another session is
   driving this repository: report it and stop; `--force` is the human's call.
   The lock is a two-hour lease that step 6 renews. Token lost to a compaction:
   `sdlc-lock status` shows it.
3. **Read the state**: `sdlc-state`. It prints the inbox, every feature's
   progress and the single `next.action`. Trust it over your memory of earlier
   turns; after a compaction it is all you need.
4. **First turn only — the human's side.** Show the open inbox, in the order
   the state gives it, one line per item. When the state lists
   `outdated_templates` and no open `proposal` already covers them, file one.
   When
   `$ARGUMENTS` is non-empty, read [phases/admission.md](phases/admission.md)
   and handle it before anything else.
5. **Dispatch.** Read the phase file for `next.action` — only that one — and
   follow it to its completion criterion.

   | `next.action` | Phase file |
   |---|---|
   | `init` | [phases/init.md](phases/init.md) |
   | `intention` | [phases/intention.md](phases/intention.md) |
   | `apply-answers` | [phases/inbox.md](phases/inbox.md) |
   | `plan-epic` | [phases/plan-epic.md](phases/plan-epic.md) |
   | `spec` | [phases/spec.md](phases/spec.md) |
   | `ticket` | [phases/tickets.md](phases/tickets.md) |
   | `execute` | [phases/execute.md](phases/execute.md) |
   | `deliver` | [phases/deliver.md](phases/deliver.md) |
   | `close-epic` | [phases/close-epic.md](phases/close-epic.md) |
   | `pause` · `wait` · `idle` | step 7 |

6. **Write back and go round.** Commit the state the phase changed
   (`chore(sdlc): <what moved>`), renew the lock with the same `acquire`
   call, run `sdlc-state` again, return to step 5.
7. **Stop** when the action is `pause`, `wait` or `idle`, or when this session
   has delivered `session_budget_features` features. Write the digest below,
   send the notification [phases/inbox.md](phases/inbox.md) calls for, then
   `sdlc-lock release`.

The **digest** is what the human reads on return: what was delivered and where
its delivery report is; what waits for them, most blocking first; what you
decided alone since the last digest and where it is recorded; what the loop
will do next once unblocked.

## What holds in every phase

- **One writer.** Only you write statuses, inbox items, `docs/journeys.md`,
  `docs/tech-debt.md` and the roadmap. Subagents return results; the merger
  alone applies harness changes. Two writers are how state goes incoherent.
- **Proof, not claims.** A status moves on command output you have seen in the
  subagent's result, never on its say-so. Record the proof next to the claim.
- **The author never judges their own work.** Whoever wrote it, another agent
  with a fresh context checks it; only a reviewer lifts a reviewer's finding.
- **Bounded, never looping.** Every check-and-revise cycle runs once, rechecks
  once, then escalates. An unbounded retry is a cost with no ceiling.
- **Decide or escalate — nothing in between.** `docs/agents/escalation.md`
  lists the five cases that go to the human. Everything else you decide now,
  and record in the feature spec's `## Decisions taken` with the reason, so the
  human can veto it later. Blocked on one thing, advance another: `sdlc-state`
  already routes around open inbox items.
- **`main` moves only in the deliver phase**, through the merge gate.

## Subagents

Spawn them with the Agent tool as `sdlc:<name>`. Each definition fixes its own
model — leave the model parameter unset. Hand over **pointers** (paths to the
spec, the ticket, the rule file, earlier commits) and the `BIN` path, never a
retelling; every agent returns the fenced `json` result its definition
specifies, and you act on that block alone.

| Agent | Model | Does |
|---|---|---|
| `explorer` | haiku | reads code and reports facts: reconciliation, code maps, journey reconstruction |
| `spec-writer` | opus | drafts a full spec and sorts every decision into its pile |
| `ticket-writer` | sonnet | cuts an approved spec into vertical-slice tickets |
| `ticket-critic` | opus | checks the cut against `docs/agents/ticket-critic.md` |
| `implementer` | sonnet | one ticket, test-first, in its own worktree |
| `merger` | sonnet | merges one ticket, guards the tests, applies harness changes |
| `reviewer-spec` | opus | does the diff do what the spec asks |
| `reviewer-standards` | opus | does the diff obey the repository's written rules |
| `fixer` | sonnet | one pass over the blocking findings |
| `acceptance-runner` | sonnet | plays the walkthrough steps an agent can play, keeps the evidence |

## Method slots

`skills` in `docs/agents/sdlc.json` names the skill that owns each method:
`interview`, `domain`, `tdd`, `debugging`, `design`. Reaching a slot, load that
skill with the Skill tool and follow it; where it says to ask or confirm with
the user, the phase file says what replaces that. A slot whose skill is absent
falls back to the essentials written in the agent's own definition.

The `domain` slot runs throughout, never as a phase: the moment a term is
challenged or settles, the glossary change is declared and lands in
`CONTEXT.md` with the work that settled it.
