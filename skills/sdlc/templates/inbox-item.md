---
id: <item-slug>
type: question
status: open
blocks: [<feature-or-epic-slug>]
created: <YYYY-MM-DD>
---

<!-- sdlc:template inbox-item 1 -->

## Question

The decision the human is being asked to make, in one or two sentences.
State it, do not re-derive it from other files.

## Recommendation

What the orchestrator would do absent an answer, and why. Every item carries
one, even an `alert` — an answer is a decision, and a decision needs a
default to compare against.

## Blocks

What stays frozen while this item is `open` — mirrors the frontmatter
`blocks` list in prose, naming the feature or epic and what happens to it
(paused mid-ticket, not yet specced, etc).

## Meanwhile

What the orchestrator does instead of waiting idle: which other feature or
epic it moves to. `None — nothing else to work on` when there is nothing.

## Answer

Empty until the human fills it. Non-empty `## Answer` plus `status:
answered` is what tells the orchestrator to apply it and close the item —
write the decision here, not a discussion of it.

`type` picks the shape above:

- `alert` — something was reverted; `## Question` states what and
  `## Recommendation` names the exact command that did it.
- `question` — one of the five cases of `docs/agents/escalation.md`. When a
  ticket or review findings raised it, `## Blocks` names the ticket id or the
  finding ids, so the answer can be applied to them.
- `approval` — a gate the human switched on: a spec to approve
  (`spec_gate: always`) or a feature to merge (`merge: human`).
- `acceptance` — `## Question` points at the feature's
  `docs/features/<feature>/delivery.md` for the human to walk through.
- `proposal` — a change to conventions or scope the orchestrator suggests
  but will not make alone (a refactoring epic, a template upgrade).
