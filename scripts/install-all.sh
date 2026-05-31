#!/bin/bash
# install-all.sh — Install all Scaled CS agents
# Usage: ./scripts/install-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
AGENTS_DIR="$REPO_DIR/agents"

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    Scaled Customer Success — Agent Installer             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check if Hermes is installed
if ! command -v hermes &> /dev/null; then
    echo "❌ Error: hermes command not found"
    echo "   Install Hermes Agent first: https://hermes-agent.nousresearch.com/docs/getting-started/quickstart"
    exit 1
fi

echo "📦 Installing agents..."
echo ""

# Install each agent
AGENTS=("galileo" "tycho" "curie" "hopper" "euclid" "kepler")

for agent in "${AGENTS[@]}"; do
    AGENT_DIR="$AGENTS_DIR/$agent"
    
    if [ ! -d "$AGENT_DIR" ]; then
        echo "⚠️  Skipping $agent — directory not found"
        continue
    fi
    
    echo "→ Installing $agent..."
    hermes profile install "$AGENT_DIR" --name "$agent" --alias 2>/dev/null || {
        echo "  ⚠️  $agent may already be installed. Skipping..."
    }
    echo ""
done

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║    ✅ Installation complete!                             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Installed agents:"
hermes profile list | grep -E "galileo|tycho|curie|hopper|euclid|kepler" || true
echo ""
echo "Next steps:"
echo "  1. Set up API keys in each agent's .env file"
echo "  2. Start Galileo's gateway: hermes gateway start -p galileo"
echo "  3. Chat with Galileo: hermes -p galileo"
echo ""
echo "For setup instructions, see: docs/setup-guide.md"
