#!/usr/bin/env python3
"""hermes-webhook-receiver — the HTTP endpoint Operator-Surface calls when an
approval is decided.

Design goals:
  - Zero dependencies (Python stdlib only). Runs under systemd as a user
    service, no pip/venv overhead.
  - Async dispatch — never blocks the caller. Returns 202 in <100ms.
  - HMAC-signed. The shared secret is in ~/.hermes/secrets/webhook.env
    (chmod 600). Operator-Surface must compute the signature over the
    raw request body and send it as `X-Hermes-Signature: sha256=<hex>`.
  - Idempotent-by-construction. The endpoint just dispatches Galileo;
    every downstream step (Galileo → Hopper/Bell → Supabase) is itself
    idempotent via approvals.metadata.executed.
  - Route table at the top — adding a new webhook type is one line.

Routes:
  POST /webhook/approval         Operator-Surface posts here on decide.
                                 Body: {"approval_id": "<uuid>", "decision":
                                 "approved"|"rejected", "actor": "<email>",
                                 "metadata": {...}}
                                 → spawns: galileo -z "execute approval <id>"
  POST /webhook/approval/dry-run Same shape, but Galileo only inspects,
                                 never executes. Useful for testing.
  GET  /healthz                  Plaintext "ok\\n" for monitoring.
  GET  /                         Tiny landing page (so accidental browser
                                 visits do not error confusingly).

Logging: stdout (captured by systemd journal). Every request gets a
correlation id; every dispatch logs the spawned command + pid.
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------- config ----------------

LISTEN_HOST = os.environ.get("HERMES_WEBHOOK_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("HERMES_WEBHOOK_PORT", "8080"))
SECRET_ENV_VAR = "HERMES_WEBHOOK_SECRET"
GALILEO_BIN = os.environ.get("GALILEO_BIN", os.path.expanduser("~/.local/bin/galileo"))
MAX_BODY_BYTES = 64 * 1024  # 64 KB — webhook payloads are tiny

# In-memory dedup window. Vercel may retry on transient failures; the same
# approval_id arriving twice within DEDUP_WINDOW_SEC of the first call is
# acknowledged as 200 OK but NOT re-dispatched. Downstream idempotency
# (metadata.executed) is the real guard, but this avoids spawning two Galileo
# processes for the same approval in the same second.
DEDUP_WINDOW_SEC = 60
_recent_dispatches: dict[str, float] = {}

# ---------------- secret + signature ----------------

def _load_secret() -> bytes:
    """Read the HMAC shared secret. Service refuses to start without it."""
    val = os.environ.get(SECRET_ENV_VAR)
    if not val:
        sys.stderr.write(
            "FATAL: " + SECRET_ENV_VAR + " is not set. The service refuses to\n"
            "start without a secret — that would mean any unauthenticated\n"
            "caller could trigger approval execution. Put the secret in\n"
            "~/.hermes/secrets/webhook.env and load it via the systemd\n"
            "EnvironmentFile= directive.\n"
        )
        sys.exit(2)
    return val.encode("utf-8")


def _verify_signature(secret: bytes, body: bytes, sent_header: str | None) -> bool:
    """Constant-time HMAC verification of X-Hermes-Signature: sha256=<hex>."""
    if not sent_header:
        return False
    if not sent_header.startswith("sha256="):
        return False
    sent_hex = sent_header[len("sha256="):]
    expected_hex = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent_hex, expected_hex)


# ---------------- route handlers ----------------
#
# Each handler returns (status_code, response_dict). It MUST NOT block on the
# downstream dispatch — use _spawn_galileo to fire-and-forget.

DISPATCH_LOG_DIR = os.path.expanduser("~/.hermes/dispatch-logs")


def _spawn_galileo(prompt: str, corr_id: str) -> int:
    """Spawn galileo -z "<prompt>" detached. Returns the child PID.

    Captures stdout+stderr to ~/.hermes/dispatch-logs/galileo-<corr>.log so
    that failures leave a forensic trail. Before this change the receiver
    sent both streams to /dev/null, which meant any crash inside Galileo
    (model errors, OOM, gmail-token expiry, etc.) was invisible — the
    approval metadata showed no execution_blocker / execution_error
    because Galileo never got far enough to write them, and there was no
    out-of-band log to look at either.
    """
    try:
        os.makedirs(DISPATCH_LOG_DIR, exist_ok=True)
    except Exception as e:
        logging.warning("could not create %s: %s — falling back to DEVNULL", DISPATCH_LOG_DIR, e)
        log_fd = subprocess.DEVNULL
    else:
        log_path = os.path.join(DISPATCH_LOG_DIR, "galileo-" + corr_id + ".log")
        log_fd = open(log_path, "ab", buffering=0)
        # First write to the log identifies the dispatch — helpful when
        # tailing if multiple corr_ids ran near each other.
        log_fd.write(("=== dispatched " + corr_id + " prompt=" + repr(prompt) + "\n").encode())
    proc = subprocess.Popen(
        [GALILEO_BIN, "-z", prompt],
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    # Parent closes its file handle; child has already inherited the fd.
    if log_fd is not subprocess.DEVNULL:
        try:
            log_fd.close()
        except Exception:
            pass
    logging.info("corr=%s dispatched galileo pid=%s prompt=%r", corr_id, proc.pid, prompt)
    return proc.pid


def _dedup_check(key: str) -> bool:
    """Return True if this key has been dispatched recently. Prunes old entries."""
    now = time.time()
    cutoff = now - DEDUP_WINDOW_SEC
    # Prune
    for k in list(_recent_dispatches.keys()):
        if _recent_dispatches[k] < cutoff:
            del _recent_dispatches[k]
    if key in _recent_dispatches:
        return True
    _recent_dispatches[key] = now
    return False


def handle_approval(body: dict, corr_id: str, dry_run: bool = False) -> tuple[int, dict]:
    """Dispatch Galileo to execute (or inspect) an approval row."""
    approval_id = body.get("approval_id") or body.get("id")
    decision = body.get("decision") or body.get("status")

    if not approval_id:
        return 400, {"ok": False, "error": "missing approval_id"}

    # We only fire on `approved` — `rejected` is a no-op for downstream Hopper
    # (his bright-line guard refuses anyway), but we acknowledge gracefully.
    if decision and decision not in ("approved", "rejected"):
        return 400, {"ok": False, "error": "unknown decision: " + str(decision)}

    if decision == "rejected":
        logging.info("corr=%s approval=%s decision=rejected — no dispatch needed", corr_id, approval_id)
        return 202, {
            "ok": True,
            "approval_id": approval_id,
            "decision": "rejected",
            "dispatched": False,
            "note": "rejected approvals require no execution",
            "corr_id": corr_id,
        }

    # Dedup — same approval_id arriving twice in 60s is treated as a retry.
    dedup_key = approval_id + ("|dry" if dry_run else "")
    if _dedup_check(dedup_key):
        logging.info("corr=%s approval=%s dedup'd (recent dispatch)", corr_id, approval_id)
        return 200, {
            "ok": True,
            "approval_id": approval_id,
            "dispatched": False,
            "note": "already dispatched within dedup window",
            "corr_id": corr_id,
        }

    verb = "inspect" if dry_run else "execute"
    prompt = (
        verb + " approval " + approval_id + " — webhook from operator-surface "
        "(corr=" + corr_id + "). Use the execute-approval skill (Hopper) or "
        "send-approved (Bell) based on action_type."
    )
    pid = _spawn_galileo(prompt, corr_id)

    return 202, {
        "ok": True,
        "approval_id": approval_id,
        "dispatched": True,
        "verb": verb,
        "galileo_pid": pid,
        "corr_id": corr_id,
    }


def handle_health() -> tuple[int, str]:
    return 200, "ok\n"


def handle_root() -> tuple[int, str]:
    return 200, (
        "hermes-webhook-receiver\n"
        "POST /webhook/approval — Operator-Surface approval webhook\n"
        "POST /webhook/approval/dry-run — preview only\n"
        "GET  /healthz — health probe\n"
    )


# Route table — adding a new webhook is one line.
JSON_ROUTES = {
    ("POST", "/webhook/approval"):         lambda body, cid: handle_approval(body, cid, dry_run=False),
    ("POST", "/webhook/approval/dry-run"): lambda body, cid: handle_approval(body, cid, dry_run=True),
}
PLAIN_ROUTES = {
    ("GET", "/healthz"): handle_health,
    ("GET", "/"):        handle_root,
}


# ---------------- http handler ----------------

class Handler(BaseHTTPRequestHandler):
    server_version = "hermes-webhook-receiver/1.0"

    def log_message(self, fmt: str, *args) -> None:
        # Route access logs through python logging so systemd journal sees them.
        logging.info("%s - " + fmt, self.address_string(), *args)

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Hermes-Receiver", "1.0")
        self.end_headers()
        self.wfile.write(body)

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self._write(status, body, "application/json")

    def _write_plain(self, status: int, text: str) -> None:
        self._write(status, text.encode("utf-8"), "text/plain; charset=utf-8")

    def _read_body(self) -> bytes | None:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            self._write_json(413, {"ok": False, "error": "body too large"})
            return None
        return self.rfile.read(length) if length else b""

    def do_GET(self) -> None:
        key = ("GET", self.path.split("?")[0])
        if key not in PLAIN_ROUTES:
            self._write_json(404, {"ok": False, "error": "no such route"})
            return
        status, text = PLAIN_ROUTES[key]()
        self._write_plain(status, text)

    def do_POST(self) -> None:
        corr_id = uuid.uuid4().hex[:12]
        path = self.path.split("?")[0]
        key = ("POST", path)
        if key not in JSON_ROUTES:
            self._write_json(404, {"ok": False, "error": "no such route"})
            return

        raw_body = self._read_body()
        if raw_body is None:
            return

        # ---- HMAC verification — non-negotiable ----
        sent_sig = self.headers.get("X-Hermes-Signature")
        if not _verify_signature(SECRET, raw_body, sent_sig):
            logging.warning("corr=%s path=%s SIGNATURE INVALID from %s", corr_id, path, self.address_string())
            self._write_json(401, {"ok": False, "error": "signature invalid or missing"})
            return

        # ---- parse JSON body ----
        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception as e:
            self._write_json(400, {"ok": False, "error": "invalid json: " + str(e)[:120]})
            return

        # ---- dispatch handler ----
        try:
            status, payload = JSON_ROUTES[key](body, corr_id)
        except Exception as e:
            logging.exception("corr=%s path=%s handler raised", corr_id, path)
            self._write_json(500, {"ok": False, "error": "internal: " + type(e).__name__})
            return

        self._write_json(status, payload)


# ---------------- main ----------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )
    SECRET = _load_secret()
    logging.info("hermes-webhook-receiver starting on %s:%d", LISTEN_HOST, LISTEN_PORT)
    logging.info("galileo bin: %s (%s)", GALILEO_BIN, "exists" if os.path.exists(GALILEO_BIN) else "MISSING — dispatch will fail")
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("shutdown via keyboard interrupt")
        server.server_close()
