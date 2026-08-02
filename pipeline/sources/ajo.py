"""AcademicJobsOnline adapter — same Duke-built public_job_boards API as MathJobs.

AJO hosts all disciplines; there is no server-side subject filter, so we pull
the whole board and keep US/CA records whose subject/title look mathematical.
"""
import json

from .common import fetch_url, strip_html, looks_mathy
from .mathjobs import classify_type, _clean_date

FEED = "https://academicjobsonline.org/ajo/public_job_boards?limit=2000&page=1&all_postings=1"


def fetch():
    data = json.loads(fetch_url(FEED))
    jobs = []
    for rec in data.get("results", []):
        if rec.get("country") not in ("US", "CA"):
            continue
        subject = strip_html(rec.get("subject") or "")
        title = strip_html(rec.get("name") or "")
        if not (looks_mathy(subject) or looks_mathy(title)):
            continue
        jobs.append(
            {
                "id": f"ajo-{rec['id']}",
                "source": "ajo",
                "institution": rec.get("univ") or "",
                "department": rec.get("unit_name") or "",
                "title": title,
                "position_type": classify_type(rec.get("type"), title),
                "mathjobs_type": rec.get("type"),
                "city": rec.get("city") or "",
                "state": rec.get("state") or "",
                "country": rec.get("country"),
                "posted": _clean_date(rec.get("open_date_raw")),
                "deadline": _clean_date((rec.get("deadline_raw") or "")[:10]),
                "close_date": _clean_date(rec.get("close_date_raw")),
                "url": rec.get("url"),
                "apply_url": rec.get("apply") or rec.get("url"),
                "subject": subject,
                "description": strip_html(rec.get("description") or ""),
            }
        )
    return jobs


if __name__ == "__main__":
    print(f"{len(fetch())} US/CA math jobs from AJO")
