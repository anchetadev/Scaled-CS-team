# Status ledger format

Append-only JSONL. One JSON object per line, one line per event. Workers append; Leo reads, polls, and rotates rows to archive on close.

- **Active file:** `/home/hermes/botfather/status/active.jsonl` — only tasks not yet `done` or `escalated`.
- **Archive file:** `/home/hermes/botfather/status/archive.jsonl` — closed rows, append-only forever.

## Required fields on every entry

| Field | Type | Notes |
|---|---|---|
| `ts` | string | ISO 8601 UTC, e.g. `2026-05-31T14:22:07Z`. Workers use `date -u +%Y-%m-%dT%H:%M:%SZ`. |
| `task_id` | string | Unique per dispatch. Pipeline tasks use `<run_id>/<worker>` form, e.g. `run-2026-05-31-acme-4471/tycho`. |
| `worker` | string | The persona/profile name: `euclid`, `tycho`, `curie`, `kepler`, `hopper`, or `galileo`. |
| `event` | string | One of: `dispatched`, `ack`, `progress`, `poke`, `retry`, `blocker`, `done`, `escalated`. |
| `by` | string | `galileo` if Leo wrote the row, otherwise the worker name. Mirrors `worker` for worker-written rows. |

## Event-specific payloads

### `dispatched` (written by Leo)
```json
{"ts":"...","task_id":"...","worker":"tycho","event":"dispatched","by":"galileo",
 "prompt":"<the full -z prompt string>",
 "run_id":"<optional pipeline id>",
 "deadline_hint_seconds":1800}
```

### `ack` (written by worker, within 2 min of dispatched)
```json
{"ts":"...","task_id":"...","worker":"tycho","event":"ack","by":"tycho",
 "received_prompt":"<echo back the first 120 chars, for sanity>"}
```

### `progress` (written by worker, at most 10 min apart)
```json
{"ts":"...","task_id":"...","worker":"tycho","event":"progress","by":"tycho",
 "note":"<one short line — what just happened or what's in progress>",
 "pct_complete":35}
```
`pct_complete` is optional. `note` is required and must be a real change from the prior progress entry — "still working" is acceptable only if it's literally true (e.g. waiting on Salesforce response).

### `poke` (written by Leo)
```json
{"ts":"...","task_id":"...","worker":"tycho","event":"poke","by":"galileo",
 "reason":"silence_age_exceeded",
 "silence_age_seconds":720}
```

### `retry` (written by Leo)
```json
{"ts":"...","task_id":"...","worker":"tycho","event":"retry","by":"galileo",
 "reason":"silence_age_exceeded",
 "killed_pid":12345,
 "redispatched_prompt":"<the new -z prompt>",
 "retry_count":1}
```

### `blocker` (written by worker)
```json
{"ts":"...","task_id":"...","worker":"tycho","event":"blocker","by":"tycho",
 "reason":"<one line, plain English — what's blocking>",
 "needs":"<one line — what would unblock; e.g. 'sandbox creds', 'admin to grant API access'>"}
```
Workers MUST write a `blocker` and stop, never silently wait. Leo posts blockers to `#galileo-updates` immediately.

### `done` (written by worker)
```json
{"ts":"...","task_id":"...","worker":"tycho","event":"done","by":"tycho",
 "output_path":"/home/hermes/botfather/runs/<run_id>/tycho-output.md",
 "summary":"<one line — what the artifact is>"}
```
Prefer `output_path` for anything over ~30 lines; inline `output` field is acceptable for very short results.

### `escalated` (written by Leo)
```json
{"ts":"...","task_id":"...","worker":"tycho","event":"escalated","by":"galileo",
 "posted_to":"#galileo-updates",
 "reason":"<one line>"}
```
Final entry for the row. Move the whole row's history to `archive.jsonl`.

## Rotation

When a task closes (`done` or `escalated`), Leo:
1. Greps all lines for that `task_id` out of `active.jsonl`.
2. Appends them to `archive.jsonl`.
3. Rewrites `active.jsonl` without the closed rows.

Implementation note: file locking matters. Workers append concurrently. Use `flock` on writes (`flock -x active.jsonl -c 'echo "<json>" >> active.jsonl'`) or each worker writes to its own `active.<worker>.jsonl` shard and Leo merges on read. Shard-per-worker is simpler and avoids lock contention — recommended.

## Sanity checks Leo runs each poll

- Any row with `event: dispatched` but no `ack` within 120 s of `ts` → ack failure path.
- Any row whose latest entry is older than the cadence-defined threshold → run watchdog steps.
- Any row with `event: done` or `escalated` still in `active.jsonl` → rotate to archive.
- Any malformed line (JSON parse fails) → log a warning, skip the line, do not block on it.
