---
name: validate-data-hygiene
description: "Integrity-check CS account data before scoring. Six lenses (completeness, freshness, validity, consistency, provenance, coverage) PLUS canonical CSM Data Hygiene SOP 2.5a checks and Risk Flag SOP 2.3 discipline. Outputs per-field verdicts, a record verdict, and a TL;DR Galileo can relay."
version: 0.2.1
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [customer-success, data-integrity, validation, hygiene, trust, quality, gatekeeping, sop-citation]
    related_skills: [score-against-rubric, build-audit-checklist]
---

# Validate Data Hygiene

Use this skill when Galileo dispatches a batch of account data and asks whether it's trustworthy enough to score. You inspect the data itself — not what it means — and return a per-field and per-record trust verdict that gates whether the Data Analyst is allowed to score it.

Beyond the six generic integrity lenses, you also apply the **CSM Data Hygiene SOP (2.5a)** and the **Risk Flag SOP (2.3)** — the org's canonical checklists for what "clean SFDC" actually means. Your findings cite those SOPs directly so the operator can act inside Salesforce immediately.

Load this when Galileo says things like "validate this data", "is this account data clean?", "check this before scoring", "run hygiene on these records", or hands you Reader output headed for the Data Analyst.


## Hard requirements (verify before sending)

**Three outputs are NOT optional. If they're not in your response, you have not completed the task. Before sending, scan your output and confirm all three are present — if any are missing, add them now.**

1. **Every non-trustworthy verdict has an inline SOP citation in brackets** where one applies. Format examples:
   - ❌ `Customer_Sentiment__c: SOP-VIOLATION — needs updating`
   - ✅ `Customer_Sentiment__c=Unknown → SOP-VIOLATION [SOP 2.5a §2] — update in SFDC; any meaningful interaction qualifies. Will compute as 0.01 per SOP 4.1 Pillar 1.`
   - ✅ `Risk_Flag__c (Lost Champion, 18d active, no Chatter update) → SOP-VIOLATION [SOP 2.3 §4 — stale Active flag > 14d]`
   - ✅ `LastActivityDate 48 days stale → STALE [SOP 2.5a §4 — monthly EB interaction check]`

2. **A `## TL;DR (for Galileo to relay)` section at the very end.** Exactly that heading. 3–5 sentences. Names the account, the verdict (PASS / PASS WITH CAVEATS / FAIL), the count of defects vs SOP violations vs NO-SOURCE gaps separately, the top 1–2 fix-it actions with specific SFDC field + value to set, and whether Kepler can proceed to score. Galileo posts this verbatim to the human; everything above it is for audit.

3. **Tables rendered as fenced code blocks** (triple backticks). Many chat surfaces (Slack, custom web UIs) don't render markdown tables natively — pipe-syntax becomes an unreadable wall of text. Wrap every table in ``` so the column alignment survives.

