"""Unsubscribe via List-Unsubscribe headers (RFC 2369 / RFC 8058).

Dry run by default: prints the plan and writes nothing outbound. With
--execute it sends RFC 8058 one-click POSTs, and with --allow-get also
follows plain https unsubscribe links. mailto: unsubscribes are never sent;
they are listed for the owner, because sending email needs their approval.

Never clicks row-by-row on Gmail's subscriptions page (rows shift after each
click, and one user lost seven subscriptions they had marked keep).

Input (senders.json), one entry per sender, from the newest message:
  [{"domain": "brand.com", "address": "news@brand.com",
    "list_unsubscribe": "<https://brand.com/u?x=1>, <mailto:u@brand.com>",
    "list_unsubscribe_post": "List-Unsubscribe=One-Click"}]

Output: appends one line per sender to the ledger (JSONL), status one of
  ok-oneclick | ok-get | manual-mailto | manual | no-link | failed | planned-*

Usage:
  python -m gmail_org unsubscribe senders.json --ledger unsub-ledger.jsonl [--execute] [--allow-get]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; mailbox-organizer/1.0)"


def parse_header(value: str | None) -> tuple[list[str], list[str]]:
    """Return (https_urls, mailto_urls) from a List-Unsubscribe header."""
    urls = re.findall(r"<([^>]+)>", value or "")
    if not urls and value:
        urls = [u.strip() for u in value.split(",")]
    https = [u for u in urls if u.lower().startswith("https://")]
    mailto = [u for u in urls if u.lower().startswith("mailto:")]
    return https, mailto


def plan(entry: dict) -> tuple[str, str | None]:
    https, mailto = parse_header(entry.get("list_unsubscribe"))
    one_click = "one-click" in str(entry.get("list_unsubscribe_post") or "").lower()
    if https and one_click:
        return "oneclick", https[0]
    if https:
        return "get", https[0]
    if entry.get("body_url", "").lower().startswith("https://"):
        return "get", entry["body_url"]
    if mailto:
        return "mailto", mailto[0]
    return "none", None


def _request(url: str, method: str) -> int:
    data = b"List-Unsubscribe=One-Click" if method == "POST" else None
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": UA})
    if data:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read(2048)  # never keep or print page bodies
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def run(entries: list[dict], execute: bool, allow_get: bool) -> list[dict]:
    out = []
    for e in entries:
        kind, url = plan(e)
        rec = {"domain": e.get("domain"), "address": e.get("address"), "method": kind, "url": url,
               "at": dt.datetime.now().isoformat(timespec="seconds")}
        if kind == "none":
            rec["status"] = "no-link"
        elif kind == "mailto":
            rec["status"] = "manual-mailto"
        elif not execute:
            rec["status"] = f"planned-{kind}"
        elif kind == "oneclick":
            code = _request(url, "POST")
            if 200 <= code < 300:
                rec["status"] = "ok-oneclick"
            elif allow_get:
                code = _request(url, "GET")
                rec["status"] = "ok-get" if 200 <= code < 400 else "manual"
            else:
                rec["status"] = "manual"
            rec["http"] = code
        else:  # get
            if allow_get:
                code = _request(url, "GET")
                rec["status"] = "ok-get" if 200 <= code < 400 else "manual"
                rec["http"] = code
            else:
                rec["status"] = "manual"
        out.append(rec)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Unsubscribe via List-Unsubscribe (dry run unless --execute)")
    ap.add_argument("senders")
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--allow-get", action="store_true")
    a = ap.parse_args(argv)
    entries = json.load(open(a.senders, encoding="utf-8"))
    results = run(entries, a.execute, a.allow_get)
    with open(a.ledger, "a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tally: dict[str, int] = {}
    for r in results:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    print(("EXECUTED: " if a.execute else "DRY RUN: ") + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    manual = [r for r in results if r["status"].startswith("manual")]
    if manual:
        print("Needs your hand:")
        for r in manual:
            print(f"  {r['domain']}: {r['url']}")


if __name__ == "__main__":
    main()
