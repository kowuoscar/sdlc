# Phase: spec

Turn the next feature into `docs/features/<feature>/spec.md`. **Draft first,
ask after**: the human reacts to a complete proposal instead of answering a
questionnaire.

## Steps

A spec that already exists is **resumed, never rewritten**: skip to step 3 —
answers have already been copied in by the inbox phase. Respawn the
spec-writer only to revise what an answer or an objection names, handing it
the existing spec as its base.

1. **Reconcile.** The epic says what is wanted; the code says what is possible.
   Spawn `sdlc:explorer` with the epic file and `ARCHITECTURE.md`, scoped to the
   modules this feature touches and to their sections of `docs/tech-debt.md`.
   It reports facts: what exists, what conflicts, what will be expensive, which
   test seams already exist, which debt entries sit in the way.
   Done when you hold its findings, with `path:line` evidence.

2. **Draft.** Spawn `sdlc:spec-writer` with pointers to the epic, the feature
   line, `PRODUCT.md`, `docs/journeys.md`, `CONTEXT.md`, the reconciliation
   findings, `docs/agents/issue-tracker.md`, `docs/agents/escalation.md`,
   `METHODS` and the `domain` slot value — its method is
   `methods/to-spec/SKILL.md`, a synthesis with no interview. It writes the whole spec and
   sorts every decision into one of three **piles**:

   | Pile | Goes to |
   |---|---|
   | settled by the intention or by the code | the spec, silently |
   | **how** it is built, and easy to undo | `## Decisions taken`, with the reason |
   | **what** the user sees, or hard to undo | `## Open questions`, with a recommendation |

   The test seams are a *how*: they go to `## Testing decisions` and
   `## Decisions taken`, where the method skills would have asked the user.
   Debt in the way becomes prefactoring in `## Solution`. On the first feature
   with a user interface in a project that has no `DESIGN.md`, the visual
   direction is a *what*: an open question with two or three concrete
   directions and a recommendation. Once answered, committing it is an
   agent's ticket.
   Done when the spec exists with every template section present, the
   walkthrough written, and `## Open questions` either listing real
   escalations or reading `None`.

3. **Check the piles.** Read `## Open questions` against
   `docs/agents/escalation.md`. A question that fits none of the five cases is
   yours: decide it, move it to `## Decisions taken`. A `## Decisions taken`
   entry that does fit a case moves the other way. This is the step that keeps
   the inbox quiet *and* honest.

4. **Gate.** Take the first line that applies:
   - an open question has no inbox item yet → one `question` item each,
     blocking this feature. Stop here; approval of a spec with holes means
     nothing.
   - `## Open questions` reads `None` and `spec_gate` is `questions-only` →
     set `status: approved`.
   - `## Open questions` reads `None` and `spec_gate` is `always` → one
     `approval` item blocking this feature: what to read is the user stories,
     the non-goals, the decisions taken and the walkthrough — the solution is
     theirs to skip. The inbox phase sets `approved` on their yes.
   The spec stays `draft` while an item blocks it; `sdlc-state` works on
   something else meanwhile.

Done when the spec is `approved`, or is `draft` with its inbox items filed.
Commit: `docs(<feature>): draft spec` / `docs(<feature>): approve spec`.
