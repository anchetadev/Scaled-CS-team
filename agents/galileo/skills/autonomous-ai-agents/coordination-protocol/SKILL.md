---
name: coordination-protocol
description: "Track dispatched workers via a status ledger, run a watchdog on silence, and escalate to the team on a fixed cadence. Use whenever a worker is in flight."
version: 0.1.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [coordination, watchdog, handoff, supervisor, status, ledger, bot-father]
    related_skills: [agent-dispatch, escalation-handoff, slack-etiquette]
---

# Coordination Protocol

You dispatched a worker. Now what? This skill is the rules of engagement for everything *after* dispatch: how you know the worker is alive, when you intervene, when you pull the human in.

**The principle.** Workers don't promise check-ins. Workers *write ledger entries as they work*, and you *poll the ledger on your own cadence*. If a worker forgets to update, the watchdog catches it — never you, hours later, wondering why nothing happened.

This is the fix for the silent-bot problem. Don't trust worker self-discipline. Build the watchdog into yourself.

Load this skill whenever:
- You just dispatched a worker (set up tracking immediately).
- You haven't heard from an in-flight worker in a while (consult the watchdog rules, don't improvise).
- A worker reports a blocker or finishes (close the ledger entry, decide next step).

## The ledger

Every active dispatch has one row in **`/home/hermes/botfather/status/active.jsonl`** on the droplet. The worker appends entries to it; you read them.

Schema is documented in [`references/ledger-format.md`](references/ledger-format.md). Every entry has at minimum: `ts` (ISO 8601 UTC), `task_id`, `worker`, `event`, and an event-specific payload.

Required event sequence for every dispatch:

1. `dispatched` — *you* write this when you fire the worker (`<profile> -z "..."` succeeded).
2. `ack` — *worker* writes within **2 minutes** to confirm it received the work.
3. `progress` — *worker* writes at least every **10 minutes** while working (one per milestone; "still working on X" is fine if nothing new).
4. `blocker` — *worker* writes if it gets stuck (with `reason` and `needs`).
5. `done` — *worker* writes on completion (with `output_path` or inline `output`).

When a worker reports `done` or `blocker`, you move the row from `active.jsonl` to **`/home/hermes/botfather/status/archive.jsonl`** so the active file stays small and pollable.

Timings are in [`references/cadence.yaml`](references/cadence.yaml). Don't memorize numbers — read the file when you need to compute "is X overdue?"

## The watchdog (this is the actual fix)

After every dispatch, you own a polling obligation until the task closes. The watchdog is just: read the ledger, compute the last-event age per active task, act on thresholds.

**Polling cadence:** check the ledger every **5 minutes** while any task is active. Use a background tail/poll loop, a cron tick, or just remember to look — but do not wait for the worker to ping you.

**For each active task, compute `silence_age = now - last_entry.ts` and act:**

| `silence_age` | Action |
|---|---|
| < 10 min | Nothing. Worker is within cadence. |
| 10–20 min | **Soft poke.** Send the worker a one-line nudge: `<profile> -z "Status check on task <task_id> — please append a progress entry to /home/hermes/botfather/status/active.jsonl"`. Log a `poke` entry yourself. |
| 20–30 min | **Auto-retry.** Kill the worker process (`pkill -f "<profile>"` or whatever the wrapper exposes), redispatch the *original* prompt once, log a `retry` entry. This burns one retry. |
| > 30 min after retry, or any second silence | **Escalate.** Post to `#galileo-updates` per the escalation rules below. Stop polling this task — it's the human's now. |

You get **one** auto-retry per task. After that, escalate. Do not silently retry twice; that's the loop you're trying to avoid.

**`ack` is special.** If a worker doesn't `ack` within 2 minutes of `dispatched`, assume the wrapper choked on the prompt (the multi-line `-z` gotcha is the most common cause — see `agent-dispatch`). Don't soft-poke; immediately redispatch with a sanity-checked single-line prompt. If the second dispatch also doesn't `ack`, escalate as a tooling failure, not a worker failure.

## Reporting to the team

Cadence: **milestone-only**. You do not heartbeat to the team on a timer. You post to `#galileo-updates` (channel `C0B6PHEG60H`) on these events, and only these:

- **`dispatched`** — "On it: asking Tycho to pull Acme #4471's raw fields. Back in a few." (One line.)
- **`done`** — relay the worker's output per the `agent-dispatch` rules: one-line summary, then the verbatim output, then your commentary.
- **`blocker`** — "Tycho hit a blocker on #4471: `<reason>`. Needs: `<needs>`. Holding the pipeline until resolved." Tag the right human if the blocker names them.
- **`escalation`** (watchdog fired) — see the escalation rules below.

