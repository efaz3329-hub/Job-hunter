"""Append-only undo log: every pass that changes the mailbox writes one entry.

The useful part is not the count, it is the judgement calls: "this sender had
no precedent, I put it under X, because Y". That is the line the owner reads
and corrects. The thread ids are what make a pass reversible.

Usage:
  python -m gmail_org undo-log add  --log logs/undo-log.jsonl --entry entry.json
  python -m gmail_org undo-log show --log logs/undo-log.jsonl [--last 5]
  python -m gmail_org undo-log reverse --log logs/undo-log.jsonl --pass 7

entry.json:
  {"kind": "label" | "trash" | "archive" | "unsubscribe" | "filters",
   "summary": "Labelled 212 inbox threads",
   "changes": [{"op": "add_label", "label": "Jobs/Alerts", "thread_ids": ["..."]},
               {"op": "trash", "thread_ids": ["..."]},
               {"op": "remove_label", "label": "INBOX", "thread_ids": ["..."]}],
   "judgement_calls": ["shohoz.com had no precedent; filed under Travel (bus tickets)"],
   "left_bare": ["3 OTP emails from bKash"]}
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os

REVERSE = {"add_label": "remove_label", "remove_label": "add_label", "trash": "untrash", "untrash": "trash"}


def read(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def add(path: str, entry: dict) -> dict:
    entries = read(path)
    entry = {"pass": (entries[-1]["pass"] + 1) if entries else 1,
             "at": dt.datetime.now().isoformat(timespec="seconds"), **entry}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def render(e: dict) -> str:
    lines = [f"## Pass {e['pass']} — {e['at']} — {e.get('kind', '?')}", e.get("summary", "")]
    for c in e.get("changes", []):
        lines.append(f"- {c['op']}{' ' + c['label'] if c.get('label') else ''}: {len(c.get('thread_ids', []))} thread(s)")
    if e.get("judgement_calls"):
        lines.append("Judgement calls:")
        lines += [f"  - {j}" for j in e["judgement_calls"]]
    if e.get("left_bare"):
        lines.append("Left bare: " + "; ".join(e["left_bare"]))
    return "\n".join(lines)


def reverse_plan(e: dict) -> list[dict]:
    plan = []
    for c in reversed(e.get("changes", [])):
        op = REVERSE.get(c["op"])
        if op:
            plan.append({"op": op, "label": c.get("label"), "thread_ids": c.get("thread_ids", [])})
    return plan


def main(argv=None):
    ap = argparse.ArgumentParser(description="Undo log for mailbox passes")
    ap.add_argument("cmd", choices=["add", "show", "reverse"])
    ap.add_argument("--log", required=True)
    ap.add_argument("--entry")
    ap.add_argument("--last", type=int, default=5)
    ap.add_argument("--pass", dest="pass_no", type=int)
    a = ap.parse_args(argv)
    if a.cmd == "add":
        e = add(a.log, json.load(open(a.entry, encoding="utf-8")))
        print(render(e))
    elif a.cmd == "show":
        for e in read(a.log)[-a.last:]:
            print(render(e) + "\n")
    else:
        match = [e for e in read(a.log) if e["pass"] == a.pass_no]
        if not match:
            raise SystemExit(f"no pass {a.pass_no} in {a.log}")
        print(json.dumps(reverse_plan(match[0]), indent=2))


if __name__ == "__main__":
    main()
