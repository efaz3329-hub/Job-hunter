"""Merge per-slice sender inventories into one per-domain review list.

Each slice file (inventory-<slice>.json) is what a scan of one date range
wrote, keyed by sender address:
  {"news@mail.brand.com": {"count": 41, "latest": "2026-11-02", "unsub": true,
                           "subjects": ["50% off this weekend", "..."]}}

Output (review-data.json): one record per registrable domain, biggest first,
with a conservative suggested decision:
  delete  unsubscribe (if still active) and trash the backlog
  promo   keep subscribed, label, skip the inbox
  keep    keep subscribed, label, stay in the inbox
  skip    do not touch  (protected, personal, low-volume, job mail)

Usage:
  python -m gmail_org inventory --dir scans/ --out review-data.json [--today 2026-11-20]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os

from .classify import Classifier
from .config import load_rules
from .domains import is_free_mail, registrable_domain


def _date(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def merge(slices: list[dict], rules: dict, today: dt.date) -> list[dict]:
    clf = Classifier(rules)
    owner = {a.lower() for a in rules.get("owner_addresses", [])}
    extra = set(rules.get("extra_two_part_tlds", []))
    active_days = int(rules["cleanup"]["active_months"]) * 30
    min_delete = int(rules["cleanup"]["min_messages_for_delete_default"])

    by_addr: dict[str, dict] = {}
    for sl in slices:
        for addr, rec in sl.items():
            addr = addr.lower()
            cur = by_addr.setdefault(addr, {"count": 0, "latest": None, "unsub": False, "subjects": []})
            cur["count"] += int(rec.get("count", 0))
            d = _date(rec.get("latest"))
            if d and (cur["latest"] is None or d > cur["latest"]):
                cur["latest"] = d
            cur["unsub"] = cur["unsub"] or bool(rec.get("unsub"))
            for s in rec.get("subjects", [])[:5]:
                if len(cur["subjects"]) < 8 and s not in cur["subjects"]:
                    cur["subjects"].append(s)

    domains: dict[str, dict] = {}
    for addr, rec in by_addr.items():
        if addr in owner:
            continue
        dom = registrable_domain(addr, extra)
        d = domains.setdefault(dom, {"domain": dom, "addresses": [], "count": 0, "latest": None,
                                     "unsub": False, "subjects": [], "protected_hits": []})
        d["addresses"].append({"address": addr, "count": rec["count"], "unsub": rec["unsub"]})
        d["count"] += rec["count"]
        if rec["latest"] and (d["latest"] is None or rec["latest"] > d["latest"]):
            d["latest"] = rec["latest"]
        d["unsub"] = d["unsub"] or rec["unsub"]
        d["subjects"] = (d["subjects"] + rec["subjects"])[:8]
        for s in rec["subjects"]:
            r = clf.classify({"from": addr, "subject": s, "list_unsubscribe": rec["unsub"]})
            if r.protected:
                d["protected_hits"].append(f"{r.category}: {s}")

    out = []
    for d in domains.values():
        d["active"] = bool(d["latest"] and (today - d["latest"]).days <= active_days)
        d["addresses"].sort(key=lambda a: -a["count"])
        decision, why = "promo", "bulk sender, labelled"
        if is_free_mail(d["domain"]):
            decision, why = "skip", "personal free-mail domain: never bulk-delete"
        elif d["protected_hits"]:
            decision, why = "skip", "sends records too (" + d["protected_hits"][0] + "); unsubscribe marketing only"
        elif any(clf.classify({"from": a["address"], "subject": ""}).category in ("job", "work", "never-touch", "personal")
                 for a in d["addresses"]):
            decision, why = "skip", "job, work, VIP or never-touch sender"
        elif d["count"] < min_delete:
            decision, why = "skip", f"fewer than {min_delete} messages"
        elif d["unsub"] or not d["active"]:
            decision, why = "delete", "bulk with unsubscribe link" if d["active"] else "dormant sender: trash backlog only"
        d["suggested"] = decision
        d["why"] = why
        d["mixed"] = bool(d["protected_hits"]) and d["unsub"]
        d["latest"] = d["latest"].isoformat() if d["latest"] else None
        out.append(d)
    out.sort(key=lambda d: -d["count"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge sender inventories into review-data.json")
    ap.add_argument("--dir", required=True, help="folder holding inventory-*.json slices")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rules")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today)")
    a = ap.parse_args(argv)
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    slices = [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(a.dir, "inventory-*.json")))]
    if not slices:
        raise SystemExit(f"no inventory-*.json files in {a.dir}")
    data = merge(slices, load_rules(a.rules), today)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    total = sum(d["count"] for d in data)
    sug = {}
    for d in data:
        sug[d["suggested"]] = sug.get(d["suggested"], 0) + 1
    active = sum(1 for d in data if d["active"])
    print(f"{len(data)} domains, {total} messages, {active} active / {len(data) - active} dormant. "
          f"Suggested: " + ", ".join(f"{k} {v}" for k, v in sorted(sug.items())))


if __name__ == "__main__":
    main()
