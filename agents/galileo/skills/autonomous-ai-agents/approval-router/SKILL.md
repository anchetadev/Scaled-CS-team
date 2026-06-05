---
name: approval-router
description: "Route an Operator-Surface approval to the right executor (Bell for customer-facing email, Hopper for Salesforce writes). Triggered by the webhook from Operator-Surface when a human clicks Approve."
version: 0.1.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [approval, routing, webhook, operator-surface, dispatch, controlled-executor, bright-line]
    related_skills: [agent-dispatch, coordination-protocol]
---

# Approval Router

Use this skill when you receive a request to **execute an approval** — typically from the Operator-Surface webhook ("Execute approval `<id>` — webhook from Operator-Surface"), or from a human asking you to run an approved item.

Your job is **routing**, not execution. You read the approval, decide which worker owns its action type, and dispatch the right one. You do not write to Salesforce; you do not send email. Those are Hopper's and Bell's jobs respectively.

Load this when you see prompts like *"Execute approval `<uuid>`"*, *"Run approved item `<uuid>`"*, *"Webhook fired for approval `<uuid>` — handle it"*, or any variant where an approval id is the central object.

## The routing table (this IS the policy)

```
action_type             → worker        → command
─────────────────────────────────────────────────────────────────────────
send_reply              → bell          → bell -z "send-approved <id>"
send_email              → bell          → bell -z "send-approved <id>"
create_task             → hopper        → hopper -z "execute approval <id>"
update_field            → hopper        → hopper -z "execute approval <id>"
change_health_band      → hopper        → hopper -z "execute approval <id>"
add_save_plan           → hopper        → hopper -z "execute approval <id>"
flag_data_gap           → hopper        → hopper -z "execute approval <id>"
chatter_post            → bell          → bell -z "post chatter for approval <id>" (if gated; otherwise Bell auto-posts)
─────────────────────────────────────────────────────────────────────────
(anything else)         → REFUSE — unknown action_type, flag to user, do not dispatch blind
```

**Bell handles communications** (email + chatter). **Hopper handles Salesforce writes** (everything else). Galileo himself never executes — he routes.

## When NOT to use

- The user asks about an approval's *content* or *meaning* (what does it propose, what's the rationale) — that's reading, not routing. Use the agent-dispatch skill to dispatch Kepler or read directly from Supabase. Don't dispatch the executor.
- The user asks you to *change* an approval's status (approve / reject from the chat) — refuse. The Operator-Surface UI owns status changes; you only act on what's already approved there.
- The user asks you to dispatch Hopper or Bell directly without an approval id — that's just regular dispatch. Use the agent-dispatch skill, not this one.
- The webhook arrives but the action_type is missing or unknown — refuse to route. Don't guess.

## Core method

### 1. Acknowledge in ledger

Per the operating contract, append an `ack` entry to your ledger shard before doing anything. The watchdog is waiting.

### 2. Look up the approval

Read the approval row from Supabase to get `action_type` + `status` + `metadata.executed`. Two ways:

**Option A — call Hopper's `inspect` (read-only):**

```bash
python3 ~/.hermes/profiles/hopper/bin/execute_approval.py inspect <approval_id>
```

Returns JSON with `action_type`, `status`, `would_execute`, `blockers`. Hopper's `inspect` is safe to call even for `send_reply` action_types — it's pure read, no side effects, no handler dispatch.

**Option B — direct Supabase read** (no Hopper involvement):

```bash
python3 -c '
import os, json, urllib.request
env = {}
for line in open(os.path.expanduser("~/.hermes/profiles/galileo/.env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k] = v.strip()
url = env["SUPABASE_URL"].rstrip("/") + "/rest/v1/approvals?id=eq.<APPROVAL_ID>&select=id,action_type,status,metadata"
r = urllib.request.Request(url); r.add_header("apikey", env["SUPABASE_SERVICE_ROLE_KEY"]); r.add_header("Authorization","Bearer "+env["SUPABASE_SERVICE_ROLE_KEY"])
print(urllib.request.urlopen(r).read().decode())'
```

Option A is preferred — Hopper's `inspect` already returns the right shape and lists blockers. Option B is the fallback when Hopper isn't available.

### 3. Pre-flight checks (the bright line lives downstream, but check anyway)

Before dispatching:

- **`status == "approved"`** — if pending/rejected, refuse. Tell the user; don't dispatch.
- **`metadata.executed`** is not `true` — if already executed, no-op. Tell the user the previous outcome from `metadata.outcome`.
- **`action_type`** is in the routing table — if it's not, refuse and flag to the user. NEVER dispatch blindly to an unknown action_type.

