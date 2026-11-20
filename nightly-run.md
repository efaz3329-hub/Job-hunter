# Nightly run (11:05 PM Dhaka, report by 11:30 PM)

Steps the scheduled run follows. Never submit an application or send an email to an employer.

1. Read profile.md, master-cv.md, tracker.csv.
2. Gmail search for job alerts from the last ~26 hours:
   `from:(jobalerts-noreply@linkedin.com OR jobs-noreply@linkedin.com OR bdjobs.com OR skill.jobs) newer_than:2d`
   Also check for replies from employers (interview calls, rejections) for jobs in tracker.csv and update status.
   The `job-mail` skill in email-organizer/ does this sorting: `python -m gmail_org jobs` splits the mail into
   alerts, tracker status updates and unmatched employer replies (see email-organizer/skills/job-mail/SKILL.md).
3. Extract each job (title, company, location, link, deadline, salary if shown). Drop any already in tracker.csv.
4. For each job, fill the facts in score.py's format from the alert text (and the posting, when it can be read).
   When the full posting cannot be read, score from what is known and mark "preliminary".
5. Run `python score.py today.json`. Skips are counted, not listed.
6. Write reports/{YYYY-MM-DD}.md from report-template.md: up to 8 shortlisted jobs with why, gaps, prep.
7. Append all new jobs to tracker.csv with status `new` (or `skipped`).
8. Post a short summary in the project thread with the report attached, which notifies Efaz's phone.
9. Follow-ups: any applied job with follow_up_on <= today goes in the report's Pipeline line.

On approval ("apply 1, 3"): open the posting (in Efaz's Chrome when needed), write a tailored CV and cover letter from
master-cv.md into applications/{id}/, then either fill the form for Efaz to submit or create a Gmail draft for email
applications. Set status `ready`, then `applied` once Efaz confirms, with follow_up_on = applied + 7 days.
