// sdlc — the walk-through, the station rail and the theme switch.
// No dependency. Everything here is an enhancement: the page reads fine without it.

(function () {
  "use strict";

  // Each step: what changed in the repository, what sdlc-state answers, who moves.
  // `actor` is one of "you", "agent", "script" — the only three colours of the page.
  var STEPS = [
    {
      repo: [["new", "(an empty git repository)"]],
      action: "init",
      reason: "docs/agents/sdlc.json is missing",
      text: "The first /sdlc asks before installing anything, settles the config in one round, and shows the permission list before writing it.",
      actor: "you", who: "You say yes. The orchestrator installs docs/agents/."
    },
    {
      repo: [["old", "docs/agents/sdlc.json"], ["old", "docs/agents/*.md"], ["old", "CLAUDE.md          the map"]],
      action: "intention",
      reason: "docs/journeys.md is missing",
      text: "The one synchronous conversation. On existing code the explorers read first and play back what the product does today; the interview covers only the gap.",
      actor: "you", who: "You and the orchestrator · explorer (haiku) reads the code."
    },
    {
      repo: [["new", "PRODUCT.md"], ["new", "docs/journeys.md   Pay online — wanted"], ["new", "docs/roadmap/online-payment.md   planned"]],
      action: "plan-epic", target: "online-payment",
      reason: "the epic has no feature line yet",
      text: "The epic is cut into features, each demoable alone. None of them is specified yet: the spec of feature two depends on the code feature one leaves behind.",
      actor: "agent", who: "explorer (haiku), then the orchestrator."
    },
    {
      repo: [["old", "docs/roadmap/online-payment.md"], ["new", "  - [ ] card-checkout"], ["new", "  - [ ] email-receipt"]],
      action: "spec", target: "card-checkout",
      reason: "the epic's next feature has no spec yet",
      text: "Reconcile the epic with the code, then draft the whole spec. Every decision lands in a pile: settled, taken alone, or yours.",
      actor: "agent", who: "explorer (haiku) · spec-writer (opus)."
    },
    {
      repo: [["new", "docs/features/card-checkout/spec.md   draft"], ["new", "  ## Decisions taken   4"], ["new", "  ## Open questions    1"], ["new", "docs/inbox/refund-in-part.md   question · blocks card-checkout"]],
      action: "wait",
      reason: "everything that exists is blocked",
      text: "One question was genuinely yours: do we refund in part? It is filed with a recommendation. With a second epic, the loop would be working on it right now.",
      actor: "you", who: "You — in under a minute, from the item alone."
    },
    {
      repo: [["new", "docs/inbox/refund-in-part.md   answered"], ["new", "  ## Answer: no partial refunds"]],
      action: "apply-answers",
      reason: "1 inbox item is answered",
      text: "An answer is a decision, so it is copied into the spec. Then the item is deleted: the decision survives, the task dies.",
      actor: "agent", who: "The orchestrator — the only writer of the inbox."
    },
    {
      repo: [["new", "docs/features/card-checkout/spec.md   approved"], ["old", "  ## Open questions    None"]],
      action: "ticket", target: "card-checkout",
      reason: "approved, but no tickets yet",
      text: "Vertical slices with an honest graph. A script checks the mechanical half; an independent critic checks eight rules written as tests.",
      actor: "agent", who: "ticket-writer (sonnet) · sdlc-check-tickets · ticket-critic (opus)."
    },
    {
      repo: [["new", "tickets/charge-card.md    ready-for-agent"], ["new", "tickets/show-decline.md   ready-for-agent · depends_on charge-card"]],
      action: "execute", target: "card-checkout",
      reason: "frontier: charge-card",
      text: "One ticket, one fresh context, one worktree, test-first. It returns done, with the output of verify as proof.",
      actor: "agent", who: "implementer (sonnet)."
    },
    {
      repo: [["old", "tickets/charge-card.md    in-progress → done"], ["new", "  merged · tests guarded · verify green"], ["old", "tickets/show-decline.md   ready-for-agent"]],
      action: "execute", target: "card-checkout",
      reason: "frontier: show-decline",
      text: "The merger refused nothing: no existing test was weakened, the branch is green, the new module is on the map. The frontier moves.",
      actor: "script", who: "merger (sonnet) · sdlc-test-guard · sdlc-check-harness."
    },
    {
      repo: [["old", "tickets/charge-card.md    done"], ["new", "tickets/show-decline.md   done"]],
      action: "deliver", target: "card-checkout",
      reason: "every ticket is done",
      text: "Two reviewers who never see each other's context, and an agent that plays the walkthrough in a real browser and keeps the evidence.",
      actor: "agent", who: "reviewer-spec and reviewer-standards (opus) · acceptance-runner (sonnet)."
    },
    {
      repo: [["new", "findings.json"], ["new", "  F1 spec-partial   cited · open      → blocks"], ["new", "  F2 rule-violated  no citation       → downgraded"], ["new", "  F3 smell                            → never blocks"], ["new", "acceptance.json   step 1 passed · step 2 yours"]],
      action: "deliver", target: "card-checkout",
      reason: "sdlc-merge-gate: ok false — F1",
      text: "The gate refuses. F1 quotes the spec line it rests on, so it blocks. F2 quotes nothing, so it is only an opinion. One fix pass, then the reviewer that raised F1 checks the fix.",
      actor: "script", who: "sdlc-merge-gate · fixer (sonnet) · reviewer-spec (opus)."
    },
    {
      repo: [["old", "findings.json"], ["new", "  F1 spec-partial   confirmed"], ["new", "main: one merge commit · verify green"], ["new", "spec.md   delivered"], ["new", "delivery.md   how to check it, how to undo it"], ["new", "docs/inbox/walk-card-checkout.md   acceptance"]],
      action: "spec", target: "email-receipt",
      reason: "the epic's next feature has no spec yet",
      text: "The gate said yes, so the orchestrator merged. Your walkthrough is waiting — and the loop is not. It has already started the next feature.",
      actor: "you", who: "You, when you have time. The cap on pending walkthroughs is what bounds the loop."
    },
    {
      repo: [["old", "  - [x] card-checkout"], ["new", "  - [x] email-receipt"]],
      action: "close-epic", target: "online-payment",
      reason: "every feature line is delivered or dropped",
      text: "The journey is played end to end on main. It moves to exists on proof only. Later is emptied explicitly, and one batched proposal reaches you.",
      actor: "agent", who: "acceptance-runner (sonnet), then the orchestrator."
    },
    {
      repo: [["new", "docs/journeys.md   Pay online — exists"], ["new", "docs/roadmap/online-payment.md   done"]],
      action: "idle",
      reason: "nothing left to do",
      text: "Until you type /sdlc with the next idea.",
      actor: "you", who: "You."
    }
  ];

  var stepper = document.getElementById("stepper");
  if (stepper) {
    var repo = document.getElementById("step-repo");
    var action = document.getElementById("step-action");
    var text = document.getElementById("step-text");
    var who = document.getElementById("step-who");
    var count = document.getElementById("step-count");
    var bar = document.getElementById("step-bar");
    var prev = document.getElementById("step-prev");
    var next = document.getElementById("step-next");
    var index = 0;
    var KEY = { you: "k-you", agent: "k-agent", script: "k-script" };

    var render = function () {
      var step = STEPS[index];
      repo.textContent = "";
      step.repo.forEach(function (line) {
        var span = document.createElement("span");
        span.className = line[0];
        span.textContent = line[1] + "\n";
        repo.appendChild(span);
      });
      action.textContent = step.action + (step.target ? " " + step.target : "");
      var reason = document.createElement("small");
      reason.textContent = step.reason;
      action.appendChild(reason);
      text.textContent = step.text;
      who.textContent = "";
      var key = document.createElement("i");
      key.className = KEY[step.actor];
      who.appendChild(key);
      who.appendChild(document.createTextNode(step.who));
      who.className = "who" + (step.actor === "you" ? " you" : step.actor === "script" ? " script" : "");
      count.textContent = (index + 1) + " / " + STEPS.length;
      bar.style.width = ((index + 1) / STEPS.length * 100) + "%";
      prev.disabled = index === 0;
      next.disabled = index === STEPS.length - 1;
    };
    var go = function (delta) {
      index = Math.max(0, Math.min(STEPS.length - 1, index + delta));
      render();
    };
    prev.addEventListener("click", function () { go(-1); });
    next.addEventListener("click", function () { go(1); });
    stepper.addEventListener("keydown", function (event) {
      if (event.key === "ArrowRight") { go(1); event.preventDefault(); }
      if (event.key === "ArrowLeft") { go(-1); event.preventDefault(); }
    });
    render();
  }

  // The rail follows the station in view.
  var stations = document.querySelectorAll("[data-station]");
  if (stations.length && "IntersectionObserver" in window) {
    var items = {};
    document.querySelectorAll(".rail a").forEach(function (link) {
      items[link.getAttribute("href").slice(1)] = link.parentElement;
    });
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        Object.keys(items).forEach(function (id) { items[id].classList.remove("is-current"); });
        if (items[entry.target.id]) { items[entry.target.id].classList.add("is-current"); }
      });
    }, { rootMargin: "-30% 0px -60% 0px" });
    stations.forEach(function (station) { observer.observe(station); });
  }

  // Theme: follow the system until the reader chooses.
  var button = document.getElementById("theme");
  if (button) {
    var root = document.documentElement;
    var stored = null;
    try { stored = localStorage.getItem("sdlc-theme"); } catch (error) { stored = null; }
    if (stored === "light" || stored === "dark") { root.setAttribute("data-theme", stored); }
    button.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var chosen = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", chosen);
      try { localStorage.setItem("sdlc-theme", chosen); } catch (error) { /* private mode */ }
    });
  }
}());
