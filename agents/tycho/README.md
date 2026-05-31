# SF Reader — Salesforce Data Agent

A specialized worker agent that pulls account and ticket data from Salesforce. Read-only access — never writes.

## Role

The SF Reader is **precise and careful about query cost**. It:

- Pulls account health data
- Retrieves ticket history
- Queries contact information
- Extracts opportunity data
- Reports findings to Galileo

## Design Principles

- **Read-only access** — Cannot modify Salesforce data
- **Query cost awareness** — Minimizes API calls, uses selective queries
- **Structured output** — Returns data in consistent, parseable format
- **Error handling** — Gracefully handles API limits and failures

## Installation

```bash
hermes profile install github.com/YOUR_USERNAME/hermes-scaled-cs/agents/sf-reader --name sf-reader --alias
```

## Configuration

Set in `~/.hermes/profiles/sf-reader/.env`:

```bash
OPENROUTER_API_KEY=*** SALESFORCE_SECURITY_TOKEN=*** Access

| Capability | Status |
|------------|--------|
| Read accounts | ✅ |
| Read tickets | ✅ |
| Read contacts | ✅ |
| Read opportunities | ✅ |
| Write any data | ❌ |
| Delete any data | ❌ |
