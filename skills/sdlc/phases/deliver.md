# Phase: deliver

Every ticket is done. Decide — mechanically — whether the feature may reach
the main branch, take it there, and tell the human how to check it.
`docs/agents/review.md` is the rule file for everything below.

First, look at the main branch: when it already contains this feature's
merge commit and no later revert of it, the merge happened — resume at the
`verify` on main in step 6.

## Steps

1. **Bring the branch up to date.** When main carries a revert of an earlier
   merge of this feature, first undo that revert on the feature branch
   (`git revert <revert commit>`) — merging main otherwise erases the feature.
   Then merge the main branch into `feature/<feature>` and run `verify`. Red
   here is integration work, so it is a ticket: add an `enabler` ticket
   `integrate-<main branch>` describing the failure, `ready-for-agent`, and let
   the loop return to `execute`.

2. **Review, in parallel**, each agent with a fresh context and pointers only
   (spec, `docs/agents/review.md`, `METHODS`, the diff command
   `git diff <main>...HEAD`). The review method is
   `methods/code-review/SKILL.md` — two axes that never see each other's
   context; you supply what it would ask the user for (the fixed point is the
   main branch, the spec is this feature's), and `docs/agents/review.md` turns
   its report into typed findings and a verdict:
   - `sdlc:reviewer-spec` and `sdlc:reviewer-standards`;
   - `sdlc:acceptance-runner` on the spec's whole walkthrough — it plays the
     `[agent]` steps and returns the `[human]` ones as `pending`, because
     `acceptance.json` needs an entry for every step;
   - on a feature that touched UI, the `design` slot's audit and critique, and
     `web-design-guidelines` when installed — their findings are typed
     `design-guideline`.

   Assemble their results into `findings.json` and `acceptance.json`; you are
   their single writer. For each finding returned: assign the next id (`F1`,
   `F2`, …), set `raised_by` to the agent that returned it, `state: open`,
   `after_review: false`, and carry `in_changed_lines` through. A failed
   walkthrough step is also a finding: `acceptance-failed`, citing the step,
   raised by the acceptance-runner. A finding first raised during the
   re-review gets `after_review: true`.

3. **One fix pass.** With no blocking finding, skip. Otherwise spawn one
   `sdlc:fixer` with `findings.json`, the spec, `docs/agents/review.md`,
   `METHODS` and the `tdd` slot value. It fixes every blocking finding, and the
   smells that sit in lines this feature already changed; other smells become
   debt. Mark what it fixed `fixed`.

4. **Re-review the blocking findings only.** The reviewers that raised them —
   fresh instances — set each to `confirmed`, `dismissed` with a reason, or
   leave it `open`. The acceptance-runner replays failed steps. The fixer never
   lifts a finding.

5. **The gate.** `sdlc-merge-gate <feature>`. You merge on its `ok: true` and
   on nothing else — not on your own reading of the reports. `ok: false` after
   the one fix pass: escalation case 4, a `question` item listing the
   `blocking` ids, feature blocked. Commit findings, acceptance and evidence on
   the feature branch either way.

6. **Merge**, per `merge` in the config:
   - `auto` — `pull_requests: true`: mark the pull request ready and
     `gh pr merge --merge`, then update local main. Otherwise
     `git merge --no-ff feature/<feature>` on main, message
     `feat(<feature>): <spec title>`. One feature is one merge commit, so one
     command undoes it.
   - `human` — mark the pull request ready (or leave the branch) and, unless
     an open item already asks for it, file an `approval` item blocking the
     feature that names the branch and the gate result. Stop this phase; the
     check at the top resumes delivery once they have merged.

   The loop never pushes the main branch. Records committed on local main
   travel to the remote inside the next feature branch.

   Then run `verify` **on main**. Red: `git revert -m 1 <merge commit>`, an
   `alert` item with the output, the feature blocked. Main is always green.

7. **Record**, on main: spec `status: delivered`; the epic's feature line
   ticked; one `docs/tech-debt.md` line per unfixed smell; `delivery.md` from
   the template, with the exact revert command; an `acceptance` inbox item
   pointing to it. Remove the feature's worktrees and its merged branch.
   Commit: `docs(<feature>): deliver`.

You do not wait for the walkthrough. The next feature starts now; the human's
verdict comes back through admission. What bounds how far you run ahead is
`max_pending_acceptance` — their walkthrough is the only check in this loop
that does not share an agent's blind spots.

Done when `sdlc-state` no longer lists the feature as active.
