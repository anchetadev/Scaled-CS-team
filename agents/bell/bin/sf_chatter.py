#!/usr/bin/env python3
"""Bell's Chatter writer — post a FeedItem to a Salesforce record.

This is Bell's *auto* write: an internal Chatter summary on an Opportunity.
Customer-facing email is NOT this — that flow goes through propose_email.py
and requires explicit human approval.

usage: sf_chatter.py <parentId> <body text>
       (body can also be piped on stdin if omitted)

Auth: OAuth 2.0 Client Credentials against the Salesforce CS Seeder External
Client App (admin role). Loads creds from the bell profile .env:
  SALESFORCE_SEEDER_INSTANCE_URL
  SALESFORCE_SEEDER_CONSUMER_KEY
  SALESFORCE_SEEDER_CONSUMER_SECRET
"""
import os, sys, json, requests
from simple_salesforce import Salesforce

ENV_PATH = os.path.expanduser("~/.hermes/profiles/bell/.env")
NEEDED = [
    "SALESFORCE_SEEDER_INSTANCE_URL",
    "SALESFORCE_SEEDER_CONSUMER_KEY",
    "SALESFORCE_SEEDER_CONSUMER_SECRET",
]


def load_env():
    v = {k: os.environ.get(k, "") for k in NEEDED}
    if not all(v.values()) and os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, val = line.split("=", 1)
            if k in NEEDED and not v.get(k):
                v[k] = val.strip()
    return v


def connect():
    v = load_env()
    missing = [k for k in NEEDED if not v[k]]
    if missing:
        print(json.dumps({"ok": False, "error": "missing: " + ",".join(missing)}))
        sys.exit(2)
    inst = v["SALESFORCE_SEEDER_INSTANCE_URL"].rstrip("/")
    r = requests.post(
        inst + "/services/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": v["SALESFORCE_SEEDER_CONSUMER_KEY"],
            "client_secret": v["SALESFORCE_SEEDER_CONSUMER_SECRET"],
        },
        timeout=30,
    )
    if r.status_code != 200:
        print(json.dumps({"ok": False, "error": "auth", "detail": r.text[:300]}))
        sys.exit(1)
    j = r.json()
    return Salesforce(instance_url=j.get("instance_url", inst), session_id=j["access_token"])


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "usage: sf_chatter.py <parentId> <body>"}))
        sys.exit(2)
    parent = sys.argv[1]
    body = sys.argv[2] if len(sys.argv) > 2 else sys.stdin.read()
    body = body.strip()
    if not body:
        print(json.dumps({"ok": False, "error": "empty body"}))
        sys.exit(2)
    sf = connect()
    try:
        res = sf.FeedItem.create({"ParentId": parent, "Body": body})
        print(json.dumps({"ok": True, "feed_item_id": res.get("id"), "parent": parent, "chars": len(body)}))
    except Exception as e:
        print(json.dumps({"ok": False, "error_type": type(e).__name__, "detail": str(e)[:400]}))
        sys.exit(3)


if __name__ == "__main__":
    main()
