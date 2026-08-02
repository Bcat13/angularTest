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


MATH_KEYWORDS = re.compile(
    r"math|statist|actuar|algebra|combinat|geometr|topolog|probabil|number theory|"
    r"analysis|operations research|data science",
    re.I,
)


def looks_mathy(text):
    return bool(MATH_KEYWORDS.search(text or ""))
