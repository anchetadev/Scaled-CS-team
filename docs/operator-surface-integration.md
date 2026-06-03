# Operator Surface integration

The **Operator Surface** is a separate Supabase-backed application that holds the human-approval queue for the Scaled CS platform. Bell (and any future Hermes agent that needs human sign-off before acting on a customer) files draft actions into this queue; a human approves or rejects them in the Operator Surface UI; the Hermes agent then either executes the approved action or stops.

This doc covers the integration contract: how Bell talks to the Operator Surface, what tables he touches, the lifecycle of an approval, and how the bright line — "agent drafts; human approves; agent executes only after approval" — is enforced.

This repo does **not** ship the Operator Surface app itself. It only documents what an agent on this side of the boundary needs to know to integrate.

## The boundary

```
   Hermes side                                Operator Surface side
   ───────────                                ──────────────────────
                  service-role key
   Bell  ────────────────────────────▶  Supabase (PostgREST)
   (propose, poll, send-approved)         agents, agent_runs, approvals
                                                       │
                                                       ▼
                                              CSM (browser UI)
                                              approve / reject / edit
```

Two distinct identities:

- **Hermes-side writes** use the Supabase **service-role key** (bypasses Row-Level Security). Bell uses this to insert approval rows, mark them executed, and read status. The key never leaves the Hermes droplet — it is not exposed to any browser or end-user code.
- **CSM-side writes** (decisions on approvals) go through the Operator Surface UI's authenticated session and are subject to RLS. The CSM cannot bypass approvals; the agent cannot pretend to be a CSM.

The separation is the safety model. Bell cannot self-approve because the only credential he holds (service-role) is *trusted but auditable* — every PATCH that flips `status` from `pending` to `approved` records `decided_by` (the CSM's `auth.users.id`), and the Operator Surface UI is the only thing that performs that PATCH in production.

## Tables Bell touches

| Table | Bell's access | Used for |
|---|---|---|
| `agents` | read + insert (idempotent upsert by `slug`) | Register Bell's runtime identity in the agent registry |
| `agent_runs` | insert | Group a batch of related approvals; one row per dispatch |
| `approvals` | insert + read + PATCH (metadata only in production) | The actual draft/decision/execution lifecycle |

Bell never writes to `auth.users`, RLS policy tables, or anything else. The `approve` subcommand in `bin/propose_email.py` is a demo helper only — production flow puts the CSM's decision through the Operator Surface UI, not through Bell.

## The `approvals` row shape

```jsonc
{
  "id": "<uuid>",
  "agent_id": "<uuid pointing at agents.id>",
  "agent_run_id": "<uuid pointing at agent_runs.id>",
  "action_type": "send_reply",            // Bell only uses send_reply today
  "target_record_type": "opportunity",    // Salesforce Opportunity Id below
  "target_record_id": "006...",
  "current_value": null,
  "proposed_value": {                     // the draft itself
    "channel": "email",
    "to": ["customer@example.com"],
    "subject": "Re: our chat yesterday",
    "body_md": "Hi Jane, ...",
    "attachments": []
  },
  "rationale": "Follow-up drafted by Bell from the meeting transcript.",
  "status": "pending",                    // pending → approved | rejected
  "decided_by": null,                     // CSM's auth.users.id when approved
  "decided_at": null,                     // timestamp of decision
  "metadata": {
    "account": "Pyramid Construction",
    "drafted_by": "bell",
    "risk_level": "med",
    "executed": false,                    // Bell flips this true on send
    "sent_via": null,                     // "gmail" once sent
    "gmail_message_id": null              // Gmail message id for audit
  }
}
```

## Lifecycle (the bright line in motion)

```
  Bell                             Operator Surface             CSM (browser)
   │                                                                  │
   │  propose (POST /approvals)                                       │
   │  status=pending, metadata.executed=false                         │
   │  ───────────────────────────────────▶                            │
   │                                       polls / shows in queue ───▶│
   │                                                                  │
   │                                       ◀─── CSM reviews,          │
   │                                            optionally edits      │
   │                                            proposed_value,       │
   │                                            clicks Approve        │
   │                                                                  │
   │                                       PATCH /approvals/<id>      │
   │                                       status=approved,           │
   │                                       decided_by=<csm uid>,      │
   │                                       decided_at=now()           │
   │                                                                  │
   │  send-approved <id>                                              │
   │  ─────▶ GET status; if != approved → REFUSE (bright line)        │
   │  ─────▶ Gmail API send (from CSM's own Gmail)                    │
   │  ─────▶ PATCH metadata.executed=true,                            │
   │          sent_via="gmail", gmail_message_id="..."                │
   │                                                                  │
```

The bright line is enforced at three layers:

1. **Bell's SOUL** tells him to draft and propose, never to send unilaterally.
2. **`bin/propose_email.py send-approved`** queries `status` first and refuses to send when it isn't `approved`. This is code, not prompt.
3. **The send itself goes through the CSM's Gmail OAuth token**, not Bell's. If the CSM revokes the token, Bell loses the ability to send entirely — regardless of any approval state.

## Subcommands of `bin/propose_email.py`

| Subcommand | Direction | Notes |
|---|---|---|
| `propose <json>` | Hermes → OpSurface | Insert a pending approval. Idempotent in the agent registry (upsert by slug) but **not** idempotent in approvals — calling twice files two drafts. |
| `poll <id>` | Hermes → OpSurface (read) | Check current status. |
| `approve <id>` | Hermes → OpSurface (PATCH) | **Demo only.** Simulates the CSM's decision. Production never calls this. Requires `OPERATOR_SURFACE_CSM_UID` set. |
| `send-approved <id>` | Hermes → Gmail (with status guard) | The bright-line execution. Refuses on non-approved status; sends via Gmail; stamps metadata.executed. |
| `mark-executed <id>` | Hermes → OpSurface (PATCH) | Called by `send-approved` internally; usually not invoked directly. |

## Provisioning checklist

To wire Bell into an Operator Surface instance:

1. **Get the project URL and service-role key** from the Operator Surface Supabase project (Settings → API). Put them in `~/.hermes/profiles/bell/.env` as `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
2. **Decide the agent slug.** Default is `renewal-outreach` (a legacy name that maps to Bell's email-drafting). Override via `OPERATOR_SURFACE_AGENT_SLUG` if your Operator Surface uses a different slug.
3. **Verify the schema.** The Operator Surface must already have `agents`, `agent_runs`, and `approvals` tables with the columns described above. If not, that's a deployment of the Operator Surface app itself, not something this repo handles.
4. **(Demo only)** If you'll run `approve` from the Hermes side for testing, set `OPERATOR_SURFACE_CSM_UID` to a real `auth.users.id` in the same Supabase project. In production, leave it unset.
5. **Authorize Gmail.** Run the `productivity/google-workspace` skill's OAuth flow once for the CSM's account, with scopes `gmail.readonly + gmail.send + gmail.modify`. The token lands at `~/.hermes/google_token.json` (default location).

After provisioning, smoke-test end-to-end with a throwaway opportunity:

```bash
# 1. Bell drafts
bell -z "Draft a recap email for opportunity 006xxx using the transcript at /tmp/test-transcript.txt"

# 2. CSM approves in Operator Surface UI (or for demo: `propose_email.py approve <id>`)

# 3. Bell sends
bell -z "Send approval <id> if it's approved"
```

A successful run leaves: a Chatter post on the opp (via `sf_chatter.py`), an `approvals` row with `status=approved` and `metadata.executed=true`, and a sent email in the customer's inbox originating from the CSM's address.
