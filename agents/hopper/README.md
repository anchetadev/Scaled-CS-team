# Hopper — Controlled Executor

Hopper is the Salesforce-write agent for the Scaled CS platform. Named for **Grace Hopper** — the careful, precise debugger — he writes changes to Salesforce only after a human has approved them in the Operator Surface, and refuses any other path.

## Role

The Operator Surface owns approvals. Hopper owns execution. The two are deliberately separate identities so neither can do the other's job:

1. An agent (Bell, Curie, Hopper himself for retroactive proposals) files an approval row in the Operator Surface Supabase with `status: pending`.
2. A human reviews and decides in the Operator Surface UI. The UI flips `status` to `approved` or `rejected`.
3. On approve, the Operator Surface webhooks the Hermes droplet. Galileo receives, dispatches Hopper with the approval id.
4. Hopper reads the approval, **refuses if `status != approved` or if `metadata.executed` is already `true`**, then performs the Salesforce write.
5. Hopper stamps the outcome back into the approval row.

## The bright line, enforced in code

`bin/execute_approval.py` is the gate. It runs three checks before any handler fires:

1. `approvals.status == "approved"` — else refuses with `{"refused": true, "reason": "bright_line"}`.
2. `approvals.metadata.executed` is not already `true` — else no-ops with `{"noop": true, "reason": "idempotent_skip"}`.
3. The `action_type` has a registered handler — else refuses with a clear "no handler registered" error and stamps an `execution_blocker` on the approval.

Same pattern Bell uses for `send-approved`. If you defeat the prompt, the script still refuses. If you defeat the script, the SF Connected App's permission set still refuses. Three layers.

## Action types

Registered in `HANDLERS` at the top of `bin/execute_approval.py`. Easy to extend — one function + one registry line.

| `action_type` | What it does | SObject |
|---|---|---|
| `create_task` | Creates a Task related to the target record | Task |
| `update_field` | Generic single-field update (proposed_value carries `field` + `new_value`) | Account / Opportunity / Contact |
| `change_health_band` | Sets `Account.Health_Band__c` | Account |
| `add_save_plan` | Sets `Account.CSM_Save_Plan__c` | Account |
| `flag_data_gap` | Creates a `Risk_Flag__c` record | Risk_Flag__c |

`send_reply` is **not** handled by Hopper — that's Bell. Galileo routes by action_type.

## Stub mode

If `SALESFORCE_HOPPER_INSTANCE_URL` / `_CONSUMER_KEY` / `_CONSUMER_SECRET` are absent from `~/.hermes/profiles/hopper/.env`, `bin/sf_writer.py` runs in stub mode — returns deterministic fake SF record ids prefixed `STUB-`. This lets the full webhook → Galileo → Hopper → Supabase round trip be smoke-tested before the Connected App is provisioned.

Stub-mode results explicitly include `"stub": true` and `"note": "no SF creds configured; returning stub success"` so nothing accidentally relies on a fake id thinking it's real.

## Connectors

| File | What |
|---|---|
| `bin/sf_writer.py` | Write-scope SF client (OAuth Client Credentials). WRITE_ALLOWLIST at the top of the file defines exactly which SObject + field combinations Hopper can touch. Refuses outside-the-allowlist writes at the Python layer before the SF API is ever called. |
| `bin/execute_approval.py` | The bright-line wrapper. `execute <id>` enforces the three checks above and dispatches to the right handler. `inspect <id>` is read-only — prints what would happen and what's blocking, useful for Galileo to preview. `list-handlers` lists registered action_types. |

Both scripts ship executable and read credentials from `~/.hermes/profiles/hopper/.env`.

## Installation

```bash
hermes profile install ./agents/hopper --name hopper --alias
```

Then make the bin scripts executable in the live profile (the installer should preserve mode, but belt-and-suspenders):

```bash
chmod +x ~/.hermes/profiles/hopper/bin/*.py
```

## Configuration

Set in the `hopper` profile `.env`:

```bash
OPENROUTER_API_KEY=...

# Operator Surface approval queue (same Supabase Bell uses)
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...

# Salesforce write connector (Hopper Executor Connected App).
# Optional — until set, sf_writer.py runs in stub mode and returns fake ids.
SALESFORCE_HOPPER_INSTANCE_URL=https://yourco.develop.my.salesforce.com
SALESFORCE_HOPPER_CONSUMER_KEY=...
SALESFORCE_HOPPER_CONSUMER_SECRET=...
```

## Salesforce Connected App setup

The Connected App's Run-As user should hold a permission set scoped to exactly the SObjects + fields in `bin/sf_writer.py`'s `WRITE_ALLOWLIST`. As of v1.2.0:

| SObject | Fields |
|---|---|
| Account | Health_Band__c, CSM_Save_Plan__c, Customer_Sentiment__c, Meeting_Cadence__c, Description |
| Opportunity | StageName, CloseDate, Amount, CSM_Forecast__c, Description |
| Contact | Title, Email, Description |
| Task | Subject, ActivityDate, Priority, Status, WhatId, OwnerId, Description |
| Event | Subject, ActivityDate, StartDateTime, EndDateTime, WhatId, OwnerId |
| Risk_Flag__c | Account__c, Risk_Type__c, Status__c, Description__c |
| FeedItem | ParentId, Body |

Any change to the allowlist should be paired with a permission-set change on the Salesforce side. Drift between the two is fine in the safe direction (SF more restrictive than allowlist) but dangerous in the unsafe direction (allowlist permits something SF will reject mid-flight, surfacing as an error that operators have to debug).

## Access matrix

| Capability | Status |
|---|---|
| Read account data | no (that is Tycho's job) |
| Write to Salesforce | yes, allowlisted objects/fields only |
| Send customer email | no (that is Bell's job) |
| Decide which change to make | no (Galileo + the upstream agent decide) |
| Validate data correctness | no (Curie does that) |
| Approve approvals | **never** — approval lives in the Operator Surface, not in Hopper |

## Related docs

- [`docs/operator-surface-integration.md`](../../docs/operator-surface-integration.md) — the integration contract Bell + Hopper share
- [`SOUL.md`](SOUL.md) — Hopper's persona and the explicit bright-line statement
- Bell's `propose_email.py send-approved` — the prior-art template Hopper's `execute_approval.py` mirrors
