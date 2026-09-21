# Tech debt

<!-- sdlc:template tech-debt 1 -->

Entries are opinions, not obligations — a later reader may dismiss one with
a reason instead of paying it. Debt on a module is paid when a later feature
touches that module, not on a schedule. The orchestrator is the single
writer, at delivery; nobody else appends here.

One level-2 heading per module path, one list line per entry: path in
backticks, `smell: <name>`, a note, the feature that recorded it, the date —
separated by ` · `.

## <module/path>

- `<file/path>` · smell: <name> · <what is wrong, one line> · <feature-slug> · <YYYY-MM-DD>
