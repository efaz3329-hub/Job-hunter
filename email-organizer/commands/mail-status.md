---
description: Show the organizer's state - checkpoints, undo log, pending manual unsubscribes, temporary filters to retire
---

Without touching the mailbox, read `work/` and `logs/` and report:
1. Cleanup phase reached (from `work/cleanup/*.json`), and what is next.
2. Last 3 undo-log passes: `python -m gmail_org undo-log show --log logs/undo-log.jsonl --last 3`.
3. Senders in `work/cleanup/unsub-ledger.jsonl` with status `manual*`, with their links.
4. Temporary trash filters older than 14 days that should be retired.
5. Whether Trash still needs emptying after the last cleanup.
