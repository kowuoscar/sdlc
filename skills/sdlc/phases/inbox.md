# Phase: inbox

The inbox is the human's attention, and attention is the scarcest resource in
this loop. One file per item in `docs/inbox/`, from `templates/inbox-item.md`.

## Writing an item

An item is a deferred interview question. It carries: the question in one
sentence; **your recommendation and its reason**; what it blocks (`blocks:`
lists the feature or epic slugs — this is what lets `sdlc-state` route around
it); and what you are doing meanwhile. The human should be able to answer from
the item alone, in under a minute, without opening the code.

| `type` | When | `blocks` |
|---|---|---|
| `alert` | `main` was reverted, or the repository is in a state you could not repair | what is unsafe to continue |
| `question` | one of the five cases of `docs/agents/escalation.md` | the feature or epic that needs the answer |
| `approval` | `spec_gate` is `always` and a spec is ready | that feature |
| `acceptance` | a feature was delivered; points to its `delivery.md` | nothing — you never wait for a walkthrough |
| `proposal` | epic closure, debt threshold, outdated templates, a rule to promote | nothing |

One question per item. Related questions about the same spec are separate
items with the same `blocks`, so each can be answered when it can. An item
raised by a ticket or by findings names them in `## Blocks` — the ticket id,
the finding ids — so that the answer can be applied to them.

## Applying answers (`apply-answers`)

For each `answered` item: an answer is a **decision**, so it goes where
decisions live — copy it into the spec (`## User stories`, `## Goals /
Non-goals` or `## Decisions taken`, and out of `## Open questions`), the epic or
`PRODUCT.md`. Then apply what the answer unblocks, by what the item was about:

| The item was | The answer does |
|---|---|
| a spec `approval`, yes | spec `status: approved` |
| a spec `approval`, no | respawn `sdlc:spec-writer` on the existing spec with the objections verbatim as corrections, then file a fresh `approval` |
| a merge `approval` (`merge: human`) | nothing here — the deliver phase sees the merge on the main branch and resumes |
| a `question` naming a ticket (`needs-info`, `ready-for-human`) | the ticket goes to `ready-for-agent` with the answer added to its `## Context` — or to `done` when the human did the work themselves, or `wontfix` |
| a `question` listing blocking findings (case 4 at delivery) | the human outranks a reviewer: findings they overrule become `dismissed`, note `human: <reason>`; findings they want fixed authorise **one** more `sdlc:fixer` pass and re-review |
| an `acceptance`, accepted | spec `status: accepted` |
| an `acceptance`, with objections | treat the text as feedback through [admission.md](admission.md), then spec `status: accepted` — the follow-up feature carries the rest |
| an `alert` | what the human says; the feature it blocked resumes |
| a `proposal` | apply what was accepted — a rule added, an epic placed and set `planned`, templates updated |

Finally set the item `closed` and delete the file: the decision survives, the
task dies.

Done when no item is `answered`.

## Notifying

Send a push notification in exactly three cases: the loop stops on `wait` with
open `question` or `approval` items (everything is blocked); it stops on
`pause` (the pending-acceptance cap is reached); an `alert` was written.
Lead with what they would act on: "sdlc: 2 questions block card-checkout".
Everything else waits for their next `/sdlc` — a notification nobody needed
teaches them to ignore the ones they do.
