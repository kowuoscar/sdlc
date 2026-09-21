# Phase: tickets

Cut an approved spec into tickets without asking the human. What replaces
their judgement is an independent critic upstream and a way out downstream.

## Steps

1. **Cut.** Spawn `sdlc:ticket-writer` with the spec, `ARCHITECTURE.md` and
   `docs/agents/issue-tracker.md`. First-ticket conventions:
   - the very first ticket of an empty project is
     `templates/tickets/foundation.md` — without `verify` nothing after it is
     checkable;
   - the first frontend ticket of a project is
     `templates/tickets/design-system.md`, and every other frontend ticket
     depends on it.
2. **Mechanical check.** `sdlc-check-tickets <feature>`. Errors go straight
   back to the writer; they need no judgement.
3. **Critique.** Spawn `sdlc:ticket-critic` with the spec, the tickets and
   `docs/agents/ticket-critic.md`. It answers with a verdict per rule, each
   failure citing the ticket and the rule.
4. **One revision.** Failures go back to the writer once, then steps 2–3 run
   once more. Still failing: escalation case 4, a `question` item carrying the
   critic's objections — the cut is telling you the spec is unclear.
5. Set every ticket `ready-for-agent` — `ready-for-human` only where the work
   needs a person's hands (a credential, an account, a purchase) — write the
   spec's `## Execution order`, run `sdlc-check-tickets` a last time.

The critic is not the last line of defence: during execution an implementer may
hand a ticket back as `too-big` with a proposed split. Tickets are disposable;
re-cutting is cheap, which is why no human gate sits here.

Done when `sdlc-check-tickets` passes and `sdlc-state` answers `execute`.
Commit: `docs(<feature>): cut tickets`.
