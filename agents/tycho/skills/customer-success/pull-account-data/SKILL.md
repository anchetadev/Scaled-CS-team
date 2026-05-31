---
name: pull-account-data
description: "Pull raw account data from Salesforce (read-only) for one or more accounts, mapped to a rubric's required signals, and emit NEEDS SOURCE markers for anything not in Salesforce."
version: 0.1.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [customer-success, salesforce, data-pull, reader, read-only, soql]
    related_skills: [validate-data-hygiene, score-against-rubric, build-audit-checklist]
---

# Pull Account Data

Use this skill when Galileo asks you to pull an account's data from Salesforce for the pipeline. You query read-only, return the raw record faithfully, and flag every rubric signal that doesn't live in Salesforce. Your output goes to the Validator next.

Load this when Galileo says "pull account X", "get the Salesforce data for these accounts", "read account #… for renewal scoring", or hands you a rubric and asks you to source its data.

## When NOT to use

- Galileo asks whether the data is clean/trustworthy — that's the **Validator's** job. You pull; you don't judge.
- Galileo asks what the data means for renewal/health — that's the **Data Analyst's** job.
- Galileo asks you to update/change a record — that's the **Controlled Executor's** job. You are read-only; refuse and route it.

## Connector (wired at build time)

> STATUS: pending live credentials. Tycho authenticates as a Salesforce **Integration User** (API-only, read-only permission set) against the sandbox. Connection details live in `profiles/tycho/.env` (instance URL, Connected App key/secret, integration-user username/password/token). The connector exposes **read/SELECT operations only** — there is no write code path. When the connector lands, record the exact tool/command name for querying here.

Until wired, this skill documents the *procedure*; the query mechanism is filled in once the Salesforce connector is connected and the write-rejection boundary is verified.

## Core method

### 1. Confirm the request
Which account(s)? Which rubric's data requirements are you pulling for (if given)? Restate in one line.

### 2. Map rubric signals → Salesforce objects
Pull only what the rubric needs, from where it actually lives:

| Rubric area | Salesforce object/fields (typical) |
|---|---|
| Contract timing & terms | `Contract.EndDate`, `Contract.Auto_Renewal__c` (or equiv), term, value |
| ARR / value trend | `Opportunity` (renewal/upsell, ARR, stage, CloseDate); contract value history |
| Health score | `Account.Health_Score__c` *(only if native; else NEEDS SOURCE → Gainsight/Totango)* |
| Stakeholders | `Contact` (champion, exec sponsor, decision-maker, LastActivityDate) |
| CSM touchpoints | `Task` / `Event` (QBR/EBR, check-ins, escalations logged in CRM) |
| Account meta | `Account` (tier, owner, key dates) |

Confirm the actual field API names against the org — custom fields vary (`__c` suffix). Record the mapping in memory so future pulls are consistent.

### 3. Query read-only
Issue SELECT/SOQL only. Be economical — request the fields the rubric needs, not `SELECT *`-style over-pulls. If a query is large or spans many records, note the cost in Read notes.

### 4. Return the raw record
Field-by-field, exact Salesforce field name + exact value. **Preserve nulls/empties — never substitute a default or a guess.** If a value looks wrong, report it as-is and note it; do not correct it (correcting it would blind the Validator).

### 5. Flag the rest
For every rubric signal not in Salesforce, emit:
```
NEEDS SOURCE: <signal> — not available in Salesforce; requires <system>.
```
Common ones for the renewal-risk rubric: product usage/MAU/logins/feature adoption (product analytics), ticket counts & severities (Zendesk/Jira), CSAT (survey system), payment issues (billing). Also note any field you *should* have read but couldn't due to permissions.

## Output structure

```markdown
# [Account] — Salesforce Pull

**Account:** [name] ([Salesforce Id])
**Pulled:** [objects queried] · [field count] fields

## Fields
| Object.Field | Value | Notes |
|---|---|---|
| ... | ... | ... |

## Needs source (not in Salesforce)
- NEEDS SOURCE: [signal] — requires [system]

## Read notes
- [permission-denied fields, large-query warnings, anything the Validator should know]

---

Pulled [account] from Salesforce: [N] fields returned, [G] gaps flagged as needs-source.
```

## Discipline

- **Read-only, always.** SELECT/SOQL only. Never write/update/delete/upsert/Apex. If asked, refuse and route to the Executor.
- **Faithful, not helpful.** Empty stays empty; wrong-looking stays as-is (flagged, not fixed). Faithfulness is the whole job — the Validator can only catch problems you didn't paper over.
- **No interpretation.** Report values, never meaning.
- **Make gaps loud.** A missing *system* must look different from a missing *value* — that's what NEEDS SOURCE is for.

## Memory

Remember the field-to-rubric mapping (which `__c` field feeds which rubric item), which signals are chronically NEEDS SOURCE (candidates for a new reader integration), and expensive query patterns to avoid.
