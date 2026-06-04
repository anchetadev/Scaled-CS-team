---
name: agent-dispatch
description: "Send work to one of Galileo's persistent worker agents and relay the result back to the team."
version: 0.6.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [dispatch, delegation, supervisor, workers, agents, hand-off, bot-father]
    related_skills: []
---

# Agent Dispatch

Use this skill when a teammate's request is a fit for one of your persistent worker agents — not something you should do yourself. You are the bot father; this is how you actually act like one.

Load this when you find yourself about to:
- Do recurring work (cron jobs, daily reports, batch reviews) — that belongs to a worker.
- Run a structured procedure that one of your agents owns (e.g. building an audit checklist → Euclid).
- Hand off a multi-step pipeline (e.g. audit a customer = Euclid → Tycho → Curie → Kepler → Hopper).

If the work is one-off, judgment-heavy, or conversational, do it yourself.

## Your worker roster (current)

| Persona | Role — owns | Profile | Has external access? |
|---|---|---|---|
| **Euclid** | Rubric / SOP Author — defining checklists, scoring rubrics, SOPs (definitions only) | `euclid` | No — zero data access, ever |
| **Tycho** | Salesforce Reader — pulling raw account data, a dumb pipe, no interpretation | `tycho` | Read-only Salesforce (pending live creds) |
| **Curie** | Hygiene + Score Validator — integrity check: is the data trustworthy? (independent of meaning) | `curie` | No |
| **Kepler** | Data Analyst — scoring the data against the rubric: what does it mean? | `kepler` | Read-only (works on Tycho's data) |
| **Hopper** | Controlled Executor — writing approved changes back, per-batch human approval | `hopper` | Write Salesforce |

When you dispatch, name the agent in third person ("I'll have Euclid draft that"). Workers are teammates, not limbs.

**The key boundaries:** Curie asks *is the data trustworthy?*; Kepler asks *what does it mean?* — integrity stays an independent check, so never let Kepler self-certify the data it's interpreting. And Euclid *defines* scores while Kepler *applies* them — never collapse those two.

## Core method

### 1. Pick the right worker

Match the request to the worker that owns it. If no worker fits and the work is recurring, *propose creating a new persistent agent* rather than absorbing it. If the work is genuinely one-off, do it yourself.

If the work spans multiple workers (e.g. "audit account #4471 for renewal risk"), dispatch them in pipeline order and stitch the outputs:
1. **Euclid** (Rubric Author) — confirm the rubric exists (or have it drafted)
2. **Tycho** (Reader) — pull the account's raw data (dumb pipe, no interpretation)
3. **Curie** (Validator) — confirm the data is trustworthy (integrity check)
4. **Kepler** (Data Analyst) — score the validated data against the rubric (interpretation)
5. **Hopper** (Executor) — write changes, only with explicit human approval per batch

### 2. Tell the human what's happening

Before dispatch, post a short heads-up in the channel/DM:
> "On it — asking Euclid to draft the renewal-risk checklist. Back in a minute."

This sets expectations (a worker is doing it, not you instantly) and makes the architecture visible.

### 3. Dispatch the work

Run the worker as a one-shot prompt from your shell using the `-z` flag (one-shot prompt mode — no interactive REPL, no session reuse). Pattern:

```bash
<profile-name> -z "<instruction for the worker>"
```

Examples:
- `euclid -z "Draft a checklist for our renewal-risk audit. Scope: customers in the 90 days before contract end. Use the build-audit-checklist skill."`
- `euclid -z "Revise the renewal-risk checklist based on this team feedback: <paste>"`

Two gotchas learned in practice:
- **Keep the `-z` prompt a single line.** A multi-line argument (e.g. `-z "$(cat bigfile)"`) drops the worker into its interactive TUI instead of running one-shot. If you need to hand a worker a long rubric or data blob, save it to a file and tell the worker to read the file itself (workers have terminal/file tools).
- **Use absolute paths, not `~`.** Worker terminal tools don't reliably expand `~`. Say `/home/anche/.hermes/botfather/rubrics/renewal-risk.md`, not `~/.hermes/...`, or the worker may report the file "doesn't exist" and refuse.

The worker's reply is the artifact. Capture it; do not paraphrase it for the human until you've read it.

Each worker profile has its own SOUL and own credentials. You are not running them as you — you are sending instructions and receiving output. Treat each dispatch as you would a teammate's email.

### 4. Read the output before relaying

- Skim for obvious mistakes (scope drift, missing sections, hallucinated signals).
- If the worker asked you a clarifying question, answer it yourself if you can, or relay to the human if you can't.
- If the output is malformed (wrong structure, missing sign-off line), send the worker back a short correction prompt — don't fix it yourself; the worker needs to learn its own discipline.

### 5. Relay to the human

- Lead with a one-line summary of what the worker produced.
- Paste the worker's output verbatim in a code block or thread.
- Add your own commentary in plain English — what to look at, what to decide, what's next.
- Name the worker so the team learns who does what: "Euclid drafted this — let me know if the framework looks right and I'll have them flesh it out."

## Anti-patterns

- **Don't ghost-dispatch.** If a worker is doing the work, say so. Hiding it makes the architecture invisible and trains the team to expect you to do everything.
- **Don't paraphrase worker output without showing it.** The point of having specialists is their work is auditable. Show, then summarize.
- **Don't fix worker output silently.** If the Analyst's checklist has a problem, send it back. Patching it yourself teaches the worker nothing and breaks the chain of trust.
- **Don't dispatch outside a worker's scope.** If you find yourself asking Euclid to do something other than rubrics, you're misusing the roster. Either route to the right worker, propose a new one, or do it yourself.

## Memory

After a dispatch, remember:
- Which worker handled what kind of request — pattern-match faster next time.
- Worker output quirks you've had to correct — surface in a checkpoint with the user if a pattern emerges.
- Pipelines that worked end-to-end — these are templates for future runs.



## Live updates between dispatches — design note (removed v1.4.5)

A "pipeline narration cadence" was attempted in v1.4.2 — Galileo would emit short status messages ("Tycho ✓ — 8 fields", "→ Curie running...") between worker dispatches so the user would feel the work progressing. It was removed in v1.4.5 after live testing showed the local Galileo tab UI **buffers the full response** rather than streaming, so any narration content arrived all at once at the end alongside the full output. Same wallclock, no perceived improvement.

**The real path to live updates** is hooking the front-end into the worker ledger at `/home/hermes/botfather/status/active.jsonl` — workers already write `ack` / `progress` / `done` events to that file (see the `coordination-protocol` skill), and a UI subscriber can render them independent of whatever Galileo is doing. That's a UI-side change, not a Galileo-side change.

For now: focus on the **TL;DR-first inverted pyramid** (below) — when the response lands, the takeaway is the first thing the user reads. That is the responsiveness improvement we can deliver from the agent side.

## v1.4.0+ dispatch reminders (Kepler / Curie)

When you dispatch to Kepler or Curie, include these instructions in your prompt. The skills themselves require them, but reminding in-prompt makes Mimo dramatically more reliable about following through:

- `"End your output with a '## TL;DR (for Galileo to relay)' section per the v1.4.0 contract — 3–5 sentences I can post verbatim."`
- `"Cite every score / verdict with the relevant SOP section inline in brackets (e.g. [SOP 4.1 Pillar 1, Sub-Score 2], [SOP 2.5a §2], [SOP 2.3 §4])."`
- `"Render every table as a fenced code block (triple backticks) so column alignment survives in the chat surface."`

Belt-and-suspenders. The skill is the canon; the dispatch prompt is the reinforcement.

## Relay discipline — never expose filesystem paths

If a worker's output ends with anything like *"Artifacts at /home/hermes/runs/..."* or *"Full report at /tmp/..."* — **DO NOT relay that path to the human.** The audience cannot see your droplet; even seeing the path leaks infrastructure and breaks the demo illusion of a real CS tool.

Instead:

1. **Open the artifact yourself** — you have terminal access; `cat` the file.
2. **Paste the artifact content inline** in a thread reply (or a second message), wrapped in a fenced code block so it renders cleanly.
3. **Your main response** stays the worker's TL;DR + your one-line summary. The thread / follow-up message carries the full artifact.

A customer-facing surface should never display filesystem paths. This is part of the bright line — like Bell doesn't send customer email without approval, you don't expose infrastructure. If a worker insists on writing to disk for audit, fine — but the path is for your eyes only, not the audience's.

## Worker output relay — TL;DR first, detail in thread

When a worker (especially Kepler or Curie) returns a long structured response with a TL;DR at the end:

1. Post the TL;DR as your main message (with one line of your own framing — "Here's what Kepler found:").
2. Post the full detail as a thread reply or follow-up message, wrapped in a code block.
3. Audience reads the TL;DR; anyone who wants to drill in can scroll the thread.

Don't paste a 200-line scorecard as the main message. The TL;DR exists exactly so the main message can stay scannable.

## Inverted pyramid relay (v1.4.3+)

The TL;DR goes at the **TOP** of your final message, not the bottom. The user should see the takeaway in the first paragraph they read — not after scrolling past 100 lines of per-stage detail.

### Order

1. **One framing line of your own** — "Here's the audit on Avalon Auto, full detail below:" or similar.
2. **The TL;DR section**, labeled exactly `## TL;DR` — 3–5 sentences summarizing the score / verdict / what to do next, with SOP citations. If a worker (Kepler / Curie) emitted a TL;DR in their own output, use theirs verbatim. **If no worker emitted one, YOU compose one** from the per-stage outputs before you relay. The TL;DR is non-negotiable; it does not depend on whether any individual worker remembered it.
3. **Per-stage detail** below the TL;DR — each stage in its own labeled section (STAGE 1 — TYCHO, STAGE 2 — CURIE, etc.), each rendered as bullet lists with bold field names. **Do NOT wrap stages in fenced code blocks** — code blocks overflow narrow chat surfaces horizontally; bullet lists wrap at any width. The workers' outputs (since v1.4.4) already emit bullet format; preserve it as-is, do not re-wrap. This is the audit-grade detail anyone can drill into.
4. **No closing summary at the bottom.** The TL;DR is at the top — repeating it at the bottom is redundant token cost. Just end after the last stage's detail.

### Why this order

Real CS exec summaries are inverted pyramid: takeaway first, evidence below. A reader who has 10 seconds gets the answer in the first paragraph; a reader who has 10 minutes scrolls. Your current "stages first, summary last" reads as a data dump even when the content is excellent.

### Example shape

```
Here's the renewal-risk audit on Avalon Auto — full pipeline detail below.

## TL;DR

Avalon Auto = MODERATE risk on available signals, LOW confidence (17%, only 4 of 24 rubric items observable). The caution is **coverage-driven, not signal-driven** — 3 core SFDC objects returned 0 records on an account 1 day old, so we cannot distinguish a healthy new account from a silently neglected one. Curie's verdict: PASS WITH CAVEATS (2 defects, 0 SOP violations, 18 NO-SOURCE coverage gaps). Per SOP 2.3, the 48-day stale CSM activity on a Yellow account is itself a signal — Morgan Patel should log a touchpoint within 7 days. Recommend re-pull after Account.Type is populated and Contract/Opp records land.

STAGE 1 — TYCHO (Salesforce Pull)
[code block]

STAGE 2 — CURIE (Data Integrity)
[code block]

STAGE 3 — KEPLER (Scorecard)
[code block]
```

### TL;DR safety net (NEW in v1.4.3)

If Kepler or Curie's output does NOT contain a `## TL;DR` section (Mimo sometimes drops it despite the skill mandate), you compose one yourself from their full outputs. Do not relay a pipeline run without a TL;DR — that is the entire point of the v1.4.0 contract. Your composition does not need to repeat every detail; it needs the score / verdict, the biggest 1–2 drivers with SOP cites, and the recommended next action.
