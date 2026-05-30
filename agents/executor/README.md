# Executor — Controlled Salesforce Writer

A specialized worker agent that writes changes back to Salesforce. Slow, deliberate, and confirmation-seeking. Requires per-batch human approval.

## Role

The Executor **writes changes to Salesforce only with approval**. It:

- Receives fix instructions from Galileo
- Prepares change batches for review
- Requests human approval before executing
- Executes approved changes
- Reports results back to Galileo

## Design Principles

- **Slow and deliberate** — Never rushes. Double-checks every change.
- **Confirmation-seeking** — Always asks before acting. "Are you sure?" is its default state.
- **Per-batch approval** — Groups changes into batches, requires approval for each batch.
- **Audit trail** — Logs every change made, with before/after values.
- **Rollback ready** — Can undo changes if something goes wrong.

## Installation

```bash
hermes profile install github.com/YOUR_USERNAME/hermes-scaled-cs/agents/executor --name executor --alias
```

## Configuration

Set in `~/.hermes/profiles/executor/.env`:

```bash
OPENROUTER_API_KEY=*** SALESFORCE_SECURITY_TOKEN=*** Capabilities

| Capability | Status |
|------------|--------|
| Update records | ✅ (with approval) |
| Create records | ✅ (with approval) |
| Delete records | ❌ |
| Bulk operations | ✅ (with approval) |
| Rollback changes | ✅ |

## Approval Workflow

```
1. Galileo dispatches fix instructions
2. Executor prepares change batch
3. Executor presents batch for review:
   ┌─────────────────────────────────────────┐
   │ CHANGE BATCH #001                       │
   │ Account: Acme Corp (001XX000003DGP0)    │
   │ Changes:                                │
   │   • CSM__c: null → "Jane Smith"         │
   │   • Segment__c: "Enterprise"            │
   │                                         │
   │ Approve? [y/n]                          │
   └─────────────────────────────────────────┘
4. Human approves → Executor executes
5. Executor reports results
```
