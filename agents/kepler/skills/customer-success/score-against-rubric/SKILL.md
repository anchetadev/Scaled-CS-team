---
name: score-against-rubric
description: "Score validated CS account data against a Rubric Author rubric and interpret what it means (binary / 1-5 / weighted)."
version: 0.1.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [customer-success, scoring, rubric, interpretation, renewal-risk, health-score, data-analysis]
    related_skills: [build-audit-checklist]
---

# Score Against Rubric

Use this skill when Galileo dispatches account data plus a rubric and asks you to score it. You apply the rubric mechanically, cite the evidence behind every score, roll up to an overall result, and interpret what it means in plain English.

Load this when Galileo says things like "score this account against the renewal-risk rubric", "what does this data mean for account X", "run the health rubric on these accounts", or hands you a rubric + data together.

## When NOT to use

- Galileo asks whether the data is trustworthy / clean — that's the **Validator's** job, upstream and independent of you. Don't self-certify. Tell Galileo.
- Galileo hands you data with no rubric — you need a rubric to score against. Ask Galileo to get one from the **Rubric Author**.
- Galileo asks you to pull the data — that's the **Reader's** job.
- Galileo asks you to apply a fix / write a change — that's the **Controlled Executor's** job. You can recommend; you never apply.
- Galileo asks you to change the rubric — flag the gap to the **Rubric Author**; don't rewrite it.

## Prerequisites

You need BOTH:
1. **A rubric** — categories, items, each item's signal and scoring rule (binary / 1-5 / weighted). Authored by the Rubric Author.
2. **Validated account data** — already pulled by the Reader and confirmed trustworthy by the Validator.

If either is missing or ambiguous, stop and ask Galileo before scoring.

## Core method

### 1. Confirm inputs

Restate which rubric and which account(s) you're scoring, in one line. Surfaces mismatches early (wrong rubric for the data, etc.).

### 2. Score each item

For every item in the rubric:
- Apply the rubric's scoring rule exactly (binary → pass/fail; 1-5 → use the rubric's anchors; weighted → the rubric's weight).
- **Cite the data point** that drove the score. No score without a named piece of evidence.
- **State confidence** (high/med/low) based on how directly the data supports the score.
- If the data can't support the item, mark **"insufficient data"** — never guess to fill a gap.

Score faithfully. Do not invent criteria, reweight categories, or apply gut feel that isn't written in the rubric. The rubric is the ruler; you don't bend it.

### 3. Roll up — on TWO separate axes

Aggregate item scores into category scores and an overall, following the rubric's weighting. **Show the arithmetic.** If items were "insufficient data," state how you handled them (excluded, etc.) — don't hide the choice.

Then express the result on **two independent axes. Never collapse them into one number that hides which is which:**

- **Risk on available signals** — the risk band (Low / Moderate / High / Critical) implied by *only the items you could actually score*. Answers: "what does the data we DO have say?" A pile of green signals → **Low**, even if most of the rubric was unobservable.
- **Confidence (coverage)** — how much of the rubric was observable: `scored ÷ total`, as a %. Band it: **High** (≥70% observable), **Medium** (40–69%), **Low** (<40%). Answers: "how much of the picture can we see?"

These are orthogonal. A healthy account we can barely see is **Low risk / Low confidence** — NOT "Moderate risk." **A coverage gap is a visibility problem, never a risk signal. Never let missing data masquerade as risk.**

### 4. Interpret — and ALWAYS say why the rating is what it is

The part humans actually read. In plain English:
- **Headline** — lead with both axes: e.g. *"Low risk on available signals; low confidence — only 29% of the rubric is observable."*
- **Why this rating (mandatory)** — name the driver explicitly. Is any caution coming from **warning signs in the data** (signal-driven) or from **blind spots / missing data sources** (coverage-driven)? A stretched-thin CSM must tell at a glance whether this account is *actually concerning* or *just under-instrumented*. Never leave a non-"Low/High-confidence" rating unexplained.
- **What's driving it** — the 2–3 items that moved the available-signals read most.
- **Recommended next step** — match it to the driver: a *coverage-driven* caution calls for "integrate source X" or "confirm Y," NOT a customer intervention; a *signal-driven* risk calls for a real CS action. Don't tell a CSM to chase a healthy customer just because we can't see their product usage.

### 5. Flag

Three lists, always present (write "(none)" if empty):
- **Insufficient data** — items you couldn't score.
- **Contradictions to recheck** — data that looked impossible or internally inconsistent. Kick these back to Galileo for the Validator; do NOT silently correct them.
- **Rubric gaps noticed** — items the rubric should cover but doesn't, or anchors that were ambiguous. Notes for the Rubric Author.

## Output structure

```markdown
# [Account/entity] — [Rubric name] Score

**Risk on available signals: [Low / Moderate / High / Critical]**
**Confidence: [High / Medium / Low]** — [N of M] items observable ([X]%)
**Why this rating:** [one line — signal-driven (warning signs in the data) vs coverage-driven (blind spots / missing sources)]

## Scores by category

### [Category]
- [Item]: **[score]** — [data point cited] (confidence: high/med/low)
- Category roll-up: [score] [show weighting math]

## Interpretation
[headline / what's driving it / recommended next step]

## Flags
- Insufficient data: [items or (none)]
- Contradictions to recheck: [items or (none)]
- Rubric gaps noticed: [notes or (none)]

---

Scored [entity]: [risk band] on available signals, [confidence band] confidence ([N]/[M] observable). Caution is [signal-driven | coverage-driven | none].
```

## Discipline

- **Two axes, never one.** Always report *risk on available signals* and *confidence/coverage* separately. A coverage gap is never reported as risk — a healthy-but-barely-visible account is "Low risk / Low confidence," not "Moderate risk."
- **Always attribute the rating.** Any result that isn't a clean "Low risk / High confidence" states in one line whether the caution is **signal-driven** (real warning signs) or **coverage-driven** (blind spots). A CSM should never have to guess whether an account is actually at risk or just under-instrumented.
- **Every score cites evidence.** A score with no named data point behind it is a bug.
- **Never silently fix data.** Contradictions get flagged and kicked back, not corrected.
- **Never silently fix the rubric.** Gaps get flagged for the Rubric Author, not patched in place.
- **Recommend, don't apply.** Your output can say "renew outreach this week"; it cannot make the change.

## Memory

After scoring, remember the rubric's typical score distribution so future outliers stand out, and any rubric gaps you keep hitting (so Galileo can route a fix to the Rubric Author).
