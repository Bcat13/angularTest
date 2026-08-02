"""Chronicle of Higher Education mathematics RSS (PositionType=79).

Catches teaching-oriented liberal-arts postings that never reach MathJobs.
Item title format: "Institution: Job Title"; description ends with
"State, United States".
"""
import re
import xml.etree.ElementTree as ET

from .common import fetch_url, strip_html
from .mathjobs import classify_type

FEED = "https://jobs.chronicle.com/jobsrss/?PositionType=79&countrycode=US"

LOC_RE = re.compile(r"([A-Z][\w .-]+),\s*United States\s*$")
JOB_ID_RE = re.compile(r"/job/(\d+)/")


def fetch():
    root = ET.fromstring(fetch_url(FEED))
    jobs = []
    for item in root.iter("item"):
        raw_title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").split("?")[0]
        desc = strip_html(item.findtext("description") or "")
        idm = JOB_ID_RE.search(link)
        if not idm:
            continue
        if ":" in raw_title:
            institution, title = [s.strip() for s in raw_title.split(":", 1)]
        else:
            institution, title = "", raw_title
        state = ""
        lm = LOC_RE.search(desc)
        if lm:
            state = lm.group(1).strip()
        jobs.append(
            {
                "id": f"chron-{idm.group(1)}",
                "source": "chronicle",
                "institution": institution,
                "department": "",
                "title": title,
                "position_type": classify_type(None, title),
                "mathjobs_type": None,
                "city": "",
                "state": state,
                "country": "US",
                "posted": None,
                "deadline": None,
                "close_date": None,
                "url": link,
                "apply_url": link,
                "subject": "Mathematics",
                "description": desc,
            }
        )
    return jobs


if __name__ == "__main__":
    for j in fetch()[:10]:
        print(j["institution"][:45], "|", j["title"][:50], "|", j["state"])
