---
description: Inventory every sender, review, then unsubscribe and trash the backlog (approval-gated)
argument-hint: "[safe | fast]"
---

Load the `inbox-cleanup` skill and run it from the phase the checkpoint files say is next
(start at phase 0 when `work/cleanup/` is empty). Default mode is `safe`.
Nothing is unsubscribed or trashed until the user has returned the review decisions.
