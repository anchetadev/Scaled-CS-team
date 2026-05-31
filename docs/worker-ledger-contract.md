# Worker ledger contract

**Read by:** every worker (Euclid, Tycho, Curie, Kepler, Hopper) on every dispatch.
**Maintained by:** Galileo (Leo) reads what you write here.

You are a worker. Galileo dispatched you. He is *not* sitting next to you waiting for replies — he is supervising several workers at once and uses this ledger as the only reliable signal that you're alive and progressing.

**Promise nothing. Write entries.** Do not say "I'll let you know when it's done." Galileo doesn't trust promises (workers forget). He trusts entries in this file.

## The file

`/home/hermes/botfather/status/active.<your-profile>.jsonl` — your own shard, one entry per line. Append-only. Use:

```bash
echo '{"ts":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'","task_id":"<id>","worker":"<your-profile>","event":"<event>","by":"<your-profile>", ...}' \
  >> /home/hermes/botfather/status/active.<your-profile>.jsonl
```

If `flock` is available, prefer:
```bash
flock -x /home/hermes/botfather/status/active.<your-profile>.jsonl -c '...append...'
```

## What you owe Leo (in order, on every dispatch)

1. **`ack` within 2 minutes of receiving the prompt.** This is non-negotiable. If you can read this contract, you can write an ack. Echo the first 120 chars of the prompt you received so Leo can confirm it wasn't truncated.

2. **A `progress` entry at minimum every 10 minutes of working.** Real progress when you have it; honest "still waiting on X" when you don't. If you genuinely cannot work for 10 minutes (e.g. external API timeout), write `progress` saying so — silence is read as a stall, not as patience.

3. **A `blocker` entry the moment you cannot proceed.** Never sit on a blocker. The whole point of having a supervisor is that he routes blockers to humans. Write the blocker, stop working, and wait for instructions in your next dispatch. Required fields: `reason` (one line, plain English) and `needs` (one line, what would unblock you).

4. **A `done` entry on completion.** Include `output_path` (absolute) to the artifact, or a short inline `output` for results under ~30 lines. After writing `done`, stop. Do not start additional work; Leo will dispatch you again if there is more.

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
