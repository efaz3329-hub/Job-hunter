"""Deterministic job fit score (0-97), adapted from Servation/job-search-mcp's computeMatchScore.

Claude reads each job and fills in the facts; this script does the arithmetic so scores stay consistent.
Usage: python score.py jobs.json   (a list of job objects; prints the scored list as JSON)

Job fields (all optional except title/company):
  title, company, url, source, location
  core: list of core requirements found in the posting
  matched: requirements Efaz meets (subset of core)
  required_years: years of experience asked for (number)
  marketing_years_required: true if those years must be in marketing specifically
  bba_required: true if BBA/MBA is stated as mandatory (not "preferred")
  cgpa_cutoff: minimum CGPA stated (number) or null
  field_sales: true if the job carries field/territory sales targets
  salary_max: advertised monthly maximum in BDT, or null
  outside_dhaka: true if based outside Dhaka
  big_opportunity: true if a top employer / real step up (allows outside Dhaka or 20-25k pay)
  bkash_internal: true for a bKash internal opening
"""
import json, sys

YOE_TOTAL = 2.0       # customer-facing years
YOE_MARKETING = 0.5   # marketing-specific years
PENALTY_PER_YEAR = 7
MAX_EXP_PENALTY = 21
CAP_BBA = 50
CAP_CGPA = 35
CEIL = 97
MIN_SALARY = 20000
GOOD_SALARY = 25000
CAP_LOW_PAY = 55


def score_job(j):
    if j.get("field_sales"):
        return 0, "Skip: field sales targets.", "skip"
    if j.get("salary_max") and j["salary_max"] < MIN_SALARY:
        return 0, f"Skip: salary max BDT {j['salary_max']:,} is below 20,000.", "skip"
    if j.get("outside_dhaka") and not j.get("big_opportunity"):
        return 0, "Skip: outside Dhaka and not a big opportunity.", "skip"

    core = j.get("core") or []
    matched = j.get("matched") or []
    total = max(len(core), len(matched), 1)
    score = round(100 * len(matched) / total)
    notes = [f"Met {len(matched)}/{total} core requirements"]
    missing = [c for c in core if c not in matched]
    if missing:
        notes[0] += f" (missing: {', '.join(missing[:3])})"

    yoe = YOE_MARKETING if j.get("marketing_years_required") else YOE_TOTAL
    gap = max(0.0, float(j.get("required_years") or 0) - yoe)
    pen = min(round(gap * PENALTY_PER_YEAR), MAX_EXP_PENALTY)
    if pen:
        score -= pen
        notes.append(f"needs {j['required_years']}y, has {yoe:g}y (-{pen})")

    if j.get("bba_required"):
        score = min(score, CAP_BBA)
        notes.append("BBA/MBA required (capped at 50)")
    if j.get("cgpa_cutoff") and j["cgpa_cutoff"] > 2.89:
        score = min(score, CAP_CGPA)
        notes.append(f"CGPA cutoff {j['cgpa_cutoff']} vs your 2.89 (capped at 35)")
    if j.get("salary_max") and j["salary_max"] < GOOD_SALARY and not j.get("big_opportunity"):
        score = min(score, CAP_LOW_PAY)
        notes.append(f"pays at most BDT {j['salary_max']:,}, worth it only for a good opportunity (capped at 55)")
    if j.get("bkash_internal"):
        score += 10
        notes.append("bKash internal move (+10)")
    if j.get("outside_dhaka"):
        notes.append("outside Dhaka, flagged as big opportunity")

    score = max(0, min(CEIL, score))
    priority = "high" if score >= 70 else "medium" if score >= 50 else "low"
    return score, "; ".join(notes) + ".", priority


def main(path):
    jobs = json.load(open(path, encoding="utf-8"))
    for j in jobs:
        j["score"], j["reason"], j["priority"] = score_job(j)
    jobs.sort(key=lambda j: j["score"], reverse=True)
    json.dump(jobs, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main(sys.argv[1])
