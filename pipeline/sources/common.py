"""Shared fetch/parse helpers for source adapters."""
import gzip
import html
import re
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 EliseJobFinder/1.0"

TAG_RE = re.compile(r"<[^>]+>")


def fetch_url(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return raw


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<(br|/p|/div|/li|/h[1-6])[^>]*>", "\n", s, flags=re.I)
    s = TAG_RE.sub("", s)
    s = html.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", s)).strip()


# Pure/applied mathematics indicators. Deliberately NOT statistics, CS, data
# science, actuarial, or operations research — Elise only wants mathematics
# positions, even when the hosting department is joint (Math & Stats etc.).
MATH_KEYWORDS = re.compile(
    r"\bmath|algebra|combinat|geometr|topolog|number theory|analysis|"
    r"probabilit|dynamical systems|logic|pde|differential equation",
    re.I,
)

NON_MATH_KEYWORDS = re.compile(
    r"statisti|biostat|data science|data analytics|computer science|computing|"
    r"software|informatics|artificial intelligence|machine learning|"
    r"cyber\s?security|actuar|operations research|econometric",
    re.I,
)

# phrases whose "math" substring should not count as a mathematics signal
_FALSE_MATH = re.compile(r"mathematical statistics", re.I)

# unit names embedded in titles ("... – Department of Mathematics and
# Statistics", "Center for Computational Mathematics") describe the unit, not
# the position's discipline. Stops at commas/parens so coordinate disciplines
# ("Faculty of Practice, Data Science") survive the strip.
_DEPT_PHRASE = re.compile(
    r"(department|dept\.?|school|faculty|division|college) of [\w&/’' -]+"
    r"|(center|centre|institute) (for|of) [\w&/’' -]+",
    re.I,
)

# "Machine Learning for Mathematical & Quantum Physics" — math as application
# domain of a non-math discipline, not the discipline itself
_DOMAIN_QUALIFIER = re.compile(r"\b(for|applied to) (the )?mathematical\b", re.I)


def looks_mathy(text):
    return bool(MATH_KEYWORDS.search(_FALSE_MATH.sub("", text or "")))


def classify_discipline(title, subject="", department="", description=""):
    """Return 'math', 'non_math', or 'unknown' for a posting.

    The position TITLE is decisive when it names a discipline: a title naming
    mathematics is kept even if it also names statistics (explicitly joint
    hires can go to a mathematician), while a stats/CS/DS-only title is
    excluded no matter what the hosting department is called. Subject,
    department, and description are consulted only for discipline-silent
    titles.
    """
    t = _DOMAIN_QUALIFIER.sub(" ", _DEPT_PHRASE.sub(" ", title or ""))
    if looks_mathy(t):
        return "math"
    if NON_MATH_KEYWORDS.search(t):
        return "non_math"
    for text in (subject, department, description[:600]):
        if not text or not text.strip():
            continue
        if looks_mathy(text):
            return "math"
        if NON_MATH_KEYWORDS.search(text):
            return "non_math"
    return "unknown"
