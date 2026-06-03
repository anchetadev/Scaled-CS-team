# hermes-scaled-cs

A team of coordinated AI agents for **Scaled Customer Success** — built on [Hermes Agent](https://github.com/NousResearch/hermes-agent).

This platform automates account-health monitoring, renewal-risk auditing, post-meeting follow-up, and Salesforce operations at scale by distributing work across specialized agents with strict role boundaries. Humans talk to **Galileo**; Galileo dispatches the work to a team of named specialists and relays the results back.

## The team

Each agent is named for a scientist whose work mirrors its role — the names are the architecture.

| Persona | Role | Profile | Access |
|---|---|---|---|
| **Galileo** | Supervisor / bot father — human-facing front door, coordinates the workers | `galileo` | Orchestration (Slack) |
| **Euclid** | Rubric / SOP Author — defines the checklists, rubrics, and scoring rules | `euclid` | None (definitions only, zero data) |
| **Tycho** | Salesforce Reader — pulls raw account data, faithfully, a dumb pipe | `tycho` | Read-only Salesforce |
| **Curie** | Hygiene + Score Validator — is the data trustworthy? (integrity check) | `curie` | None |
| **Kepler** | Data Analyst — scores the data against the rubric; what does it mean? | `kepler` | Read-only (works on Tycho's data) |
| **Hopper** | Controlled Executor — writes approved changes, per-batch human approval | `hopper` | Write Salesforce (gated) |
| **Bell** | Communications Specialist — post-meeting Chatter + customer-email drafting, with the customer send gated behind explicit CSM approval | `bell` | Salesforce Chatter (write), Operator Surface approval queue (write), Gmail send-as-CSM (only when approval = `approved`) |

Why the names fit: **Euclid** built everything from exact definitions. **Tycho** Brahe made history's most precise observations and handed them to **Kepler**, who found the meaning in them — exactly the Reader→Analyst handoff. **Curie** trusted nothing she had not measured. **Hopper** (Grace Hopper) was the careful, precise executor who coined "debugging." **Bell** turned distance into conversation — the right name for the agent that handles the communications follow-through.

## The workflows

Galileo dispatches to two parallel workflows under him: the renewal-risk pipeline (five agents in sequence) and the post-meeting follow-up workflow (Bell, on his own). Each is its own pipeline with its own safety model.

```
                            ┌──────────────────────────────┐
   Slack team  ───────────▶ │            GALILEO           │ ◀─── escalates to humans
                            │   (supervisor / bot father)  │
                            └──────────────┬───────────────┘
                                           │ dispatches
                  ┌────────────────────────┴────────────────────────┐
                  │                                                 │
            renewal-risk pipeline                          post-meeting workflow
                  │                                                 │
   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    ┌──────────┐
   │  EUCLID  │─▶│  TYCHO   │─▶│  CURIE   │─▶│  KEPLER  │─▶│  HOPPER  │    │   BELL   │
   │ defines  │  │  pulls   │  │ validates│  │ interprets│ │  writes  │    │  Chatter │
   │  rubric  │  │   data   │  │ integrity│  │  & scores │ │ (approval)│   │  + draft │
   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │ + send   │
                                                                            │(approval)│
                                                                            └──────────┘
```

Each boundary is a deliberate safety separation, not just an org chart:
- **Euclid defines** scores; **Kepler applies** them — the author never touches live data.
- **Tycho reads** (read-only creds); **Hopper writes** (separate, gated) — a read mistake can't reach write.
- **Curie** asks *is the data trustworthy?*; **Kepler** asks *what does it mean?* — integrity stays an independent check.
- **Bell drafts** the customer email; the **CSM approves** in the Operator Surface; only then does the send fire — from the CSM's own Gmail, not Bell's identity. Bell's `send-approved` subcommand refuses to send when `status != "approved"`, enforcing the bright line in code, not prompt.

## Install

Requires [Hermes Agent](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) `>= 0.13.0`.

```bash
# Install every agent at once
./scripts/install-all.sh

# Or install one
hermes profile install ./agents/tycho --name tycho --alias
hermes profile install ./agents/bell  --name bell  --alias
```

After install, populate each agent's `.env` (a `.env.EXAMPLE` is generated listing required keys), then:

```bash
hermes gateway start -p galileo      # bring Galileo online in Slack
hermes -p galileo                    # chat with Galileo directly
```

For Bell, also make the helper scripts executable:

```bash
chmod +x ~/.hermes/profiles/bell/bin/*.py
```

## Environment

- **All agents:** `OPENROUTER_API_KEY`
- **Galileo:** `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` (+ optional `SLACK_ALLOWED_USERS`)
- **Tycho:** Salesforce External Client App OAuth — `SALESFORCE_INSTANCE_URL`, `SALESFORCE_CONSUMER_KEY`, `SALESFORCE_CONSUMER_SECRET`
- **Hopper:** write-capable Salesforce creds — declared but optional; the executor's approval gate is still under design.
- **Bell:** CS Seeder OAuth (`SALESFORCE_SEEDER_INSTANCE_URL` + key + secret), Operator Surface Supabase (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`), plus Gmail OAuth via the `productivity/google-workspace` skill.

Secrets (`.env`, `auth.json`, memories, sessions, `state.db`) are git-ignored and never shipped.

## Keeping live profiles in sync with the repo

After committing a SOUL, README, or skill change to this repo, sync the live profiles on the droplet:

```bash
./scripts/sync-profiles.sh --dry-run     # preview
./scripts/sync-profiles.sh               # apply
# script prints `systemctl --user restart hermes-gateway-<name>.service` per affected profile
```

See [`docs/sync-workflow.md`](docs/sync-workflow.md) for what gets synced and what stays runtime-only.

## Docs

- [`docs/architecture.md`](docs/architecture.md) — how the pipeline fits together
- [`docs/agent-roles.md`](docs/agent-roles.md) — each agent's responsibilities and boundaries
- [`docs/setup-guide.md`](docs/setup-guide.md) — step-by-step setup
- [`docs/extending.md`](docs/extending.md) — adding a new agent to the team
- [`docs/sync-workflow.md`](docs/sync-workflow.md) — distribution → live profile syncing
- [`docs/operator-surface-integration.md`](docs/operator-surface-integration.md) — Bell's approval-queue integration with the Operator Surface app
- [`docs/worker-ledger-contract.md`](docs/worker-ledger-contract.md) — the operating contract every worker reads at dispatch time

## License

MIT © Angel Ancheta
