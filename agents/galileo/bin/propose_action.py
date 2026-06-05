#!/usr/bin/env python3
"""Galileo's approval drafter — file a non-email approval row in the Operator
Surface for human review.

Counterpart to Bell's `propose_email.py propose`: where Bell drafts customer-
facing email approvals (`send_reply`), Galileo drafts everything else that
needs human sign-off before a Salesforce write:
  - create_task        (renewal-readiness prep, follow-up tasks)
  - update_field       (generic single-field updates on Account/Opp/Contact)
  - change_health_band (specialized Account.Health_Band__c change)
  - add_save_plan      (specialized Account.CSM_Save_Plan__c write)
  - flag_data_gap      (Risk_Flag__c record marking a hygiene/conflict issue)

The action_type set MUST stay in sync with Hopper's HANDLERS registry in
~/.hermes/profiles/hopper/bin/execute_approval.py and Galileo's approval-router
skill routing table. If you add a new action_type here, add the handler in
Hopper too, and add the route in Galileo's skill.

Subcommands:
  propose <json>          File a new pending approval. Drafted_by = "galileo".
  list-action-types       Show the action types this script knows how to file.
  inspect <approval_id>   Read an existing approval (status, action_type, etc.).
                          Galileo's approval-router skill uses this for routing.

Reads creds from ~/.hermes/profiles/galileo/.env (with env-var overrides):
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  OPERATOR_SURFACE_AGENT_SLUG   (optional; default "galileo")
"""

import json
import os
import sys
import urllib.error
import urllib.request


ENV_PATH = os.path.expanduser("~/.hermes/profiles/galileo/.env")

# Must stay in sync with Hopper's HANDLERS in
# ~/.hermes/profiles/hopper/bin/execute_approval.py
KNOWN_ACTION_TYPES = {
    "create_task",
    "update_field",
    "change_health_band",
    "add_save_plan",
    "flag_data_gap",
}

# Action types that exist but are NOT for Galileo to draft — these are
# Bell's domain. Flagged here so a misroute is caught at draft time,
# not at execution time.
BELL_ACTION_TYPES = {
    "send_reply",
    "send_email",
    "chatter_post",
}


# ---------------- env + supabase plumbing ----------------

def load_env():
    v = {}
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, val = line.split("=", 1)
                v[k] = val.strip()
    for k in (
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "OPERATOR_SURFACE_AGENT_SLUG",
    ):
        if os.environ.get(k):
            v[k] = os.environ[k]
    return v


def need(env, *keys):
    missing = [k for k in keys if not env.get(k)]
    if missing:
        fail("missing in " + ENV_PATH + ": " + ",".join(missing))


def fail(msg, status=None, detail=None, exit_code=2):
    out = {"ok": False, "error": msg}
    if status is not None:
        out["status"] = status
    if detail is not None:
        out["detail"] = detail
    print(json.dumps(out))
    sys.exit(exit_code)


def req(method, path, body=None, prefer=None):
    env = load_env()
    need(env, "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
    base = env["SUPABASE_URL"].rstrip("/")
    key = env["SUPABASE_SERVICE_ROLE_KEY"]
    full = base + path if path.startswith("/") else path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(full, data=data, method=method)
    r.add_header("apikey", key)
    r.add_header("Authorization", "Bearer " + key)
    r.add_header("Content-Type", "application/json")
    if prefer:
        r.add_header("Prefer", prefer)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            txt = resp.read().decode()
            return resp.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:400]}


def agent_slug():
    return load_env().get("OPERATOR_SURFACE_AGENT_SLUG") or "galileo"


def ensure_agent():
    """Idempotent upsert of Galileo's row in the agents registry."""
    slug = agent_slug()
    st, rows = req("GET", "/rest/v1/agents?slug=eq." + slug + "&select=id")
    if st == 200 and rows:
        return rows[0]["id"]
    st, rows = req(
        "POST",
        "/rest/v1/agents",
        body={
            "slug": slug,
            "name": "Galileo",
            "status": "running",
            "metadata": {
                "owner": "csm-platform",
                "runtime": "hermes+galileo+mimo",
                "tags": ["orchestrator", "router", "drafter"],
                "version": "0.1.0",
            },
        },
        prefer="return=representation",
    )
    if st in (200, 201) and rows:
        return rows[0]["id"]
    fail("ensure_agent failed", status=st, detail=rows, exit_code=3)


def new_run(agent_id, summary):
    st, rows = req(
        "POST",
        "/rest/v1/agent_runs",
        body={
            "agent_id": agent_id,
            "status": "succeeded",
            "triggered_by": "manual",
            "items_processed": 1,
            "output_summary": summary,
            "metadata": {"by": "galileo"},
        },
        prefer="return=representation",
    )
    return rows[0]["id"] if st in (200, 201) and rows else None


