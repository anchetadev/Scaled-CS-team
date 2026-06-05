#!/usr/bin/env python3
"""Hopper Salesforce writer connector — write-scope, OAuth Client Credentials.

Mirrors Tycho sf_reader.py shape but with create/update support against the
allowlisted objects Hopper is permitted to touch. Same OAuth Client
Credentials flow against a dedicated Connected App whose Run-As user holds
a narrow write permission set.

Stub mode: if env vars are missing, returns dry-run results that look like
real SF responses (ok=True, id="STUB-<uuid>"). This lets the entire pipeline
(Operator-Surface webhook → Hermes receiver → Galileo → Hopper) be smoke-
tested before the Connected App + permission set are live.

Stub mode is announced explicitly in the result so nothing accidentally
relies on a fake id thinking it is real.
"""

import json
import os
import sys
import uuid
import urllib.error
import urllib.request


WRITE_ALLOWLIST = {
    "Account": {"Health_Band__c", "CSM_Save_Plan__c", "Customer_Sentiment__c", "Meeting_Cadence__c", "Description"},
    "Opportunity": {"StageName", "CloseDate", "Amount", "CSM_Forecast__c", "Description"},
    "Contact": {"Title", "Email", "Description"},
    "Task": {"Subject", "ActivityDate", "Priority", "Status", "WhatId", "OwnerId", "Description"},
    "Event": {"Subject", "ActivityDate", "StartDateTime", "EndDateTime", "WhatId", "OwnerId"},
    "Risk_Flag__c": {"Account__c", "Risk_Type__c", "Status__c", "Description__c"},
    "FeedItem": {"ParentId", "Body"},
}


class SalesforceWriter:
    """Thin write-side wrapper around the SF REST API.

    All writes pass through `_check_allowlist` first — refuses to write to
    objects/fields outside the configured allowlist. This is the *third*
    layer of write protection (the others being: the Connected App user's
    permission set, and the bright-line check in execute_approval.py).
    """

    def __init__(self, instance_url, access_token, stub=False):
        self.instance_url = (instance_url or "").rstrip("/") if not stub else None
        self.access_token = access_token
        self.stub = stub

    @classmethod
    def from_env(cls, env):
        url = env.get("SALESFORCE_HOPPER_INSTANCE_URL")
        key = env.get("SALESFORCE_HOPPER_CONSUMER_KEY")
        secret = env.get("SALESFORCE_HOPPER_CONSUMER_SECRET")
        if not (url and key and secret):
            return cls(None, None, stub=True)
        token, instance = cls._get_token(url, key, secret)
        return cls(instance, token, stub=False)

    @staticmethod
    def _get_token(instance_url, consumer_key, consumer_secret):
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": consumer_key,
            "client_secret": consumer_secret,
        }).encode()
        req = urllib.request.Request(
            instance_url.rstrip("/") + "/services/oauth2/token",
            data=body,
            method="POST",
        )
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                j = json.loads(resp.read().decode())
                return j["access_token"], j.get("instance_url", instance_url)
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                "SF OAuth failed: " + str(e.code) + " " + e.read().decode()[:300]
            )

    # ---------------- public API ----------------

    def create(self, sobject, fields):
        self._check_allowlist(sobject, fields.keys())
        if self.stub:
            return self._stub_create(sobject, fields)
        return self._api("POST", "/sobjects/" + sobject + "/", fields)

    def update(self, sobject, record_id, fields):
        self._check_allowlist(sobject, fields.keys())
        if self.stub:
            return self._stub_update(sobject, record_id, fields)
        return self._api(
            "PATCH",
            "/sobjects/" + sobject + "/" + record_id,
            fields,
        )

    def user_id_for_email(self, email):
        """Look up a User Id by email — used for OwnerId resolution.

        Stub mode returns a deterministic fake id so tests are stable.
        """
        if self.stub:
            return "STUB-USER-" + email
        soql = "SELECT Id FROM User WHERE Email='" + email.replace("'", "\\'") + "' LIMIT 1"
        st, body = self._api_raw(
            "GET",
            "/query?q=" + urllib.parse.quote(soql),
        )
        if st == 200 and body and body.get("records"):
            return body["records"][0]["Id"]
        return None

    # ---------------- internals ----------------

    def _check_allowlist(self, sobject, fields):
        if sobject not in WRITE_ALLOWLIST:
            raise PermissionError(
                "Hopper is not permitted to write to " + sobject +
                " — add to WRITE_ALLOWLIST if intentional"
            )
        bad = [f for f in fields if f not in WRITE_ALLOWLIST[sobject]]
        if bad:
            raise PermissionError(
                "Hopper is not permitted to write fields " + str(bad) +
                " on " + sobject + " — add to WRITE_ALLOWLIST if intentional"
            )

    def _api(self, method, path, body=None):
        st, parsed = self._api_raw(method, path, body)
        if st in (200, 201):
            return {"ok": True, "id": (parsed or {}).get("id"), "status": st}
        if st == 204:
            return {"ok": True, "id": None, "status": 204}
        return {"ok": False, "error": parsed, "status": st}

    def _api_raw(self, method, path, body=None):
        if not self.access_token:
            raise RuntimeError("SF client has no access token (stub mode misuse?)")
        url = self.instance_url + "/services/data/v60.0" + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + self.access_token)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                txt = resp.read().decode()
                return resp.status, (json.loads(txt) if txt else None)
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode())
            except Exception:
                detail = {"raw": "(unparseable)"}
            return e.code, detail

    # ---------------- stub-mode shims ----------------

    def _stub_create(self, sobject, fields):
        stub_id = "STUB-" + sobject + "-" + uuid.uuid4().hex[:12]
        return {
            "ok": True,
            "id": stub_id,
            "status": 201,
            "stub": True,
            "note": "no SF creds configured; returning stub success",
            "would_have_written": {sobject: fields},
        }

    def _stub_update(self, sobject, record_id, fields):
        return {
            "ok": True,
            "id": record_id,
            "status": 204,
            "stub": True,
            "note": "no SF creds configured; returning stub success",
            "would_have_written": {sobject: {record_id: fields}},
        }


# urllib.parse is needed for query escaping above; import lazily so the
# module loads cleanly even on minimal interpreters.
import urllib.parse  # noqa: E402


# Smoke-test mode: `python3 sf_writer.py` prints whether SF creds are
# configured and what mode the writer would run in.
if __name__ == "__main__":
    env = {k: v for k, v in os.environ.items() if k.startswith("SALESFORCE_HOPPER_")}
    if not env:
        # Try reading the profile env too — same logic as execute_approval.py
        env_path = os.path.expanduser("~/.hermes/profiles/hopper/.env")
        if os.path.exists(env_path):
            for line in open(env_path):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.startswith("SALESFORCE_HOPPER_"):
                        env[k] = v.strip()
    have = sorted(k for k in env if env[k])
    missing = [k for k in (
        "SALESFORCE_HOPPER_INSTANCE_URL",
        "SALESFORCE_HOPPER_CONSUMER_KEY",
        "SALESFORCE_HOPPER_CONSUMER_SECRET",
    ) if k not in have]
    print(json.dumps({
        "have": have,
        "missing": missing,
        "mode": "live" if not missing else "stub",
        "allowlist_objects": sorted(WRITE_ALLOWLIST.keys()),
    }, indent=2))
