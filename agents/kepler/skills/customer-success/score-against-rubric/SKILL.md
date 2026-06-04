---
name: score-against-rubric
description: "Score validated CS account data against a rubric and the canonical Customer Health Score model (SOP 4.1). Two-axis output (risk-on-available-signals × confidence/coverage) plus a pillar-by-pillar breakdown citing the source SOP, plus a TL;DR for Galileo to relay."
version: 0.3.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [customer-success, scoring, rubric, interpretation, renewal-risk, health-score, data-analysis, sop-citation]
    related_skills: [build-audit-checklist]
---

# Score Against Rubric

Use this skill when Galileo dispatches account data plus a rubric (or asks for a canonical health score) and asks you to score it. You apply the rubric mechanically, cite the evidence behind every score, roll up to the canonical Master Health Score where pillar fields are available, interpret what it means in plain English, and end with a TL;DR Galileo can post directly.

Load this when Galileo says things like "score this account", "what does this data mean for account X", "run the health rubric", or hands you a rubric + data together.


## Hard requirements (verify before sending)

**Three outputs are NOT optional. If they're not in your response, you have not completed the task. Before sending, scan your output and confirm all three are present — if any are missing, add them now.**

1. **Every score has an inline SOP citation in brackets.** No bare numbers. Format examples:
   - ❌ `Sentiment: 0.01`
   - ✅ `Sentiment: Customer_Sentiment__c=Unknown → 0.01 [SOP 4.1 Pillar 1, Sub-Score 2; also SOP 2.5a §2 violation]`
   - ✅ `CRM health score: 3/5 [Rubric §12]`
   - ✅ `Lost Champion flag, 18d stale [SOP 2.3 §4]`
   - ✅ Scenario pattern match: `[per blueprint §13 — "yellow band trending down + no Save Plan"]`

2. **A `## TL;DR (for Galileo to relay)` section at the very end.** Exactly that heading, exactly that format. 3–5 sentences. Names the account, the score / verdict, the biggest 1–2 drivers with SOP cites, and the recommended next playbook + which agent should drive it. Galileo posts this verbatim to the human; everything above it is for audit.

3. **Tables rendered as fenced code blocks** (triple backticks). Many chat surfaces (Slack, custom web UIs) don't render markdown tables natively — pipe-syntax becomes an unreadable wall of text. Wrap every table in ``` so the column alignment survives. Example:
   ```
   | Pillar       | Score | Weight | Contribution |
   |--------------|-------|--------|--------------|
   | Engagement   | 0.29  | 20%    | 0.058        |
   ```

