Enforce via tooling, not here: formatting → `gofmt`/`goimports`; static
analysis → `go vet` + `staticcheck`, wired into `verify`.

1. Every function that can fail returns `error` as its last value; a CLI
   command's `main` calls a `run(args) error` it can test, and only `main`
   itself calls `os.Exit`.
2. Wrap errors with `fmt.Errorf("doing X: %w", err)` at each layer that adds
   context; never `fmt.Errorf("%v", err)` (loses `errors.Is`/`As`), never a
   bare re-return that leaves the caller guessing where it failed.
3. `context.Context` is the first parameter of any function that does I/O or
   can be cancelled, named `ctx`, never stored on a struct.
4. A long-running command honors context cancellation (Ctrl-C): check
   `ctx.Err()` in loops and pass `ctx` through to every client call.
5. Table-driven tests (`[]struct{ name string; ... }` + `t.Run(tt.name,
   ...)`) are the default shape for anything with more than one case; a
   hand-copied test per case is a smell.
6. CLI flags are parsed once in `main`/`cmd`, validated immediately, and
   passed down as typed arguments — no package below `cmd/` reads
   `os.Args` or a flag global directly.
7. Exported package APIs signal failure with sentinel errors
   (`var ErrNotFound = errors.New(...)`) or typed error structs, checked by
   callers with `errors.Is`/`errors.As` — never by string-matching
   `err.Error()`.
8. A package's public surface is small and deliberate: unexported by
   default, exported only when another package needs it, with the
   `internal/` directory enforcing it rather than convention alone.
9. A goroutine started by a command is tracked with a `sync.WaitGroup` or
   `errgroup.Group`; a fire-and-forget goroutine that can outlive `main` is
   a leak, not a shortcut.
10. Use structured logging (`log/slog`) for diagnostics beyond direct CLI
    output; CLI output (the human result, on stdout) and diagnostic logging
    (stderr) go through different writers, never mixed.
11. A subprocess call runs with an explicit timeout via
    `exec.CommandContext`, never a bare `exec.Command`.
