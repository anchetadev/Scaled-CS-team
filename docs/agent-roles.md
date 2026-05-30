# Agent Roles

Detailed breakdown of each agent's role, responsibilities, and boundaries.

## Overview

The Scaled Customer Success platform uses a team of 5 specialized agents, each with strict role boundaries. This separation ensures that:

- Mistakes can't cascade across agents
- Human approval is required for risky operations
- Each agent does ONE thing well
- Galileo coordinates without doing everything himself

## Galileo — Supervisor

### Role
The human-facing coordinator. Galileo lives in Slack and is the single point of contact for the team.

### Responsibilities
- **Answer questions** — Direct responses for one-off, conversational, or judgment-based queries
- **Dispatch workers** — Send work to the appropriate specialized agent
- **Enforce boundaries** — Ensure agents stay in their lane
- **Report results** — Translate worker output into plain English

### Capabilities
- Full tool access (terminal, files, web, code)
- Spawns and manages worker agents
- Accesses all agent outputs
- Makes coordination decisions

### Boundaries
- Does NOT directly access Salesforce (delegates to SF Reader)
- Does NOT validate data (delegates to Validator)
- Does NOT execute changes (delegates to Executor)
- Does NOT create frameworks (delegates to SOP Analyst)

### When to Use
- User has a question
- User wants to check account health
- User wants to fix an issue
- User needs a report

---

## SOP Analyst — Framework Builder

### Role
Creates checklists, scoring rubrics, and validation templates that other agents use.

### Responsibilities
- **Build checklists** — Step-by-step validation criteria
- **Create scoring frameworks** — Weighted health score components
- **Design templates** — Reusable document templates
- **Document procedures** — Standard operating procedures

### Capabilities
- Logic and documentation only
- Produces structured YAML/JSON output
- Creates reusable frameworks

### Boundaries
- Does NOT access Salesforce
- Does NOT validate data
- Does NOT execute changes
- Does NOT access external systems

### When to Use
- Need a new validation checklist
- Need to update scoring criteria
- Need a new template
- Need to document a procedure

---

## Analyst — Traditional Data Analysis

### Role
Analyzes data and extracts insights — trends, patterns, and actionable recommendations.

### Responsibilities
- **Analyze trends** — Health score changes, engagement patterns over time
- **Identify patterns** — Common characteristics of at-risk or high-performing accounts
- **Generate insights** — Translate data into actionable recommendations
- **Produce reports** — Summaries, dashboards, analytical narratives

### Capabilities
- Trend analysis
- Pattern detection
- Report generation
- Data-driven recommendations

### Boundaries
- Does NOT write to Salesforce
- Does NOT execute changes
- Does NOT create frameworks (SOP Analyst does that)
- Does NOT access external systems

### When to Use
- Need to understand why a metric changed
- Need to identify patterns in account data
- Need a report or summary
- Need data-driven recommendations

---

## SF Reader — Data Retriever

### Role
Pulls account and ticket data from Salesforce. Read-only access.

### Responsibilities
- **Query accounts** — Name, health score, CSM, renewal date, ARR, segment
- **Query tickets** — Status, priority, owner, created date, resolution
- **Query contacts** — Name, email, role, last activity
- **Query opportunities** — Stage, amount, close date, owner

### Capabilities
- SOQL queries
- Data extraction
- Structured output (JSON, tables)

### Boundaries
- Does NOT write to Salesforce
- Does NOT delete records
- Does NOT modify data
- Does NOT validate data

### When to Use
- Need account data
- Need ticket history
- Need contact information
- Need opportunity data

---

## Validator — Issue Detector

### Role
Flags account hygiene issues against the SOP checklist. Skeptical, blunt, picky.

### Responsibilities
- **Check hygiene** — Required fields, stale data, naming conventions
- **Score accounts** — Health score calculation and validation
- **Flag issues** — Severity ratings, recommendations
- **Report findings** — Structured validation reports

### Capabilities
- Data validation
- Checklist enforcement
- Issue detection

### Boundaries
- Does NOT write to Salesforce
- Does NOT fix issues
- Does NOT make business decisions
- Does NOT access external systems

### When to Use
- Need to validate account data
- Need to check hygiene
- Need to score accounts
- Need to find issues

---

## Executor — Change Writer

### Role
Writes changes to Salesforce. Requires per-batch human approval.

### Responsibilities
- **Prepare changes** — Group related changes into batches
- **Request approval** — Present batches for human review
- **Execute changes** — Apply approved changes
- **Report results** — Confirm what was changed

### Capabilities
- SOQL DML operations (INSERT, UPDATE)
- Batch processing
- Rollback support

### Boundaries
- Does NOT execute without approval
- Does NOT delete records
- Does NOT make business decisions
- Does NOT validate data

### When to Use
- Need to update a record
- Need to create a record
- Need to fix an issue
- Need to apply changes

---

## Interaction Patterns

### Pattern 1: Health Check

```
User: "Check health of Acme Corp"
  │
  ├──► SF Reader: Pull account data
  ├──► SF Reader: Pull ticket history
  │
  ├──► Validator: Check hygiene
  ├──► Validator: Score account
  │
  └──► Galileo: Compile report
```

### Pattern 2: Issue Fix

```
User: "Fix the missing CSM on Acme Corp"
  │
  ├──► SF Reader: Pull current data
  ├──► Validator: Confirm issue
  │
  ├──► Executor: Prepare change batch
  ├──► Executor: Request approval
  │
  User: "Approved"
  │
  ├──► Executor: Execute change
  └──► Galileo: Confirm success
```

### Pattern 3: Framework Creation

```
User: "Create a new checklist for Q2 reviews"
  │
  ├──► SOP Analyst: Build checklist
  ├──► SOP Analyst: Define scoring criteria
  │
  └──► Galileo: Report checklist created
```

### Pattern 4: Bulk Review

```
User: "Review all Enterprise accounts"
  │
  ├──► SF Reader: Pull Enterprise accounts (parallel)
  │
  ├──► Validator: Check Account A (parallel)
  ├──► Validator: Check Account B (parallel)
  ├──► Validator: Check Account C (parallel)
  │
  └──► Galileo: Compile bulk report
```

## Boundary Enforcement

Galileo enforces boundaries by:

1. **Checking agent capabilities** — Before dispatching, verify the agent can do the task
2. **Redirecting misrequests** — If an agent tries to do something outside its role, redirect
3. **Requiring approval** — For Executor operations, always require human approval
4. **Monitoring output** — Review agent output before passing to user

## Adding New Agents

When adding a new agent:

1. Define its role clearly
2. Set strict boundaries
3. Document capabilities
4. Update Galileo's SOUL.md to include it in the roster
5. Update this file with the new agent's details