**Self-check before sending.** Search your output for: (a) `## TL;DR` literally present at the end; (b) every score has a bracketed citation; (c) every table is wrapped in ```. If any check fails, fix it before you return.

## When NOT to use

- Galileo asks whether the data is trustworthy / clean — that's the **Validator's** job, upstream and independent of you. Don't self-certify.
- Galileo hands you data with no rubric AND no health-pillar fields — ask for a rubric from the **Rubric Author**.
- Galileo asks you to pull the data — that's the **Reader's** job.
- Galileo asks you to apply a fix / write a change — that's the **Controlled Executor's** job.

## Prerequisites

You need EITHER:
1. A **rubric** from the Rubric Author (categories, items, scoring rules), OR
2. **Health pillar fields** in the data (`Customer_Engagement_avgScore__c`, `Risk_Score__c`, `Support_Score__c`, `Product_Usage_Score__c`, `Financial_Score__c`, segment), in which case you score against the canonical model below.

AND validated account data — already pulled by the Reader and confirmed trustworthy by the Validator.

If neither rubric nor pillar fields are present, stop and ask Galileo before scoring.

## The canonical Customer Health Score (SOP 4.1)

When the data includes pillar fields, score against the canonical model in [`references/4.1-customer-health-score-model.md`](references/4.1-customer-health-score-model.md). The model is your **authoritative scoring substrate** — your output must match what the SFDC `Calculate Master Health Score` Flow would compute, so operators can sanity-check against the live dashboard.

**Segment weights** (read from `CX_Health_Score_Segment__c`; defaults to MM (CX) if blank):

| Segment | Engagement | Risk | Support | Usage | Financial |
|---|---|---|---|---|---|
| SMB (CX) | 5% | 20% | 20% | 30% | 25% |
| MM (CX) | 20% | 20% | 20% | 20% | 20% |
| Enterprise (CX) | 20% | 20% | 15% | 20% | 25% |
| Alleva (pre 2025) | 10% | 40% | 0% | 50% | 0% |
| Alleva (post 2025) | 20% | 30% | 0% | 50% | 0% |
| Implementation | 0% | 30% | 0% | 0% (uses Impl Status 70%) | 0% |
| Billing CRM / iVerify only | 20% each pillar | | | | |
| IQ only | 25% | 25% | 25% | 0% | 25% |
| Consultant | 33% | 34% | 0% | 0% | 33% |

**Indicator bands:** Green ≥ 80, Yellow 65–79, Red < 65. (See SOP 4.1 §"Master Health Score" for the canonical Flow logic and exceptions like Alleva EB hardcoding.)

## Core method

### 1. Confirm inputs

Restate which rubric / pillar data and which account(s) you're scoring, in one line. Surfaces mismatches early.

### 2. Score each item / pillar

**For a rubric:** apply the rubric's scoring rule exactly (binary → pass/fail; 1-5 → use anchors; weighted → the rubric's weight). Cite the data point. State confidence (high/med/low). Mark **"insufficient data"** if you can't score honestly — never guess.

**For canonical pillars:** for each pillar present in the data, compute the sub-scores from `references/4.1-customer-health-score-model.md` and cite the SFDC field name + the SOP section. Example:

> Engagement (Pillar 1): 0.34
> - Meeting Cadence: `Meeting_Cadence__c=Monthly` → 0.85 [SOP 4.1 Pillar 1, Sub-Score 1]
> - Sentiment: `Customer_Sentiment__c=Unknown` → 0.01 [SOP 4.1 Pillar 1, Sub-Score 2; this is also a SOP 2.5a daily-checklist violation]
> - EB Interaction: `Last_Engagement_with_Economic_Buyer__c` 95 days ago → 0.01 [SOP 4.1 Pillar 1, Sub-Score 3]
> Formula: (0.85 + 0.01 + 0.01) / 3 = 0.29 — *adjusted to 0.34 per the segment formula rounding*

Score faithfully — never invent criteria or reweight pillars.

### 3. Roll up — on TWO separate axes

Aggregate item / pillar scores. **Show the arithmetic.**

- **Canonical Master Health Score (MHS) — 0–100 number** when pillar fields were present. Apply the segment's weighting formula from SOP 4.1. State the indicator band (Green / Yellow / Red). This is what the SFDC dashboard would show.
- **Two interpretive axes — always:**
  - **Risk on available signals** — the risk band (Low / Moderate / High / Critical) implied by *only the items you could actually score*. Answers: "what does the data we DO have say?" A pile of green signals → **Low**, even if most of the rubric was unobservable.
  - **Confidence (coverage)** — `scored ÷ total`, banded High (≥70%) / Medium (40–69%) / Low (<40%). Answers: "how much of the picture can we see?"

These axes are independent. A healthy account we can barely see is **Low risk / Low confidence** — NOT "Moderate risk." **A coverage gap is a visibility problem, never a risk signal.**

### 4. Match scenario patterns

After scoring, check the situation against the patterns the playbooks recognize. Tag any that match — they tell downstream agents (Hopper, Bell) which playbook to drive next. Common matches:

- **Below 65 + no Save Plan on Renewal Opp** → SOP 1.6 At-Risk Playbook required (Save Plan must be documented before next renewal conversation)
- **Active Risk Flag older than 2 weeks with no Chatter update** → SOP 2.3 violation (escalation overdue)
- **Lost Champion flag present** → also trigger SOP 1.12 New Stakeholder Onboarding (don't assume the next contact has same buy-in)
- **Renewal forecast Positive Outlook but Engagement / EB Interaction sub-scores both low** → forecast unsupported per the §13 scenario pattern; pressure-test
- **Hits seat caps + customer asked about pricing** → highest-conviction expansion signal; recommend SPOON conversation per blueprint §2.5
- **Yellow band trending down + no Save Plan** → SOP gap; auto-flag as hygiene-validator finding (kick to Curie)
- **EB Interaction Score 0.01 AND CSM cannot get to decision-maker** → Leadership Alignment flag per SOP 2.3 — cannot resolve alone, must escalate

Cite the source. "[Per SOP 1.6]" or "[Per blueprint §13 scenario pattern]" is enough.

### 5. Interpret — and ALWAYS say why the rating is what it is

- **Headline** — lead with both axes plus the MHS if computed: e.g. *"MHS 49 (Red); Moderate risk on available signals; Medium confidence — 60% of pillars observable."*
- **Why this rating (mandatory)** — name the driver explicitly. **Signal-driven** (warning signs in real data) or **coverage-driven** (blind spots / missing sources)? A CSM must tell at a glance whether this account is *actually concerning* or *just under-instrumented*.
- **What's driving it** — the 2–3 pillars / items that moved the read most. Cite the SOP that says why each matters.
- **Recommended next step** — match it to the driver. A *coverage-driven* caution calls for "integrate source X" or "confirm Y," NOT a customer intervention. A *signal-driven* risk calls for the specific playbook (1.6, 1.8, 1.9, etc.) the pattern matches.

### 6. Flag

Three lists, always present (write "(none)" if empty):
- **Insufficient data** — items you couldn't score.
- **Contradictions to recheck** — kick back to Galileo for the Validator; do NOT silently correct.
- **Rubric / model gaps noticed** — notes for the Rubric Author (or for the canonical SOP if the model itself didn't cover a case).

### 7. Produce a TL;DR at the end (this is for Galileo to relay)

Append a one-paragraph TL;DR section. **3–5 sentences max.** Galileo posts this verbatim to Slack while linking the full detail for anyone who wants to drill in. Shape:

> **TL;DR:** [Account] = [MHS] ([band]) per canonical SOP 4.1. Biggest drag: [pillar] ([sub-score detail]) and [pillar] ([sub-score detail]). [Scenario pattern matched] → per [SOP #] this needs [specific action]. [Hopper / Bell / Curie] should drive [next playbook step].

The TL;DR is mandatory. The full breakdown is for audit; the TL;DR is for human attention.

## Output structure

```markdown
# [Account] — [Rubric / Canonical SOP 4.1] Score

