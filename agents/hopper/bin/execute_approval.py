#!/usr/bin/env python3
"""Hopper approval executor — the bright-line gated Salesforce writer.

Mirrors Bell propose_email.py send-approved pattern, but for every
Salesforce-side action_type (create_task, update_field, change_health_band,
add_save_plan, etc.).

Subcommands:
  execute <approval_id>   Reads approval from Supabase; refuses if status !=
                          approved or if metadata.executed is already true;
                          dispatches to the right handler based on action_type;
                          writes outcome back to Supabase metadata.
  inspect <approval_id>   Read-only diagnostic — prints what would be done.
                          Useful for Galileo to preview before triggering exec.
  list-handlers           Lists registered action_type handlers (extensibility check).

Bright-line enforcement (in code, not prompt):
  - status MUST be approved — else refuses with reason
  - metadata.executed MUST NOT be true — idempotency guard
  - action_type MUST be registered — unknown types refuse rather than wing it

Reads creds from ~/.hermes/profiles/hopper/.env:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  SALESFORCE_HOPPER_INSTANCE_URL
  SALESFORCE_HOPPER_CONSUMER_KEY
  SALESFORCE_HOPPER_CONSUMER_SECRET

Future-proofing:
  - HANDLERS dict at the top — adding a new action_type is one function +
    one registry line. No conditional spaghetti.
  - Each handler returns a structured outcome dict (ok, sf_record_id, error).
    Same shape regardless of action_type.
  - sf_writer.py is the only place SF API logic lives — handlers compose it.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ENV_PATH = os.path.expanduser("~/.hermes/profiles/hopper/.env")


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
        "SALESFORCE_HOPPER_INSTANCE_URL",
        "SALESFORCE_HOPPER_CONSUMER_KEY",
        "SALESFORCE_HOPPER_CONSUMER_SECRET",
    ):
        if os.environ.get(k):
            v[k] = os.environ[k]
    return v


def need(env, *keys):
    missing = [k for k in keys if not env.get(k)]
    if missing:
        fail("missing in " + ENV_PATH + ": " + ",".join(missing))


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


def get_approval(aid):
    st, rows = req(
        "GET",
        "/rest/v1/approvals?id=eq." + aid +
        "&select=id,action_type,target_record_type,target_record_id,proposed_value,status,decided_at,decided_by,metadata,agent_id",
    )
    if st != 200 or not rows:
        fail("approval not found: " + aid, status=st, detail=rows)
    return rows[0]


def patch_approval_metadata(aid, merge):
    """Merge keys into approvals.metadata without clobbering existing keys."""
    st, rows = req("GET", "/rest/v1/approvals?id=eq." + aid + "&select=metadata")
    base = (rows[0].get("metadata") or {}) if (st == 200 and rows) else {}
    base.update(merge)
    st, rows = req(
        "PATCH",
        "/rest/v1/approvals?id=eq." + aid,
        body={"metadata": base},
        prefer="return=representation",
    )
    return st in (200, 204)


# ---------------- helpers ----------------

def fail(msg, status=None, detail=None, exit_code=3):
    out = {"ok": False, "error": msg}
    if status is not None:
        out["status"] = status
    if detail is not None:
        out["detail"] = detail
    print(json.dumps(out))
    sys.exit(exit_code)


def ok(payload):
    print(json.dumps({"ok": True, **payload}))


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---------------- sf client (lazy import — keeps stub-mode fast) ----------------

def sf_client():
    """Lazily import sf_writer so list-handlers / inspect work without SF creds."""
    # Bin dir is added to sys.path by the parent process; allow same-dir import.
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    from sf_writer import SalesforceWriter
    return SalesforceWriter.from_env(load_env())


# ---------------- action_type handlers ----------------
#
# Contract: each handler takes (sf, approval) and returns a dict with at least
#     {"ok": bool, "outcome": <human-readable string>, "sf_record_id": <id or None>}
# Handlers MUST NOT mutate the approval row themselves — the dispatcher does that
# after the handler returns, so the audit chain (decided_at -> executed_at) is
# always written by the same code path.

def h_create_task(sf, approval):
    """Create a Salesforce Task related to the target record."""
    pv = approval.get("proposed_value") or {}
    fields = {
        "Subject": pv.get("subject", "(no subject)"),
        "ActivityDate": pv.get("due_date"),
        "Priority": pv.get("priority", "Normal"),
        "Status": "Not Started",
        "WhatId": approval.get("target_record_id") or pv.get("related_record"),
    }
    if pv.get("assigned_to"):
        fields["OwnerId"] = sf.user_id_for_email(pv["assigned_to"])
    fields = {k: v for k, v in fields.items() if v is not None}
    result = sf.create("Task", fields)
    return {
        "ok": result.get("ok", False),
        "outcome": "Task created: " + (result.get("id") or "(no id)"),
        "sf_record_id": result.get("id"),
        "sf_object": "Task",
    }


def h_update_field(sf, approval):
    """Generic single-field update on the target record.

    proposed_value shape: {"field": "<API name>", "new_value": <value>}
    target_record_type drives the SObject name.
    """
    pv = approval.get("proposed_value") or {}
    field = pv.get("field")
    new_value = pv.get("new_value")
    record_id = approval.get("target_record_id")
    record_type = approval.get("target_record_type") or "Account"
    if not field or record_id is None:
        return {"ok": False, "outcome": "missing field or target_record_id", "sf_record_id": None}
    sobject = _sobject_name(record_type)
    result = sf.update(sobject, record_id, {field: new_value})
    return {
        "ok": result.get("ok", False),
        "outcome": sobject + "." + field + " updated on " + record_id,
        "sf_record_id": record_id,
        "sf_object": sobject,
    }


def h_change_health_band(sf, approval):
    """Specialized update_field — sets Account.Health_Band__c."""
    pv = approval.get("proposed_value") or {}
    new_band = pv.get("new_band") or pv.get("new_value")
    record_id = approval.get("target_record_id")
    if not new_band or not record_id:
        return {"ok": False, "outcome": "missing new_band or target_record_id", "sf_record_id": None}
    result = sf.update("Account", record_id, {"Health_Band__c": new_band})
    return {
        "ok": result.get("ok", False),
        "outcome": "Account.Health_Band__c set to " + new_band + " on " + record_id,
        "sf_record_id": record_id,
        "sf_object": "Account",
    }


def h_add_save_plan(sf, approval):
    """Specialized update_field — sets Account.CSM_Save_Plan__c."""
    pv = approval.get("proposed_value") or {}
    plan = pv.get("save_plan") or pv.get("body_md")
    record_id = approval.get("target_record_id")
    if not plan or not record_id:
        return {"ok": False, "outcome": "missing save_plan body or target_record_id", "sf_record_id": None}
    result = sf.update("Account", record_id, {"CSM_Save_Plan__c": plan})
    return {
        "ok": result.get("ok", False),
        "outcome": "Save plan written to Account " + record_id,
        "sf_record_id": record_id,
        "sf_object": "Account",
    }


def h_flag_data_gap(sf, approval):
    """Create or update a Risk_Flag__c record marking a data-quality conflict."""
    pv = approval.get("proposed_value") or {}
    record_id = approval.get("target_record_id")
    fields = {
        "Account__c": record_id,
        "Risk_Type__c": pv.get("label") or "Data Conflict",
        "Status__c": "Active",
        "Description__c": pv.get("description") or pv.get("rationale") or "Flagged via approval queue",
    }
    fields = {k: v for k, v in fields.items() if v is not None}
    result = sf.create("Risk_Flag__c", fields)
    return {
        "ok": result.get("ok", False),
        "outcome": "Risk_Flag__c created: " + (result.get("id") or "(no id)"),
        "sf_record_id": result.get("id"),
        "sf_object": "Risk_Flag__c",
    }


# Registry — adding a new action_type is one line.
HANDLERS = {
    "create_task": h_create_task,
    "update_field": h_update_field,
    "change_health_band": h_change_health_band,
    "add_save_plan": h_add_save_plan,
    "flag_data_gap": h_flag_data_gap,
}


def _sobject_name(target_record_type):
    """Normalize Operator-Surface lowercase target_record_type to SF SObject names."""
    if not target_record_type:
        return "Account"
    t = target_record_type.lower()
    if t.startswith("salesforce."):
        t = t.split(".", 1)[1]
    return {
        "account": "Account",
        "opportunity": "Opportunity",
        "contact": "Contact",
        "task": "Task",
        "event": "Event",
        "contract": "Contract",
    }.get(t, t.capitalize() if not t.endswith("__c") else t)


# ---------------- commands ----------------

def cmd_list_handlers():
    print(json.dumps({"ok": True, "handlers": sorted(HANDLERS.keys())}))


def cmd_inspect(aid):
    a = get_approval(aid)
    pv = a.get("proposed_value") or {}
    md = a.get("metadata") or {}
    action_type = a.get("action_type")
    handler_present = action_type in HANDLERS
    print(json.dumps({
        "ok": True,
        "approval_id": aid,
        "status": a.get("status"),
        "executed_already": bool(md.get("executed")),
        "action_type": action_type,
        "handler_registered": handler_present,
        "target_record_type": a.get("target_record_type"),
        "target_record_id": a.get("target_record_id"),
        "proposed_value": pv,
        "would_execute": (
            a.get("status") == "approved"
            and not md.get("executed")
            and handler_present
        ),
        "blockers": _why_not(a, handler_present),
    }))


def _why_not(a, handler_present):
    blockers = []
    if a.get("status") != "approved":
        blockers.append("status is " + str(a.get("status")) + " — needs to be approved")
    if (a.get("metadata") or {}).get("executed"):
        blockers.append("metadata.executed is already true — idempotency guard")
    if not handler_present:
        blockers.append("action_type " + str(a.get("action_type")) + " has no registered handler")
    return blockers


def cmd_execute(aid):
    a = get_approval(aid)
    md = a.get("metadata") or {}
    action_type = a.get("action_type")

    # ---- bright line 1: status must be approved ----
    if a.get("status") != "approved":
        print(json.dumps({
            "ok": False,
            "refused": True,
            "reason": "bright_line",
            "detail": "status is " + str(a.get("status")) + " — Hopper executes only when approved",
            "approval_id": aid,
        }))
        sys.exit(0)

    # ---- bright line 2: idempotency — never double-execute ----
    if md.get("executed"):
        print(json.dumps({
            "ok": True,
            "noop": True,
            "reason": "idempotent_skip",
            "detail": "metadata.executed is already true",
            "approval_id": aid,
            "previous_outcome": md.get("outcome"),
        }))
        sys.exit(0)

    # ---- handler routing ----
    handler = HANDLERS.get(action_type)
    if not handler:
        # Future-proofing: do NOT execute an unknown action_type. Fail loudly.
        patch_approval_metadata(aid, {
            "execution_attempted_at": now_iso(),
            "execution_blocker": "no handler registered for action_type " + str(action_type),
        })
        fail(
            "no handler registered for action_type " + str(action_type),
            detail={"registered": sorted(HANDLERS.keys())},
        )

    # ---- execute via the handler ----
    try:
        sf = sf_client()
    except Exception as e:
        patch_approval_metadata(aid, {
            "execution_attempted_at": now_iso(),
            "execution_blocker": "sf_client init failed: " + type(e).__name__ + ": " + str(e)[:200],
        })
        fail("sf_client init failed: " + type(e).__name__, detail=str(e)[:300])

    try:
        result = handler(sf, a)
    except Exception as e:
        patch_approval_metadata(aid, {
            "execution_attempted_at": now_iso(),
            "execution_error": type(e).__name__ + ": " + str(e)[:300],
        })
        fail("handler raised: " + type(e).__name__, detail=str(e)[:400])

    # ---- stamp outcome (audit chain closes here) ----
    patch_approval_metadata(aid, {
        "executed": bool(result.get("ok")),
        "executed_at": now_iso(),
        "executed_by": "hopper",
        "outcome": result.get("outcome"),
        "sf_record_id": result.get("sf_record_id"),
        "sf_object": result.get("sf_object"),
    })

    ok({
        "approval_id": aid,
        "action_type": action_type,
        **result,
    })


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "execute":
        if len(sys.argv) < 3:
            fail("usage: execute_approval.py execute <approval_id>")
        cmd_execute(sys.argv[2])
    elif cmd == "inspect":
        if len(sys.argv) < 3:
            fail("usage: execute_approval.py inspect <approval_id>")
        cmd_inspect(sys.argv[2])
    elif cmd == "list-handlers":
        cmd_list_handlers()
    else:
        fail("usage: execute <id> | inspect <id> | list-handlers")
