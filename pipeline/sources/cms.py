"""Canadian Mathematical Society job board — WordPress REST API.

Institution and location live inside the rendered ad text, so we extract the
first institution-shaped phrase; enrichment then geocodes it against the
curated Canadian institutions list.
"""
import json
import re

from .common import fetch_url, strip_html
from .mathjobs import classify_type

FEED = "https://cms.math.ca/wp-json/wp/v2/job-ad?per_page=100&orderby=date&order=desc"

INST_RE = re.compile(
    r"((?:Universit[ée] de [A-ZÉ][\w'’.-]+(?: [A-ZÉ][\w'’.-]+)?)"
    r"|(?:University of [A-Z][\w'’.-]+(?: [A-Z][\w'’.-]+){0,3})"
    r"|(?:[A-Z][\w'’.-]+(?: [A-Z][\w'’.&-]+){0,3} (?:University|College|Polytechnique))"
    r"|HEC Montr[ée]al)"
)

DEADLINE_RE = re.compile(
    r"(?:deadline|apply by|applications? (?:must be )?(?:received|submitted)[^.]{0,40}?by|review of applications (?:will )?begins? (?:on )?)"
    r"[^.]{0,60}?(\w+ \d{1,2},? \d{4})",
    re.I,
)


def _parse_date(s):
    from datetime import datetime
    for fmt in ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
        try:
            return datetime.strptime(s.replace("  ", " "), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def fetch():
    data = json.loads(fetch_url(FEED))
    jobs = []
    for rec in data:
        title = strip_html(rec["title"]["rendered"])
        body = strip_html(rec["content"]["rendered"])
        # drop territory acknowledgements etc. when hunting for the institution:
        # the hiring school is almost always in the first sentences mentioning
        # a department or "invites applications"
        m = INST_RE.search(body)
        institution = m.group(1).strip() if m else ""
        # CMS occasionally carries overseas ads; this board is our Canada source
        if re.search(
            r"Hong Kong|China|Shenzhen|Singapore|Abu Dhabi|Qatar|Saudi|Aarhus|Monash|Australia|Denmark|Copenhagen|Zurich|ETH",
            institution + " " + title,
        ):
            continue
        dm = DEADLINE_RE.search(body)
        deadline = _parse_date(dm.group(1)) if dm else None
        jobs.append(
            {
                "id": f"cms-{rec['id']}",
                "source": "cms",
                "institution": institution or "(see posting)",
                "department": "",
                "title": title,
                "position_type": classify_type(None, title),
                "mathjobs_type": None,
                "city": "",
                "state": "",
                "country": "CA",
                "posted": rec["date"][:10],
                "deadline": deadline,
                "close_date": None,
                "url": rec["link"],
                "apply_url": rec["link"],
                "subject": "",
                "description": body,
            }
        )
    return jobs


if __name__ == "__main__":
    for j in fetch()[:10]:
        print(j["posted"], "|", j["institution"][:40], "|", j["title"][:50], "|", j["deadline"])
