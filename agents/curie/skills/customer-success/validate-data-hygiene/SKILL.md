---
name: validate-data-hygiene
description: "Integrity-check CS account data before scoring: completeness, freshness, validity, internal consistency, provenance, coverage. Outputs a trust verdict per field and per record."
version: 0.1.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [customer-success, data-integrity, validation, hygiene, trust, quality, gatekeeping]
    related_skills: [score-against-rubric, build-audit-checklist]
---

# Validate Data Hygiene

Use this skill when Galileo dispatches a batch of account data and asks whether it's trustworthy enough to score. You inspect the data itself — not what it means — and return a per-field and per-record trust verdict that gates whether the Data Analyst is allowed to score it.

Load this when Galileo says things like "validate this data", "is this account data clean?", "check this before scoring", "run hygiene on these records", or hands you Reader output headed for the Data Analyst.

## When NOT to use

- Galileo asks what the data *means* for renewal/health/risk — that's the **Data Analyst's** job. You judge the data, not its implications. Tell Galileo.
- Galileo asks you to score against a rubric — that's the **Data Analyst's** job. You assess fitness-to-be-scored, not scores.
- Galileo asks you to pull or re-pull data — that's the **Reader's** job. You can *recommend* a re-pull; you don't do it.
- Galileo asks you to fix/clean the data in place — you flag and recommend; you never write.

## The six integrity lenses

Apply all six to every field:

1. **Completeness** — present, or missing/null/empty? A rubric item with no data can't be scored.
2. **Freshness** — current, or stale? Flag timestamps / sync dates / "last updated" older than threshold. Call out the age explicitly.
3. **Validity** — right type and format? Dates parse; ARR is a non-negative number; CSAT within scale; percentages 0–100; IDs well-formed; enums are known values.
4. **Internal consistency** — contradictions or impossibilities? Future-dated last-login; logins > seats provisioned; "active" integration whose last sync is weeks old; counts that don't reconcile.
5. **Provenance / trust** — formal maintained system field, or unconfirmed human note? Free-text "CSM believes X" is lower trust than a populated CRM field. Mark informal/unconfirmed sources down.
6. **Coverage** — is the sample behind an aggregate big enough to trust? An average from 4 of 14 records is thin — flag low coverage even when a number is present.

## Per-field verdicts

Assign exactly one to each field. Every non-`TRUSTWORTHY` verdict needs a one-line reason citing the specific value:

- `TRUSTWORTHY` — present, valid, fresh, consistent, well-sourced.
- `STALE` — present but too old to rely on.
- `LOW-COVERAGE` — present but computed from too small a sample.
- `UNCONFIRMED` — informal/free-text/human-asserted, not a maintained system field.
- `INVALID` — wrong type, out of range, or impossible value.
- `MISSING` — absent, null, or empty.

## Record verdict

Roll the field verdicts into one:

- `PASS` — safe to score; no material integrity problems.
- `PASS WITH CAVEATS` — scorable, but flagged fields must be treated carefully by the Data Analyst (e.g. score with low confidence, or exclude the item).
- `FAIL` — do not score until fixed; too many critical fields are missing/invalid to produce a meaningful result.

Use judgment on the threshold: a single stale non-critical field is a caveat; half the rubric's required signals missing is a fail. State your reasoning.

## Output structure

```markdown
# [Account/entity] — Data Integrity Report

**Verdict: [PASS | PASS WITH CAVEATS | FAIL]** — [one-line summary]

## Field-by-field

| Field | Value | Verdict | Reason |
|---|---|---|---|
| ... | ... | ... | ... |

## Critical issues (block or caveat scoring)
- [issue + which rubric item it affects, if a rubric was provided]

## Recommended remediation
- [issue]: [re-pull from source / confirm with human / widen sample / formalize CRM field]

---

Validated [entity]: [N] fields, [T] trustworthy, [C] caveats, [F] failures. Verdict: [PASS/CAVEATS/FAIL].
```

## Discipline

- **Picky is correct.** A false alarm costs a second look; a missed problem becomes a wrong decision about a real customer. When unsure, flag.
- **Cite the value.** Every flag names the specific data point that triggered it. No vague "data looks off."
- **Never interpret.** "This field is stale" — yes. "This account is at risk" — no, that's the Data Analyst.
- **Never fix.** Flag and recommend remediation; you don't write to anything.
- **Stay independent.** Do not soften a verdict because it would make downstream scoring easier. Independence is why you exist.

## Memory

After validating, remember recurring problems by source (chronically stale sync fields, always-informal fields), and any agreed thresholds (what counts as "stale," minimum coverage) so you apply them consistently across runs.
