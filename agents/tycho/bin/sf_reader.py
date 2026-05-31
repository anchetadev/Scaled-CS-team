#!/usr/bin/env python3
"""Tycho's read-only Salesforce connector (OAuth client-credentials). SELECT-only."""
import os, sys, json, re, requests
ENV_PATH = os.path.expanduser("~/.hermes/profiles/tycho/.env")
NEEDED = ["SALESFORCE_INSTANCE_URL","SALESFORCE_CONSUMER_KEY","SALESFORCE_CONSUMER_SECRET"]
def load_env():
    vals = {k: os.environ.get(k,"") for k in NEEDED}
    if not all(vals.values()) and os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            line = line.strip()
            if line.startswith("#") or "=" not in line: continue
            k, v = line.split("=", 1)
            if k in NEEDED and not vals.get(k): vals[k] = v.strip()
    return vals
def get_token():
    v = load_env()
    missing = [k for k in NEEDED if not v[k]]
    if missing:
        print(json.dumps({"ok":False,"error":"missing: "+",".join(missing)})); sys.exit(2)
    inst = v["SALESFORCE_INSTANCE_URL"].rstrip("/")
    r = requests.post(inst+"/services/oauth2/token",
        data={"grant_type":"client_credentials","client_id":v["SALESFORCE_CONSUMER_KEY"],
              "client_secret":v["SALESFORCE_CONSUMER_SECRET"]}, timeout=30)
    if r.status_code != 200:
        print(json.dumps({"ok":False,"error":"token request failed","status":r.status_code,"detail":r.text[:400]})); sys.exit(2)
    j = r.json(); return j["access_token"], j.get("instance_url", inst)
def connect():
    from simple_salesforce import Salesforce
    tok, inst = get_token()
    return Salesforce(instance_url=inst, session_id=tok)
def cmd_login():
    sf = connect(); r = sf.query("SELECT count() FROM Account")
    print(json.dumps({"ok":True,"instance":sf.sf_instance,"account_count":r["totalSize"]}))
def cmd_query(soql):
    s = soql.strip()
    if not re.match(r"(?is)^\s*SELECT\s", s):
        print(json.dumps({"ok":False,"error":"read-only: only SELECT allowed"})); sys.exit(3)
    if re.search(r"(?is)\b(INSERT|UPDATE|DELETE|UPSERT|MERGE)\b", s):
        print(json.dumps({"ok":False,"error":"read-only: DML keyword blocked"})); sys.exit(3)
    sf = connect(); r = sf.query_all(s)
    recs = [{k:v for k,v in rec.items() if k!="attributes"} for rec in r["records"][:50]]
    print(json.dumps({"ok":True,"totalSize":r["totalSize"],"records":recs}, default=str))
def cmd_boundary_test():
    sf = connect()
    try:
        res = sf.Account.create({"Name":"__tycho_boundary_test__"})
        rid = res.get("id") if isinstance(res,dict) else None
        cleaned = False
        if rid:
            try: sf.Account.delete(rid); cleaned = True
            except Exception: pass
        print(json.dumps({"ok":False,"boundary":"FAILED","detail":"write SUCCEEDED — read-only NOT enforced","cleaned_up":cleaned}))
    except Exception as e:
        print(json.dumps({"ok":True,"boundary":"ENFORCED","error_type":type(e).__name__,"detail":str(e)[:400]}))
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "login"
    try:
        if cmd=="login": cmd_login()
        elif cmd=="query": cmd_query(sys.argv[2])
        elif cmd=="boundary-test": cmd_boundary_test()
        else: print(json.dumps({"ok":False,"error":"unknown command: "+cmd})); sys.exit(1)
    except SystemExit: raise
    except Exception as e:
        print(json.dumps({"ok":False,"error_type":type(e).__name__,"detail":str(e)[:400]})); sys.exit(4)
