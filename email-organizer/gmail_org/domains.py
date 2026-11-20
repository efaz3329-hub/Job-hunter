"""Sender address parsing and registrable-domain grouping.

Group by registrable domain, not by address: one retailer sends from
news@edm.brand.com, offers@brand.com and hello@mail.brand.com. Deciding per
address leaves mail arriving, which reads as "you said you fixed this".
"""
from __future__ import annotations

import re
from email.utils import parseaddr

# Second-level suffixes under which the registrable domain is three labels deep.
# Not the full Public Suffix List, but it covers the regions this tool meets
# (Bangladesh first) and is easy to extend in rules.json -> "extra_two_part_tlds".
TWO_PART_TLDS = {
    # Bangladesh
    "com.bd", "net.bd", "org.bd", "edu.bd", "ac.bd", "gov.bd", "info.bd", "co.bd", "mil.bd",
    # South Asia / common
    "co.in", "net.in", "org.in", "ac.in", "gov.in", "com.pk", "com.np", "lk.com", "com.lk",
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "edu.au", "gov.au",
    "co.nz", "co.jp", "co.kr", "com.sg", "com.my", "com.hk", "com.tw", "com.cn", "com.br",
    "com.mx", "co.za", "com.tr", "com.sa", "ae.org", "co.id", "com.ph", "com.vn",
}

FREE_MAIL = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "msn.com",
    "yahoo.com", "ymail.com", "icloud.com", "me.com", "mac.com", "aol.com", "proton.me",
    "protonmail.com", "gmx.com", "zoho.com", "yandex.com", "mail.com", "qq.com", "163.com",
}

NOREPLY_RE = re.compile(r"(no[-_.]?reply|do[-_.]?not[-_.]?reply|notifications?|mailer|bounce|alerts?)@", re.I)


def parse_sender(from_header: str) -> tuple[str, str]:
    """Return (display_name, lowercase_address) from a From: header."""
    name, addr = parseaddr(from_header or "")
    return name.strip(), addr.strip().lower()


def registrable_domain(address_or_host: str, extra_two_part: set[str] | None = None) -> str:
    """news@edm.brand.com.bd -> brand.com.bd ; alerts@mail.linkedin.com -> linkedin.com"""
    host = address_or_host.rsplit("@", 1)[-1].strip().lower().rstrip(".")
    parts = [p for p in host.split(".") if p]
    if len(parts) <= 2:
        return ".".join(parts)
    suffixes = TWO_PART_TLDS | (extra_two_part or set())
    if ".".join(parts[-2:]) in suffixes:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_free_mail(address: str) -> bool:
    return registrable_domain(address) in FREE_MAIL


def is_noreply(address: str) -> bool:
    return bool(NOREPLY_RE.search(address or ""))
