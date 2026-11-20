---
description: Triage recent mail into Reply / Review / Noise, with job mail split out
argument-hint: "[today | 3d | week | work | jobs]"
---

Load the `email-triage` skill and run it.

Arguments: `today` = newer_than:12h, `3d` or `week` = newer_than:3d / 7d, default newer_than:1d.
`work` = only work-domain mail, `jobs` = only job mail (then also run the `job-mail` skill's sort step).
Read-only unless the user then approves an action.
