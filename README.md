# sdlc

A Claude Code plugin that lets an agent run a software project — and calls you
only for the decisions that are yours.

You describe what you want. The loop turns it into journeys, epics, specs,
tickets, test-first code, reviewed and merged features, and a walkthrough for
you to check each one by hand. It asks you a question in five defined cases
and no others; the only other stops are the gates you switched on yourself.

```
/sdlc:sdlc                continue the project
/sdlc:sdlc <anything>     an idea, an answer to the inbox, a verdict on a delivery
```

Once installed, the short `/sdlc` works too, as long as no personal
`commands/sdlc.md` or skill of the same name shadows it; this document writes
`/sdlc` throughout.

## How it works

**The loop is stateless; the repository is the only state.** Every turn reads
the repository, takes the single next action it calls for, and writes the
result back. A session that dies loses nothing.

```
            ATTENTION (you)   intention · inbox · acceptance
                 ▲   │
        escalate │   │ answers
                 │   ▼
            CONTROL   the orchestrator: read state, pick the next step, delegate
                 │   ▲
   ticket +      │   │ proof
   pointers      ▼   │
            EXECUTION ─────▶ VERIFICATION
            fresh workers    never the author
                 │   │
                 ▼   ▼
            STATE   the repository
```

| Step | What happens | You |
|---|---|---|
| Intention | On existing code the agent reads first, plays back what the product does today, and interviews you only about the gap. Output: `PRODUCT.md`, journeys (`exists` / `partial` / `wanted`), epics, the harness | here, once |
| Spec | Reconcile the epic with the code, **draft first, ask after**. Every decision lands in a pile: settled, taken alone (you can veto later), or yours | only real questions |
| Tickets | Vertical slices. An independent critic replaces "does this cut feel right?" | — |
| Execute | Parallel implementers, test-first, one ticket each in its own worktree. Four outcomes: `done`, `too-big`, `blocked`, `failed` | — |
| Deliver | Typed, cited findings; a script — not an agent — answers "may this merge?". One feature is one merge commit, so one command undoes it | the walkthrough, when you have time |
| Close the epic | Journeys played end to end, `Later` promoted explicitly, a retro that proposes rules | proposals |

The five cases that reach your inbox: an unanswered *what*; an irreversible
decision; your intention contradicted by the code; an agent that is stuck; an
action out of bounds. Everything else the agent decides and records.

## Install

```
/plugin marketplace add <owner>/sdlc
/plugin install sdlc@sdlc
```

From a local checkout, for one session: `claude --plugin-dir /path/to/sdlc`.
Installed for good from a local checkout:

```
claude plugin marketplace add /path/to/sdlc
claude plugin install sdlc@sdlc
```

An installed plugin is a **cached copy** of the version in `plugin.json`. After
changing this repository, bump the version, then
`claude plugin marketplace update sdlc && claude plugin update sdlc@sdlc`.

Then, in the repository you want built: `/sdlc`. The first run initialises it —
after asking — and shows you the permission list before writing it.

Requires `python3` (3.9+) and `git`. `gh` when `pull_requests` is on;
`playwright-cli` to play user-interface walkthroughs.

## Settings

`docs/agents/sdlc.json` in the target repository. The ones you will touch:

| Key | Values | |
|---|---|---|
| `spec_gate` | `always` · `questions-only` | approve every spec, or only answer real questions. Start on `always`; autonomy is earned on evidence |
| `merge` | `auto` · `human` | who merges a delivered feature. Use `human` where a push to main deploys |
| `max_implementers` | 3 | concurrent implementers |
| `max_pending_acceptance` | 3 | how far the loop may run ahead of your walkthroughs before it pauses |
| `session_budget_features` | 3 | features one session delivers before it stops |
| `pull_requests` | `false` | push feature branches and merge through GitHub |
| `skills` | slot → skill | which installed skill owns each method: `interview`, `domain`, `tdd`, `debugging`, `design` |

Full reference: [docs/contracts.md](docs/contracts.md).

## Models

Each role is a subagent with its model fixed in `agents/`:

| Model | Roles |
|---|---|
| haiku | `explorer` |
| sonnet | `ticket-writer`, `implementer`, `merger`, `fixer`, `acceptance-runner` |
| opus | `spec-writer`, `ticket-critic`, `reviewer-spec`, `reviewer-standards` |

The orchestrator runs on whatever model your session uses.

## Method skills

The loop owns the sequence, the file formats and the verdicts. *How* to
interview, model a domain, do TDD, debug or design is delegated to whichever
skills you have installed, named in `skills`. The defaults are Matt Pocock's
`grilling`, `domain-modeling`, `tdd`, `diagnosing-bugs`, and `impeccable` for
interfaces. A slot whose skill is missing falls back to the essentials embedded
in the agent.

## Repository layout

```
.claude-plugin/     plugin and marketplace manifests
skills/sdlc/        SKILL.md (the loop) · phases/ (one per action) · templates/
agents/             the ten subagents
hooks/              session-start summary · out-of-bounds guard
bin/ · scripts/     the mechanical checks (python, standard library only)
tools/              plugin validation and packaging, used by CI
tests/              unit tests of scripts, hooks and tools
docs/               contracts.md (data formats) · design.md (why it is built this way)
```

## Development

```
python3 -m unittest discover -s tests -v    # tests
python3 tools/validate_plugin.py            # prose, agents, templates and manifests agree
claude plugin validate .                    # official manifest validation
python3 tools/package.py                    # dist/sdlc-<version>.zip + SHA256SUMS
```

CI runs all four on every push and pull request and uploads the packaged plugin
as an artefact. Pushing a tag `vX.Y.Z` that matches `plugin.json` publishes a
GitHub release with the archive and its checksum.

Changing a machine-read format means: `docs/contracts.md` first, then the
script and its tests, then the template — and bump that template's marker.

## Licence

MIT.
