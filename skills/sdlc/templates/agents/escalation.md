# Escalation

<!-- sdlc:template escalation 1 -->

The human's attention is spent on five cases. **This list is closed.** A
decision that fits none of them is the agent's: take it now, record it in the
feature spec's `## Decisions taken` with its reason, and carry on — the human
can veto it afterwards, and it was chosen to be cheap to undo.

| # | Case | It is this case when | Examples |
|---|---|---|---|
| 1 | **An unanswered *what*** | behaviour the user will see has several reasonable answers, and neither `PRODUCT.md`, `docs/journeys.md` nor the epic settles it | refund in part or only in full; who may cancel a booking; what an empty state offers |
| 2 | **An irreversible decision** | undoing it later costs more than a revert | a migration that drops or rewrites data; adopting a paid or hosted service; a public API or file-format contract; a licence-bearing dependency |
| 3 | **Intention against code** | a journey or non-goal asks for X and the code makes X impossible, or several times the expected cost | the journey needs offline use and the app is server-rendered throughout |
| 4 | **Stuck** | a bounded cycle ran out: a ticket failed twice, a cut failed its critic twice, blocking findings survived the fix pass, the session budget ended mid-feature | — |
| 5 | **Out of bounds** | the work needs something an agent may not do here | reading secrets, deploying, publishing, spending money, force-pushing, rewriting the main branch's history |

## Telling *what* from *how*

*What*: a person using the product could notice the difference and might
object. *How*: only someone reading the code could. Naming, structure,
libraries that are free and replaceable, test seams, error-handling style,
file layout — all *how*. When a *how* is hard to undo it is case 2, not case 1.

## Filing

One `question` item per decision, from the inbox template: the question in one
sentence, **a recommendation with its reason**, what it blocks, what continues
meanwhile. An item the human cannot answer from the item alone is not ready
to file. Case 4 items carry the evidence — the diagnosis, the critic's
objections, the blocking finding ids.

Case 5 is never worked around: no alternative route to the same forbidden
effect. File it and move to other work.
