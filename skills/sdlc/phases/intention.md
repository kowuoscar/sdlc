# Phase: intention

The one thing no agent can look up is what the human wants. This phase gets it
once, thoroughly, so the rest of the loop never has to ask "what" again. It is
synchronous: the human is here, use them.

Output, identical whether the project is empty or not: `PRODUCT.md`,
`docs/journeys.md`, `docs/roadmap/`, and `ARCHITECTURE.md` when code exists.

## With existing code — read before asking

1. Spawn `sdlc:explorer` agents in parallel, one per area, each reading only
   what carries intent: entry points (routes, screens, commands), the data
   model, test titles, the README and the last ~50 commit subjects. Ask for:
   the journeys the code supports today, each with the entry point that proves
   it and whether it runs end to end; and a module map — path, one-line
   responsibility, what it depends on.
2. **Play it back.** "Here is what your project does today": the reconstructed
   journeys with a proposed state each. The code proves a thing exists, not
   that it was meant that way — the human corrects.
3. Write `ARCHITECTURE.md` from the module maps, following the template: it
   points, it never describes. Run `sdlc-check-harness`.
4. Interview **only the gap**: what is missing, what is half done, what comes
   next. The human never repeats what the code already says.

## With an empty repository

Interview from zero: who it is for and in what situation, the problem, the
journeys, the non-goals, and the stack — a user decision, asked once, recorded in
`PRODUCT.md` (including "delegated: <choice and why>" when they leave it to you).
Every journey starts as `wanted`. `ARCHITECTURE.md` waits for the foundation
ticket.

## The interview

Run the `interview` method here — this is where it belongs: read
`methods/grilling/SKILL.md` under `METHODS` and follow it (or load the skill
the slot names). Keep the glossary alive while you do, with the `domain`
method, `methods/domain-modeling/SKILL.md`.

Interview about **what and for whom**, never about how. Stop when you could
write the acceptance walkthrough of every journey without guessing.

## Write

- `PRODUCT.md` from the template — confirmed facts and explicitly marked open
  decisions only. An existing one is updated, never replaced.
- `docs/journeys.md` — each journey in a few lines, with its state.
- `docs/roadmap/<epic>.md` — an epic brings one or more journeys to `exists`.
  Fill `## Intent` and `## Journeys`; leave `## Features` empty, cutting is
  `plan-epic`'s job and depends on the code at that moment.
- `docs/roadmap/README.md` — the order. Propose it (dependencies first, then
  what unblocks a complete journey soonest); the human disposes.

Epics agreed in this conversation are `planned`.

Done when the human has validated the journeys, their states and the epic
order. Commit: `docs(sdlc): record intention`.
