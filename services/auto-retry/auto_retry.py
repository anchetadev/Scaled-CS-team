#!/usr/bin/env python3
"""Scaled-CS auto-retry service.

Runs on a 60s systemd timer. Scans Supabase for approvals stuck in the
"approved-but-not-yet-executed" state and re-dispatches them to Galileo
on an exponential schedule. After 4 unsuccessful retries, marks the row
as needing attention so the CSM sees it.

Rationale: the CSM clicks Approve and moves on. They shouldn't be the
ones diagnosing why a Galileo dispatch crashed. Bell and Hopper are
already idempotent on metadata.executed=true, so re-dispatching a row
that quietly succeeded between checks is a clean no-op.

Schedule (measured from the last activity — either decided_at or
last_retry_at, whichever is more recent):

    attempt 1: + 2 min     # gives original dispatch room to finish
    attempt 2: + 5 min
    attempt 3: + 10 min
    attempt 4: + 20 min
    exhausted: writes metadata.execution_blocker = "auto-retry exhausted"

State stored in row.metadata:
    retry_attempts   (int)  — count of auto-retries fired so far
    last_retry_at    (ISO)  — when the last retry fired
    execution_blocker (str) — set when we give up; surfaces to CSM
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

# Schedule: minutes since last activity at which each retry fires.
# Length of this list = total auto-retries before exhaustion.
RETRY_SCHEDULE_MIN = [2, 5, 10, 20]

# Read Supabase creds from galileo's profile env (already on droplet)
ENV_PATH = os.path.expanduser("~/.hermes/profiles/galileo/.env")
GALILEO_BIN = os.path.expanduser("~/.local/bin/galileo")
LOG_DIR = os.path.expanduser("~/.hermes/dispatch-logs")


def load_env():
    """Read KEY=VALUE pairs from the env file. Also overlay actual env vars."""
    v = {}
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, val = line.split("=", 1)
                v[k] = val.strip()
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if os.environ.get(k):
            v[k] = os.environ[k]
    return v


def supabase_req(method, path, body=None):
    env = load_env()
    base = env["SUPABASE_URL"].rstrip("/")
    key = env["SUPABASE_SERVICE_ROLE_KEY"]
    full = base + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(full, data=data, method=method)
    r.add_header("apikey", key)
    r.add_header("Authorization", "Bearer " + key)
    r.add_header("Content-Type", "application/json")
    if method == "PATCH":
        r.add_header("Prefer", "return=representation")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            txt = resp.read().decode()
            return resp.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode()[:400]}


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def find_due_retries():
    """Return list of (row, next_attempt_number) for approvals due to retry now."""
    url = (
        "/rest/v1/approvals"
        "?status=eq.approved"
        "&select=id,decided_at,metadata,action_type,target_record_id"
        "&order=decided_at.asc"
    )
    st, rows = supabase_req("GET", url)
    if st != 200 or not rows:
        return []
    out = []
    now = datetime.now(timezone.utc)
    for row in rows:
        m = row.get("metadata") or {}
        if m.get("executed") is True:
            continue
        attempts = int(m.get("retry_attempts") or 0)
        if attempts >= len(RETRY_SCHEDULE_MIN):
            # Exhausted — mark execution_blocker if not already there so the
            # UI surfaces "needs attention". Idempotent.
            if not m.get("execution_blocker"):
                m["execution_blocker"] = (
                    "auto-retry exhausted ("
                    + str(len(RETRY_SCHEDULE_MIN))
                    + " attempts) — likely Galileo dispatch or downstream worker failure"
                )
                supabase_req(
                    "PATCH",
                    "/rest/v1/approvals?id=eq." + row["id"],
                    body={"metadata": m},
                )
            continue
        last_action = m.get("last_retry_at") or row.get("decided_at")
        last_dt = parse_iso(last_action)
        if last_dt is None:
            continue
        next_delay_min = RETRY_SCHEDULE_MIN[attempts]
        elapsed_min = (now - last_dt).total_seconds() / 60
        if elapsed_min >= next_delay_min:
            out.append((row, attempts + 1))
    return out


def dispatch(row, attempt_number):
    """Fire a Galileo dispatch for this approval. Stamps metadata first so
    that crash-and-relaunch of the auto-retry service doesn't double-fire."""
    aid = row["id"]
    m = row.get("metadata") or {}
    new_meta = dict(m)
    new_meta["retry_attempts"] = attempt_number
    new_meta["last_retry_at"] = datetime.now(timezone.utc).isoformat()
    # Clear prior blocker — auto-retry deserves a fresh chance to set/clear it
    for k in ("execution_blocker", "execution_error"):
        new_meta.pop(k, None)
    st, _ = supabase_req(
        "PATCH",
        "/rest/v1/approvals?id=eq." + aid,
        body={"metadata": new_meta},
    )
    if st not in (200, 204):
        print(json.dumps({"ok": False, "step": "patch_metadata", "approval_id": aid, "status": st}))
        return

    corr_id = "autoretry-" + uuid.uuid4().hex[:12]
    prompt = (
        "execute approval " + aid
        + " — auto-retry attempt " + str(attempt_number)
        + " (corr=" + corr_id + ")."
        + " Use the execute-approval skill (Hopper) or send-approved (Bell) based on action_type."
    )

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, "galileo-" + corr_id + ".log")
        log_fd = open(log_path, "ab", buffering=0)
        log_fd.write(
            ("=== auto-retry " + corr_id
             + " attempt=" + str(attempt_number)
             + " approval=" + aid
             + " prompt=" + repr(prompt) + "\n").encode()
        )
        subprocess.Popen(
            [GALILEO_BIN, "-z", prompt],
            stdout=log_fd, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            log_fd.close()
        except Exception:
            pass
    except Exception as e:
        print(json.dumps({"ok": False, "step": "dispatch", "approval_id": aid, "error": str(e)}))
        return

    print(json.dumps({
        "ok": True,
        "approval_id": aid,
        "attempt": attempt_number,
        "corr": corr_id,
        "action_type": row.get("action_type"),
    }))


def main():
    due = find_due_retries()
    if not due:
        # Silent when nothing to do — keeps journal noise low
        return 0
    print(json.dumps({"ok": True, "step": "scan", "due_count": len(due)}))
    for row, attempt_number in due:
        dispatch(row, attempt_number)
    return 0


if __name__ == "__main__":
    sys.exit(main())
