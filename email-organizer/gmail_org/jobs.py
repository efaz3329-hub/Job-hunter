"""Bridge to Job-hunter: pull job mail out of a scan and line it up with tracker.csv.

Job-hunter's nightly run (../nightly-run.md) reads job alerts and employer
replies. This step does the sorting so that run starts from a clean list:

  alerts          job alert emails to extract jobs from (then ../score.py)
  status_updates  employer replies matched to a company in tracker.csv,
                  with the suggested new status (interview / rejected / applied)
  unmatched       employer-looking replies with no tracker match: a human looks

It never changes tracker.csv itself; the nightly run does, after reading the mail.

Usage:
  python -m gmail_org jobs messages.json [--tracker ~/job-hunter-private/tracker.csv]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re

from .classify import Classifier
from .config import load_rules

STATUS = {"interview": "interview", "rejection": "rejected", "application": "applied"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def load_companies(tracker: str | None) -> list[str]:
    if not tracker or not os.path.exists(tracker):
        return []
    with open(tracker, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    names = {(r.get("company") or r.get("Company") or "").strip() for r in rows}
    return sorted(n for n in names if len(_norm(n)) >= 3)


def sort_job_mail(messages: list[dict], companies: list[str], rules: dict | None = None) -> dict:
    clf = Classifier(rules or load_rules())
    out = {"alerts": [], "status_updates": [], "unmatched": []}
    for m in messages:
        r = clf.classify(m)
        if r.category != "job":
            continue
        if r.job_event == "alert":
            out["alerts"].append({"id": r.id, "thread_id": r.thread_id, "from": r.sender, "subject": r.subject})
            continue
        hay = " " + _norm(f"{m.get('from', '')} {r.domain.split('.')[0]} {r.subject} {m.get('snippet', '')}") + " "
        company = next((c for c in companies if f" {_norm(c)} " in hay), None)
        item = {"id": r.id, "thread_id": r.thread_id, "from": r.sender, "subject": r.subject,
                "event": r.job_event, "suggested_status": STATUS[r.job_event]}
        if company:
            out["status_updates"].append({"company": company, **item})
        else:
            out["unmatched"].append(item)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sort job mail for Job-hunter's nightly run")
    ap.add_argument("messages")
    ap.add_argument("--tracker")
    ap.add_argument("--rules")
    a = ap.parse_args(argv)
    msgs = json.load(open(a.messages, encoding="utf-8"))
    res = sort_job_mail(msgs, load_companies(a.tracker), load_rules(a.rules))
    json.dump(res, __import__("sys").stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
