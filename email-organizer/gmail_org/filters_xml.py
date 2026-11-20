"""Generate a Gmail filter import file (mailFilters.xml).

The built-in Gmail connector can label and trash but has no filter API, and
filters are what stop the pile from growing back. Gmail can import filters
from XML: Settings > Filters and Blocked Addresses > Import filters > choose
file > tick "Apply new filters to existing email" > Create filters.

Filters come from two places:
  * rules (job alert senders, sender_labels map)
  * decisions from the review page (promo / keep / delete)

Design choices (each from a real mistake in the source repos):
  * Labelled mail stays in the inbox unless the owner chose "promo"
    (skip-inbox filters made job alerts silently disappear for one user).
  * "delete" decisions become TEMPORARY trash filters, listed separately, to
    cover the days before an unsubscribe takes effect. Retire them later.
  * A filter can carry only one user label, so one filter per label.
  * Security mail is never filtered.
  * The optional terms-of-service trash rule always carries its negation,
    or "Verify your email - updated Terms" goes to Trash.

Usage:
  python -m gmail_org filters --out mailFilters.xml [--decisions decisions.json]
                              [--jobs-skip-inbox] [--tos-trash]
"""
from __future__ import annotations

import argparse
import json
from xml.sax.saxutils import quoteattr

from .config import load_rules

CHUNK = 20  # senders per filter; Gmail rejects very long criteria


def _entry(props: dict[str, str]) -> str:
    lines = ["  <entry>", "    <category term='filter'></category>", "    <title>Mail Filter</title>",
             "    <content></content>"]
    for k, v in props.items():
        lines.append(f"    <apps:property name='{k}' value={quoteattr(v)}/>")
    lines.append("  </entry>")
    return "\n".join(lines)


def _chunks(items: list[str]) -> list[list[str]]:
    items = sorted(set(i for i in items if i))
    return [items[i:i + CHUNK] for i in range(0, len(items), CHUNK)]


def build_filters(rules: dict, decisions: dict | None = None, jobs_skip_inbox: bool = False,
                  tos_trash: bool = False) -> tuple[list[dict], list[dict]]:
    """Return (permanent_filters, temporary_filters) as property dicts."""
    L = rules["labels"]
    perm: list[dict] = []
    temp: list[dict] = []

    for group in _chunks(rules.get("job_alert_senders", [])):
        p = {"from": " OR ".join(group), "label": L["jobs_alerts"], "shouldNeverSpam": "true"}
        if jobs_skip_inbox:
            p["shouldArchive"] = "true"
        perm.append(p)

    by_label: dict[str, list[str]] = {}
    skip_inbox: set[str] = set()
    for dom, label in rules.get("sender_labels", {}).items():
        by_label.setdefault(label, []).append(dom)

    if decisions:
        for state in ("promo", "keep"):
            for d in decisions.get(state, []):
                label = d.get("label") or (L["deals"] if state == "promo" else None)
                if not label:
                    continue
                by_label.setdefault(label, []).append(d["domain"])
                if state == "promo":
                    skip_inbox.add(d["domain"])
        for group in _chunks([d["domain"] for d in decisions.get("delete", [])]):
            temp.append({"from": " OR ".join(group), "doesNotHaveTheWord":
                         "invoice OR receipt OR statement OR bill OR payslip OR otp OR verification",
                         "shouldTrash": "true"})

    for label, doms in sorted(by_label.items()):
        inbox_doms = [d for d in doms if d not in skip_inbox]
        archive_doms = [d for d in doms if d in skip_inbox]
        for group in _chunks(inbox_doms):
            perm.append({"from": " OR ".join(group), "label": label})
        for group in _chunks(archive_doms):
            perm.append({"from": " OR ".join(group), "label": label, "shouldArchive": "true"})

    if tos_trash:
        perm.append({
            "subject": '"terms of service" OR "terms and conditions" OR "terms of use" OR "privacy policy" OR "user agreement"',
            "doesNotHaveTheWord": 'code OR verification OR verify OR "security alert" OR password OR otp',
            "shouldTrash": "true"})
    return perm, temp


def to_xml(filters: list[dict]) -> str:
    head = ("<?xml version='1.0' encoding='UTF-8'?>\n"
            "<feed xmlns='http://www.w3.org/2005/Atom' xmlns:apps='http://schemas.google.com/apps/2006'>\n"
            "  <title>Mail Filters</title>")
    return head + "\n" + "\n".join(_entry(f) for f in filters) + "\n</feed>\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write Gmail filter import XML")
    ap.add_argument("--out", required=True)
    ap.add_argument("--decisions", help="decisions.json from the review step")
    ap.add_argument("--rules")
    ap.add_argument("--jobs-skip-inbox", action="store_true", help="archive job alerts (default: keep in inbox)")
    ap.add_argument("--tos-trash", action="store_true", help="trash terms/privacy-policy notices (with negation)")
    ap.add_argument("--no-temp", action="store_true", help="leave out temporary trash filters")
    a = ap.parse_args(argv)
    decisions = json.load(open(a.decisions, encoding="utf-8")) if a.decisions else None
    perm, temp = build_filters(load_rules(a.rules), decisions, a.jobs_skip_inbox, a.tos_trash)
    filters = perm + ([] if a.no_temp else temp)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(to_xml(filters))
    print(f"wrote {a.out}: {len(perm)} permanent filter(s), {0 if a.no_temp else len(temp)} temporary trash filter(s)")
    if temp and not a.no_temp:
        print("Temporary trash filters (retire once the sender has stopped, usually 1-2 weeks):")
        for t in temp:
            print("  from:", t["from"])


if __name__ == "__main__":
    main()
