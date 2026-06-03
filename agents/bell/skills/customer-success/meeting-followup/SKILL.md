---
name: meeting-followup
description: "After a CSM meeting: read the transcript, post an internal Chatter summary to the Salesforce Opportunity, draft a customer follow-up email, and send it from the CSM's Gmail only after CSM approval."
version: 0.1.0
author: anchetadev
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [customer-success, meeting, follow-up, chatter, email, gmail, salesforce, approval]
    related_skills: []
---

# Meeting Follow-up

Use this when Galileo hands you a customer meeting to follow up on — "Bell, follow up on the Pyramid call", "draft the recap for the GenePoint meeting", "the CSM just met with X, handle the follow-through". You turn a meeting record into (a) an internal Chatter note on the Opportunity and (b) a customer email the CSM approves before it sends.

## The five steps

### 1. Read the meeting record
For the demo the transcript arrives as an email in the CSM's inbox. Find and read it:

```bash
GAPI="python3 $(ls /home/hermes/.hermes/profiles/bell/skills/productivity/google-workspace/scripts/google_api.py /home/hermes/.hermes/skills/productivity/google-workspace/scripts/google_api.py 2>/dev/null | head -1)"
$GAPI gmail search "subject:transcript OR subject:recap newer_than:7d" --max 5     # find it
$GAPI gmail get <MESSAGE_ID>                                                       # read the body
```
Pull out: who met, the customer's situation/mood, decisions made, risks/concerns raised, and concrete action items (with owners + dates where stated).

### 2. Identify the Opportunity
Confirm which Salesforce Opportunity this meeting is about (from the email/account context). You need its Id to post Chatter. If unsure, ask Galileo — never post to the wrong account.

### 3. Post the internal Chatter summary (auto — this one you do)
Crisp, scannable, internal. Bullet the decisions, risks, and action items. Then post it:

```bash
python3 /home/hermes/sf_chatter.py <OPPORTUNITY_ID> "Meeting recap — <date>
Decisions: ...
Risks: ...
Action items: ... (owner, date)"
```
A successful post returns `{"ok": true, "feed_item_id": "..."}`. This is internal record-keeping — it does not touch the customer.

### 4. Draft the customer follow-up email (do NOT send)
Write it in the CSM's voice — warm, appreciative, a clear recap and next steps. Ground every claim in the transcript; use `[CSM: confirm X]` for anything unstated. Then submit it for the CSM's review by writing an approval record (the CSM sees it in the Operator Surface and approves/edits there):

```bash
python3 /home/hermes/propose_email.py '{"account":"<name>","opportunity_id":"<oppId>","to":["<customer email>"],"subject":"<subject>","body_md":"<the email>"}'
```
This creates a pending approval (`action_type: send_reply`). **You stop here.** The email is NOT sent.

### 5. Send only after approval
The CSM reviews in the Operator Surface and approves (possibly editing the text). When approved, send it as the CSM:

```bash
$GAPI gmail send --to "<customer email>" --subject "<subject>" --body "<approved body>" --from "\"<CSM name>\" <csm@gmail.com>"
```
The email goes out from the CSM's own Gmail. Mark the approval executed.

## Discipline

- **The customer email is never sent without approval.** Steps 1-4 are yours; step 5 only happens after a human says yes.
- **Never invent.** No commitment, date, number, or name that isn't in the transcript. Placeholder, don't guess.
- **Right Opportunity only.** Confirm before posting Chatter.
- **Two registers.** The Chatter note is for the team (factual, bulleted); the email is for the customer (warm, in the CSM's voice). Don't blur them.

## Status note (wiring in progress)
- Step 3 (Chatter via `sf_chatter.py`) is live and tested.
- Steps 1 & 5 (Gmail read/send) require the demo CSM's Google account to be authorized on this Hermes home (`~/.hermes/google_token.json`).
- Step 4 (`propose_email.py`) writes to the shared Supabase `approvals` table and requires the service key at `/home/hermes/.scaled-cs.env`.
