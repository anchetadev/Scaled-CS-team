#!/usr/bin/env python3
"""Bell's approval bridge to the Operator Surface (shared Supabase).

  propose <json>     -> ensure the agent + an agent_run exist, then insert a
                        `send_reply` approval (status=pending) carrying the
                        drafted email. Prints the approval id. Bell STOPS here.
  poll <id>          -> check an approval's status (pending|approved|rejected).
  approve <id>       -> DEMO ONLY: simulate the CSM approving in the surface.
                        In production this PATCH happens via the Operator Surface
                        UI, not here. Bell himself MUST NOT call this in real flow.
  send-approved <id> -> If approved, send the email from the CSM's Gmail and
                        stamp the approval as executed. Refuses if not approved.
  mark-executed <id> -> Stamp metadata.executed = true (called by send-approved).

Reads from the bell profile .env at ~/.hermes/profiles/bell/.env:
  SUPABASE_URL                  - Operator Surface project URL
  SUPABASE_SERVICE_ROLE_KEY     - service-role key (bypasses RLS; Hermes side only)
  OPERATOR_SURFACE_AGENT_SLUG   - agent registry slug (default: renewal-outreach)
  OPERATOR_SURFACE_CSM_UID      - DEMO ONLY: uuid used by the approve subcommand
  BELL_GOOGLE_API_SCRIPT        - path to the google_api.py helper (default tries
                                  both profile and global skills hub locations)

JSON for `propose` (matches Operator Surface send_reply schema):
  {"account":"Pyramid Construction","opportunity_id":"006...","to":["x@y.com"],
   "subject":"...","body_md":"...","rationale":"optional"}
"""
import os, sys, json, subprocess, urllib.request, urllib.error
from datetime import datetime, timezone

ENV_PATH = os.path.expanduser("~/.hermes/profiles/bell/.env")
DEFAULT_AGENT_SLUG = "galileo"


def load_env():
    v = {}
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, val = line.split("=", 1)
                v[k] = val.strip()
    # env vars override file
    for k in (
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "OPERATOR_SURFACE_AGENT_SLUG",
        "OPERATOR_SURFACE_CSM_UID",
        "BELL_GOOGLE_API_SCRIPT",
    ):
        if os.environ.get(k):
            v[k] = os.environ[k]
    return v


def need(env, *keys):
    missing = [k for k in keys if not env.get(k)]
    if missing:
        print(json.dumps({"ok": False, "error": "missing in " + ENV_PATH + ": " + ",".join(missing)}))
        sys.exit(2)


def google_api_script():
    env = load_env()
    if env.get("BELL_GOOGLE_API_SCRIPT"):
        return env["BELL_GOOGLE_API_SCRIPT"]
    candidates = [
        os.path.expanduser("~/.hermes/profiles/bell/skills/productivity/google-workspace/scripts/google_api.py"),
        os.path.expanduser("~/.hermes/skills/productivity/google-workspace/scripts/google_api.py"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[-1]  # let the failure happen visibly downstream


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
    return load_env().get("OPERATOR_SURFACE_AGENT_SLUG") or DEFAULT_AGENT_SLUG


def ensure_agent():
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
                "runtime": "hermes+bell+mimo",
                "tags": ["renewals", "email"],
                "version": "0.1.0",
            },
        },
        prefer="return=representation",
    )
    if st in (200, 201) and rows:
        return rows[0]["id"]
    print(json.dumps({"ok": False, "step": "ensure_agent", "status": st, "detail": rows}))
    sys.exit(3)


def new_run(agent_id):
    st, rows = req(
        "POST",
        "/rest/v1/agent_runs",
        body={
            "agent_id": agent_id,
            "status": "succeeded",
            "triggered_by": "manual",
            "items_processed": 1,
            "output_summary": "drafted 1 follow-up email",
            "metadata": {"by": "bell"},
        },
        prefer="return=representation",
    )
    return rows[0]["id"] if st in (200, 201) and rows else None


def cmd_propose(payload):
    p = json.loads(payload)
    agent_id = ensure_agent()
    run_id = new_run(agent_id)
    approval = {
        "agent_id": agent_id,
        "agent_run_id": run_id,
        "action_type": "send_reply",
        "target_record_type": "opportunity",
        "target_record_id": p.get("opportunity_id", ""),
        "current_value": None,
        "proposed_value": {
            "channel": "email",
            "to": p["to"],
            "subject": p["subject"],
            "body_md": p["body_md"],
            "attachments": [],
        },
        "rationale": p.get("rationale", "Follow-up drafted from the meeting transcript."),
        "status": "pending",
        "metadata": {"account": p.get("account"), "drafted_by": "bell", "risk_level": "med"},
    }
    st, rows = req("POST", "/rest/v1/approvals", body=approval, prefer="return=representation")
    if st in (200, 201) and rows:
        print(json.dumps({
            "ok": True,
            "approval_id": rows[0]["id"],
            "status": "pending",
            "note": "Draft is in the Operator Surface for CSM review. NOT sent.",
        }))
    else:
        print(json.dumps({"ok": False, "step": "approval", "status": st, "detail": rows}))
        sys.exit(3)


