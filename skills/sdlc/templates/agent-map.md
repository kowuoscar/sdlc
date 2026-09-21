<!-- sdlc:map:start -->
# <Project name>

<!-- sdlc:template agent-map 1 -->

<One line: what this project does.>
<One line: who it is for.>

Verify command: see `docs/agents/sdlc.json`.

| You need | Read |
|---|---|
| Who and why | `PRODUCT.md` |
| What journeys exist, are partial, or are wanted | `docs/journeys.md` |
| Where code lives, module boundaries, entry points | `ARCHITECTURE.md` |
| Domain vocabulary | `CONTEXT.md` |
| The visual world (UI work only) | `DESIGN.md` |
| Planned work, epic order | `docs/roadmap/` |
| A feature's spec and tickets | `docs/features/` |
| Past irreversible decisions | `docs/adr/` |
| Known debt | `docs/tech-debt.md` |
| Open questions, approvals, alerts awaiting a human | `docs/inbox/` |

Every rule an agent must follow is indexed in `docs/agents/README.md` — read
it before writing code, a spec or a ticket.

Feature work runs through `/sdlc`: it reads the state of this repository and takes the next step.
<!-- sdlc:map:end -->
