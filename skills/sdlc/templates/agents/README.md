# Rules for agents

<!-- sdlc:template agents-index 1 -->

Everything an agent must respect in this repository lives in this directory,
one file per reader. Read the rows that name your role; skip the rest.

| File | Read by | When |
|---|---|---|
| `docs/agents/sdlc.json` | the orchestrator, every `sdlc-*` executable | every turn of the loop — settings, the `verify` command, the method slots |
| `docs/agents/issue-tracker.md` | anyone writing a spec, a ticket or a commit that closes one | before writing it — formats, statuses, Definition of Done |
| `docs/agents/escalation.md` | the orchestrator; an implementer about to return `blocked` | whenever a decision might be the human's |
| `docs/agents/ticket-critic.md` | the ticket writer and the ticket critic | cutting a spec into tickets |
| `docs/agents/review.md` | reviewers, the fixer, the acceptance runner, the orchestrator at delivery | reviewing a feature branch |
| `docs/agents/coding-standards.md` | implementers before coding; the standards reviewer | every ticket, every review |
| `docs/agents/frontend.md` | anyone touching a user interface | tickets labelled `frontend` |

A file added here gets a row here; `sdlc-check-harness` fails otherwise.

A new rule file is created the day an agent went wrong for lack of it — never
ahead of need.
