# Setup Guide

Complete setup instructions for the Scaled Customer Success agent platform.

## Prerequisites

### Required Software

1. **Hermes Agent** — Install from [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
   ```bash
   curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
   ```

2. **Git** — For cloning the repository
   ```bash
   # macOS
   brew install git
   
   # Ubuntu/Debian
   sudo apt install git
   
   # Windows
   # Download from https://git-scm.com/
   ```

### Required Accounts

1. **OpenRouter** (or alternative LLM provider)
   - Sign up at [openrouter.ai](https://openrouter.ai)
   - Get your API key from the dashboard

2. **Slack** (for Slack integration)
   - Create a Slack workspace or use existing
   - Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps)
   - Enable Socket Mode
   - Install to workspace

3. **Salesforce** (for data agents)
   - Salesforce user account with API access
   - Security token (Profile → Settings → Reset Security Token)

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/hermes-scaled-cs.git
cd hermes-scaled-cs
```

### Step 2: Run the Installer

```bash
chmod +x scripts/install-all.sh
./scripts/install-all.sh
```

This will install all 5 agents as Hermes profiles:
- `galileo` — Supervisor
- `sf-reader` — Salesforce Reader
- `validator` — Hygiene Validator
- `executor` — Controlled Executor
- `sop-analyst` — SOP Analyst

### Step 3: Verify Installation

```bash
hermes profile list
```

You should see all 5 profiles listed.

## Configuration

### Galileo (Supervisor)

Edit `~/.hermes/profiles/galileo/.env`:

```bash
# Required: Model access
OPENROUTER_API_KEY=your_openrouter_key_here

# Required: Slack integration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Optional: Salesforce (if Galileo needs direct access)
SALESFORCE_USERNAME=your@email.com
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_token
```

### SF Reader

Edit `~/.hermes/profiles/sf-reader/.env`:

```bash
# Required: Model access
OPENROUTER_API_KEY=your_openrouter_key_here

# Required: Salesforce credentials
SALESFORCE_USERNAME=your@email.com
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_token
```

### Executor

Edit `~/.hermes/profiles/executor/.env`:

```bash
# Required: Model access
OPENROUTER_API_KEY=your_openrouter_key_here

# Required: Salesforce credentials (use a dedicated write user if possible)
SALESFORCE_USERNAME=your@email.com
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_token
```

### Validator & SOP Analyst

Edit `~/.hermes/profiles/validator/.env` and `~/.hermes/profiles/sop-analyst/.env`:

```bash
# Required: Model access only
OPENROUTER_API_KEY=your_openrouter_key_here
```

## Slack Setup

### Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App"
3. Choose "From scratch"
4. Name: "Scaled CS Bot" (or similar)
5. Select your workspace

### Enable Socket Mode

1. Go to "Socket Mode" in the left sidebar
2. Enable Socket Mode
3. Generate an app-level token with `connections:write` scope
4. Copy the token (starts with `xapp-`)

### Set Bot Permissions

1. Go to "OAuth & Permissions"
2. Add these Bot Token Scopes:
   - `app_mentions:read`
   - `chat:write`
   - `channels:history`
   - `groups:history`
   - `im:history`
   - `mpim:history`

### Install to Workspace

1. Click "Install to Workspace"
2. Authorize the app
3. Copy the Bot User OAuth Token (starts with `xoxb-`)

### Start the Gateway

```bash
hermes gateway start -p galileo
```

## Testing

### Test Individual Agents

```bash
# Test Galileo
hermes -p galileo -q "Hello, who are you?"

# Test SF Reader
hermes -p sf-reader -q "What can you query?"

# Test Validator
hermes -p validator -q "What do you validate?"

# Test Executor
hermes -p executor -q "What is your approval workflow?"

# Test SOP Analyst
hermes -p sop-analyst -q "What kind of checklists can you create?"
```

### Test the Full Workflow

1. Start Galileo's gateway
2. Send a message in Slack: "Check the health of Acme Corp"
3. Watch Galileo coordinate the workers
4. Verify the results

## Troubleshooting

### Common Issues

**"Profile not found"**
```bash
# Re-run the installer
./scripts/install-all.sh
```

**"API key not set"**
```bash
# Check the .env file
cat ~/.hermes/profiles/galileo/.env

# Verify the key is set
hermes -p galileo -q "What model are you using?"
```

**"Slack connection failed"**
```bash
# Check gateway status
hermes gateway status -p galileo

# View logs
tail -f ~/.hermes/profiles/galileo/logs/gateway.log
```

**"Salesforce connection failed"**
```bash
# Test credentials
hermes -p sf-reader -q "Test Salesforce connection"

# Check if security token is appended to password
# Password should be: your_password + security_token
```

### Getting Help

1. Check the [Hermes Agent docs](https://hermes-agent.nousresearch.com/docs/)
2. Review agent logs in `~/.hermes/profiles/<agent>/logs/`
3. Open an issue on GitHub

## Next Steps

- Read [Agent Roles](agent-roles.md) to understand who does what
- Review [Architecture](architecture.md) for system design details
- Check [Extending](extending.md) to add new agents
