"""MathJobs.org adapter — uses the official public_job_boards JSON feed.

Feed docs (from the feed's own hint field): params limit, page, sort_order,
sort_by, search, all_postings, date_from, date_to, unit_name, tenant_id,
position_id, xml, csv.
"""
import gzip
import json
import re
import urllib.request

FEED = "https://www.mathjobs.org/jobs/public_job_boards?limit=2000&page=1&all_postings=1"
UA = "JobBoardReader/1.0 (personal use; contact: bcatania13@gmail.com)"

TAG_RE = re.compile(r"<[^>]+>")

# MathJobs "type" field → our normalized position type
TYPE_MAP = {
    "Tenured/Tenure-track faculty": "tenure_track",
    "Tenured & Senior faculty": "tenure_track",
    "Open Rank": "tenure_track",
    "Postdoctoral": "postdoc",
    "Fellowship or award": "postdoc",
    "Teaching stream faculty": "lecturer",
    "Non tenure-track faculty": None,  # decide from title
    "Non-regular rank faculty": None,
    "Administration": "other",
    "Student programs": "other",
    "BEGIN": "other",
    "Other": None,
}


def _clean_date(s):
    if not s or s.startswith("0000"):
        return None
    return s


def _strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<(br|/p|/div|/li)[^>]*>", "\n", s, flags=re.I)
    s = TAG_RE.sub("", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#x27;", "'")
    s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def classify_type(mj_type, title):
    t = (title or "").lower()
    mapped = TYPE_MAP.get(mj_type or "", None)
    if mapped:
        return mapped
    # Fall back to title keywords
    if re.search(r"post[- ]?doc|research (fellow|associate)|fellowship", t):
        return "postdoc"
    if "visiting" in t:
        return "visiting"
    if re.search(r"tenure[- ]track|tenured", t):
        return "tenure_track"
    if re.search(r"lecturer|instructor|teaching (professor|faculty|assistant professor)", t):
        return "lecturer"
    if re.search(r"assistant professor|associate professor|full professor|professor of", t):
        # untyped professor listings are usually tenure-stream
        return "tenure_track"
    return "other"


def fetch():
    req = urllib.request.Request(FEED, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":  # server gzips regardless of Accept-Encoding
        raw = gzip.decompress(raw)
    data = json.loads(raw)
    jobs = []
    for rec in data.get("results", []):
        if rec.get("country") not in ("US", "CA"):
            continue
        title = _strip_html(rec.get("name") or "")
        jobs.append(
            {
                "id": f"mathjobs-{rec['id']}",
                "source": "mathjobs",
                "institution": rec.get("univ") or "",
                "department": rec.get("unit_name") or "",
                "title": title,
                "position_type": classify_type(rec.get("type"), title + " " + (rec.get("tag") or "")),
                "mathjobs_type": rec.get("type"),
                "city": rec.get("city") or "",
                "state": rec.get("state") or "",
                "country": rec.get("country"),
                "posted": _clean_date(rec.get("open_date_raw")),
                "deadline": _clean_date((rec.get("deadline_raw") or "")[:10]),
                "close_date": _clean_date(rec.get("close_date_raw")),
                "url": rec.get("url"),
                "apply_url": rec.get("apply") or rec.get("url"),
                "subject": _strip_html(rec.get("subject") or ""),
                "description": _strip_html(rec.get("description") or ""),
            }
        )
    return jobs


if __name__ == "__main__":
    js = fetch()
    print(f"{len(js)} US/CA jobs from MathJobs")
