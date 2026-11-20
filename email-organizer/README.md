# Email organizer

A Claude-run Gmail organizer for Efaz, built to sit next to the job hunter. It keeps the inbox to what needs
Efaz, makes job mail impossible to lose, and stops newsletters and promotions for real.

What it combines and why: [docs/analysis.md](docs/analysis.md).

## What it does

| Ask Claude | Command | What happens |
|---|---|---|
| "check my email" | `/triage` | Last 24h sorted into Reply or act / Job mail / Review / Noise. Drafts replies on request, never sends |
| "clean up my mailbox" | `/cleanup` | Every sender grouped by domain → review page → real unsubscribes → backlog to Trash |
| "sort my mail into labels" | `/labels` | Logged passes of 200-300 threads, learned from how Efaz already labels, plus a filter file |
| "any job emails?" | `/jobmail` | Job alerts and employer replies lined up for the nightly job run |
| "where are we?" | `/mail-status` | Checkpoints, undo log, manual unsubscribes left, filters to retire |

## Safety rules (all skills)

1. **Trash only**, never permanent delete. Trash keeps mail 30 days. Emptying Trash is Efaz's job.
2. **Nothing changes without a yes in the thread**: no trash, label pass, archive, unsubscribe or filter until approved.
3. **Never sends email.** Replies are drafts; Efaz presses Send.
4. **Security mail stays bare**: OTPs, sign-in alerts and password resets are never labelled or trashed.
5. **Protected senders** (bKash, banks, bills, orders, government, education, health, anyone Efaz writes to,
   and all job mail) are never bulk-trashed. Unsure → keep.
6. **Starred mail is never trashed.**
7. **Every change is logged** in `logs/undo-log.jsonl` with thread ids, so any pass can be reversed.

## Setup (once, about 5 minutes)

1. Gmail is already connected to Claude (the built-in Gmail connector). Nothing else to install: the scripts are
   Python 3.9+ standard library only.
2. Copy the example rules and fill in your own:
   ```bash
   cp config/my-rules.example.json config/my-rules.json
   ```
   Put in your own addresses, `work_domains` (bkash.com), family and close contacts (`vip_senders`), and
   anything to leave alone (`never_touch`). `my-rules.json` is gitignored.
3. To use the slash commands in Claude Code, add this folder as a plugin, or just ask in the project thread
   ("check my email", "clean up my mailbox"); the skills work either way.
4. After the first cleanup or a few label passes, import `work/mailFilters.xml` in
   Gmail → Settings → Filters and Blocked Addresses → Import filters, and tick "Apply new filters to existing email".

## Layout

| Path | What it is |
|---|---|
| `skills/email-triage/` | Daily triage |
| `skills/inbox-cleanup/` | Inventory, review, unsubscribe, trash. `references/` has pitfalls and protected senders |
| `skills/label-organizer/` | Label passes, filters, undo |
| `skills/job-mail/` | Handoff to `../nightly-run.md` |
| `commands/` | `/triage`, `/cleanup`, `/labels`, `/jobmail`, `/mail-status` |
| `config/rules.default.json` | Patterns, labels, job alert senders, sender → label map |
| `gmail_org/` | Scripts (`python -m gmail_org <command>`): `classify`, `inventory`, `review-page`, `filters`, `unsubscribe`, `undo-log`, `jobs` |
| `tests/` | `python -m unittest discover -s tests` |
| `work/`, `logs/` | Mailbox data and the undo log. Gitignored, never committed |

## Try it without touching Gmail

```bash
cd email-organizer
python -m gmail_org classify examples/messages.sample.json --report
python -m gmail_org jobs examples/messages.sample.json
python -m gmail_org filters --out /tmp/mailFilters.xml
```

## Credits

Ideas and rules adapted from shawnchiao/gmail-organize-skill, dcerniglia/gmail-cleanup-mcp,
sarangk3/gmail-cleanup-agent, ericporres/email-triage-plugin and noambrand/gmail-label-cleanup. Ideas and rules were rewritten here, not copied.
