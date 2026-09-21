# Phase: close-epic

Every feature of the epic is delivered or dropped. Three green features can
still make a broken journey — the seams between them were nobody's ticket.

## Steps

1. **Play the journeys end to end, on main.** Spawn `sdlc:acceptance-runner`
   with `docs/agents/review.md` and the epic's `## Journeys`: each journey from its first step to its last,
   as one run, evidence kept under `docs/roadmap/evidence/<epic>/`.
2. **Move the journeys on proof only.** Played through: `exists` in
   `docs/journeys.md`. Not playable: it stays `partial`, the epic stays open —
   add the missing feature line and let the loop build it, or, when what is
   missing is a *what*, escalate. Steps only a human can play: `partial`, with
   an `acceptance` item naming them.
3. **Empty `## Later`.** Every entry gets an explicit decision: a new epic
   (`status: proposed`, a new `wanted` journey if it is one), a feature line on
   another epic, or dropped with the reason written next to it. Nothing in
   `Later` disappears silently; it is the project's memory of what was put off.
4. **Retro — proposals only.** The method is `methods/retro/SKILL.md` under
   `METHODS`: its categories are what to look for; its sources here are this
   epic's specs, findings, delivery reports and closed inbox items rather than
   session logs; its writing guide is `methods/writing-for-agents/SKILL.md`;
   and where it presents candidates to the user, you file them. In this loop
   they usually show up as:
   - smells of the same kind recorded on several features → a rule for
     `docs/agents/coding-standards.md`, or better, a lint rule;
   - escalations that a sharper `PRODUCT.md` or journey would have answered →
     the sentence to add;
   - places an explorer or implementer got lost → a harness pointer to add;
   - rule-file lines no finding ever cited → candidates for deletion;
   - modules in `sdlc-state`'s `debt.over_threshold` → a refactoring epic.
   File **one** `proposal` item carrying all of them. A rule that blocks every
   future merge, and what to work on next, are the human's to decide.
5. Set the epic `done`. Commit: `docs(<epic>): close epic`.

You do not wait for the proposal's answer: the next `planned` epic starts now.
Epics created here are `proposed` and wait for the human to place them.

Done when the epic is `done` with `## Later` empty — or stays open with the
missing feature line added or the question filed, which is step 2's outcome.
