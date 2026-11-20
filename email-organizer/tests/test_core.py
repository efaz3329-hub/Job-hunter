import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail_org import filters_xml, inventory, jobs, review_page, undo_log, unsubscribe  # noqa: E402
from gmail_org.classify import Classifier, triage_report  # noqa: E402
from gmail_org.config import load_rules, merge_rules  # noqa: E402
from gmail_org.domains import registrable_domain  # noqa: E402

RULES = merge_rules(load_rules(os.devnull + ".missing"), {
    "owner_addresses": ["me@gmail.com"], "work_domains": ["bkash.com"], "vip_senders": ["mom@gmail.com"],
})


def M(frm, subject, snippet="", **kw):
    return {"id": subject[:8], "from": frm, "subject": subject, "snippet": snippet, **kw}


class Domains(unittest.TestCase):
    def test_registrable(self):
        self.assertEqual(registrable_domain("news@edm.daraz.com.bd"), "daraz.com.bd")
        self.assertEqual(registrable_domain("jobalerts-noreply@linkedin.com"), "linkedin.com")
        self.assertEqual(registrable_domain("x@mail.shop.co.uk"), "shop.co.uk")
        self.assertEqual(registrable_domain("a@b.io"), "b.io")


class Classify(unittest.TestCase):
    c = Classifier(RULES)

    def k(self, *a, **kw):
        return self.c.classify(M(*a, **kw))

    def test_security_left_bare_even_from_bulk(self):
        r = self.k("no-reply@accounts.google.com", "Your verification code is 123456", list_unsubscribe=True)
        self.assertEqual((r.category, r.action, r.protected), ("security", "keep-bare", True))
        self.assertEqual(self.k("no-reply@bank.com", "Unusual activity: was this you?").tier, 1)

    def test_job_alert_and_replies(self):
        r = self.k("LinkedIn <jobalerts-noreply@linkedin.com>", "CRM Executive at Daraz and 9 more")
        self.assertEqual((r.job_event, r.label), ("alert", "Jobs/Alerts"))
        r = self.k("HR <hr@grameenphone.com>", "Interview invitation - Customer Engagement Executive")
        self.assertEqual((r.job_event, r.tier, r.label), ("interview", 1, "Jobs/Interviews"))
        r = self.k("careers@robi.com.bd", "Your application", "Unfortunately we will not be proceeding")
        self.assertEqual(r.job_event, "rejection")

    def test_marketing_interview_word_is_not_job(self):
        r = self.k("news@coursera.org", "Ace your next interview with this course", list_unsubscribe=True)
        self.assertNotEqual(r.category, "job")

    def test_records_protected_and_urgent(self):
        r = self.k("billing@desco.org.bd", "Electricity bill - payment due tomorrow")
        self.assertEqual((r.category, r.tier, r.protected), ("bills", 1, True))
        r = self.k("orders@daraz.com.bd", "Your order has shipped", list_unsubscribe=True)
        self.assertEqual((r.category, r.label, r.protected), ("receipts", "Receipts & Orders", True))

    def test_people(self):
        self.assertEqual(self.k("Mom <mom@gmail.com>", "dinner").tier, 1)
        self.assertEqual(self.k("Friend <rafi@gmail.com>", "hey").category, "personal")
        self.assertEqual(self.k("boss@bkash.com", "Q4 numbers").category, "work")

    def test_noise(self):
        r = self.k("deals@shop.com", "Flash sale: 50% off everything", list_unsubscribe=True)
        self.assertEqual((r.tier, r.category, r.action), (3, "deals", "unsubscribe-candidate"))
        r = self.k("noreply@facebookmail.com", "Rafi tagged you in a photo")
        self.assertEqual((r.category, r.label), ("social", "Social"))
        r = self.k("deals@shop.com", "Flash sale", list_unsubscribe=True, labels=["STARRED"])
        self.assertEqual(r.action, "label")

    def test_salary_is_not_sale(self):
        r = self.k("hr@acme.com", "Salary disbursed for November")
        self.assertEqual(r.category, "finance")

    def test_unknown_goes_to_review(self):
        r = self.k("someone@company.com", "Quick question about the doc")
        self.assertEqual((r.tier, r.action), (2, "keep"))

    def test_report(self):
        rs = [self.k("deals@shop.com", "Sale", list_unsubscribe=True), self.k("mom@gmail.com", "hi")]
        rep = triage_report(rs)
        self.assertIn("Reply or act (1)", rep)
        self.assertIn("Noise (1)", rep)


