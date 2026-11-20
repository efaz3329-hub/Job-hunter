---
name: inbox-cleanup
description: Use when the mailbox is full or out of storage, has thousands of unread messages, or the user wants to unsubscribe from newsletters and promotions, clear the backlog, or reach inbox zero; also /cleanup. Inventories every sender by domain, builds a review page, then unsubscribes for real and moves the approved backlog to Trash.
---

# Inbox cleanup

From shawnchiao/gmail-organize-skill (domain inventory, review page, real unsubscribes, protected
senders, pitfalls), with dry-run-first execution from dcerniglia/gmail-cleanup-mcp and the
keep-when-unsure rules from sarangk3/gmail-cleanup-agent.

**Read `references/pitfalls.md` before starting.** It is short and every line cost someone mail.

Work in `work/cleanup/`. Every phase writes a file, so a killed session resumes from the files alone.

## Absolute rules

1. Trash only. Never permanent delete. Emptying Trash is the user's action, and no storage comes back until they do.
2. Every trash query ends with `-is:starred`.
3. Never bulk-trash a protected category (`references/protected-senders.md`). Unsure → keep.
4. Nothing is unsubscribed or trashed until the user has returned decisions from the review page.
5. Unsubscribing is outbound. Show the batch and get a yes before `--execute`.
6. Marketing and records share domains: offer "unsubscribe only, keep the mail".

## Modes

- **safe** (default): every domain goes through the review page.
- **fast**: domains the inventory marks `delete` with 20+ messages and an unsubscribe link are pre-approved;
  everything else still goes to review. Only on the user's explicit request.

## Phases

| | Phase | Writes |
|---|---|---|
| 0 | Baseline: inbox count, `in:trash`, `in:spam`, storage figure from the user | `baseline.json` |
| 1 | Inventory every sender | `inventory-*.json` → `review-data.json` |
| 2 | Review page, decisions back | `decisions.json` |
| 3 | Unsubscribe active `delete` senders | `unsub-ledger.jsonl` |
| 4 | Trash approved backlog, rescue sweep | undo-log entry |
| 5 | Labels + filters (label-organizer skill) | `mailFilters.xml` |
| 6 | Monthly routine | — |

Phases 3 and 4 can run in parallel. 5 depends on neither.

### 0. Baseline
Ask two questions first: should labelled mail still land in the inbox (default: yes, only pure deals skip it),
and safe or fast. Save the answers in `config/my-rules.json` notes so the next run does not ask again.

### 1. Inventory
Slice by age so the work can be split and resumed:

```
-in:sent -in:chats newer_than:1y
-in:sent -in:chats older_than:1y newer_than:3y
-in:sent -in:chats older_than:3y
```

Per slice, page `search_threads` to exhaustion (never trust `resultCountEstimate`, it caps near 201).
Aggregate in memory to `{address: {count, latest, unsub, subjects[≤5]}}` and write `inventory-<slice>.json`.
If you hand a slice to a subagent, it writes its file before returning and returns the exact `nextPageToken`
if it stopped early, so the next agent continues from it.

```bash
python -m gmail_org inventory --dir work/cleanup --out work/cleanup/review-data.json
```

Check: are the senders the user complains about in the list? If not, the sweep is incomplete. Say so.

### 2. Review
```bash
python -m gmail_org review-page --data work/cleanup/review-data.json --out work/cleanup/review.html
```
Publish or attach the page. The user flips each domain between delete / promo / keep / skip and pastes back the
`DECISIONS v1` block. Parse it with `gmail_org.review_page.parse_decisions` into `decisions.json`.
If the paste is ambiguous (a count that doesn't match, a header missing), **ask**. A wrong guess trashes thousands.

### 3. Unsubscribe
Only `delete` domains active in the last 6 months. Dormant ones just need their backlog trashed.

For each address: newest message (`search_threads from:<addr>`, 1 result) → `List-Unsubscribe` and
`List-Unsubscribe-Post` headers. If the connector does not expose headers, read the message in a subagent
(~10 senders each) and extract the link (`unsubscribe`, `opt-out`, `preferences`, `list-manage`). No body
reaches the main context. Write `senders.json`, then:

```bash
python -m gmail_org unsubscribe work/cleanup/senders.json --ledger work/cleanup/unsub-ledger.jsonl          # dry run
python -m gmail_org unsubscribe work/cleanup/senders.json --ledger work/cleanup/unsub-ledger.jsonl --execute --allow-get   # after yes
```

Expect 60-75% automatic. The rest (logins, JavaScript pages, mailto) go to the user as a list of links.
A temporary trash filter covers them meanwhile (phase 5).

### 4. Trash the backlog
Per approved domain group (≤20 domains): first preview, then act.

```
from:(d1 OR d2 OR ...) -is:starred
```

1. Count with `search_threads` and show "would trash N threads from these domains".
2. On yes, `trash_thread` per thread id. Batch steadily; if Gmail starts refusing (rate limit), stop,
   do something else for ~30 minutes, then continue. It is not an auth problem.
3. Log the thread ids: `python -m gmail_org undo-log add --log logs/undo-log.jsonl --entry <file>`.
4. **Rescue sweep** for any mixed domain before telling the user to empty Trash:
   `in:trash from:(<domain>) (bill OR invoice OR payslip OR statement OR receipt OR tax OR otp)` → `untrash_thread`.

For tens of thousands of threads, the browser is faster: search → select all → "Select all conversations that
match this search" → Delete. Use it only with the user's go-ahead and verify the count dropped.

### 5. Labels and filters
Hand off to the `label-organizer` skill: create labels, then
`python -m gmail_org filters --out work/mailFilters.xml --decisions work/cleanup/decisions.json`.

### 6. Maintain (offer a monthly reminder)
- `label:Subscriptions/Deals older_than:30d -is:starred` → trash (after showing the count)
- `newer_than:30d unsubscribe -label:Subscriptions/Deals -label:Subscriptions/News` → new senders to review
- Retire temporary trash filters for senders that have stopped
- Empty Trash (user)

## Report

Lead with before/after inbox count (and storage once the user empties Trash; the figure lags hours).
Then: what was unsubscribed, what needs a manual unsubscribe (links), anything you are unsure about and how to
get it back (Trash, 30 days), and the one thing only they can do: empty Trash. State what did not finish.
