# Ticket critic

<!-- sdlc:template ticket-critic 1 -->

Rules a cut of tickets must pass, written as tests. `sdlc-check-tickets` has
already proved the mechanical half (frontmatter, sections, graph validity,
story coverage, execution order); these are the ones that need reading. The
critic returns one verdict per rule — `pass`, or `fail` naming the ticket and
quoting the line that fails it. A verdict without a quote is not a verdict.

## R1 — Every ticket is a vertical slice

At least one acceptance criterion describes something a user, an API caller or
an operator can observe, and the ticket is demoable once it alone is merged on
top of its blockers.

- Fails: "Create the `payments` table" · "Add the PaymentService class" · "Write the API client".
- Passes: "A booking can be paid by card and shows as paid" — even if it needs
  the table, the service and the client.
- Exempt: tickets labelled `enabler` (foundation, design system, prefactoring,
  and the expand/migrate/contract steps of a wide refactor). An `enabler` must
  still say which later ticket it enables.

## R2 — Every ticket fits one fresh context

An implementer starting from nothing can read what it needs, write the tests
and the code, and get `verify` green without its context filling up. Signals
of a ticket that does not fit: more than 7 acceptance criteria; more than 3
modules of `ARCHITECTURE.md` touched; "and" joining two behaviours in the
title; acceptance criteria that fall into two groups with no shared code.

- Fails: "Users can register, log in and reset their password".
- Passes: three tickets, the second and third depending on the first.

## R3 — Acceptance criteria are observable and checkable

Each criterion can be shown true or false by running something. It names
behaviour, never implementation.

- Fails: "Uses a repository pattern" · "Code is clean" · "Handles errors properly".
- Passes: "A declined card leaves the booking unpaid and shows the decline reason".

## R4 — The graph is honest

Every `depends_on` edge is a real gate: the dependent ticket cannot be built or
demoed without the blocker merged. No real gate is missing.

- Fails (superfluous): two tickets touching different journeys chained "to keep
  things orderly" — it serialises work that could run in parallel.
- Fails (missing): a ticket whose criteria use an endpoint that another ticket
  creates, with no edge between them.

## R5 — `## Tests` names cases and a seam

The cases cover the happy path, the boundaries and the errors the acceptance
criteria imply, and name the seam from the spec's `## Testing decisions`. A
bug-fix ticket's first case reproduces the bug and fails before the fix.

- Fails: "Unit tests for the service" · a seam the spec never agreed.

## R6 — `## Regression` names what is at risk

Already-shipped behaviour this ticket could break, and the existing test that
protects it — or `N/A — <reason>`. Any existing test the ticket expects to
modify is listed here with the reason; the merger refuses the merge otherwise.

## R7 — The walkthrough is reachable

Every step of the spec's `## Acceptance walkthrough` is made possible by some
ticket's acceptance criteria. A step no ticket enables means a missing ticket
or a walkthrough that promises more than the spec.

## R8 — Nothing beyond the spec

Every ticket traces to the spec: a story, or for an `enabler`, a named later
ticket. Work with no such trace is scope the human never saw.