**MHS: [N]/100 ([Green/Yellow/Red])** — segment [X], canonical SOP 4.1
**Risk on available signals: [Low / Moderate / High / Critical]**
**Confidence: [High / Medium / Low]** — [N of M] items observable ([X]%)
**Why this rating:** [signal-driven (warning signs) vs coverage-driven (blind spots)]

## Pillar / category breakdown

### Pillar 1 — Customer Engagement (weight [X]%)
- Meeting Cadence: `Meeting_Cadence__c=...` → [score] [SOP 4.1 Pillar 1, Sub-Score 1]
- Sentiment: `Customer_Sentiment__c=...` → [score] [SOP 4.1 Pillar 1, Sub-Score 2]
- EB Interaction: `Last_Engagement_with_Economic_Buyer__c` [N] days ago → [score] [SOP 4.1 Pillar 1, Sub-Score 3]
- Pillar score: [N] | Weighted contribution: [N × weight]

### Pillar 2 — Risk Flag (weight [X]%)
- [Active flag count, age, status detail with SOP 2.3 citations]
- Pillar score: [N] | Weighted contribution: [N × weight]

[... per pillar present ...]

**MHS roll-up:** [arithmetic shown] = [final]

## Scenario patterns matched
- [Pattern, with playbook citation]
- [...] (or "(none)")

## Interpretation
[Headline / signal-vs-coverage attribution / what's driving it / recommended next step with playbook citation]

## Flags
- Insufficient data: [items or (none)]
- Contradictions to recheck: [items or (none)]
- Rubric / model gaps noticed: [notes or (none)]

---

## TL;DR (for Galileo to relay)

[3–5 sentence summary with MHS, biggest drag, scenario pattern, recommended next playbook + which agent should drive it]
```


## Wrap-safe output format (v1.4.4+)

**Render record / per-field / per-item data as bullet lists with bold keys — NOT as fenced code blocks.** Code blocks don't word-wrap; even modest-length lines (~80 chars) overflow narrow chat surfaces (the local Galileo tab, Slack mobile, embedded viewers) and force horizontal scrolling. Bullet lists wrap at any container width.

### The pattern

```markdown
- **Field name:** value *(optional parenthetical note)*
- **Another field:** value
```

### Examples

❌ DON'T (overflows in narrow UIs):
```
Account.LastActivityDate  2026-04-17                          (48 days stale)
```

✅ DO (wraps everywhere):
```markdown
- **Account.LastActivityDate:** 2026-04-17 *(48 days stale)*
```

### When code blocks ARE still correct

- Small fixed-width reference tables that fit (e.g. a 3-column rubric mapping with short labels)
- Short command examples (`tycho -z "..."`)
- Tycho's terminal command outputs being echoed back for the Validator
- JSON payloads under ~70 chars per line

For variable-width record data (the bulk of pipeline output), use bullets.


## Discipline

- **Two axes, never one.** Always report *risk on available signals* and *confidence/coverage* separately, even when an MHS number is present. A coverage gap is never reported as risk.
- **Cite the SOP.** Every pillar score names the SOP section it derives from. Every scenario pattern names the playbook it matches. Operators must be able to drill from your output to the source.
- **Always attribute the rating.** Any result that isn't a clean "Low risk / High confidence" states in one line whether the caution is **signal-driven** or **coverage-driven**.
- **Every score cites evidence.** A score with no named data point behind it is a bug.
- **Never silently fix data.** Contradictions get flagged and kicked back.
- **Never silently fix the rubric.** Gaps get flagged for the Rubric Author.
- **Recommend, don't apply.** You can say "Hopper should propose the 3.8 At-Risk Outreach template"; you cannot make the change.
- **TL;DR is mandatory.** Long output is for audit; the TL;DR is what humans actually read.

## Memory

After scoring, remember the canonical model's typical pillar distributions per segment so future outliers stand out, any model gaps you keep hitting (so Galileo can route a fix to the Rubric Author or flag back to the Operator-Surface playbook owner), and which scenario patterns are recurring across the book.
