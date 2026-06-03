# Bell — Communications Specialist

Bell is the communications agent for the Scaled CS platform. Named for **Alexander Graham Bell** — who turned distance into conversation — he takes the busywork out of a CSM's post-meeting follow-up so the human keeps their time for relationship work.

## Role

Bell sits *parallel to* the renewal-risk pipeline, not in it. He runs the **post-meeting workflow**:

1. **Read the meeting record** — transcript or recap from the CSM's Gmail.
2. **Identify the Opportunity** — confirm which Salesforce account/opp the meeting was about.
3. **Post an internal Chatter summary** — factual, bulleted, auto. Saves the CSM the typing-up tedium and keeps the account history honest.
4. **Draft a customer follow-up email** — warm, in the CSM's voice, with `[CSM: confirm X]` placeholders for anything unstated.
5. **File the draft as a pending approval** in the Operator Surface. **Bell stops here.** The customer email is NEVER sent without explicit CSM approval.
6. **On approval, send from the CSM's Gmail** and stamp the approval executed.

## The bright line (enforced in code, not just prompt)

- **Internal Chatter is Bell's to post automatically.** Low-risk, internal record-keeping on the Opportunity.
- **A customer-facing email is NEVER Bell's to send.** He drafts and files for approval. The send only happens after a human signs off — and goes from the CSM's own Gmail, not Bell's identity.

`bin/propose_email.py send-approved <id>` enforces this at the code level: it queries the approval row and refuses to send if `status != "approved"`. This is the same boundary as `Tycho reads / Hopper writes` — a separate identity for the action that carries customer-facing consequences.

## Connectors

This distribution ships two helper scripts at `bin/`:

| Script | What it does | Auth |
|---|---|---|
| `bin/sf_chatter.py` | Posts a `FeedItem` to a Salesforce record (the auto Chatter summary in step 3) | OAuth Client Credentials against the CS Seeder External Client App (admin role — Chatter writes require it) |
| `bin/propose_email.py` | Files and manages approvals in the Operator Surface (steps 5–6) | Supabase service-role key (Hermes side only; bypasses RLS) |

Gmail read/send (steps 1 and 6) uses the bundled `productivity/google-workspace` skill's `google_api.py`, with an OAuth token authorized for the demo CSM's account (`gmail.readonly + gmail.send + gmail.modify`).

## Installation

```bash
hermes profile install ./agents/bell --name bell --alias
```

Then make the `bin/` scripts executable in the live profile (they're shipped executable in the repo; `hermes profile install` preserves the mode):

```bash
chmod +x ~/.hermes/profiles/bell/bin/*.py
```

Python dependencies for the connectors: `simple-salesforce`, `requests` (both standard on most installs; `urllib` for Supabase is stdlib-only).

## Configuration

Set in the `bell` profile `.env` (see `distribution.yaml` for the authoritative list):

```bash
OPENROUTER_API_KEY=...

# Salesforce Chatter writer (CS Seeder admin app — Chatter requires write scope)
SALESFORCE_SEEDER_INSTANCE_URL=https://yourco.develop.my.salesforce.com
SALESFORCE_SEEDER_CONSUMER_KEY=...
SALESFORCE_SEEDER_CONSUMER_SECRET=...

# Operator Surface approval queue (Hermes side; service-role key bypasses RLS)
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...

# Optional overrides:
# OPERATOR_SURFACE_AGENT_SLUG=renewal-outreach     # registry slug (default shown)
# OPERATOR_SURFACE_CSM_UID=<uuid>                  # only needed if you use the demo `approve` command
# BELL_GOOGLE_API_SCRIPT=/path/to/google_api.py    # auto-detected if not set
```

Gmail OAuth is configured separately via the `productivity/google-workspace` skill — see that skill's setup docs.

## Access

| Capability | Status |
|---|---|
| Post internal Chatter to a Salesforce Opportunity | yes (auto) |
| Draft a customer-facing email | yes (draft only) |
| File a draft as a pending approval in the Operator Surface | yes |
| Send a customer email | only when `approval.status == "approved"` (enforced in `send-approved`) |
| Score or interpret renewal risk | no (that is Kepler) |
| Read raw Salesforce account data | no (that is Tycho) |

## Related docs

- [`docs/operator-surface-integration.md`](../../docs/operator-surface-integration.md) — Supabase schema, approval lifecycle, and how Bell fits in the broader Operator Surface app
- [`SOUL.md`](SOUL.md) — Bell's persona and the explicit bright-line
- [`skills/customer-success/meeting-followup/SKILL.md`](skills/customer-success/meeting-followup/SKILL.md) — the five-step workflow
