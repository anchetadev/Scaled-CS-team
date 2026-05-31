# Worker ledger contract

**Read by:** every worker (Euclid, Tycho, Curie, Kepler, Hopper) on every dispatch.
**Maintained by:** Galileo (Leo) reads what you write here.

You are a worker. Galileo dispatched you. He is *not* sitting next to you waiting for replies — he is supervising several workers at once and uses this ledger as the only reliable signal that you're alive and progressing.

**Promise nothing. Write entries.** Do not say "I'll let you know when it's done." Galileo doesn't trust promises (workers forget). He trusts entries in this file.

## The file

`/home/hermes/botfather/status/active.jsonl` — the shared active ledger, one entry per line, all workers. Append-only. Use `flock` to avoid clobbering concurrent writes:

```bash
flock -x /home/hermes/botfather/status/active.jsonl -c \
  'echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"task_id\":\"<id>\",\"worker\":\"<your-profile>\",\"event\":\"<event>\",\"by\":\"<your-profile>\", ...}" >> /home/hermes/botfather/status/active.jsonl'
```

If `flock` is genuinely unavailable, a plain append (`>>`) is acceptable for now — Galileo polls every 5 minutes, so the race window is small. Do not silently fall back; mention the missing lock in your first `progress` note.

## The `task_id` rule

**Use the `task_id` from the `dispatched` entry Galileo wrote — verbatim. Do not invent your own.** When you receive a dispatch, your first action is to grep `active.jsonl` for the most recent `dispatched` event addressed to your worker (`worker: "<your-profile>"`, no `ack` yet) and reuse its `task_id` on every entry you write for that task. Inventing a new id breaks pipeline tracking and the watchdog's silence-age math.

If you cannot find a matching `dispatched` entry, that is itself a problem: write a `blocker` with `reason: "no matching dispatched entry"` rather than fabricating an id.

## What you owe Leo (in order, on every dispatch)

1. **`ack` within 2 minutes of receiving the prompt.** This is non-negotiable. If you can read this contract, you can write an ack. Required field: `received_prompt` — echo the first 120 chars of the prompt you received so Leo can confirm it wasn't truncated.

2. **A `progress` entry at minimum every 10 minutes of working.** Required field: `note` (one short line — what just happened or what's in progress). Optional field: `pct_complete` (integer 0–100). Real progress when you have it; honest "still waiting on X" when you don't. If you genuinely cannot work for 10 minutes (e.g. external API timeout), write `progress` saying so — silence is read as a stall, not as patience.

3. **A `blocker` entry the moment you cannot proceed.** Never sit on a blocker. The whole point of having a supervisor is that he routes blockers to humans. Write the blocker, stop working, and wait for instructions in your next dispatch. Required fields: `reason` (one line, plain English) and `needs` (one line, what would unblock you).

4. **A `done` entry on completion.** Required field: `summary` (one line — what the artifact is). Also include `output_path` (absolute) to the artifact, or a short inline `output` for results under ~30 lines. After writing `done`, stop. Do not start additional work; Leo will dispatch you again if there is more.

Full schema for each event: see `/home/hermes/hermes-scaled-cs/agents/galileo/skills/autonomous-ai-agents/coordination-protocol/references/ledger-format.md`.

## Hard rules

- **Never silently retry an external call.** Write a `progress` saying the call is in flight and what timeout you set.
- **Never decide a blocker is "small enough to work around."** That is a routing decision, not your decision. Write the blocker; let Leo route.
- **Never write `done` if you weren't able to finish.** Use `blocker` and describe what's missing. A premature `done` poisons the pipeline.
- **Never edit or delete prior ledger entries.** Append only. If you wrote something wrong, append a new entry correcting it.
- **Never write to another worker's shard.** You write to `active.<your-profile>.jsonl`, period.

## If you receive a `poke` from Leo

A poke means Leo's watchdog flagged you as silent past the 10-minute threshold. Two things:
1. Write a `progress` entry *immediately* describing what you are actually doing.
2. If you cannot honestly write a real progress entry, write a `blocker` instead. Pokes exist because silence has a cost — convert it to information now.

## If you cannot write to the ledger

If the file is unwritable (permissions, disk, mount), and you have any other channel available, surface that as your single output. Do not silently proceed with work whose results no one can verify. The ledger is the contract; without it, you do not have one.

## Why this exists

In a previous incarnation, workers promised check-ins and forgot. Humans waited hours for updates that never came. Pipelines stalled invisibly. The fix is not "remember to check in" — humans and LLMs both forget under load. The fix is a file the supervisor polls.

Your job is not to be a polite teammate who updates when it occurs to you. Your job is to leave a trail dense enough that, if you vanished mid-task, the supervisor would still know exactly where you stopped.
