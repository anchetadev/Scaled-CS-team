# hermes-webhook-receiver

A tiny HTTP service running on the Hermes droplet that receives webhooks from Operator-Surface (and any other external system) and dispatches them through Galileo.

## Why this exists

Galileo's gateway is built around messaging platforms (Slack, etc.) — it doesn't natively listen for HTTP webhooks. When a CSM clicks **Approve** in the Operator-Surface UI, that decision needs to reach the Hermes side and trigger Hopper (for Salesforce writes) or Bell (for emails). This service is the bridge.

The flow:

```
Operator-Surface (Vercel)
   │ POST /webhook/approval  (HMAC-signed, JSON body)
   ▼
hermes-webhook-receiver (this service, port 8080 on the droplet)
   │ verifies HMAC, dedups, returns 202 in <100ms
   │ spawns asynchronously:
   ▼
galileo -z "execute approval <id> — webhook from operator-surface"
   │ Galileo reads the approval, identifies action_type, dispatches:
   ▼
Bell  (action_type = send_reply)   OR   Hopper  (everything else)
   │ Worker executes, stamps outcome back into approvals.metadata
   ▼
Operator-Surface UI shows executed=true on next render
```

## Files

| File | Role |
|---|---|
| `receiver.py` | The HTTP service. Python stdlib only — no Flask/FastAPI, no pip install. ~250 lines including comments. |
| `hermes-webhook-receiver.service` | systemd user unit. Runs the receiver under the `hermes` user, restarts on failure, logs to journal. |
| `README.md` | This file. |

## Routes

| Method | Path | What |
|---|---|---|
| POST | `/webhook/approval` | Operator-Surface posts here on approve/reject. Dispatches Galileo to execute (or no-ops if rejected). |
| POST | `/webhook/approval/dry-run` | Same shape but dispatches Galileo with `inspect` instead of `execute` — preview only. Useful for testing. |
| GET  | `/healthz` | Returns `ok\n` for monitoring. |
| GET  | `/` | Tiny landing page so accidental browser visits don't confuse anyone. |

## Auth

Every `POST` request must include an `X-Hermes-Signature: sha256=<hex>` header where the hex is HMAC-SHA256 of the raw request body, keyed by the shared secret in `~/.hermes/secrets/webhook.env`. Constant-time comparison; invalid signatures get `401`.

The receiver refuses to start if `HERMES_WEBHOOK_SECRET` is not set — unauthenticated mode is not an option.

## Idempotency

Two layers:

1. **In-process dedup** in the receiver: same `approval_id` arriving twice within 60 seconds returns 200 OK but does NOT spawn a second Galileo. Handles Vercel retry storms.
2. **Downstream idempotency** in the worker: Hopper's `execute_approval.py` checks `approvals.metadata.executed` and no-ops if already true. Bell's `send-approved` does the same.

So even if both layers were bypassed, the customer email / SF write happens at most once.

## Install + run

```bash
# 1. Generate the shared secret (32 random bytes, hex-encoded)
mkdir -p ~/.hermes/secrets
chmod 700 ~/.hermes/secrets
python3 -c "import secrets; print('HERMES_WEBHOOK_SECRET=' + secrets.token_hex(32))" \
  > ~/.hermes/secrets/webhook.env
chmod 600 ~/.hermes/secrets/webhook.env

# 2. Install the systemd unit
mkdir -p ~/.config/systemd/user
cp services/webhook-receiver/hermes-webhook-receiver.service \
  ~/.config/systemd/user/

# 3. Enable + start
systemctl --user daemon-reload
systemctl --user enable --now hermes-webhook-receiver.service

# 4. Verify
systemctl --user status hermes-webhook-receiver.service --no-pager
journalctl --user -u hermes-webhook-receiver.service -n 20
curl -s http://localhost:8080/healthz
```

## Configuration (env vars)

| Var | Default | What |
|---|---|---|
| `HERMES_WEBHOOK_SECRET` | (required) | HMAC shared secret. The Operator-Surface side needs the same value in its Vercel env. |
| `HERMES_WEBHOOK_HOST` | `0.0.0.0` | Bind host. |
| `HERMES_WEBHOOK_PORT` | `8080` | Bind port. |
| `GALILEO_BIN` | `~/.local/bin/galileo` | Path to the galileo shim. Override if it lives elsewhere. |

## Operator-Surface (Vercel) side

Two env vars to add in Vercel **Project Settings → Environment Variables**:

| Var | Value |
|---|---|
| `HERMES_WEBHOOK_URL` | `http://137.184.137.125:8080/webhook/approval` |
| `HERMES_WEBHOOK_SECRET` | The same hex string from `~/.hermes/secrets/webhook.env` on the droplet |

Then the Server Action (in `src/app/approvals/actions.ts`) computes the signature over the body and POSTs to `HERMES_WEBHOOK_URL` after the DB update succeeds. Standard fire-and-forget — the Server Action doesn't block on the webhook response beyond the initial 202.

## Smoke test (after deploy)

```bash
# From the droplet:
SECRET=$(grep -oP '(?<=HERMES_WEBHOOK_SECRET=).*' ~/.hermes/secrets/webhook.env)
BODY='{"approval_id":"test-id-12345","decision":"approved"}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print "sha256="$2}')

curl -sS -X POST http://localhost:8080/webhook/approval \
  -H "Content-Type: application/json" \
  -H "X-Hermes-Signature: $SIG" \
  -d "$BODY"
# Expect: HTTP 202, {"ok":true,"approval_id":"test-id-12345","dispatched":true,...}
# Galileo will fail to find the test-id-12345 approval — that's expected; the
# receiver itself worked. Check `journalctl --user -u hermes-webhook-receiver`
# to see the dispatch log line.

# Test bad signature:
curl -sS -X POST http://localhost:8080/webhook/approval \
  -H "Content-Type: application/json" \
  -H "X-Hermes-Signature: sha256=deadbeef" \
  -d "$BODY"
# Expect: HTTP 401, {"ok":false,"error":"signature invalid or missing"}
```

## Logs + observability

`journalctl --user -u hermes-webhook-receiver.service -f` tails live logs.

Every request gets a 12-char correlation id (`corr_id`) included in:
- The receiver's log line
- The prompt sent to Galileo (so his ledger entries reference back to it)
- The response body returned to Operator-Surface

If something goes wrong end-to-end, `grep corr=<id>` across journalctl + Galileo's ledger gives you the full trail.

## What it does NOT do

- Does not store webhook payloads anywhere. The payload is verified, dispatched, and discarded. Audit data lives in Supabase (the approval row's metadata) and the worker ledger.
- Does not retry on its own. If Galileo's process spawn fails, the receiver returns 5xx and Operator-Surface should retry — or the operator can click Approve again, and downstream idempotency means at most one execution.
- Does not handle WebSockets or long-lived connections. Pure request/response.
- Does not TLS. Behind nginx + Let's Encrypt is the production answer; for tonight's demo, the HMAC signature is the auth, and Vercel will call any URL.