These checks ARE also enforced by Hopper / Bell themselves (in code), so dispatching an unapproved id will get a clean `bright_line` refusal — but checking here saves a worker spawn for no reason.

### 4. Dispatch

Pick the worker from the routing table. Use the standard dispatch pattern from the `agent-dispatch` skill:

```bash
# Salesforce-side action
hopper -z "execute approval <id>"

# Communications-side action
bell -z "send-approved <id>"
```

Single-line `-z` per the dispatch gotcha. Wait for the worker's JSON response.

### 5. Relay

The worker returns JSON. Per the v1.4.4 wrap-safe format, relay it as a bullet list:

- **Approval:** `<id>`
- **Action type:** `<action_type>`
- **Routed to:** `bell` / `hopper`
- **Verdict:** EXECUTED / REFUSED (bright_line) / NO-OP (already executed) / BLOCKED
- **Outcome:** `<one-line description from the worker's outcome field>`
- **Mode:** live / stub *(if Hopper indicates stub mode)*
- **Audit fields written:** `metadata.executed`, `metadata.executed_at`, `metadata.executed_by`, `metadata.sf_record_id` *(if Hopper)*

End with the mandatory TL;DR section.

### 6. Ledger `done`

Append a `done` entry per the worker contract, with the outcome JSON as the inline `output`.

## Output structure

```markdown
Routed approval `<id>` to <worker>. <One-line summary>.

- **Approval:** `<id>`
- **Action type:** `<action_type>`
- **Routed to:** `<worker>`
- **Verdict:** <EXECUTED / REFUSED / NO-OP / BLOCKED>
- **Outcome:** <human-readable string from worker's outcome>
- **Mode:** live / stub
- **Audit:** `metadata.executed`, `metadata.executed_by: "<worker>"`, `metadata.sf_record_id: <id-or-null>`

---

## TL;DR (for the human)

Approval `<id>` (<action_type>): <EXECUTED / REFUSED / NO-OP>. <Plain-English one-sentence summary of what actually happened in SF or what was sent via email, including the SF record id or Gmail message id where applicable.> <If stub mode: "Stub mode — no real SF write occurred.">
```

The TL;DR is mandatory and is exactly what gets posted back to the Slack channel or the human-facing surface. Keep it to 2 sentences max.

## Discipline

- **You route; you do NOT execute.** Salesforce writes are Hopper's. Email sends are Bell's. Even if the action looks tiny, route it — never inline a write yourself.
- **The routing table is the policy.** Don't improvise routing for an action_type that isn't in the table — refuse and flag for the action-type registry to be extended (which means updating both Hopper's `HANDLERS` and this skill's table together).
- **You never modify `approvals.status`.** Only the Operator-Surface UI flips status. You read it; you don't write it.
- **Bright-line refusals are normal output, not failures.** If Hopper returns `{"refused": true, "reason": "bright_line"}`, that means the system worked correctly. Relay it verbatim with the same TL;DR shape.
- **You never draft `send_reply` approvals yourself.** Bell drafts those. You only route the ones that already exist as `approved` rows in Supabase.
- **You never draft Salesforce-write approvals via the executor.** That's what the `propose-sf-action` flow is for (separate skill, separate `propose_action.py` bin script). The router only handles existing approvals — it doesn't create them.

## Bell vs Hopper at a glance

| Concern | Bell | Hopper |
|---|---|---|
| **Domain** | Communications (email, Chatter) | Salesforce writes (Task, field updates, risk flags) |
| **Drafts approvals?** | Yes — for `send_reply` only | No — drafted upstream by Galileo |
| **Executes approvals?** | `send_reply` only | Everything else in the action_type table |
| **Credentials** | Gmail OAuth + CS Seeder for Chatter | SF Hopper Executor Connected App (write scope) |
| **Bright-line guard** | `propose_email.py send-approved` refuses on `status != "approved"` | `execute_approval.py execute` refuses the same way |

If you find yourself wondering "is this Bell or Hopper?" — ask: *does this touch a customer-facing communication?* Yes → Bell. No → Hopper.

## Memory

After each run, remember:
- Approval action_types you've routed and how often — surfaces patterns (e.g., "create_task is 90% of the queue, mostly from renewal-readiness work").
- Any action_type you refused because it wasn't in the routing table — these are signal to extend the table OR to push back on the upstream agent that filed it.
- Worker outcomes that returned `refused: bright_line` — these mean an upstream system tried to skip the human approval. Worth watching.
