# Brief: Contract Validation & Dispatch Hardening

**Project:** `/home/hermes/hermes-scaled-cs`
**Author:** Galileo (for Claude Code with Opus)
**Date:** 2026-05-31
**Goal:** Prevent contract ↔ implementation drift from ever silently breaking worker dispatches again.

---

## Problem

In v1.2.0, the worker-ledger-contract.md referenced a per-worker shard path (`active.<profile>.jsonl`) while production used a single shared file (`active.jsonl`). Workers dispatched against stale docs would write to the wrong file, and the watchdog would see silence. The v1.2.1 patch aligned docs with production, but there's nothing preventing this class of drift from recurring.

## What to build

A **pre-flight validation script** that Galileo runs before every dispatch (and that can also be run standalone). It catches contract ↔ reality mismatches *before* a worker is fired.

### Component 1: `validate-contract.sh` (or `.py` — your call)

**Location:** `/home/hermes/hermes-scaled-cs/scripts/validate-contract.sh`

**What it checks (all must pass, exit 0; any fail, exit 1 with details):**

1. **File-path existence.** Parse every absolute path mentioned in `docs/worker-ledger-contract.md` and `agents/galileo/skills/autonomous-ai-agents/coordination-protocol/references/ledger-format.md`. Verify each path either:
   - Exists on disk (for files/dirs that should already exist), OR
   - Has its parent directory writable (for files that get created at runtime, like `active.jsonl`)

   Specific paths to check:
   - `/home/hermes/botfather/status/active.jsonl` — parent dir must exist and be writable
   - `/home/hermes/botfather/status/archive.jsonl` — parent dir must exist and be writable
   - `/home/hermes/botfather/runs/` — must exist (or be creatable)
   - `/home/hermes/hermes-scaled-cs/agents/galileo/skills/autonomous-ai-agents/coordination-protocol/references/ledger-format.md` — must exist

2. **Field-name consistency.** Parse the "Required fields" table in `ledger-format.md` and the event-specific payloads. Cross-reference against the contract's prose in `worker-ledger-contract.md`. Flag any field name that appears in one but not the other. (This is the exact class of bug that hit us — the contract said `status_file` but the format doc said `active_path`, etc.)

3. **Event-type consistency.** The ledger-format defines events: `dispatched`, `ack`, `progress`, `poke`, `retry`, `blocker`, `done`, `escalated`. Verify the contract mentions all of them and doesn't reference any event type that isn't in the format doc.

4. **Worker roster consistency.** The contract names workers: Euclid, Tycho, Curie, Kepler, Hopper. Verify each has a corresponding `agents/<name>/SOUL.md` and `agents/<name>/config.yaml` in the repo.

5. **Cadence cross-check.** Read `references/cadence.yaml` and verify the thresholds mentioned in the contract's watchdog prose match the numbers in the YAML (e.g., "10 minutes" in prose = `600` in YAML for `ok.max_silence_seconds`).

6. **`flock` availability.** Quick check: `command -v flock` succeeds. If not, warn (not fail) — the contract already documents the fallback.

**Output format:** Human-readable summary. Each check as a line: `✅` or `❌` with a one-line explanation. Exit code 0 if all pass, 1 if any critical check fails.

### Component 2: `dry-run-dispatch.sh`

**Location:** `/home/hermes/hermes-scaled-cs/scripts/dry-run-dispatch.sh`

**What it does:** A minimal end-to-end test of the dispatch → ack → done flow without actually doing real work.

1. Run `validate-contract.sh` first (abort if it fails).
2. Write a synthetic `dispatched` entry to `active.jsonl` with a test task_id (e.g., `test-dry-run-<timestamp>`).
3. Verify the entry is readable back (grep + jq parse).
4. Write a synthetic `ack` entry (simulating what a worker would write).
5. Write a synthetic `done` entry.
6. Verify the full event chain for that task_id parses cleanly.
7. Clean up: remove the test entries from `active.jsonl` (or rotate them to archive).
8. Report: "Dry run passed — contract, ledger, and file permissions are all healthy." or detail what broke.

**Usage:** `./scripts/dry-run-dispatch.sh` — no arguments needed. Galileo can run this after any contract edit.

### Component 3: Wire it into the dispatch workflow

**In `agents/galileo/skills/autonomous-ai-agents/coordination-protocol/SKILL.md`**, add a step to the "When you start work" section:

> 0. Run `scripts/validate-contract.sh`. If it fails, do NOT dispatch — report the failure to the team and fix the contract first.

This becomes step 0, before the existing steps 1–5.

---

## Constraints

- **No external dependencies beyond what's already on the droplet.** Assume bash, python3, jq, grep, flock, date are available. Don't pip install anything.
- **Keep it simple.** This is a linter, not a framework. Under 200 lines per script.
- **The validation must be runnable by Galileo (Hermes agent) via terminal.** No interactive prompts, no GUI.
- **Work in the repo at `/home/hermes/hermes-scaled-cs`.** All paths are absolute.

## Acceptance criteria

1. `validate-contract.sh` passes on the current v1.2.1 contract (green baseline).
2. If I manually edit `worker-ledger-contract.md` to introduce a bad path or mismatched field name, the script catches it (exit 1, clear error message).
3. `dry-run-dispatch.sh` runs end-to-end and cleans up after itself.
4. The coordination-protocol SKILL.md is updated with the new pre-flight step.
5. Scripts are committed and pushed to the repo.

## Context files to read first

- `docs/worker-ledger-contract.md` — the contract workers read
- `agents/galileo/skills/autonomous-ai-agents/coordination-protocol/references/ledger-format.md` — the JSONL schema
- `agents/galileo/skills/autonomous-ai-agents/coordination-protocol/references/cadence.yaml` — timing constants
- `agents/galileo/skills/autonomous-ai-agents/coordination-protocol/SKILL.md` — the dispatch workflow to update
- `docs/architecture.md` — overall system context
