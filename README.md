# hermes-scaled-cs

A team of coordinated AI agents for **Scaled Customer Success** — built on [Hermes Agent](https://github.com/NousResearch/hermes-agent).

This platform automates account health monitoring, ticket triage, and Salesforce operations at scale by distributing work across specialized agents with strict role boundaries.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Slack Team                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    GALILEO                            │  │
│  │              (Supervisor / Bot Father)                │  │
│  │                                                       │  │
│  │  • Human-facing front door                           │  │
│  │  • Spawns and coordinates workers                    │  │
│  │  • Reports results in plain English                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         ▼                  ▼                  ▼             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │ SOP Analyst │   │ SF Reader   │   │ Validator   │       │
│  │ (Checklist) │   │ (Read-only) │   │ (Hygiene)   │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
│                            │                                │
│                     ┌─────────────┐                         │
│                     │  Executor   │                         │
│                     │ (Writes w/  │                         │
│                     │  approval)  │                         │
│                     └─────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Agents

| Agent | Profile Name | Role | Access Level |
|-------|--------------|------|--------------|
| **Galileo** | `galileo` | Supervisor — coordinates all workers | Full (orchestration) |
| **SOP Analyst** | `sop-analyst` | Builds audit checklists & scoring frameworks | None (logic only) |
| **Analyst** | `analyst` | Traditional data analysis — trends, patterns, insights | None (analysis only) |
| **SF Reader** | `sf-reader` | Pulls account & ticket data from Salesforce | Read-only |
| **Validator** | `validator` | Flags hygiene issues against checklist | None (read + validate) |
| **Executor** | `executor` | Writes changes back to Salesforce | Write (with human approval) |

### Design Principles

- **Reader/Executor split** — Read and write live in different identities so a mistake on one side can't reach the other.
- **Strict role boundaries** — Each agent does ONE thing well. Galileo enforces these boundaries.
- **Human-in-the-loop** — Executor requires per-batch approval before writing changes.
- **Ephemeral workers** — For one-off tasks, Galileo spawns short-lived agents that die when done.

## Quick Start

### Prerequisites

- [Hermes Agent](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) installed
- API keys: `OPENROUTER_API_KEY` (or your preferred provider)
- Slack bot tokens (for Slack integration)

### Install All Agents

```bash
# Clone the platform
git clone https://github.com/YOUR_USERNAME/hermes-scaled-cs.git
cd hermes-scaled-cs

# Run the installer
chmod +x scripts/install-all.sh
./scripts/install-all.sh
```

### Install Individual Agents

```bash
# From the cloned repo
hermes profile install ./agents/galileo --name galileo --alias
hermes profile install ./agents/sf-reader --name sf-reader --alias
hermes profile install ./agents/validator --name validator --alias
hermes profile install ./agents/executor --name executor --alias
hermes profile install ./agents/sop-analyst --name sop-analyst --alias
hermes profile install ./agents/analyst --name analyst --alias
```

## Configuration

### Required Environment Variables

Set these in each agent's `.env` file (`~/.hermes/profiles/<agent>/.env`):

```bash
# Model access (required for all agents)
OPENROUTER_API_KEY=***

# Slack integration (required for Galileo)
SLACK_BOT_TOKEN=xoxb-***
SLACK_APP_TOKEN=xapp-***

# Salesforce (required for Reader + Executor)
SALESFORCE_USERNAME=your@email.com
SALESFORCE_PASSWORD=***
SALESFORCE_SECURITY_TOKEN=***
```

### Starting the Platform

```bash
# Start Galileo's gateway (he coordinates everything)
hermes gateway start -p galileo

# Chat with Galileo
hermes -p galileo
```

## Development

### Project Structure

```
hermes-scaled-cs/
├── README.md                  # This file
├── LICENSE                    # MIT License
├── agents/
│   ├── galileo/               # Supervisor agent
│   │   ├── distribution.yaml  # Agent metadata
│   │   ├── README.md          # Agent-specific docs
│   │   ├── SOUL.md            # Personality definition
│   │   ├── config.yaml        # Model + tool config
│   │   └── skills/            # Agent-specific skills
│   ├── sf-reader/             # Salesforce Reader
│   ├── validator/             # Hygiene Validator
│   ├── executor/              # Controlled Executor
│   ├── sop-analyst/           # SOP & Scoring Analyst
│   └── analyst/               # Traditional Data Analyst
├── docs/
│   ├── architecture.md        # Detailed architecture
│   ├── setup-guide.md         # Full setup instructions
│   ├── agent-roles.md         # Who does what
│   └── extending.md           # Adding new agents
└── scripts/
    ├── install-all.sh         # Install all agents
    └── setup-sf.sh            # Salesforce credential setup
```

### Adding a New Agent

1. Create a new directory under `agents/`
2. Add `distribution.yaml`, `SOUL.md`, `config.yaml`
3. Update Galileo's `SOUL.md` to include the new agent in the roster
4. Update this README

## Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Test with `hermes profile install ./agents/<agent> --name <agent>-test`
5. Submit a PR

## License

MIT

## Links

- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [Hermes Docs](https://hermes-agent.nousresearch.com/docs/)
- [Profile Distributions](https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions)
