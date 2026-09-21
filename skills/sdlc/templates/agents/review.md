# Review

<!-- sdlc:template review 1 -->

How a feature branch earns its merge. The verdict is computed, not felt:
reviewers produce **typed, cited findings**; `sdlc-merge-gate` reads them and
answers. Nobody — reviewer, fixer or orchestrator — decides whether a finding
blocks.

## Finding types

| `type` | Raised when | Cite | Blocks |
|---|---|---|---|
| `spec-missing` | the spec asks for it and the diff does not do it | the spec line | yes |
| `spec-partial` | done for some cases the spec names, not all | the spec line | yes |
| `spec-wrong` | done, but not as the spec says | the spec line | yes |
| `out-of-scope` | behaviour in the diff that no story, no `## Decisions taken` entry and no ticket asks for | the hunk, and "no source in spec" | yes |
| `rule-violated` | the diff breaks a rule written in this repository | the rule's file and its text | yes |
| `acceptance-failed` | a walkthrough step was played and did not pass | the step | yes |
| `design-guideline` | a finding of the design audit or the interface guidelines | the guideline | yes |
| `smell` | a judgement call: a possible code smell, a nicer way | — | no |

## No citation, no block

A blocking finding quotes what it violates — the spec line, the rule with its
file, the walkthrough step. The gate counts a blocking type with an empty
citation as a `smell`, and says so. This is what stops a reviewer from
blocking on taste, or from inventing a requirement the human never wrote.

Anything a linter, formatter or type-checker already enforces is `verify`'s
business: reviewers skip it.

## States

`open` → `fixed` (the fixer did something about it) → `confirmed` (a reviewer
checked the fix). A reviewer may set `dismissed`, adding the reason to `note`.
A finding blocks while `open` or `fixed`. **Only a reviewer lifts a finding**;
the author of a fix never judges it.

## The bounded cycle

Review → one fix pass → re-review of the blocking findings only → the gate.
Blocking findings that survive are escalation case 4. There is no second fix
pass: a second pass is where an agent starts bending the code to the reviewer
instead of to the spec.

## Smells

A smell is fixed when it sits in lines this feature already changed. Otherwise
it becomes one line of `docs/tech-debt.md` — an opinion for whoever next works
in that module, who may act on it or dismiss it with a reason.

## Decisions added during the fix pass

The fixer may answer an `out-of-scope` finding by recording the behaviour in
`## Decisions taken`. Such an entry is marked `(after review)`, and the
delivery report lists it separately: permitted, and visible.

## The walkthrough

The acceptance runner plays every `[agent]` step for real — a browser through
`playwright-cli` asserting on the accessibility snapshot, real requests against
a running API, real commands — and keeps evidence (output, snapshot,
screenshot) under the feature's `evidence/`. A step it could not play is
`failed` with what stopped it, never silently `pending`. `[human]` steps stay
`pending` and go to the human in the delivery report.

## The merge condition

`sdlc-merge-gate <feature>` answers `ok: true` when: no blocking finding is
`open` or `fixed`; every `[agent]` step passed with its evidence on disk; the
harness check passes; `verify` exits 0. The orchestrator merges on that answer
and on nothing else.
