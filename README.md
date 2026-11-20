# Job hunter for Efaz

A Claude-run job hunting system: job alerts in Gmail -> filter -> score -> nightly report -> you approve -> Claude
prepares the application -> you press Submit.

| File | What it is |
|---|---|
| profile.md | Facts, targets, dealbreakers, salary rule |
| master-cv.md | The only facts a tailored CV may use |
| score.py | Fixed-formula fit score (0-97) so results stay consistent |
| report-template.md | Shape of the nightly report |
| nightly-run.md | Steps the 11:05 PM run follows |
| tracker.csv | Every job seen, its status and follow-up date |
| alert-setup.md | One-time job alert setup on LinkedIn, BDjobs, Skill.jobs |
| reports/ | One report per night |
| applications/ | Tailored CV + cover letter per approved job |
| email-organizer/ | Gmail organizer: daily triage, cleanup and unsubscribes, labels and filters, job-mail sorting for the nightly run. See [email-organizer/README.md](email-organizer/README.md) |

Commands to send in the project thread: "apply 1, 3", "skip 2", "never show {company}", "prep for {company}",
"status", "I got an interview at {company}".
For email: "check my email", "clean up my mailbox", "sort my mail into labels".

Personal files (profile.md, master-cv.md, tracker.csv, reports/, applications/) are gitignored and kept outside
this repository, because they hold contact details and CV data.
