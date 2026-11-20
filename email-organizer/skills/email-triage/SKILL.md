---
name: email-triage
description: Use when the user asks to check email, triage the inbox, catch up on mail, get a morning or evening email summary, or runs /triage. Scans recent Gmail threads, sorts them into Reply / Review / Noise with job mail split out, and offers reply drafts and archiving. Read-only until the user approves an action.
---

# Email triage

Daily view of what needs Efaz. Built from ericporres/email-triage-plugin (tiers, snippet-first, numbered
items, never auto-send) plus this repo's rule engine so the same email lands in the same tier every day.

Run all commands from the `email-organizer/` folder.

## 1. Scan

Gmail connector `search_threads`:

```
in:inbox newer_than:1d -in:chats
```

Window: `today` → `newer_than:12h`, `3d` → `newer_than:3d`, `week` → `newer_than:7d`.
Use time windows, not `is:unread`: mail read on the phone is not mail dealt with.

Write the results to `work/triage/messages.json` in the shape `gmail_org/classify.py` documents
(`id, thread_id, from, subject, snippet, date, labels, list_unsubscribe, replied`). Metadata and
snippets only. Never put full HTML bodies in the main context.

More than ~80 threads: tell the user and work in date slices.

## 2. Classify

```bash
python -m gmail_org classify work/triage/messages.json > work/triage/classified.json
python -m gmail_org classify work/triage/messages.json --report
```

The script handles the common cases. Your job is the rest:
- Read the full thread (`get_thread`) only for Tier 1 items and for Tier 2 items marked
  "no rule matched" where the snippet is not enough.
- Promote to Tier 1 anything with a direct question to Efaz, a deadline, or a reply in a thread they started.
- Demote a "time-sensitive" item that is really marketing ("sale ends today").
- When you overrule the script for a sender twice, propose adding that sender to `config/my-rules.json`.

## 3. Present

```markdown
# Inbox triage, {date, Dhaka time}
{N} emails from the last 24h.

## Reply or act ({n})
1. **{Sender}**: {subject}
   {one line: what they need} → Reply / Schedule / Pay / Forward

## Job mail ({n})
{interviews and offers first, then rejections, then "N new alerts, handed to tonight's job run"}

## Review ({n})
- **{Sender}**: {subject}: {one line}

## Noise ({n})
{n} deals, {n} social, {n} news. Unsubscribe candidates: {top domains}.
→ Archive these? Unsubscribe from any?
```

Number Tier 1 items so the user can say "draft a reply to 2".

## 4. Actions (each needs the user's go-ahead in the thread)

- **Draft a reply**: read the whole thread, draft in Efaz's voice (short, warm, direct, first names),
  save with `create_draft`, show it. **Never send.** Sending is the user's action.
- **Archive noise**: list exactly what will be archived, wait for yes, then remove the `INBOX` label
  thread by thread. Log it with `python -m gmail_org undo-log add` (see label-organizer skill).
- **Unsubscribe**: hand the domains to the `inbox-cleanup` skill's phase 3.
- **Job mail**: hand to the `job-mail` skill.

## Never

Send mail, trash anything, or touch security mail (codes, sign-in alerts, password resets) during triage.
