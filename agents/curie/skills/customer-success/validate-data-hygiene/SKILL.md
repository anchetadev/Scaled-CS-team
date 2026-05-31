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
- `INVALID` — wrong type, out of range, or impossible value, or internally contradictory.
- `MISSING` — a field that *should* be present in the source system is absent, null, or empty (e.g. an Account with no Name).
- `NO-SOURCE` — the signal lives in a system not integrated yet (product analytics, ticketing, CS platform), so there is no value to assess. This is a *coverage* gap, not a data defect. Tycho will have marked these `NEEDS SOURCE`; carry them through as `NO-SOURCE`.

**The critical distinction:** `MISSING` and `INVALID` are data *defects* — the source had a value and it's absent or broken. `NO-SOURCE` is a *coverage* gap — the source system simply isn't connected yet. Never conflate them. A pull that is 80% `NO-SOURCE` but whose present fields are all sound is *trustworthy, with thin coverage* — not untrustworthy.

## Record verdict

Roll the field verdicts into one. **The verdict is driven by data *defects* (`INVALID`/`MISSING`/`STALE`/`UNCONFIRMED` on fields that are present), NOT by coverage (`NO-SOURCE`).** Coverage gaps never, by themselves, cause a FAIL — they are the expected state until every source system is integrated, and the Data Analyst is built to score partial data and flag the rest.

- `PASS` — the present data is sound. Score it. (There may be many `NO-SOURCE` gaps — that's fine; note them.)
- `PASS WITH CAVEATS` — the present data is scorable, but specific fields carry defects the Data Analyst must handle carefully (e.g. score with low confidence, or exclude that one item). This is the right verdict when present data has a few `INVALID`/`UNCONFIRMED`/`STALE` fields *and/or* significant `NO-SOURCE` coverage gaps. **Most real pulls land here.**
- `FAIL` — reserve for when the present data is *too broken to trust at all*: the few fields that exist are mostly `INVALID`/contradictory, or a field essential to even identifying the record is `MISSING`. A FAIL means "re-pull, the data itself is wrong" — NOT "we haven't integrated enough systems yet."

Decision rule: count the *defects* among present fields. Zero defects → PASS. A handful of defects on otherwise-sound data → PASS WITH CAVEATS (caveat the specific items). The present data is mostly broken/contradictory → FAIL. `NO-SOURCE` count is reported for coverage awareness but does **not** move the verdict toward FAIL. Always state your reasoning and separate the defect count from the coverage count.

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

Validated [entity]: [N] present fields, [T] trustworthy, [D] defects (invalid/missing/stale/unconfirmed), [G] NO-SOURCE coverage gaps. Verdict: [PASS/CAVEATS/FAIL] (driven by defects, not coverage).
```

## Discipline

- **Picky is correct.** A false alarm costs a second look; a missed problem becomes a wrong decision about a real customer. When unsure, flag.
- **Cite the value.** Every flag names the specific data point that triggered it. No vague "data looks off."
- **Never interpret.** "This field is stale" — yes. "This account is at risk" — no, that's the Data Analyst.
- **Never fix.** Flag and recommend remediation; you don't write to anything.
- **Stay independent.** Do not soften a verdict because it would make downstream scoring easier. Independence is why you exist.

## Memory

After validating, remember recurring problems by source (chronically stale sync fields, always-informal fields), and any agreed thresholds (what counts as "stale," minimum coverage) so you apply them consistently across runs.
