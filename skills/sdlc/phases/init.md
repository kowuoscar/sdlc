# Phase: init

The repository has no `docs/agents/sdlc.json`. Initialising grants an agent
autonomy over this repository, so this is the one phase that is a conversation.
Templates live in `${CLAUDE_SKILL_DIR}/templates/`.

## Steps

1. **Confirm.** Say in two lines what initialising installs and ask whether to
   proceed. `/sdlc` typed in the wrong directory must cost one "no".
   Done when the human said yes.

2. **Inspect**, in one batch of read-only commands: is it a git repository
   (offer `git init` when not); which of `CLAUDE.md` / `AGENTS.md` exists; the
   stack (manifests at the root and one level down); whether there is a user
   interface; existing `PRODUCT.md`, `DESIGN.md`, `CONTEXT.md`,
   `ARCHITECTURE.md`, `docs/agents/`; the project's test, lint and type-check
   commands; whether a push to the main branch deploys (CI workflows, platform
   config files); and, when there is a user interface, whether the `design`
   skill (`impeccable` by default) is among your available skills — it is the
   one method the plugin does not bundle. Missing: say how to install it, and
   carry on; frontend tickets will wait for it. Done when you can state each fact with the file that proves it.

3. **Settle the config in one round.** Ask with AskUserQuestion, recommended
   answer first:
   - `spec_gate` — recommend `always` for a first project under this loop,
     `questions-only` once the specs it writes alone have earned trust.
   - `merge` — recommend `auto`, **unless a push to main deploys**: then `human`,
     because the right to merge would be the right to ship.
   - `max_implementers` — recommend 3.
   - `verify` — propose the single command you composed from step 2. When the
     project has none yet, keep the template's placeholder: the foundation
     ticket creates it, and the merge gate stays shut until then.
   Every other key keeps its default. Set `module_roots` and `test_globs` from
   what step 2 found. Done when `docs/agents/sdlc.json` is written and
   `sdlc-state` no longer reports `init`.

4. **Install the rule files.** Copy `templates/agents/*.md` into
   `docs/agents/`; with no interface, drop `frontend.md` and its row of the
   index. Fill
   `coding-standards.md` with the matching `templates/stacks/` file, and tell the
   human which tool-config lines that stack file recommends instead of prose.
   A destination that already exists is never overwritten: show the diff and
   ask — replace, merge or keep. A file that was already in `docs/agents/` and
   is not one of ours stays, and gets its row in `docs/agents/README.md` — read
   it to write who it is for; the harness check fails on an unindexed file.

5. **Install the map.** Put the `templates/agent-map.md` block into the
   existing `CLAUDE.md`, else the existing `AGENTS.md`; with neither, ask which
   to create. **Keep only the rows whose target exists today** — the harness
   check fails on a pointer to nothing. Whoever later creates a file the
   template lists adds its row in the same commit. A block already present between its markers is updated in place.
   Knowledge the old file held beyond pointers stays where it is — moving it
   into the harness is a proposal for later, not an init side effect.

6. **Permissions — shown, then written.** Compose the fragment from
   `templates/permissions.json`, replacing the placeholder with the project's
   real build and test commands. Print the full allow and deny lists and ask for
   confirmation; the deny list is what makes the out-of-bounds actions of
   `docs/agents/escalation.md` impossible rather than merely forbidden. On yes,
   merge its `permissions` into `.claude/settings.json`, keeping every existing
   entry and leaving the fragment's `template` key behind. The fragment lets
   agents push feature and ticket branches only: the loop never pushes the
   main branch. Deploy and publish commands specific to this project go into
   `forbidden_commands` in the config, which the guard hook enforces on the
   whole command rather than its prefix.

7. **Housekeeping.** Add `.sdlc/` to `.gitignore`. Create `docs/inbox/`,
   `docs/roadmap/`, `docs/features/` with a `.gitkeep`. Commit:
   `chore(sdlc): initialise`.

Done when `sdlc-check-harness` passes and the working tree is clean. The loop
continues on its own into `intention`.
