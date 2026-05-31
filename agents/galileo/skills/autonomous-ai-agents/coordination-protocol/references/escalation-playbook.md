# Escalation playbook

The simple case is in `SKILL.md`: one worker, watchdog fires, post the block, stop polling. This file is for the messier cases.

## Escalation triggers (the full set)

| Trigger | Path |
|---|---|
| Silence past auto-retry threshold | Standard watchdog escalation. |
| Worker `ack` fails twice (tooling failure) | Escalate as **tooling**, not worker — name the suspected cause (multi-line `-z`, missing creds, wrapper crash). |
| Worker writes `blocker` | Immediate post, no watchdog steps. Blocker is a clean handoff, not a stall. |
| Worker output is malformed (no sign-off, wrong structure, hallucinated signals) twice in a row | Escalate as **discipline**. Note: the *first* malformed output is a normal correction (send the worker back per `agent-dispatch`), not an escalation. |
| Worker repeatedly produces low-confidence output for the same kind of task | Escalate as **fit** — the worker may need a SOUL revision or a model swap. Include 2+ examples. |
| Two workers in the same pipeline have stalled in a row | Escalate as **systemic** — likely environment (droplet, gateway, creds), not any single worker. |
| User-facing deadline exists and the watchdog timeline won't fit it | Escalate *before* the watchdog fires. Don't burn the 30-min budget on a task the user needed in 10. |

## The escalation message — exact shape

Post to `#galileo-updates` (channel `C0B6PHEG60H`):

```
Stalled task: <task_id> (<worker>)
Last activity: <ts of last ledger entry> (<silence_age> ago)
What it was doing: <one-line task summary>
What I tried: dispatched at <ts>; <ack/no-ack>; soft-poke at <ts>; retry at <ts>.
Last worker output: <paste or "none">
Need from human: <kill it / redispatch with new prompt / debug the worker / fix tooling>
```

Pick exactly one `Need from human`. Multiple asks dilute the escalation. If you genuinely need two things, post two escalations.

For non-stall escalations (blocker, malformed output, fit, systemic), keep the same skeleton but substitute the relevant fields. Always end with one explicit ask.

## Mid-pipeline escalation

If a worker in position N of a pipeline blocks or escalates:

1. **Do not auto-cancel** the run. The upstream artifacts are still valuable.
2. **Do not auto-skip** to position N+1. Downstream workers depend on N's output.
3. Post the escalation with the full pipeline context: which `run_id`, which position, what's already done.
4. Wait for the human to say one of: *redo step N*, *skip step N with this manual substitute*, or *abort the run*.
5. While waiting, do not dispatch further pipeline steps. Other unrelated work can continue.

Example escalation language for a pipeline stall:
```
Stalled task: run-2026-05-31-acme-4471/curie (curie)
Pipeline position: 3 of 5 (Euclid ✓ → Tycho ✓ → Curie ✗ → Kepler → Hopper)
Upstream artifacts ready: /home/hermes/botfather/runs/.../tycho-output.md
...
Need from human: redo Curie, or skip with manual validation note?
```

## Picking the right human

Default: post in `#galileo-updates` with no tag — the user reads the channel.

@-mention only when the escalation names a specific person's responsibility:
- Tooling failures (the `-z` wrapper, gateway, profile system) → tag the user (he owns the platform).
- Vendor cred problems (Salesforce, Slack, helpdesk) → tag the user; he's the admin per memory.
- Domain questions (what *should* the rubric weight, what does *engaged* mean) → tag whoever owns the rubric for that team. If unknown, don't guess; let the user route.

When in doubt: no tag, post in channel, let the user decide who needs to see it.

## After the human resolves

Once a human responds and the task is unblocked:
1. Append a `resumed` entry to `archive.jsonl` for the closed row (`{event:"resumed", by:"galileo", note:"<what the human said>"}`).
2. If the resolution is *redispatch*, treat it as a fresh task: new `task_id`, new `dispatched` row in `active.jsonl`, full watchdog cycle.
3. If the resolution is *skip with manual substitute*, write a `manual_substitute` row pointing at the artifact path the human provided, then dispatch the *next* pipeline step against that artifact.
4. If the resolution is *abort*, write an `aborted` row for every still-pending pipeline step. Don't leave them implicitly cancelled.

## What never to do

- Never silently take over a worker's task yourself "to keep the team moving." That's how Leo-the-doer creep starts. If a worker is broken, the human needs to know.
- Never escalate without trying the soft poke and one retry first (unless the trigger is `blocker`, `ack` double-failure, or a deadline you'll miss).
- Never post a second escalation for the same `task_id` before the human acknowledges the first. Dupes train the team to ignore the channel.
- Never close a row without a final entry (`done`, `escalated`, or `aborted`). Open-ended rows look like active work to the next polling cycle.
