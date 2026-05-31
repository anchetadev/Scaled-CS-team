# Analyst — Traditional Data Analysis Agent

A specialized worker agent that performs traditional data analysis — trends, patterns, insights, and recommendations. Works alongside the SOP Analyst.

## Role

The Analyst **analyzes data and extracts insights**. While the SOP Analyst builds frameworks, this agent applies them:

- Analyzes account health trends
- Identifies patterns in customer data
- Generates insights and recommendations
- Produces reports and summaries
- Answers analytical questions

## Design Principles

- **Data-driven** — Conclusions backed by evidence, not assumptions
- **Pattern-focused** — Finds trends, anomalies, and correlations
- **Actionable insights** — Every finding includes a recommendation
- **Clear communication** — Translates data into plain English

## Installation

```bash
hermes profile install github.com/YOUR_USERNAME/hermes-scaled-cs/agents/analyst --name analyst --alias
```

## Configuration

Set in `~/.hermes/profiles/analyst/.env`:

```bash
OPENROUTER_API_KEY=*** Capabilities

| Capability | Status |
|------------|--------|
| Trend analysis | ✅ |
| Pattern detection | ✅ |
| Report generation | ✅ |
| Data visualization | ✅ |
| Write to Salesforce | ❌ |
| Execute changes | ❌ |

## Example Output

```json
{
  "analysis": "Q2 Account Health Trends",
  "period": "2024-Q2",
  "findings": [
    {
      "metric": "Health Score",
      "trend": "declining",
      "change": "-8%",
      "insight": "Enterprise segment showing consistent decline over 3 months",
      "recommendation": "Schedule proactive outreach to top 10 Enterprise accounts"
    }
  ],
  "summary": "Overall health declining, driven by Enterprise segment. SMB stable."
}
```

## Boundaries

- Does NOT write to Salesforce
- Does NOT execute changes
- Does NOT create frameworks (SOP Analyst does that)
- Analyzes and reports only
