"""University Affairs (Canada) — single-page HTML listing of all academic jobs.

Titles look like "Mathematics and Statistics - Assistant Professor"; we keep
only math-ish ones. robots.txt asks Crawl-delay: 10 — we make one request/day.
"""
import re

from .common import fetch_url, strip_html, looks_mathy
from .mathjobs import classify_type

URL = "https://universityaffairs.ca/search-jobs/"

BLOCK_RE = re.compile(r'<div class="job__block">(.*?)(?=<div class="job__block">|<footer|$)', re.S)
LINK_RE = re.compile(r'href="/search-jobs/\?job_id=(\d+)"')
TITLE_RE = re.compile(r'<h2 class="job__title">(.*?)</h[23]>', re.S)
INST_RE = re.compile(r'<div class="job__block-institution">(.*?)</div>', re.S)
LOC_RE = re.compile(r"</svg>\s*([^<]+)", re.S)


def fetch():
    html_text = fetch_url(URL).decode("utf-8", "replace")
    jobs = []
    for m in BLOCK_RE.finditer(html_text):
        block = m.group(1)
        lm, tm, im = LINK_RE.search(block), TITLE_RE.search(block), INST_RE.search(block)
        if not (lm and tm):
            continue
        title = strip_html(tm.group(1))
        if not looks_mathy(title):
            continue
        institution = strip_html(im.group(1)) if im else ""
        loc = ""
        locm = LOC_RE.search(block)
        if locm:
            loc = strip_html(locm.group(1))
        city, _, prov = [p.strip() for p in loc.partition(",")]
        jobs.append(
            {
                "id": f"ua-{lm.group(1)}",
                "source": "universityaffairs",
                "institution": institution,
                "department": "",
                "title": title,
                "position_type": classify_type(None, title),
                "mathjobs_type": None,
                "city": city,
                "state": prov,
                "country": "CA",
                "posted": None,
                "deadline": None,
                "close_date": None,
                "url": f"https://universityaffairs.ca/search-jobs/?job_id={lm.group(1)}",
                "apply_url": f"https://universityaffairs.ca/search-jobs/?job_id={lm.group(1)}",
                "subject": "",
                "description": "",
            }
        )
    return jobs


if __name__ == "__main__":
    for j in fetch():
        print(j["institution"][:45], "|", j["title"][:55], "|", j["city"], j["state"])
