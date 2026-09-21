# Coding standards

<!-- sdlc:template agents-coding-standards 1 -->

Read by every implementer before writing code, and by the reviewer when
judging a change. Four rules govern this file itself:

1. **Tool before text.** Anything a linter, formatter or type-checker can
   enforce goes into that tool's config, wired into `verify` — never
   written here as prose.
2. **A line earns its place by settling something.** It resolves a real
   choice between valid options, or records a lesson from a mistake this
   project actually made. A generality true of every codebase ("use
   meaningful names") does neither.
3. **A rule here is citable, and citable means blocking.** The reviewer
   turns a violation into a `rule-violated` finding by quoting the line it
   broke; an uncited claim is downgraded to a non-blocking smell. Write
   rules a reviewer can point at, not vibes.
4. **Keep it under ~60 lines.** It starts short and grows only when a
   recurring smell in `docs/tech-debt.md` earns promotion to a written
   rule; the loop proposes such promotions at epic closure, and the human
   decides.

## Rules

<Copied at init from the plugin's `stacks/<stack>.md` matching this
project's stack, then owned by the project — edit it here, not in the
plugin.>
