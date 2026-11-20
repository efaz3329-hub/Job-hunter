"""Rule engine: one message's metadata -> category, triage tier, label, safe action.

Claude does the judgement on ambiguous mail; this script makes the common
cases consistent from run to run (the same idea as Job-hunter's score.py).

Input: a JSON list of messages built from Gmail search results, metadata only:
  {"id", "thread_id", "from", "to", "subject", "snippet", "date",
   "labels": ["INBOX", "CATEGORY_PROMOTIONS", "STARRED", ...],
   "list_unsubscribe": true | "<url>" | null,
   "replied": true if the owner has replied in the thread}

Usage:
  python -m gmail_org.classify messages.json            # classified JSON
  python -m gmail_org.classify messages.json --report   # triage markdown

Order of rules matters and is deliberate: safety first (security mail,
never-touch, starred), then people who matter, then jobs, then records worth
keeping, and only then noise. Anything unmatched lands in Tier 2 "review",
never in a delete pile.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field

from .config import load_rules
from .domains import is_free_mail, is_noreply, parse_sender, registrable_domain

ACTIONS = ("keep-bare", "keep", "label", "archive-candidate", "unsubscribe-candidate")


@dataclass
class Result:
    id: str
    thread_id: str
    sender: str
    domain: str
    subject: str
    category: str
    tier: int
    action: str
    label: str | None = None
    protected: bool = False
    job_event: str | None = None
    reason: str = ""
    flags: list[str] = field(default_factory=list)


def _rx(patterns: list[str]) -> re.Pattern | None:
    """Case-insensitive alternation; word boundaries where the pattern edge is a word char."""
    parts = []
    for p in patterns:
        esc = re.escape(p.lower())
        if p[:1].isalnum():
            esc = r"\b" + esc
        if p[-1:].isalnum():
            esc = esc + r"\b"
        parts.append(esc)
    return re.compile("|".join(parts), re.I) if parts else None


def _hit(rx: re.Pattern | None, text: str) -> str | None:
    if not rx:
        return None
    m = rx.search(text)
    return m.group(0) if m else None


def _sender_matches(address: str, domain: str, entries: list[str]) -> str | None:
    for e in entries:
        e = e.lower().strip()
        if not e:
            continue
        if "@" in e:
            if address == e:
                return e
        elif address.endswith("@" + e) or address.endswith("." + e) or domain == e:
            return e
    return None


class Classifier:
    def __init__(self, rules: dict | None = None):
        r = rules or load_rules()
        self.r = r
        self.L = r["labels"]
        self.extra_tlds = set(r.get("extra_two_part_tlds", []))
        self.rx_security = _rx(r["security_patterns"])
        self.rx_security_urgent = _rx(r["security_urgent_patterns"])
        self.rx_urgent = _rx(r["urgent_patterns"])
        self.rx_job = {k: _rx(v) for k, v in r["job_reply_patterns"].items()}
        self.rx_protected = {k: _rx(v) for k, v in r["protected_patterns"].items()}
        self.rx_noise = {k: _rx(v) for k, v in r["noise_patterns"].items()}
        self.owner = {a.lower() for a in r.get("owner_addresses", [])}

    def classify(self, m: dict) -> Result:
        name, addr = parse_sender(m.get("from", ""))
        domain = registrable_domain(addr, self.extra_tlds) if addr else ""
        subject = m.get("subject") or ""
        text = f"{subject}\n{m.get('snippet') or ''}"
        labels = set(m.get("labels") or [])
        bulk = bool(m.get("list_unsubscribe")) or is_noreply(addr) or bool(
            labels & {"CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_FORUMS"})

        def res(category, tier, action, label=None, protected=False, reason="", job_event=None, flags=None):
            return Result(m.get("id", ""), m.get("thread_id", m.get("id", "")), addr, domain, subject,
                          category, tier, action, label, protected, job_event, reason, flags or [])

        flags = []
        if "STARRED" in labels:
            flags.append("starred")

        # 1. Security mail: never labelled, never trashed. Codes must be findable under pressure.
        urgent = _hit(self.rx_security_urgent, text)
        hit = _hit(self.rx_security, text) or urgent
        if hit:
            return res("security", 1 if urgent else 2, "keep-bare", protected=True,
                       reason=f"security mail ('{urgent or hit}'), left bare", flags=flags)

        # 2. Owner's never-touch list.
        nt = _sender_matches(addr, domain, self.r.get("never_touch", []))
        if nt:
            return res("never-touch", 2, "keep", protected=True, reason=f"on never-touch list ({nt})", flags=flags)

        # 3. People who matter.
        vip = _sender_matches(addr, domain, self.r.get("vip_senders", []))
        if vip:
            return res("personal", 1, "keep", protected=True, reason=f"VIP sender ({vip})", flags=flags)
        work = _sender_matches(addr, domain, self.r.get("work_domains", []))
        if work and not bulk:
            return res("work", 1, "keep", protected=True, reason=f"work domain ({work})", flags=flags)

        # 4. Jobs: employer replies first (Tier 1), then alerts.
        job_alert = _sender_matches(addr, domain, self.r.get("job_alert_senders", []))
        if not job_alert:
            for event, label_key, tier in (("interview", "jobs_interviews", 1),
                                           ("rejection", "jobs_rejections", 2),
                                           ("application", "jobs_applications", 2)):
                h = _hit(self.rx_job[event], text)
                if h and (event != "interview" or not bulk or "offer" in h.lower()):
                    return res("job", tier, "label", self.L[label_key], protected=True, job_event=event,
                               reason=f"job {event} ('{h}')", flags=flags)
        else:
            return res("job", 2, "label", self.L["jobs_alerts"], job_event="alert",
                       reason=f"job alert sender ({job_alert}), hand to Job-hunter", flags=flags)

        # 5. Records worth keeping (bills, statements, receipts, bookings).
        for kind in ("bills", "finance", "receipts", "travel", "records"):
            h = _hit(self.rx_protected[kind], text)
            if h:
                urgent = _hit(self.rx_urgent, text) if kind in ("bills", "finance") and not bulk else None
                label = {"bills": self.L["bills"], "finance": self.L["finance"], "receipts": self.L["receipts"],
                         "travel": self.L["travel"]}.get(kind)
                return res(kind, 1 if urgent else 2, "label" if label else "keep", label, protected=True,
                           reason=f"{kind} record ('{h}')" + (f", urgent ('{urgent}')" if urgent else ""), flags=flags)

        # 6. Personal mail from a real person.
        if addr and is_free_mail(addr) and not bulk:
            return res("personal", 1, "keep", protected=True, reason="personal address (free-mail, not bulk)", flags=flags)
        if m.get("replied"):
            return res("conversation", 1, "keep", protected=True, reason="thread you replied in", flags=flags)

        # 7. Noise: bulk mail. Label by sender map or content, then offer archive/unsubscribe.
        known_noise = _sender_matches(addr, domain, self.r.get("noise_senders", []))
        if bulk or known_noise:
            label = self.r.get("sender_labels", {}).get(domain)
            kind = None
            for k in ("social", "deals", "news", "learning"):
                h = _hit(self.rx_noise[k], text)
                if h:
                    kind = k
                    break
            if not kind:
                kind = "social" if "CATEGORY_SOCIAL" in labels else "deals" if "CATEGORY_PROMOTIONS" in labels else "news"
            label = label or self.L[kind]
            action = "unsubscribe-candidate" if m.get("list_unsubscribe") else "archive-candidate"
            if "starred" in flags:
                action = "label"
            why = "list-unsubscribe header" if m.get("list_unsubscribe") else "no-reply sender" if is_noreply(addr) \
                else "Gmail category" if not known_noise else f"known noise sender ({known_noise})"
            return res(kind, 3, action, label, reason=f"bulk mail ({why})", flags=flags)

        # 8. Direct, non-bulk mail with a deadline.
        h = _hit(self.rx_urgent, text)
        if h:
            return res("action", 1, "keep", reason=f"time-sensitive ('{h}')", flags=flags)

        # 9. Unknown: a human looks at it.
        return res("review", 2, "keep", reason="no rule matched; review", flags=flags)


def triage_report(results: list[Result], title: str = "Inbox triage") -> str:
    t1 = [r for r in results if r.tier == 1]
    t2 = [r for r in results if r.tier == 2]
    t3 = [r for r in results if r.tier == 3]
    out = [f"# {title}", f"{len(results)} emails scanned.", "", f"## Reply or act ({len(t1)})", ""]
    for i, r in enumerate(t1, 1):
        out.append(f"{i}. **{r.sender}** — {r.subject}  \n   _{r.category}: {r.reason}_")
    out += ["", f"## Review ({len(t2)})", ""]
    for r in t2:
        tag = f" `{r.label}`" if r.label else ""
        out.append(f"- **{r.sender}** — {r.subject}{tag}")
    counts: dict[str, int] = {}
    for r in t3:
        counts[r.category] = counts.get(r.category, 0) + 1
    unsub = sorted({r.domain for r in t3 if r.action == "unsubscribe-candidate"})
    out += ["", f"## Noise ({len(t3)})", ", ".join(f"{n} {k}" for k, n in sorted(counts.items())) or "none"]
    if unsub:
        out.append(f"Unsubscribe candidates: {', '.join(unsub[:15])}" + (" …" if len(unsub) > 15 else ""))
    jobs = [r for r in results if r.category == "job"]
    if jobs:
        ev: dict[str, int] = {}
        for r in jobs:
            ev[r.job_event or "?"] = ev.get(r.job_event or "?", 0) + 1
        out += ["", "## Job mail", ", ".join(f"{n} {k}" for k, n in sorted(ev.items())) + " (handed to Job-hunter)"]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("messages")
    ap.add_argument("--rules")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)
    c = Classifier(load_rules(a.rules))
    msgs = json.load(open(a.messages, encoding="utf-8"))
    results = [c.classify(m) for m in msgs]
    if a.report:
        sys.stdout.write(triage_report(results))
    else:
        json.dump([asdict(r) for r in results], sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
