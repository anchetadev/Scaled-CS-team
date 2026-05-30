# Architecture

Detailed architecture of the Scaled Customer Success agent platform.

## System Overview

The platform consists of 5 coordinated agents that work together to manage account health at scale. Each agent has a specific role and strict boundaries to prevent mistakes.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Slack Team                                │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                         GALILEO                               │  │
│  │                   (Supervisor / Bot Father)                   │  │
│  │                                                               │  │
│  │  • Human-facing front door                                   │  │
│  │  • Spawns and coordinates workers                            │  │
│  │  • Enforces role boundaries                                  │  │
│  │  • Reports results in plain English                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                 │                                   │
│           ┌─────────────────────┼─────────────────────┐             │
│           │                     │                     │             │
│           ▼                     ▼                     ▼             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   SOP ANALYST   │  │    SF READER    │  │   VALIDATOR     │     │
│  │                 │  │                 │  │                 │     │
│  │ • Builds        │  │ • Pulls account │  │ • Flags hygiene │     │
│  │   checklists    │  │   data          │  │   issues        │     │
│  │ • Creates       │  │ • Queries       │  │ • Scores        │     │
│  │   scoring       │  │   tickets       │  │   accounts      │     │
│  │   frameworks    │  │ • Read-only     │  │ • No write      │     │
│  │ • No external   │  │   access        │  │   access        │     │
│  │   access        │  │                 │  │                 │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                 │                                   │
│                                 ▼                                   │
│                      ┌─────────────────┐                            │
│                      │    EXECUTOR     │                            │
│                      │                 │                            │
│                      │ • Writes to SF  │                            │
│                      │ • Requires      │                            │
│                      │   approval      │                            │
│                      │ • Audit trail   │                            │
│                      │ • Rollback      │                            │
│                      │   ready         │                            │
│                      └─────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Agent Responsibilities

### Galileo (Supervisor)
- **Primary role**: Human interface and coordination
- **Capabilities**: Full tool access, spawns workers, enforces boundaries
- **Access level**: Orchestration (doesn't directly access Salesforce)
- **Personality**: Warm, patient teacher, delegator by default

### SOP Analyst
- **Primary role**: Framework creation
- **Capabilities**: Logic and documentation only
- **Access level**: None (no external systems)
- **Output**: Checklists, scoring rubrics, templates, procedures

### SF Reader
- **Primary role**: Data retrieval
- **Capabilities**: SOQL queries, data extraction
- **Access level**: Read-only Salesforce
- **Output**: Account data, ticket history, contact info, opportunities

### Validator
- **Primary role**: Issue detection
- **Capabilities**: Data validation, checklist enforcement
- **Access level**: None (receives data from SF Reader)
- **Output**: Validation reports, issue flags, severity ratings

### Executor
- **Primary role**: Change execution
- **Capabilities**: SOQL DML operations
- **Access level**: Write Salesforce (with approval)
- **Output**: Change confirmations, rollback capabilities

## Data Flow

### Typical Workflow

```
1. User asks Galileo: "Check health of Acme Corp"
                         │
2. Galileo dispatches SF Reader ◄──────────────────────┘
                         │
3. SF Reader queries Salesforce ──► Returns account data
                         │
4. Galileo dispatches Validator ◄──────────────────────┘
                         │
5. Validator checks against SOP ──► Returns issues list
                         │
6. Galileo presents findings to user
                         │
7. User says: "Fix the missing CSM"
                         │
8. Galileo dispatches Executor ◄──────────────────────┘
                         │
9. Executor prepares change batch ──► Requests approval
                         │
10. User approves
                         │
11. Executor executes change ──► Reports success
                         │
12. Galileo confirms to user
```

### Parallel Workflows

Galileo can dispatch multiple agents simultaneously:

```
User: "Review all Enterprise accounts"
         │
         ├──► SF Reader: Pull Enterprise accounts
         ├──► SF Reader: Pull ticket history (parallel)
         └──► SOP Analyst: Prepare checklist
                │
         ◄──────┘ (all complete)
         │
         ├──► Validator: Check Account A
         ├──► Validator: Check Account B
         └──► Validator: Check Account C (parallel)
                │
         ◄──────┘ (all complete)
         │
    Galileo: Compile report
```

## Security Model

### Access Boundaries

| Agent | Salesforce | External APIs | File System | Network |
|-------|------------|---------------|-------------|---------|
| Galileo | Via workers | ✅ | ✅ | ✅ |
| SOP Analyst | ❌ | ❌ | ✅ | ❌ |
| SF Reader | Read-only | ✅ | ❌ | ✅ |
| Validator | ❌ | ❌ | ❌ | ❌ |
| Executor | Write (approved) | ✅ | ❌ | ✅ |

### Why the Split?

- **Reader/Executor separation** — A bug in the Reader can't corrupt data
- **Validator isolation** — Pure logic, no side effects
- **Executor approval** — Human-in-the-loop prevents mistakes
- **SOP Analyst sandboxed** — Framework creation only, no execution

## Error Handling

### Agent-Level Errors

Each agent handles its own errors:
- **SF Reader**: API limits, query timeouts, permission errors
- **Validator**: Invalid data, missing fields, edge cases
- **Executor**: Validation errors, permission denied, partial failures

### System-Level Errors

Galileo handles system-wide issues:
- **Agent unresponsive** — Retry with backoff, then escalate to human
- **Conflicting results** — Present both sides, let human decide
- **Cascading failures** — Stop workflow, report status, await guidance

## Scaling Considerations

### Current Design

- Single Galileo instance coordinates all work
- Workers are spawned on-demand
- Each worker is stateless (no persistent memory)

### Future Scaling

- **Multiple Galileos** — Different teams, different Slack channels
- **Worker pools** — Pre-spawned workers for faster response
- **Persistent workers** — Remember context across sessions
- **Distributed execution** — Workers on different machines

## Integration Points

### Slack

- Galileo lives in Slack as the team's interface
- Workers communicate through Galileo (not directly to Slack)
- Human approval happens in Slack threads

### Salesforce

- SF Reader uses read-only API credentials
- Executor uses write API credentials (separate user)
- No direct Salesforce access for other agents

### Hermes Agent

- Built on Hermes Agent framework
- Uses profiles for agent isolation
- Leverages Hermes skills for capability extension