# ---------------- commands ----------------

def cmd_list_action_types():
    print(json.dumps({
        "ok": True,
        "galileo_drafts": sorted(KNOWN_ACTION_TYPES),
        "bell_drafts": sorted(BELL_ACTION_TYPES),
        "note": (
            "Galileo files non-email approvals via this script with "
            "drafted_by='galileo'. Bell files send_reply/email via "
            "propose_email.py with drafted_by='bell'. Add a new action_type "
            "here AND add the handler in Hopper's execute_approval.py."
        ),
    }))


def cmd_inspect(aid):
    st, rows = req(
        "GET",
        "/rest/v1/approvals?id=eq." + aid +
        "&select=id,action_type,target_record_type,target_record_id,proposed_value,status,metadata,decided_at,decided_by",
    )
    if st != 200 or not rows:
        fail("approval not found: " + aid, status=st, detail=rows, exit_code=3)
    a = rows[0]
    print(json.dumps({
        "ok": True,
        "approval_id": aid,
        "action_type": a.get("action_type"),
        "status": a.get("status"),
        "executed_already": bool((a.get("metadata") or {}).get("executed")),
        "drafted_by": (a.get("metadata") or {}).get("drafted_by"),
        "target_record_type": a.get("target_record_type"),
        "target_record_id": a.get("target_record_id"),
        "decided_at": a.get("decided_at"),
        "should_route_to": _route(a.get("action_type")),
    }))


def _route(action_type):
    """Mirror of the routing table in Galileo's approval-router skill."""
    if action_type in BELL_ACTION_TYPES:
        return "bell"
    if action_type in KNOWN_ACTION_TYPES:
        return "hopper"
    return None  # unknown — caller must refuse


def cmd_propose(payload_json):
    """File a new pending approval as Galileo (drafted_by: galileo)."""
    try:
        p = json.loads(payload_json)
    except json.JSONDecodeError as e:
        fail("invalid JSON: " + str(e))

    # ---- validate required fields ----
    required = ["action_type", "target_record_id", "proposed_value"]
    missing = [k for k in required if not p.get(k)]
    if missing:
        fail("missing required fields: " + ",".join(missing),
             detail={"required": required, "got": sorted(p.keys())})

    action_type = p["action_type"]

    # ---- enforce drafting boundary ----
    if action_type in BELL_ACTION_TYPES:
        fail(
            "Galileo does not draft " + action_type +
            " — that is Bell's job. Use propose_email.py from Bell's profile instead.",
            detail={"action_type": action_type, "drafted_by_for_this_type": "bell"},
        )
    if action_type not in KNOWN_ACTION_TYPES:
        fail(
            "unknown action_type " + action_type +
            " — Galileo only drafts the registered set.",
            detail={"known": sorted(KNOWN_ACTION_TYPES)},
        )

    # ---- build approval row ----
    agent_id = ensure_agent()
    run_id = new_run(agent_id, "drafted 1 " + action_type + " approval")

    approval = {
        "agent_id": agent_id,
        "agent_run_id": run_id,
        "action_type": action_type,
        "target_record_type": p.get("target_record_type") or "salesforce.account",
        "target_record_id": p["target_record_id"],
        "current_value": p.get("current_value"),
        "proposed_value": p["proposed_value"],
        "rationale": p.get("rationale", "Drafted as part of the orchestration."),
        "status": "pending",
        "metadata": {
            "drafted_by": "galileo",
            "risk_level": p.get("risk_level", "med"),
            "account_name": p.get("account"),
        },
    }

    # ---- write to Supabase ----
    st, rows = req(
        "POST",
        "/rest/v1/approvals",
        body=approval,
        prefer="return=representation",
    )
    if st in (200, 201) and rows:
        print(json.dumps({
            "ok": True,
            "approval_id": rows[0]["id"],
            "action_type": action_type,
            "status": "pending",
            "note": (
                "Approval filed. Will route to " + (_route(action_type) or "unknown") +
                " once the human approves in the Operator Surface."
            ),
        }))
    else:
        fail("approval insert failed", status=st, detail=rows, exit_code=3)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "propose":
        if len(sys.argv) < 3:
            fail("usage: propose_action.py propose '<json>'", exit_code=1)
        cmd_propose(sys.argv[2])
    elif cmd == "inspect":
        if len(sys.argv) < 3:
            fail("usage: propose_action.py inspect <approval_id>", exit_code=1)
        cmd_inspect(sys.argv[2])
    elif cmd == "list-action-types":
        cmd_list_action_types()
    else:
        fail(
            "usage: propose_action.py propose <json> | inspect <id> | list-action-types",
            exit_code=1,
        )
