# Pitfalls

Condensed from the source repos' run notes (mainly shawnchiao/gmail-organize-skill and
noambrand/gmail-label-cleanup). Each one cost real time or real mail.

1. **Gmail's subscriptions page is incomplete.** It lists only what Gmail calls a subscription; one run found
   104 there versus 661 sending domains by search. Build the inventory from search, never from that page.
2. **Group by registrable domain, not address.** One retailer, three addresses. `from:(brand.com)` matches subdomains.
   Watch two-part suffixes such as `.com.bd` (handled in `gmail_org/domains.py`).
3. **`resultCountEstimate` is not a count.** It caps near 201. Page to exhaustion or say the figure is partial.
4. **Pagination outlives one agent.** ~80 pages per agent. Write partial results to disk and pass the exact
   `nextPageToken` on. Page tokens expire; for resumable archive work, page by date (`before:YYYY/MM/DD`).
5. **Message bodies kill context.** A marketing email is 30-250 KB of HTML. Inventory with metadata only;
   extract unsubscribe links in subagents, ~10 senders each.
6. **Never click row-by-row in a live list.** Rows shift after each unsubscribe; one run unsubscribed seven
   wanted senders. Use `List-Unsubscribe` links instead. Bulk select-all in the message list is reliable.
7. **Split active from dormant.** A sender silent for 6+ months needs only its backlog trashed. Usually halves the work.
8. **Trash counts toward storage.** Nothing is reclaimed until Trash is emptied (by the user, or after 30 days).
   Say it before they ask. Bulk trashing keeps landing for minutes; empty Trash after it settles.
9. **Gmail throttles bulk work.** Errors like `#2002` or "Too many concurrent requests": stop, do other work,
   come back in ~30 minutes. Retry only the ids that failed, never the whole batch.
10. **Filters are scaffolding.** An auto-trash filter does not stop the sender. Use it while an unsubscribe
    takes effect, then retire it.
11. **Records hide in "junk" domains.** Telecoms send offers and bills; banks send offers and statements; the
    employer sends newsletters and payslips. Offer "unsubscribe only, keep the mail", and run the rescue sweep.
12. **Decide the destination before filtering.** A blanket skip-inbox rule made someone's job alerts vanish.
    Default: labelled mail stays in the inbox; only pure deals skip it.
13. **Filters never touch old mail** unless "Apply to existing" is ticked at import. The backlog is separate work.
14. **A Gmail filter carries one user label.** Two labels means two filters.
15. **The terms-of-service trash rule needs its negation**, or "Verify your email, updated Terms" goes to Trash.
16. **Assume the session dies mid-job.** Checkpoint every phase to a file. Write before returning, not after.
