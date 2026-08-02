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


# --- Subfield rule (Elise): keep combinatorics or general/open-field math; ---
# --- drop positions explicitly restricted to a different subfield.          ---
# Scanned on title + subject only: descriptions routinely enumerate a whole
# department's research areas, which would misread a general call as narrow.
COMBINATORICS = re.compile(r"combinator|discrete math|graph theory", re.I)

SUBFIELDS = [
    ("number theory", re.compile(r"number theor|th[ée]orie des nombres", re.I)),
    ("geometry", re.compile(r"g[ée]?om[ée]tr", re.I)),
    ("topology", re.compile(r"topolog", re.I)),
    ("analysis", re.compile(r"\banalysis\b|\banalyse\b", re.I)),
    ("PDE / differential equations", re.compile(r"differential equation|\bpdes?\b", re.I)),
    ("probability / stochastics", re.compile(r"probabilit|stochastic", re.I)),
    ("logic / foundations", re.compile(r"\blogic\b|set theory|model theory", re.I)),
    ("dynamical systems", re.compile(r"dynamical system|ergodic", re.I)),
    ("mathematical physics / quantum", re.compile(r"mathematical physics|quantum", re.I)),
    ("numerical / scientific computing", re.compile(r"numerical|scientific computing", re.I)),
    ("applied mathematics", re.compile(r"applied math", re.I)),
    ("mathematical biology", re.compile(r"mathematical biology|biomath", re.I)),
    ("optimization", re.compile(r"optimization", re.I)),
    ("fluid dynamics", re.compile(r"\bfluids?\b", re.I)),
    ("cryptography", re.compile(r"cryptograph", re.I)),
    ("representation theory", re.compile(r"representation theor|th[ée]orie des repr[ée]sentations", re.I)),
    ("algebra", re.compile(r"\balgebra|\balg[èe]bre", re.I)),
    ("mathematics education", re.compile(r"math(ematics)? education", re.I)),
    ("financial mathematics", re.compile(r"financial math|mathematical finance", re.I)),
]


# markers that a search is open-field even though specific areas are named.
# "a related field" (singular) is the "anyone may apply" idiom; the plural in
# "closely related fields such as X" narrows rather than opens, so it doesn't count.
_OPEN_FIELD = re.compile(
    r"pure\b.{0,20}?(and|or|&|/)\s*applied|all (research )?areas|any (research )?(area|field)"
    r"|related field(?!s)|broadly construed|areas? of mathematics",
    re.I,
)

# "mathematics" standing alone (not "applied/financial/... mathematics") listed
# in a subject line means mathematicians of any stripe may apply
_BARE_MATH = re.compile(
    r"(?<!applied )(?<!financial )(?<!computational )(?<!industrial )(?<!undergraduate )\bmathematics\b",
    re.I,
)


def classify_subfield(title, subject=""):
    """Return ('combinatorics'|'general'|<other subfield name>, ok_bool).

    Precedence: combinatorics anywhere wins; open-field markers win next; a
    subfield stated in the TITLE restricts the search; a subject line that
    lists bare "mathematics" among acceptable areas is open even if it also
    names specific subfields; otherwise subject-stated subfields restrict.
    """
    t = _DOMAIN_QUALIFIER.sub(" ", _DEPT_PHRASE.sub(" ", title or ""))
    if COMBINATORICS.search(f"{t} ; {subject}"):
        return "combinatorics", True
    # title first: an open marker there ("Pure Mathematics or Applied
    # Mathematics") wins, then a title-stated subfield restricts regardless of
    # how the subject line hedges
    if _OPEN_FIELD.search(t):
        return "general", True
    for name, rx in SUBFIELDS:
        if rx.search(t):
            return name, False
    if subject:
        if _OPEN_FIELD.search(subject) or _BARE_MATH.search(subject):
            return "general", True
        for name, rx in SUBFIELDS:
            if rx.search(subject):
                return name, False
    return "general", True


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