You do **not** post `ack`, `progress`, `poke`, or `retry` events to the team. Those live in the ledger; the team doesn't need to see the plumbing.

If the user explicitly asks "what's the status?" — read the ledger and answer from it, don't guess. If the ledger doesn't have a recent entry, say so honestly: "Last update from Tycho was 7 minutes ago: still pulling fields."

## Escalation (when the watchdog gives up)

When you escalate, post to `#galileo-updates` with exactly this shape:

```
Stalled task: <task_id> (<worker>)
Last activity: <ts of last ledger entry> (<silence_age> ago)
What it was doing: <one-line task summary>
What I tried: dispatched at <ts>; <ack/no-ack>; soft-poke at <ts>; retry at <ts>.
Last worker output: <paste or "none">
Need from human: <one of: kill it, redispatch with new prompt, debug the worker, fix tooling>
```

After posting, stop polling. The task is the human's responsibility until they redirect you. Move the row to `archive.jsonl` with `event: "escalated"`.

Full escalation decision tree is in [`references/escalation-playbook.md`](references/escalation-playbook.md) — read it when the situation is messier than the simple watchdog case (pipeline of multiple workers, worker partially completed before stalling, etc.).

## Pipeline handoff (multi-worker dispatch)

When a request crosses workers — e.g. *audit account #4471* = Euclid → Tycho → Curie → Kepler → Hopper — every worker gets its own `task_id` and its own ledger row. They are not one task with five owners; they are five tasks chained.

Rules:

1. **One worker at a time, in order.** Don't dispatch Tycho until Euclid's row reads `done`. Each handoff is an explicit step you take, not an automatic cascade — handoffs are where things go wrong silently, so make them deliberate.
2. **Carry forward the upstream artifact path.** Each downstream dispatch references the upstream worker's output file (absolute path). E.g., when you dispatch Curie, the prompt says `validate the data at /home/hermes/botfather/runs/<run_id>/tycho-output.md against the rubric at /home/hermes/botfather/rubrics/renewal-risk.md`. No paraphrasing of upstream output into a new prompt — pass the file.
3. **One watchdog per active worker.** If you have Euclid and a parallel-but-unrelated Tycho both running, you watchdog both independently. Stalls don't cascade — Tycho stalling doesn't affect a different Tycho task.
4. **Pipeline-level `task_id`.** When you start a pipeline, generate a `run_id` (e.g. `run-2026-05-31-acme-4471`) and tag every worker's `task_id` with it: `run-2026-05-31-acme-4471/euclid`, `.../tycho`, etc. Makes the whole pipeline greppable in one filter.

If a worker mid-pipeline blocks or escalates, do **not** auto-cancel the run. Post the escalation, hold the next worker, and wait for the human to say *redo*, *skip*, or *abort the run*.

## When you start work

On every fresh dispatch, do these in order, in one breath:

1. Generate `task_id` (and `run_id` if it's a pipeline).
2. Append a `dispatched` entry to `active.jsonl`.
3. Fire the worker (`<profile> -z "<single-line prompt>"`).
4. Post the heads-up to `#galileo-updates`.
5. Note the next watchdog check time (now + 5 min).

If you skip any of these, you don't have a watchdog — you have hope.

## Anti-patterns

- **Don't wait for the worker.** The whole point is you poll, not the worker pushes. Waiting passively is the bug.
- **Don't escalate without trying the soft poke and the one retry.** The watchdog has steps; use them.
- **Don't retry more than once silently.** Two silent retries → loop. Escalate after one.
- **Don't paraphrase the ledger to the team.** When the watchdog fires, paste the actual escalation block. The team needs the timestamps, not your vibes.
- **Don't leave done/blocked rows in `active.jsonl`.** Move them to archive immediately. A bloated active file is the same as no ledger.
- **Don't take over a stalled worker's work yourself.** That trains you (and the team) to expect Galileo-as-doer when a worker fails. Escalate; let the human decide rebuild vs. workaround.

## Memory

After each run, remember:
- Workers that stalled and why (pattern emerges → propose a SOUL fix to the worker, not a Leo workaround).
- Pipelines that completed clean end-to-end (those become reusable templates).
- Tooling failures (e.g. the `-z` multi-line gotcha) — surface to the user; those are not worker bugs.

Related:
- `agent-dispatch` — how to send the work (this skill is what happens after).
- `escalation-handoff` — how to hand a problem to the right human once you've escalated.
- `slack-etiquette` — channel/DM/thread discipline for the messages this skill triggers.
