# What the six reference repos do, and what this organizer takes from each

Read on 2026-11-20.

| Repo | Form | Core idea | Taken here |
|---|---|---|---|
| shawnchiao/gmail-organize-skill | Claude skill + 2 Python scripts | Full cleanup: inventory every sender by **registrable domain**, review page, real `List-Unsubscribe` unsubscribes, trash backlog, labels + filters, monthly routine. Strong pitfalls list from a real run. | The whole cleanup flow (`inbox-cleanup`), domain grouping, review page, protected senders, active vs dormant, rescue sweep, pitfalls |
| dcerniglia/gmail-cleanup-mcp | TypeScript MCP server (Gmail API, OAuth) | Fills the built-in connector's gaps: bulk trash (500/call), `search_and_trash` with **dry run**, filter create/list/delete, `List-Unsubscribe` extraction. | Dry-run-before-trash everywhere; filters as first-class output. Instead of running an OAuth server, filters ship as a Gmail import file |
| sarangk3/gmail-cleanup-agent | Prompt + standalone Python (rule lists) | Scan ~50 threads, classify DELETE/KEEP with reasons, review, trash. Keep list: people, action needed, finance, recent receipts, **job application updates**, security. | DELETE/KEEP rules folded into the rule engine; "ambiguous → keep" default |
| ericporres/email-triage-plugin | Claude Code plugin (skill + `/email`, `/summary`) | Daily triage into **Reply needed / Review / Noise**, time window instead of `is:unread`, snippet-first, numbered items, draft but never send, never auto-archive. | `email-triage` skill and `/triage`, plugin layout, tiers, draft-only replies |
| noambrand/gmail-label-cleanup | Claude skill + install scripts for a full Gmail MCP | Sort a huge backlog into the owner's **own** labels: rules learned from past labelling, never invented; bounded passes; date-walking pagination; **undo log** with judgement calls; security mail stays bare; ToS trash rule with negation. | `label-organizer` skill, `undo_log.py`, date-walking, one-label-per-filter, negated ToS rule |
| efaz3329-hub/Job-hunter | Markdown runbook + `score.py` | Nightly: job alerts in Gmail → extract → deterministic score → report → Efaz approves → Claude prepares, Efaz submits. | `job-mail` skill feeds the nightly run; job mail is protected from cleanup; same "script does the arithmetic, Claude does judgement" split (`classify.py` mirrors `score.py`) |

## Common ground across all six

- Trash, never permanent delete. Nothing outbound (send, unsubscribe) without a yes.
- Keep message bodies out of the main context; decide from sender + subject + snippet.
- When unsure, keep.
- Checkpoint to files; sessions die.

## Where they differ, and the choice made here

| Question | Options seen | Choice |
|---|---|---|
| How to reach Gmail | Built-in connector (triage, cleanup-agent), own MCP server with OAuth (cleanup-mcp, label-cleanup) | Built-in connector, which Efaz already has connected. No Google Cloud project or OAuth setup |
| Filters | Gmail settings by browser (organize-skill), filter API via own MCP (cleanup-mcp, label-cleanup) | Generated `mailFilters.xml`, imported once in Gmail settings |
| Labels | Small fixed scheme (organize-skill) vs owner's existing labels (label-cleanup) | Small default scheme, overridden by whatever Efaz already uses |
| Consistency | LLM judgement each time vs fixed rule lists | Rule engine for common cases, Claude for the rest, rules grow from Efaz's corrections |