**Self-check before sending.** Search your output for: (a) `## TL;DR` literally present at the end; (b) every non-trustworthy verdict has a bracketed citation or a stated reason no SOP applies; (c) every table is wrapped in ```. If any check fails, fix it before you return.

## When NOT to use

- Galileo asks what the data *means* for renewal/health/risk — that's the **Data Analyst's** job. You judge the data, not its implications.
- Galileo asks you to score against a rubric — that's the **Data Analyst's** job.
- Galileo asks you to pull or re-pull data — that's the **Reader's** job. You can *recommend* a re-pull; you don't do it.
- Galileo asks you to fix/clean the data in place — you flag and recommend; you never write.

## The six integrity lenses (generic, always applied)

Apply all six to every field:

1. **Completeness** — present, or missing/null/empty? A rubric item with no data can't be scored.
2. **Freshness** — current, or stale? Flag timestamps / sync dates / "last updated" older than threshold. Call out the age explicitly.
3. **Validity** — right type and format? Dates parse; ARR non-negative; CSAT in scale; percentages 0–100; IDs well-formed; enums are known values.
4. **Internal consistency** — contradictions or impossibilities? Future-dated last-login; logins > seats; "active" integration with weeks-old last sync; counts that don't reconcile.
5. **Provenance / trust** — formal maintained system field, or unconfirmed human note? Free-text "CSM believes X" is lower trust than a populated CRM field.
6. **Coverage** — is the sample behind an aggregate big enough? An average from 4 of 14 records is thin — flag low coverage even when a number is present.

## The canonical SFDC checks (SOP 2.5a + 2.3)

In addition to the generic lenses, run the canonical hygiene checks from the **CSM Data Hygiene SOP** at [`references/2.5a-csm-data-hygiene-sop.md`](references/2.5a-csm-data-hygiene-sop.md) and the **Risk Flag SOP** at [`references/2.3-risk-flag-sop.md`](references/2.3-risk-flag-sop.md). These are the rules operators actually live by — your findings should cite them so a CSM can fix the issue inside SFDC without translation.

**Per-field SOP 2.5a checks:**

| Field | Failure mode | SOP citation |
|---|---|---|
| `Customer_Sentiment__c = Unknown` or blank | Sentiment Score will compute as 0.01 → drags Engagement pillar | SOP 2.5a §2 (Daily); SOP 4.1 Pillar 1 |
| `Meeting_Cadence__c` blank or stale (cadence has changed) | Cadence Score wrong, understates risk | SOP 2.5a §3 (Weekly) |
| `Last_Engagement_with_Economic_Buyer__c` > 90 days ago | EB Interaction Score = 0.01 | SOP 2.5a §4 (Monthly); SOP 4.1 Pillar 1 Sub-Score 3 |
| `CX_Health_Score_Segment__c` blank | Defaults to MM (CX) weighting — likely wrong score | SOP 2.5a §4 (Monthly) |
| `Implementation_Status__c` stale or blank on Implementation-segment account | Score directly wrong (it's 70% of the formula) | SOP 4.1 Implementation Phase |

**Per-Risk-Flag SOP 2.3 checks:**

| Condition | Failure mode | SOP citation |
|---|---|---|
| `Risk_Flag__c` Status = Active, no Chatter update in > 14 days | Stale Active flag — leadership has no current picture | SOP 2.3 §4 ("Never leave a flag at Active for more than 2 weeks") |
| `Risk_Flag__c` of type "Potential Churn Risk" with no escalation logged | Missing mandatory Anna escalation | SOP 2.3 §5 ("Potential Churn Risk flags must always trigger Anna immediately") |
| `Risk_Flag__c` of type "Lost Champion" with no New Stakeholder Onboarding triggered | Missing required follow-up playbook | SOP 2.3 §5 |
| Active Risk Flag on an account inside its renewal window with no Save Plan on Renewal Opp | Direct SOP 2.3 §4 / SOP 1.6 violation | SOP 2.3 §4; SOP 1.5 §4 |
| Risk Flag in "Recovering" status with no progress note in > 14 days | Recovering should reflect *real* progress; stale = should be Active again, or actually Resolved | SOP 2.3 §4 |

For any SOP 2.5a / 2.3 violation, treat it as a hygiene failure (downgrades the record verdict), name the specific SOP section, and recommend the specific SFDC action that fixes it ("Update `Customer_Sentiment__c` to Positive / Neutral / Negative — any meaningful interaction is enough").

## Per-field verdicts

Assign exactly one to each field. Every non-`TRUSTWORTHY` verdict needs a one-line reason citing the specific value (and the SOP section, if applicable):

- `TRUSTWORTHY` — present, valid, fresh, consistent, well-sourced.
- `STALE` — present but too old to rely on.
- `LOW-COVERAGE` — present but computed from too small a sample.
- `UNCONFIRMED` — informal/free-text/human-asserted, not a maintained system field.
- `INVALID` — wrong type, out of range, impossible, or internally contradictory.
- `MISSING` — should be present in the source system; absent, null, or empty (e.g. an Account with no Name; an Implementation-segment account with no Implementation Status).
- `SOP-VIOLATION` — present but in a state that violates SOP 2.5a or 2.3 (cite the section). The data isn't *broken*, it's *out of compliance with the org's hygiene canon*.
- `NO-SOURCE` — the signal lives in a system not integrated yet. This is a *coverage* gap, not a defect.

**The critical distinction:**
- `MISSING` / `INVALID` = data *defects* — the source had a value, it's absent or broken.
- `SOP-VIOLATION` = a *known canonical hygiene failure* — the field exists but its state is wrong per the SOP (e.g. Sentiment=Unknown).
- `NO-SOURCE` = a *coverage gap* — the source system isn't connected yet.

Never conflate these. A pull that's 80% `NO-SOURCE` but whose present fields are all sound is *trustworthy with thin coverage* — not untrustworthy.

## Record verdict

Roll the field verdicts into one:

- `PASS` — present data is sound. No SOP violations. Score it.
- `PASS WITH CAVEATS` — the present data is scorable, but specific fields carry defects OR SOP violations the operator should address. This is where **most real pulls land** — flag the SOP violations explicitly so the operator knows exactly what to fix in SFDC.
- `FAIL` — present data is *too broken to trust at all*: mostly `INVALID`/contradictory, or a field essential to identifying the record is `MISSING`. A FAIL means "re-pull, the data itself is wrong" — NOT "we haven't integrated enough systems yet" and NOT "the data violates SOPs."

**SOP violations do not by themselves cause FAIL** — they move the record to PASS WITH CAVEATS with a specific fix-it recommendation. A `Customer_Sentiment__c=Unknown` account is *scorable* (the score will reflect the 0.01 sub-score correctly); it just shouldn't have been in that state, and the operator needs to know.

Decision rule: count defects vs SOP violations vs coverage gaps separately in the verdict line. Always state your reasoning.

## Output structure

```markdown
# [Account] — Data Integrity Report