def cmd_poll(aid):
    st, rows = req(
        "GET",
        "/rest/v1/approvals?id=eq." + aid + "&select=id,status,proposed_value,decided_at",
    )
    if st == 200 and rows:
        print(json.dumps({"ok": True, "approval": rows[0]}))
    else:
        print(json.dumps({"ok": False, "status": st, "detail": rows}))


def cmd_mark(aid, extra=None):
    st, rows = req("GET", "/rest/v1/approvals?id=eq." + aid + "&select=metadata")
    meta = (rows[0].get("metadata") or {}) if (st == 200 and rows) else {}
    meta.update({"executed": True})
    if extra:
        meta.update(extra)
    st, rows = req(
        "PATCH",
        "/rest/v1/approvals?id=eq." + aid,
        body={"metadata": meta},
        prefer="return=representation",
    )
    return st in (200, 204)


def cmd_approve(aid):
    """DEMO ONLY: simulate the CSM clicking Approve in the Operator Surface.
    In production this PATCH is performed by the Operator Surface app, not here."""
    env = load_env()
    csm_uid = env.get("OPERATOR_SURFACE_CSM_UID")
    if not csm_uid:
        print(json.dumps({
            "ok": False,
            "error": "OPERATOR_SURFACE_CSM_UID not set — required for demo approve",
        }))
        sys.exit(2)
    body = {
        "status": "approved",
        "decided_by": csm_uid,
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    st, rows = req(
        "PATCH",
        "/rest/v1/approvals?id=eq." + aid,
        body=body,
        prefer="return=representation",
    )
    print(json.dumps({
        "ok": st in (200, 204),
        "status": st,
        "approval": (rows[0] if isinstance(rows, list) and rows else rows),
    }))


def cmd_send_approved(aid):
    """Bell's bright line, enforced in code: send the customer email ONLY if
    the CSM has approved it. Otherwise refuse. Then send from the CSM's Gmail."""
    st, rows = req(
        "GET",
        "/rest/v1/approvals?id=eq." + aid + "&select=id,status,proposed_value,target_record_id",
    )
    if st != 200 or not rows:
        print(json.dumps({"ok": False, "error": "approval not found", "status": st}))
        sys.exit(3)
    a = rows[0]
    if a["status"] != "approved":
        print(json.dumps({
            "ok": False,
            "refused": True,
            "status": a["status"],
            "note": "Bright line: not sending — approval status is not 'approved'.",
        }))
        sys.exit(0)
    pv = a["proposed_value"] or {}
    to = ",".join(pv.get("to", []))
    subject = pv.get("subject", "")
    body = (pv.get("body_md", "") or "").replace("**", "")  # light markdown -> plain text
    if not to or not subject:
        print(json.dumps({"ok": False, "error": "approval missing to/subject"}))
        sys.exit(3)
    gapi = google_api_script()
    out = subprocess.run(
        ["python3", gapi, "gmail", "send",
         "--to", to, "--subject", subject, "--body", body],
        capture_output=True, text=True,
    )
    so = out.stdout.strip()
    sent_id = None
    try:
        sent_id = json.loads(so).get("id")
    except Exception:
        pass
    ok = sent_id is not None
    if ok:
        cmd_mark(aid, extra={"sent_via": "gmail", "gmail_message_id": sent_id})
    print(json.dumps({
        "ok": ok,
        "approval_id": aid,
        "gmail_message_id": sent_id,
        "send_stdout": so,
        "send_stderr": out.stderr.strip(),
    }))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "propose":
        cmd_propose(sys.argv[2])
    elif cmd == "poll":
        cmd_poll(sys.argv[2])
    elif cmd == "approve":
        cmd_approve(sys.argv[2])
    elif cmd == "send-approved":
        cmd_send_approved(sys.argv[2])
    elif cmd == "mark-executed":
        print(json.dumps({"ok": cmd_mark(sys.argv[2])}))
    else:
        print(json.dumps({
            "ok": False,
            "error": "usage: propose <json> | poll <id> | approve <id> | send-approved <id> | mark-executed <id>",
        }))
        sys.exit(1)
