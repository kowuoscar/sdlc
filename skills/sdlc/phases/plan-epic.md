# Phase: plan-epic

An epic has no feature line yet. Cut it into features — and specify none of
them here.

1. Spawn `sdlc:explorer` on the modules this epic's journeys will touch
   (`ARCHITECTURE.md` names them): what already exists toward these journeys,
   what stands in the way.
2. Cut the epic into **features**: each one deliverable, demoable on its own,
   a handful of tickets, ordered so that every feature leaves the product
   working. A small epic is one feature; that is normal. Prefer the order that
   makes a journey playable end to end soonest, then widens it.
3. Write one line per feature under `## Features`. Record under `## Reworked`
   whatever the code made you change from `## Intent`, and why. Set the epic
   `in-progress`.

Only the next feature gets a spec: the spec of feature two depends on the code
that feature one leaves behind.

A cut that forces a choice about *what the product does* — not how — is
escalation case 1. With the human in the session, settle it now with the
`interview` slot. Otherwise file the question with the epic in `blocks` and
leave the epic unplanned; `sdlc-state` moves to the next epic.

Done when the epic has its feature lines and `sdlc-state` answers `spec`.
