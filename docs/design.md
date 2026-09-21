# Design

Why the plugin is built the way it is. The *what* is in `README.md`, the
formats in `contracts.md`.

## The problem

A pipeline of commands makes the human the scheduler: they know what comes
next, launch the next command, and remember what was left for later. Every
observed failure of the first version came from that — no control over epics,
no guide for checking what was built, manual chaining, forgotten intentions
between sessions.

This version inverts it. **The agent schedules; the human is an interrupt.**

## Principles

**The loop is stateless; the repository is the state.** Any session —
interactive today, relaunched or cloud-run later — reads the repository and
takes one step. Nothing depends on a conversation surviving. Consequence: no
derived state is stored; status lives in frontmatter and `sdlc-state` derives
the rest, deterministically and for free.

**Gates follow the nature of a decision, not the position in a pipeline.**
"Approve every spec" is a positional gate. "Ask when the question is about what
the user sees, or is hard to undo" is a gate by nature. The five escalation
cases are a closed list; the spec gate remains as a switch, because autonomy is
earned on evidence.

**Autonomy is bounded by what can be verified without the human.** Hence: a
single `verify` command as a precondition; proof attached to every status
change; the author never judging their own work; bounded cycles everywhere
(check, revise once, recheck, escalate).

**Mechanical where possible, judgement where unavoidable, and never mixed.** A
reviewer's *detection* is judgement. Everything after it is not: findings are
typed, a blocking finding must cite what it violates or it is downgraded, and a
script computes the merge verdict. The same split applies to tickets (script,
then critic) and to the harness (path checks, both directions).

**One writer per piece of shared state.** Statuses, inbox, journeys, debt: the
orchestrator. The feature branch, `ARCHITECTURE.md`, `CONTEXT.md`: the merger.
Implementers declare harness changes instead of making them — a textual
conflict is cheap, two agents naming one notion differently is not, and only an
explicit declaration makes that visible.

**The harness points, it never describes.** A stale path fails loudly; a stale
description lies silently. Routes and schemas are read in the code. Harness
files are created the day an agent went wrong for lack of one.

**Progressive elaboration.** Epics are aspirations, code is truth. Only the
next feature is specified and only an approved spec is cut, because each
depends on the code the previous one left behind.

**What carries a decision survives; what carries a task dies.** Specs, ADRs,
the glossary and delivery reports stay. Tickets, inbox items and epics are
disposable — except an epic's `Later`, which is the project's memory of what
was put off and must be emptied explicitly at closure.

## What replaced each human gate

| First version | Now |
|---|---|
| Interview before every spec | Draft first; three piles; only real questions reach the inbox |
| "Do these seams match your expectations?" | The spec's `## Testing decisions`, recorded as a decision taken |
| "Does this cut feel right?" | `sdlc-check-tickets`, then an independent critic with rules written as tests; downstream, an implementer may return `too-big` |
| A menu at the end of a branch | The merge gate, and the `merge` setting |
| A human reading the review | Typed findings and a computed verdict; the human plays the walkthrough instead |

The price of removing gates is that a misunderstanding is discovered later.
`max_pending_acceptance` bounds that: the human's walkthrough is the only check
that does not share an agent's blind spots, so the loop may not run far ahead
of it.

## Owning the sequence, borrowing the method

The plugin owns what makes the loop a loop: the sequence, the formats, the
verdicts, the escalation policy. It borrows *method* — how to interview, model
a domain, do TDD, debug, design — from installed skills through named slots,
and says what replaces the places where those skills would ask the user. A
missing skill degrades to embedded essentials rather than breaking the loop.

Templates are owned for the same reason: a file the loop reads must not change
shape because a third-party skill did. Where another tool reads the same file
(`PRODUCT.md` and impeccable), the template stays read-compatible with it.

## Models

Cost follows context pressure and stakes. Reading is cheap and wide: haiku.
Building is long and tool-heavy: sonnet. Judging is short, reads a diff, and
decides what reaches main: opus — also for the spec, since every later step
inherits its mistakes.

## Runtime

Level 1: a live session running `/sdlc` until nothing is actionable, then a
notification. Levels 2 (a relaunched headless session) and 3 (a cloud routine
triggered by an inbox answer) need no change to the loop, only something to
start it.

## Known limits

- An agent reviewing an agent shares its blind spots; see above.
- The harness check runs in the loop, not in the target repository's own CI,
  which does not have the plugin. Drift introduced outside the loop is caught
  at the next merge, not at the commit that caused it.
- Permission rules match command prefixes; the guard hook covers the rest, for
  commands it knows about. `forbidden_commands` is where a project adds its own.
