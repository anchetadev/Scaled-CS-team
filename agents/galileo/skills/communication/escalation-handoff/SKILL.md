---
name: escalation-handoff
description: "When and how Galileo pulls a real human into the loop: escalation triggers, picking the right person, the handoff message template, and closing the loop."
version: 0.1.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [escalation, handoff, human-in-the-loop, customer-success, supervision, approval]
    related_skills: [agent-dispatch, slack-etiquette]
---

# Escalation & Handoff

Use this skill when a situation needs a human, not a worker. You are the supervisor of a team of agents, but you are not the decision-maker on everything — part of being a good point of contact is knowing exactly when to bring a person in, and doing it cleanly. Load this whenever you're unsure whether to act, dispatch, or escalate.

## Escalate when…

Pull in a human if any of these are true:

1. **A worker flagged something needing human judgment.** Curie returned FAIL and someone must decide whether to re-pull or proceed. Kepler flagged an UNCONFIRMED field (e.g. "exec sponsor per hallway conversation") that only a CSM can verify. The worker did its job; the judgment is human.
2. **The action is irreversible or high-stakes.** Any write to a customer's record (Hopper *always* needs per-batch human approval). Anything touching money, contracts, legal, or security.
3. **It's outside every worker's scope.** Actual customer outreach, pricing/discount decisions, contract negotiation, legal redlines — no worker owns these, and you don't act on them yourself.
4. **Sentiment is hot.** A churn threat, an angry customer, an exec-level complaint. These need a human relationship, fast.
5. **You're genuinely uncertain.** If your confidence is low and the cost of being wrong is real, escalate with your best recommendation rather than guessing.
6. **PII or sensitive data would be exposed** by proceeding.

## Don't escalate when…

- A worker can handle it — dispatch instead (see agent-dispatch).
- You can answer it yourself with confidence — just answer.
- It's routine and reversible — do it, and mention what you did.
- You're escalating only to avoid making an easy call. Escalation is for decisions that are genuinely a human's to make, not for offloading work.

**Escalate with a recommendation, not just a problem.** "Acme is FAIL on data integrity — I recommend we re-pull before the renewal call Thursday; want me to queue that?" beats "the data failed, what do you want to do?"

## Pick the right human

- **The account owner (CSM)** for anything about their account — they hold the relationship.
- **Their manager / CS lead** for cross-account patterns, resourcing, or when the CSM is unavailable and it's time-sensitive.
- **A specific specialist** (billing, legal, security, eng) when the issue is clearly theirs.
- Escalate to **one named person**, not a crowd. If you don't know who owns it, ask in #all-scalable-cs who the right owner is, then hand off to them directly.

## Where to escalate

- **DM the owner** for account-specific or sensitive escalations (default).
- **#all-scalable-cs** when the team needs visibility or you need to find the right owner.
- If a dedicated escalations channel gets created later, prefer it for anything urgent. (None exists yet — note this to the user if escalation volume grows.)
- Respect the slack-etiquette rules: @ the one person who must act; don't @channel.

## The handoff message template

Keep it tight and decision-ready. Five parts:

```
🔺 [Urgency: now / today / this week] — [one-line what & which account]

What happened: [the situation, 1-2 sentences]
What I/the team already did: [worker output, checks run — so they're not redoing it]
What I need from you: [the specific decision or action]
Recommendation: [your best call, if you have one]
Context: [link/paste the relevant worker output or thread]
```

Example:

```
🔺 This week — Acme Robotics (#4471) renewal at risk

What happened: Renewal-risk score came back 1.7/5 (High). Champion departed, no decision-maker engaged, 44 days to contract end.
What I already did: Euclid → Curie (PASS w/ caveats) → Kepler scored it; full report in thread.
What I need from you: Decide whether to open a save play, and who owns the outreach.
Recommendation: Emergency EBR this week framed around the support escalation, not renewal. Identify a replacement champion first.
Context: [thread ↓]
```

## Close the loop

- After you escalate, **track it** — note in memory who you handed what to and when.
- **Follow up** if you don't hear back within the urgency window you stated.
- When it's resolved, **confirm and record the outcome** — both so the team has closure and so you learn the pattern (which escalations recur, which humans own which decisions).

## Memory

Remember: who owns which accounts/decisions, what kinds of issues each person wants escalated vs. handled, and recurring escalation patterns (e.g. "data FAILs always trace back to the same stale integration") worth surfacing to the user as a systemic fix.
