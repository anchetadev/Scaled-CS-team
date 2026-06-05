---
name: execute-approval
description: "Execute an approved Operator-Surface approval row by dispatching its action_type to the right Salesforce-write handler. Bright-line enforced in code: refuses on status != approved or metadata.executed already true."
version: 0.1.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [customer-success, salesforce, execution, approval, controlled-executor, write]
    related_skills: []
---

# Execute Approval

Use this skill when Galileo dispatches you with an approval id — typically right after a human has clicked Approve in the Operator Surface and the webhook has fired. Your job is to inspect the approval, execute the registered handler, and report the outcome.

Load this when Galileo says things like "execute approval <id>", "run the approved change for <id>", "the human approved <id> — do the SF write", or hands you a webhook payload with an approval id.

## When NOT to use

- Galileo asks you to decide *whether* a change is right — that is upstream (Curie validates, Kepler interprets, the upstream agent proposes, the human approves). You only execute approved rows.
- Galileo asks you to *send a customer email* — that is Bell's `send-approved`. Refuse and route it.
- Galileo asks you to *change the approval status* — the Operator Surface UI owns that. You never write to `approvals.status`; you only write to `approvals.metadata.*` to record outcomes.
- Galileo asks you to do a Salesforce write that does NOT correspond to an approval row in Supabase — refuse. Every write must have an approval row that audits it. No write without a paper trail.

## Prerequisites

You need:
1. An approval id (UUID) — Galileo provides this from the webhook payload.
2. Your profile `.env` populated with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (always required) and `SALESFORCE_HOPPER_*` (optional — stub mode otherwise).

## Core method

### 1. Acknowledge in the ledger immediately

Per the operating contract, write an `ack` entry to your ledger shard before doing anything else. Galileo's watchdog is waiting on it.

### 2. Inspect the approval (read-only preview)

Run:

```bash
python3 ~/.hermes/profiles/hopper/bin/execute_approval.py inspect <approval_id>
```

This prints the approval's current state, the registered handler, the would-execute flag, and a list of blockers (if any). You do not need to interpret — the JSON is structured for both you and Galileo.

If `would_execute` is `false`, **stop here** and report the blockers verbatim to Galileo. Do NOT call `execute` — the bright line will refuse anyway, but you should not even ask.

Common blocker cases:
- `status is pending — needs to be approved` → the webhook fired prematurely; flag to Galileo.
- `metadata.executed is already true — idempotency guard` → already done; no-op is correct.
- `action_type 'X' has no registered handler` → upstream agent is filing approvals of a type Hopper does not know how to execute. Flag this to Galileo for the upstream fix.

### 3. Execute

If `inspect` shows `would_execute: true`, run:

```bash
python3 ~/.hermes/profiles/hopper/bin/execute_approval.py execute <approval_id>
```

This runs the bright-line checks itself (you cannot bypass them; the script enforces them in code). On success it returns:

```json
{
  "ok": true,
  "approval_id": "...",
  "action_type": "...",
  "outcome": "<human-readable string>",
  "sf_record_id": "<SF id or STUB-... in stub mode>",
  "sf_object": "..."
}
```

On bright-line refusal (status not approved):

```json
{
  "ok": false,
  "refused": true,
  "reason": "bright_line",
  "detail": "status is 'pending' — Hopper executes only when approved"
}
```

This is **expected behavior**, not a failure. Report it verbatim to Galileo; he will know it means the human has not approved yet.

### 4. Note stub mode if active

If `sf_record_id` starts with `STUB-`, the script ran in stub mode (no SF creds). The approval's metadata in Supabase now records a successful "execution" but no actual SF write occurred. **Tell Galileo this explicitly** — the audience needs to know whether the demo just performed a real write or a simulated one.

### 5. Write the ledger `done` entry

Per the worker contract, write a `done` entry with:
- `summary`: one-line outcome string (use the `outcome` field from the script's JSON)
- `output_path` or inline `output`: the full JSON the script returned

Galileo polls the ledger; he picks up your `done` and relays.

## Output structure (relay to Galileo)

Bullet list with bold keys, per the v1.4.4 wrap-safe format:

```markdown
- **Approval:** `<approval_id>`
- **Action type:** <create_task / update_field / ...>
- **Verdict:** EXECUTED / REFUSED (bright-line) / NO-OP (already executed) / BLOCKED (no handler)
- **Outcome:** <one-line description of what happened in SF, including the SF record id>
- **Mode:** live / stub
- **Audit fields written:** `metadata.executed`, `metadata.executed_at`, `metadata.executed_by: "hopper"`, `metadata.sf_record_id`, `metadata.outcome`

---

## TL;DR (for Galileo to relay)

Approval `<id>` (<action_type>): EXECUTED / REFUSED / NO-OP. <One sentence describing what changed in Salesforce or why nothing changed.> Audit fields written to Supabase. <If stub mode: "Stub mode — no real SF write occurred.">
```

The TL;DR is mandatory. Two sentences max. Galileo will post it; the bullet detail is for audit.

## Discipline

- **You do not approve your own writes.** The Operator Surface owns approvals. If Galileo dispatches you with an unapproved id, the script refuses. Do not try to convince Galileo otherwise.
- **You do not write outside the WRITE_ALLOWLIST.** `bin/sf_writer.py` refuses at the Python layer. If a handler raises a `PermissionError`, that is correct behavior — the allowlist caught something that should not have been attempted.
- **You always inspect before you execute.** Even though `execute` runs the same checks, inspecting first lets Galileo see (and the audit log show) that you previewed before acting.
- **You never edit `approvals.status`.** Only the Operator Surface UI sets that. You write only to `approvals.metadata.*`.
- **You report bright-line refusals as outcomes, not errors.** A refused write is the system working correctly. Pass the refusal JSON through verbatim.
- **You announce stub mode explicitly.** If the SF write was simulated, the user must know. Do not let stub `STUB-...` ids look like real ones.

## Memory

After each run, remember:
- Action types that came in and what the typical `proposed_value` shape looked like — sharpens future `inspect` previews.
- Recurring `execution_blocker` patterns (missing fields, action_types not yet registered) — surface to Galileo so the upstream gets fixed.
- Whether you saw any `refused: bright_line` outcomes — those are signal that an upstream system flow tried to skip the human approval. Worth watching.
