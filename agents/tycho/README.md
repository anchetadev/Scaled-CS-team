# Tycho — Salesforce Reader

Tycho is the read-only Salesforce data agent for the Scaled CS platform. Named for Tycho Brahe — the astronomer whose meticulous observations Kepler later interpreted — Tycho pulls raw account data faithfully and hands it off. He observes; he never interprets, cleans, or writes.

## Role

Tycho sits second in the pipeline: **Euclid → Tycho → Curie → Kepler → Hopper**. He:

- Pulls Account, Contract, Opportunity, and Contact data via read-only SOQL
- Reports every field exactly as Salesforce returns it (nulls stay null; nothing inferred)
- Flags every rubric signal that does NOT live in Salesforce as `NEEDS SOURCE` (product usage, ticketing, CSAT, etc.) — the "Salesforce + flag the rest" approach
- Hands the raw pull to Curie for integrity validation

## Design principles

- **Read-only, enforced at three layers** — credential (the Salesforce user has a read-only permission set and cannot write), connector (`bin/sf_reader.py` issues SELECT only and refuses DML), and agent (SOUL + skill). Proven: a write attempt returns `CANNOT_INSERT_UPDATE_ACTIVATE_ENTITY`.
- **Faithful, not helpful** — empty stays empty, wrong-looking stays as-is (flagged, not fixed). Faithfulness is the whole job; the moment Tycho "cleans" data, Curie's integrity check becomes meaningless.
- **No interpretation** — Tycho reports what Salesforce says, never what it means. That is Kepler's job.
- **Query-cost aware** — pulls only the fields the rubric needs.

## Connector

This distribution ships the connector at `bin/sf_reader.py`. It authenticates via **OAuth 2.0 Client Credentials** against a Salesforce **External Client App** whose Run-As user holds the read-only permission set. Commands:

- `login` — authenticate and report the account count
- `query "<SOQL>"` — run a SELECT (refuses any DML)
- `boundary-test` — attempt a write; success would mean read-only is NOT enforced (expected result: rejected)

Requires the Python packages `simple-salesforce` and `requests`.

## Installation

```bash
hermes profile install ./agents/tycho --name tycho --alias
```

## Configuration

Set in the `tycho` profile `.env` (see `distribution.yaml` for the authoritative list):

```bash
OPENROUTER_API_KEY=...
SALESFORCE_INSTANCE_URL=https://yourco.develop.my.salesforce.com   # bare My Domain, NOT the salesforce-setup.com host
SALESFORCE_CONSUMER_KEY=...      # External Client App consumer key
SALESFORCE_CONSUMER_SECRET=...   # External Client App consumer secret
```

No username/password/security-token: the org has SOAP login disabled, so auth is OAuth Client Credentials only.

## Access

| Capability | Status |
|------------|--------|
| Read accounts / contracts / opportunities / contacts | yes |
| Flag non-Salesforce signals (NEEDS SOURCE) | yes |
| Write / update / delete any data | no (rejected at credential layer) |
| Interpret or score data | no (that is Kepler) |
