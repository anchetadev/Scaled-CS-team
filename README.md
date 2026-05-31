# hermes-scaled-cs

A team of coordinated AI agents for **Scaled Customer Success** — built on [Hermes Agent](https://github.com/NousResearch/hermes-agent).

This platform automates account-health monitoring, renewal-risk auditing, and Salesforce operations at scale by distributing work across specialized agents with strict role boundaries. Humans talk to **Galileo**; Galileo dispatches the work to a team of named specialists and relays the results back.

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

Why the names fit: **Euclid** built everything from exact definitions. **Tycho** Brahe made history's most precise observations and handed them to **Kepler**, who found the meaning in them — exactly the Reader→Analyst handoff. **Curie** trusted nothing she had not measured. **Hopper** (Grace Hopper) was the careful, precise executor who coined "debugging."

## The pipeline

```
                         ┌──────────────────────────────┐
   Slack team  ───────▶  │            GALILEO           │  ◀─── escalates to humans
                         │   (supervisor / bot father)  │
                         └──────────────┬───────────────┘
                                        │ dispatches
   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │  EUCLID  │──▶│  TYCHO   │──▶│  CURIE   │──▶│  KEPLER  │──▶│  HOPPER  │
   │ defines  │   │  pulls   │   │ validates│   │ interprets│  │  writes  │
   │  rubric  │   │   data   │   │ integrity│   │  & scores │  │ (approval)│
   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

Each boundary is a deliberate safety separation, not just an org chart:
- **Euclid defines** scores; **Kepler applies** them — the author never touches live data.
- **Tycho reads** (read-only creds); **Hopper writes** (separate, gated) — a read mistake can't reach write.
- **Curie** asks *is the data trustworthy?*; **Kepler** asks *what does it mean?* — integrity stays an independent check.

## Install

Requires [Hermes Agent](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) `>= 0.13.0`.

```bash
# Install every agent at once
./scripts/install-all.sh

# Or install one
hermes profile install ./agents/tycho --name tycho --alias
```

After install, populate each agent's `.env` (a `.env.EXAMPLE` is generated listing required keys), then:

```bash
hermes gateway start -p galileo      # bring Galileo online in Slack
hermes -p galileo                    # chat with Galileo directly
```

## Environment

- **All agents:** `OPENROUTER_API_KEY`
- **Galileo:** `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` (+ optional `SLACK_ALLOWED_USERS`)
- **Tycho:** Salesforce Integration-User + Connected App OAuth — `SALESFORCE_INSTANCE_URL`, `SALESFORCE_CONSUMER_KEY`, `SALESFORCE_CONSUMER_SECRET`, `SALESFORCE_USERNAME`, `SALESFORCE_PASSWORD`, `SALESFORCE_SECURITY_TOKEN`
- **Hopper:** write-capable Salesforce creds — declared but optional; the executor's approval gate is still under design.

Secrets (`.env`, `auth.json`, memories, sessions, `state.db`) are git-ignored and never shipped.

## Docs

- [`docs/architecture.md`](docs/architecture.md) — how the pipeline fits together
- [`docs/agent-roles.md`](docs/agent-roles.md) — each agent's responsibilities and boundaries
- [`docs/setup-guide.md`](docs/setup-guide.md) — step-by-step setup
- [`docs/extending.md`](docs/extending.md) — adding a new agent to the team

## License

MIT © Angel Ancheta
