---
name: job-mail
description: Use when handling job-related email - job alerts from LinkedIn, BDjobs, Skill.jobs, employer replies, interview calls, rejections, application confirmations - or when Job-hunter's nightly run needs its Gmail step; also /jobmail. Sorts job mail, labels it, and lines replies up with tracker.csv without editing it.
---

# Job mail

The bridge between this organizer and Job-hunter (`../nightly-run.md`, `../score.py`). The organizer
keeps job mail findable and never lets cleanup touch it; Job-hunter decides what to apply to.

## Sort step (nightly run step 2, or /jobmail)

1. Search the last ~2 days:
   ```
   newer_than:2d -in:sent -in:chats (from:(jobalerts-noreply@linkedin.com OR jobs-noreply@linkedin.com OR bdjobs.com OR skill.jobs)
     OR interview OR shortlisted OR assessment OR "your application" OR "thank you for applying" OR unfortunately OR offer)
   ```
   Save to `work/jobs/messages.json` (same shape as triage).
2. Sort:
   ```bash
   python -m gmail_org jobs work/jobs/messages.json --tracker <path to tracker.csv> > work/jobs/sorted.json
   ```
   - `alerts`: read each alert (in a subagent if there are many), extract jobs, and continue with
     nightly-run.md steps 3-7 (dedupe against tracker.csv, fill score.py facts, score, report).
   - `status_updates`: employer replies matched to a tracker company. Read the thread, confirm, and give the
     nightly run the new status (interview → put prep in the report; rejected → close it out).
   - `unmatched`: employer-looking replies with no tracker match. Read them; they may be from an application
     made outside the tracker. Put them in the report's Pipeline line.
3. Interview invitations and offers are urgent: if one arrives, say so at the top of the report and the
   thread message, with the date or deadline from the email.

## Labels

`Jobs/Alerts`, `Jobs/Applications`, `Jobs/Interviews`, `Jobs/Rejections`. Labelling is applied with the
owner's approval, or automatically once they have said so (record in `config/my-rules.json` → `_approvals`).
Job alerts stay in the inbox by default; the filter file can archive them with `--jobs-skip-inbox` if the
owner prefers.

## Safety

- Job mail is protected: cleanup never trashes or unsubscribes from job alert senders or anyone in tracker.csv.
- Never reply to an employer or send an application. Drafts only, and Efaz presses Send
  (same rule as nightly-run.md).
- Never edit tracker.csv from this step; the nightly run owns it.
