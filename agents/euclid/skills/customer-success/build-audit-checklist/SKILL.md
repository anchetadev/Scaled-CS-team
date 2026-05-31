---
name: build-audit-checklist
description: "Build a structured CS audit checklist with a scoring rubric for any audit domain (renewal risk, onboarding QA, health-check prep, etc.)."
version: 0.1.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [customer-success, audit, checklist, scoring, rubric, sop, retention, renewal, onboarding, qa]
    related_skills: []
---

# Build Audit Checklist

Use this skill when Galileo dispatches a request to design or revise a CS audit checklist. The output is a structured markdown checklist with a clear scoring model that the Salesforce Reader and Hygiene + Score Validator can mechanically apply downstream.

Load this when Galileo says things like "draft a checklist for X", "build the rubric for our Y audit", "what would we check for Z?", "score this audit domain", or "revise the renewal-risk checklist with these inputs."

## When NOT to use

- Galileo wants you to score an existing checklist against a specific account — that's the **Data Analyst's** job. You define rubrics; you never apply them to real data. Tell Galileo.
- Galileo wants Salesforce data — that's the **Reader's** job. Tell Galileo.
- Galileo wants to know whether the data is trustworthy — that's the **Validator's** job. Tell Galileo.
- The request is for a customer-facing document (script, email, FAQ) — out of scope for the Rubric Author.

## Core method

Always follow these five steps in order. Do not skip ahead.

### 1. Restate the scope

One sentence. What audit, what's in, what's out.

> Example: "Renewal risk audit: surface customers in the 90 days before contract end whose probability of non-renewal warrants CSM intervention. In: usage signals, support history, account metadata. Out: pricing negotiation, legal redlines."

If the scope is ambiguous (e.g., "renewal" could mean churn risk OR expansion opportunity), ask Galileo to clarify before continuing.

### 2. Propose a framework

3-6 top-level categories the checklist will cover. Each category should be:
- **Distinct** — no overlap with another category.
- **Sourced from a clear signal** — usage data, ticket data, CRM metadata, human input, etc.
- **Actionable** — a low score in this category should suggest a recognizable next step.

> Example for renewal risk: (1) Product engagement, (2) Support sentiment, (3) Account health metadata, (4) Stakeholder coverage, (5) Commercial signals.

Present the framework to Galileo before drafting full items. He may approve, edit, or reroute.

### 3. Draft the checklist

For each category, write 3-8 items. Every item has exactly three parts:

- **The check** — a question or condition stated in plain English.
- **Signal** — the specific data source or observation the check relies on. If no signal exists yet, mark as `(no signal yet)` and flag in step 4.
- **Scoring** — one of:
  - **Binary** — yes/no, pass/fail.
  - **Scale 1-5** — with brief anchors at 1, 3, and 5.
  - **Weighted** — when an item contributes a percentage to a category roll-up.

Apply the self-test before keeping each item: *Is this measurable? Is it actionable? Does a real signal back it?* If any answer is no, cut it or rewrite it.

### 4. Flag gaps

List anything the audit logically needs but can't answer with current data. These are open questions for the human — usually a missing integration, a metric we don't track, or a judgment call only a CSM can make.

> Example: "Open question: do we have product-usage telemetry per account, or only per workspace? Affects how we score 'product engagement'."

### 5. Output the full checklist

Use this exact structure so the Validator can parse it later:

```markdown
# [Audit name] Checklist

**Scope:** [one-sentence restatement]

## [Category 1 name]

1. **Check:** [the question/condition]
   **Signal:** [data source]
   **Scoring:** [binary | scale 1-5 (anchors: 1=…, 3=…, 5=…) | weighted N%]

2. ...

## [Category 2 name]

...

## Open questions

- [gap 1]
- [gap 2]

---

Checklist drafted: N categories, M items, K open questions.
```

## Output discipline

- Never ship a checklist without the open-questions section, even if it's empty (write `- (none)` so downstream agents know you considered it).
- Never invent signals you can't name. `(no signal yet)` is the honest answer.
- Never expand scope mid-draft. If a new category seems necessary, surface it as an open question; Galileo decides.

## Memory

After producing a checklist, write the audit name and framework (top-level categories) to memory. If a future request matches an existing audit's shape, propose reusing the framework rather than starting from scratch.
