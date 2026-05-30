# Extending the Platform

Guide for adding new agents to the Scaled Customer Success platform.

## When to Add a New Agent

Add a new agent when:

- You have a **recurring task** that doesn't fit existing agents
- The task requires **specialized knowledge** or tools
- The task needs **strict boundaries** to prevent mistakes
- Multiple agents would need to coordinate on this task

Don't add a new agent when:

- The task is **one-off** (use Galileo directly)
- The task fits an **existing agent's role** (delegate to them)
- The task is **simple enough** for Galileo to handle

## Step-by-Step Guide

### 1. Define the Agent's Role

Answer these questions:

- **What is its primary responsibility?** (One sentence)
- **What does it produce?** (Output format)
- **What does it NEVER do?** (Boundaries)
- **When should Galileo dispatch to it?** (Triggers)

Example:
```
Role: Email Outreach Agent
Responsibility: Draft and send customer emails
Output: Email drafts, send confirmations
Boundaries: Never sends without approval, never modifies Salesforce
Triggers: User asks to email a customer, scheduled outreach
```

### 2. Create the Agent Directory

```bash
mkdir -p agents/email-outreach
```

### 3. Create SOUL.md

Define the agent's personality and constraints:

```markdown
You are the Email Outreach Agent — a specialized email agent for the Scaled Customer Success platform. You work under Galileo's supervision.

# Your role

You draft and send customer emails. You always get approval before sending.

# Core traits

- **Professional** — Emails are well-written, on-brand
- **Approval-seeking** — Never sends without explicit approval
- **Template-aware** — Uses company templates when available
- **Personalization** — Customizes emails for each customer

# What you can do

- Draft emails from templates
- Personalize content for specific customers
- Request approval before sending
- Track send status

# Boundaries

- You do NOT send without approval
- You do NOT modify Salesforce data
- You do NOT make business decisions about email content
```

### 4. Create distribution.yaml

```yaml
name: email-outreach
version: 1.0.0
description: "Email outreach agent. Drafts and sends customer emails with approval workflow."
hermes_requires: ">=0.13.0"
author: "Your Name"
license: "MIT"

env_requires:
  - name: OPENROUTER_API_KEY
    description: "OpenRouter API key for model access"
    required: true

  - name: SMTP_HOST
    description: "SMTP server hostname"
    required: true

  - name: SMTP_USERNAME
    description: "SMTP username"
    required: true

  - name: SMTP_PASSWORD
    description: "SMTP password"
    required: true
```

### 5. Create config.yaml

```yaml
model:
  default: xiaomi/mimo-v2.5-pro
  provider: openrouter

agent:
  max_turns: 50
```

### 6. Update Galileo's SOUL.md

Add the new agent to Galileo's roster:

```markdown
# Your team of agents

...

- **Email Outreach Agent** — Drafts and sends customer emails; approval-seeking, professional. SMTP credentials.
```

### 7. Update Documentation

Update these files:

- **README.md** — Add the new agent to the agents table
- **docs/agent-roles.md** — Add a detailed section for the new agent
- **docs/architecture.md** — Update the architecture diagram

### 8. Test the Agent

```bash
# Install locally for testing
hermes profile install ./agents/email-outreach --name email-outreach-test

# Test basic functionality
hermes -p email-outreach-test -q "What can you do?"

# Test with Galileo
hermes -p galileo -q "Draft an email to Acme Corp"
```

### 9. Submit a Pull Request

```bash
git add agents/email-outreach/
git commit -m "feat: add email-outreach agent"
git push origin feature/email-outreach
# Create PR on GitHub
```

## Agent Design Principles

### Single Responsibility

Each agent does ONE thing:
- SF Reader → reads data
- Validator → validates data
- Executor → writes data
- SOP Analyst → creates frameworks

Don't create an agent that does multiple unrelated tasks.

### Strict Boundaries

Define what the agent CANNOT do:
- "You do NOT write to Salesforce"
- "You do NOT send without approval"
- "You do NOT make business decisions"

Boundaries prevent mistakes from cascading.

### Clear Output Format

Define how the agent reports results:
- JSON for programmatic consumption
- Markdown tables for human readability
- Structured messages for Galileo to parse

### Error Handling

Define how the agent handles errors:
- What to do when API limits are reached
- What to do when permissions are denied
- What to do when input is invalid

## Example: Notification Agent

Here's a complete example for a notification agent:

### SOUL.md

```markdown
You are the Notification Agent — a specialized notification agent for the Scaled Customer Success platform. You work under Galileo's supervision.

# Your role

You send notifications to customers and internal teams. You always get approval before sending external notifications.

# Core traits

- **Timely** — Sends notifications when they're needed
- **Approval-seeking** — External notifications require approval
- **Multi-channel** — Can send via email, Slack, SMS
- **Template-aware** — Uses company templates

# What you can do

- Send internal Slack notifications
- Draft external notifications
- Request approval for external sends
- Track notification status

# Boundaries

- You do NOT send external notifications without approval
- You do NOT modify customer data
- You do NOT make business decisions about notification content
```

### distribution.yaml

```yaml
name: notifications
version: 1.0.0
description: "Notification agent. Sends internal and external notifications with approval workflow."
hermes_requires: ">=0.13.0"
author: "Your Name"
license: "MIT"

env_requires:
  - name: OPENROUTER_API_KEY
    description: "OpenRouter API key for model access"
    required: true

  - name: SLACK_WEBHOOK_URL
    description: "Slack webhook URL for internal notifications"
    required: false

  - name: SENDGRID_API_KEY
    description: "SendGrid API key for email notifications"
    required: false
```

## Advanced: Agent Communication

Agents communicate through Galileo:

```
User: "Notify Acme Corp about their renewal"
  │
  ├──► SF Reader: Pull contact info
  │
  ├──► Notifications Agent: Draft notification
  │
  ├──► Galileo: Present draft to user
  │
  User: "Approved"
  │
  ├──► Notifications Agent: Send notification
  │
  └──► Galileo: Confirm success
```

Agents don't talk to each other directly — Galileo coordinates everything.

## Checklist for New Agents

- [ ] Clear role definition
- [ ] Strict boundaries documented
- [ ] SOUL.md created
- [ ] distribution.yaml created
- [ ] config.yaml created
- [ ] README.md created
- [ ] Galileo's SOUL.md updated
- [ ] Documentation updated
- [ ] Tested locally
- [ ] PR submitted