class Inventory(unittest.TestCase):
    def test_merge_suggestions(self):
        slices = [{
            "promo@mail.shop.com": {"count": 40, "latest": "2026-11-01", "unsub": True, "subjects": ["50% off"]},
            "deals@shop.com": {"count": 5, "latest": "2026-10-01", "unsub": True, "subjects": ["Sale"]},
            "news@grameenphone.com": {"count": 30, "latest": "2026-11-10", "unsub": True,
                                      "subjects": ["New offer", "Your bill for October"]},
            "old@dead.com": {"count": 12, "latest": "2023-01-01", "subjects": ["hello"]},
            "rafi@gmail.com": {"count": 50, "latest": "2026-11-10"},
            "x@tiny.com": {"count": 2, "latest": "2026-11-10", "unsub": True},
        }]
        data = {d["domain"]: d for d in inventory.merge(slices, RULES, dt.date(2026, 11, 20))}
        self.assertEqual(data["shop.com"]["count"], 45)
        self.assertEqual(data["shop.com"]["suggested"], "delete")
        self.assertEqual(data["grameenphone.com"]["suggested"], "skip")
        self.assertTrue(data["grameenphone.com"]["mixed"])
        self.assertEqual(data["dead.com"]["suggested"], "delete")
        self.assertFalse(data["dead.com"]["active"])
        self.assertEqual(data["gmail.com"]["suggested"], "skip")
        self.assertEqual(data["tiny.com"]["suggested"], "skip")


class Filters(unittest.TestCase):
    def test_xml(self):
        dec = {"promo": [{"domain": "shop.com", "label": None}], "keep": [{"domain": "news.com", "label": "Subscriptions/News"}],
               "delete": [{"domain": "spam.com"}], "skip": []}
        perm, temp = filters_xml.build_filters(RULES, dec, tos_trash=True)
        self.assertTrue(any(p.get("label") == "Jobs/Alerts" and "shouldArchive" not in p for p in perm))
        self.assertTrue(any(p.get("from") == "shop.com" and p.get("shouldArchive") == "true" for p in perm))
        tos = [p for p in perm if "subject" in p][0]
        self.assertIn("verification", tos["doesNotHaveTheWord"])
        self.assertEqual(temp[0]["from"], "spam.com")
        xml = filters_xml.to_xml(perm + temp)
        self.assertIn("apps:property name='label' value=\"Jobs/Alerts\"", xml)
        self.assertTrue(xml.startswith("<?xml"))
        import xml.dom.minidom
        xml.dom.minidom.parseString(filters_xml.to_xml(perm + temp))


class Review(unittest.TestCase):
    def test_page_and_parse(self):
        page = review_page.build([{"domain": "a.com</script>", "count": 1, "addresses": [], "suggested": "skip",
                                   "why": "", "active": True, "latest": None}], ["X"])
        self.assertNotIn("a.com</script>", page)
        dec = review_page.parse_decisions("DECISIONS v1\nDELETE (1):\nspam.com\n\nPROMO (1):\nshop.com -> Subscriptions/Deals\n")
        self.assertEqual(dec["delete"], [{"domain": "spam.com", "label": None}])
        self.assertEqual(dec["promo"][0]["label"], "Subscriptions/Deals")


class Unsub(unittest.TestCase):
    def test_plan_dry_run(self):
        e = [{"domain": "a.com", "list_unsubscribe": "<mailto:u@a.com>, <https://a.com/u>",
              "list_unsubscribe_post": "List-Unsubscribe=One-Click"},
             {"domain": "b.com", "list_unsubscribe": "<mailto:u@b.com>"},
             {"domain": "c.com"}]
        res = unsubscribe.run(e, execute=False, allow_get=False)
        self.assertEqual([r["status"] for r in res], ["planned-oneclick", "manual-mailto", "no-link"])


class Undo(unittest.TestCase):
    def test_log_and_reverse(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "u.jsonl")
            undo_log.add(p, {"kind": "label", "changes": [{"op": "add_label", "label": "Social", "thread_ids": ["t1"]},
                                                          {"op": "trash", "thread_ids": ["t2"]}]})
            e = undo_log.add(p, {"kind": "trash", "changes": []})
            self.assertEqual(e["pass"], 2)
            plan = undo_log.reverse_plan(undo_log.read(p)[0])
            self.assertEqual([x["op"] for x in plan], ["untrash", "remove_label"])


class Jobs(unittest.TestCase):
    def test_sort(self):
        msgs = [M("jobalerts-noreply@linkedin.com", "CRM Executive at Daraz"),
                M("HR <talent@shajgoj.com>", "Interview schedule for Shajgoj"),
                M("hr@unknownco.com", "Thank you for applying")]
        res = jobs.sort_job_mail(msgs, ["Shajgoj", "Daraz"], RULES)
        self.assertEqual(len(res["alerts"]), 1)
        self.assertEqual(res["status_updates"][0]["company"], "Shajgoj")
        self.assertEqual(res["status_updates"][0]["suggested_status"], "interview")
        self.assertEqual(res["unmatched"][0]["suggested_status"], "applied")


if __name__ == "__main__":
    unittest.main()