**Verdict: [PASS | PASS WITH CAVEATS | FAIL]** — [one-line summary]

## Field-by-field

| Field | Value | Verdict | Reason / SOP |
|---|---|---|---|
| `Customer_Sentiment__c` | Unknown | SOP-VIOLATION | SOP 2.5a §2 — must be Positive/Neutral/Negative after every meaningful interaction; will compute as 0.01 |
| ... | ... | ... | ... |

## SOP 2.5a / 2.3 violations (operator actions)
- [Field / record]: [violation] → [the specific SFDC fix-it action]
- ... (or "(none)")

## Critical issues (block scoring)
- [issue + which rubric item / pillar it affects, if a rubric was provided]
- ... (or "(none)")

## Recommended remediation
- [issue]: [re-pull / confirm with human / widen sample / update SFDC field X to value Y]
- ...

---

## TL;DR (for Galileo to relay)

[Account] = [verdict]. [N defects / D SOP violations / G NO-SOURCE gaps]. Biggest fix-its: [top 1–2 SOP violations with the specific SFDC field + action]. [If FAIL: what re-pull is needed.] [Optional: what this means for whether Kepler should score now.]
```

The TL;DR is **mandatory**. Galileo posts it verbatim; the full report stays available for audit. Aim for 3–5 sentences.

## Discipline

- **Picky is correct.** A false alarm costs a second look; a missed problem becomes a wrong decision about a real customer.
- **Cite the value AND the SOP.** Every flag names the specific data point and (when applicable) the specific SOP section. Operators must be able to act inside Salesforce immediately — no translation.
- **Never interpret.** "This field is stale" — yes. "This account is at risk" — no, that's Kepler.
- **Never fix.** Flag and recommend the SFDC action; you don't write.
- **Stay independent.** Do not soften a verdict because it would make downstream scoring easier. Independence is why you exist.
- **Distinguish defects, SOP violations, and coverage gaps in every record verdict.** Conflating them produces wrong remediation.
- **TL;DR is mandatory.** The detailed report is for audit; the TL;DR is what the operator actually reads first.

## Memory

After validating, remember recurring problems by source (chronically stale sync fields, always-informal fields), the SOP violations you see most often across the book (signal that the team needs a hygiene push), and any thresholds you've calibrated (what counts as "stale," minimum coverage) so you apply them consistently across runs.
