Enforce via tooling, not here: formatting → Prettier; lint (unused vars,
import order, hooks rules) → ESLint (`eslint-config-next`); type safety →
`tsc --strict` with `noUncheckedIndexedAccess`.

1. Default every component to a Server Component; add `"use client"` only
   when the file needs state, effects, or browser APIs — not to "be safe".
2. Validate all external input (form submissions, route handler bodies,
   search params) with a Zod schema at the boundary; never trust a type
   assertion past that boundary.
3. Data fetching happens in Server Components or Route Handlers, never
   inside a Client Component's `useEffect` — that reintroduces the
   waterfall the App Router exists to remove.
4. Mutations go through Server Actions; call `revalidatePath`/
   `revalidateTag` inside the action, not from the client after it resolves.
5. Cross a Server/Client boundary only with serializable props — no
   functions, class instances or `Date`s passed to a Client Component; pass
   ISO strings and format them client-side.
6. An error that should show UI uses `error.tsx` at the nearest route
   segment; an error that should crash to a boundary above is thrown, never
   swallowed and logged.
7. Environment variables consumed in the browser are prefixed
   `NEXT_PUBLIC_` and nowhere else; a secret read in a Client Component is a
   bug, not a config oversight.
8. Compose Tailwind classes from the tokens in `tailwind.config`; an
   arbitrary value (`w-[123px]`) needs a comment saying why it isn't a token.
9. Unit and component tests (Vitest + Testing Library) sit next to the file
   as `*.test.tsx`; end-to-end journeys (Playwright) sit under `e2e/`, one
   file per journey.
10. A test that needs the network mocks at the fetch boundary (MSW), never
    by stubbing an internal function — internals are allowed to change shape.
11. Loading UI uses `loading.tsx` / `<Suspense>` scoped to the slowest data
    dependency, not one spinner for the whole page.
12. Client-side global state (Zustand/Context) holds only UI state that must
    survive navigation; server state stays in the cache Next.js already
    manages — do not duplicate it into a store.
13. Route Handlers return typed JSON via one shared response helper, never
    an ad hoc shape per route.
14. `params`/`searchParams` are typed and parsed once at the top of the
    route or page; do not re-parse them further down the tree.
15. A third-party or long-running call inside a Server Component carries an
    explicit timeout/`AbortController` — an unbounded await there holds up
    the whole response.
