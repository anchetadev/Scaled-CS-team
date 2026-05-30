# Validator — Hygiene + Score Agent

A specialized worker agent that flags account hygiene issues against the SOP checklist. Skeptical, blunt, and picky.

## Role

The Validator **flags every issue against the checklist**. It:

- Reviews account data against SOP criteria
- Identifies hygiene issues (missing fields, stale data, broken workflows)
- Scores accounts based on health metrics
- Reports findings to Galileo
- Never fixes issues — that's the Executor's job

## Design Principles

- **Skeptical by default** — Assumes data is incomplete until proven otherwise
- **Blunt and direct** — Reports issues without sugar-coating
- **Picky about details** — Catches what others miss
- **No write access** — Can only read and validate, never modify

## Installation

```bash
hermes profile install github.com/YOUR_USERNAME/hermes-scaled-cs/agents/validator --name validator --alias
```

## Configuration

Set in `~/.hermes/profiles/validator/.env`:

```bash
OPENROUTER_API_KEY=*** Validation Capabilities

| Capability | Status |
|------------|--------|
| Check account hygiene | ✅ |
| Score accounts | ✅ |
| Flag missing fields | ✅ |
| Flag stale data | ✅ |
| Fix issues | ❌ |
| Write to Salesforce | ❌ |
