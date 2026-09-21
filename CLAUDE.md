# sdlc plugin

A Claude Code plugin: an agent-run delivery loop whose only state is the target
repository. This file is a map; knowledge lives where it points.

| You need | Read |
|---|---|
| What the plugin does, how to run tests and package | `README.md` |
| Why it is built this way — principles, trade-offs, what was rejected | `docs/design.md` |
| Every machine-read format and what each script checks | `docs/contracts.md` |
| The loop itself | `skills/sdlc/SKILL.md`, then one file per action in `skills/sdlc/phases/` |
| A subagent's role, model and result shape | `agents/` |
| Files written into target repositories | `skills/sdlc/templates/` |

Rules for changing this repository:

- `docs/contracts.md` is authoritative. Change a format there first, then the
  script and its tests, then the template, and bump the template's marker.
- Prose is code here. Before editing a phase, an agent or a template, load the
  `writing-for-agents` skill when installed: every line must change behaviour,
  state the positive target, and live in exactly one place.
- Everything shipped is in English and free of machine-specific paths.
- `python3 -m unittest discover -s tests` and `python3 tools/validate_plugin.py`
  pass before any commit.
