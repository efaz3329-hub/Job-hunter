---
name: label-organizer
description: Use when the user wants Gmail sorted into labels, thousands of unlabelled messages filed, a label scheme set up, Gmail filters created in bulk, or a labelling pass undone; also /labels. Learns rules from how the owner already labels mail, works the backlog in logged reversible passes, and writes an importable Gmail filter file so new mail sorts itself.
---

# Label organizer

From noambrand/gmail-label-cleanup (learn rules from the owner's own labelling, bounded passes, undo log,
security mail stays bare) and dcerniglia/gmail-cleanup-mcp (filters as the part that stops the pile growing).
The built-in Gmail connector has no filter API, so filters are delivered as a Gmail import file.

## Label scheme

Defaults live in `config/rules.default.json` → `labels`. Create only the ones the owner wants, with
`list_labels` first so nothing is duplicated, then `create_label`:

```
Jobs/Alerts  Jobs/Applications  Jobs/Interviews  Jobs/Rejections
Finance  Bills  Receipts & Orders  Travel  Learning  Social
Subscriptions/News  Subscriptions/Deals  Subscriptions/Tech
```

## The one rule

**Rules are learned from the owner's past labelling, never invented.** For each existing label,
`search_threads label:"<name>"`, read 30-50 results, record the senders in `config/my-rules.json` →
`sender_labels`. Only a sender with no precedent gets a judgement call, and that call is written into the
undo-log entry as a judgement call so it can be corrected.

Content counts too: a sender can earn two labels (a receipt from a learning platform → Learning and Receipts).
Add a second label only when the owner would look under either one.

When the owner rules on something ("leave that newsletter bare", "that's family"), write it into
`config/my-rules.json` right away (`never_touch`, `vip_senders`, `sender_labels`).

## A pass

One bounded, logged, reversible chunk: 200-300 threads.

1. **Find unlabelled mail.** Inbox first:
   `has:nouserlabels in:inbox`
   Then the archive, walking backwards by date (survives interruption, no page tokens):
   `has:nouserlabels -in:inbox -in:sent -in:draft -in:trash -in:spam -in:chats before:YYYY/MM/DD`
   Next call's `before:` is the date of the oldest result just handled.
2. **Classify.** Write the page to `work/labels/page.json` and run
   `python -m gmail_org classify work/labels/page.json > work/labels/classified.json`.
   Sender plus subject decides 90%+. Open a message only when the sender is new and the subject is ambiguous.
3. **Show the plan** to the owner: counts per label, the judgement calls, what stays bare. Wait for yes
   (after the first few passes the owner may say "go ahead with passes like this"; record that in my-rules.json
   under `_approvals` with the date and scope).
4. **Apply.** Group thread ids per label; `label_thread` per thread. On a concurrency/rate error retry only the
   failed ids.
5. **Log** every pass, even a boring one:
   ```bash
   python -m gmail_org undo-log add --log logs/undo-log.jsonl --entry work/labels/entry.json
   ```
   with `changes` (op, label, thread_ids), `judgement_calls`, and `left_bare`.

When the inbox stops yielding, what remains is the deliberately bare set (security mail, family, never-touch).
That is the end state; say so instead of "nothing found".

## Never label or trash

- One-time codes, magic links, password resets, sign-in and security alerts. Codes must be findable fast.
- Anything on `never_touch`.
- Personal mail, unless the owner already labels that person.

## Filters

A Gmail filter only acts on mail that arrives after it exists, unless "Apply new filters to existing email" is
ticked at import. Generate the file after the first few passes have revealed the real high-volume senders,
and again every few weeks:

```bash
python -m gmail_org filters --out work/mailFilters.xml [--decisions work/cleanup/decisions.json] [--tos-trash]
```

Tell the owner: Gmail → Settings → See all settings → Filters and Blocked Addresses → Import filters →
choose `mailFilters.xml` → Open file → tick "Apply new filters to existing email" → Create filters.
Mention which filters are temporary trash filters and when to retire them.

`--tos-trash` (terms/privacy-policy notices to Trash) only if the owner asks; its negation keeps verify/code mail out.

## Undo

```bash
python -m gmail_org undo-log reverse --log logs/undo-log.jsonl --pass 7
```
prints the reverse operations (remove_label / untrash). Show them, and apply on yes with `unlabel_thread`
and `untrash_thread`. Untrash works for 30 days.
