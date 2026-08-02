"""Enrichment: match institution → coordinates + classification, nearest airport.

Liberal-arts tagging:
  US: Carnegie 2021 basic code 21 (Baccalaureate — Arts & Sciences Focus).
  CA: curated `class` of primarily_undergraduate.
Airport rule: nearest large/medium scheduled-service airport within
AIRPORT_MILES straight-line miles (~1 hour drive proxy).
"""
import difflib
import json
import math
import re
from pathlib import Path

REFDATA = Path(__file__).parent / "refdata"
AIRPORT_MILES = 55

# US state name -> abbreviation (MathJobs uses full names)
US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "district of columbia": "DC",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "puerto rico": "PR", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
CA_PROVINCES = {
    "alberta": "AB", "british columbia": "BC", "manitoba": "MB", "new brunswick": "NB",
    "newfoundland and labrador": "NL", "nova scotia": "NS", "ontario": "ON",
    "prince edward island": "PE", "quebec": "QC", "saskatchewan": "SK",
}

C21_LABELS = {
    15: "research_university",  # R1
    16: "research_university",  # R2
    17: "doctoral_professional",
    18: "masters", 19: "masters", 20: "masters",
    21: "liberal_arts",
    22: "baccalaureate_diverse",
    23: "baccalaureate_associates",
}


def _norm(name):
    import unicodedata
    s = unicodedata.normalize("NFD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = s.replace("&", "and").replace("’", "'")
    s = re.sub(r"\bthe\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\bsaint\b", "st", s)
    return re.sub(r"\s+", " ", s).strip()


# MathJobs institution names that don't fuzzy-match their IPEDS record
ALIASES = {
    "university of minnesota": "University of Minnesota-Twin Cities",
    "university of illinois at urbana champaign": "University of Illinois Urbana-Champaign",
    "rutgers university new brunswick": "Rutgers University-New Brunswick",
    "penn state": "Pennsylvania State University-Main Campus",
    "pennsylvania state university": "Pennsylvania State University-Main Campus",
    "purdue university": "Purdue University-Main Campus",
    "university of colorado at boulder": "University of Colorado Boulder",
    "texas aandm university": "Texas A & M University-College Station",
    "louisiana state university": "Louisiana State University and Agricultural & Mechanical College",
    "university of nebraska lincoln": "University of Nebraska-Lincoln",
    "cuny": "CUNY Graduate School and University Center",
    "suny at albany": "SUNY at Albany",
    "ohio state university": "Ohio State University-Main Campus",
    "university of washington": "University of Washington-Seattle Campus",
    "indiana university bloomington": "Indiana University-Bloomington",
    "university of virginia": "University of Virginia-Main Campus",
    "university of south carolina": "University of South Carolina-Columbia",
    "arizona state university": "Arizona State University Campus Immersion",
    "university of pittsburgh": "University of Pittsburgh-Pittsburgh Campus",
    "university of oklahoma": "University of Oklahoma-Norman Campus",
    "st olaf college": "St. Olaf College",
    # Canadian name variants
    "laval university": "Universite Laval",
    "memorial university": "Memorial University of Newfoundland",
    "university of quebec at montreal": "Universite du Quebec a Montreal",
    "mcgill university montreal": "McGill University",
    "university of toronto st george campus": "University of Toronto",
    "university of toronto scarborough utsc": "University of Toronto Scarborough",
    "university of toronto mississauga utm": "University of Toronto Mississauga",
    "universite mcgill": "McGill University",
    "universite laurentienne": "Laurentian University",
}


class Enricher:
    def __init__(self):
        self.airports = json.loads((REFDATA / "airports.json").read_text())
        us = json.loads((REFDATA / "us_institutions.json").read_text())
        us += json.loads((REFDATA / "us_extras.json").read_text())
        ca = json.loads((REFDATA / "ca_institutions.json").read_text())
        self.us_by_norm = {}
        for inst in us:
            inst["country"] = "US"
            self.us_by_norm.setdefault(_norm(inst["name"]), inst)
        self.ca_by_norm = {_norm(i["name"]): {**i, "country": "CA"} for i in ca}
        # city index for fallback geocoding: (city_lower, state_abbr) -> (lat, lon)
        self.city_idx = {}
        for inst in us + [dict(i, country="CA") for i in ca]:
            key = (inst["city"].lower(), inst["state"])
            self.city_idx.setdefault(key, (inst["lat"], inst["lon"]))

    def state_abbr(self, state, country):
        s = (state or "").strip().lower()
        table = US_STATES if country == "US" else CA_PROVINCES
        return table.get(s, state if len(state or "") == 2 else "")

    def match_institution(self, name, country, city="", state_abbr=""):
        n = _norm(name)
        table = self.us_by_norm if country == "US" else self.ca_by_norm
        if n in ALIASES:
            n = _norm(ALIASES[n])
        if n in table:
            return table[n], "exact"
        # try dropping campus/department qualifiers after comma already handled upstream
        close = difflib.get_close_matches(n, table.keys(), n=3, cutoff=0.87)
        for c in close:
            cand = table[c]
            # guard against wrong-state fuzzy matches
            if not state_abbr or cand["state"] == state_abbr:
                return cand, "fuzzy"
        # containment: "university of x" inside longer IPEDS name, same city+state
        for key, cand in table.items():
            if (n in key or key in n) and cand["city"].lower() == city.lower():
                return cand, "containment"
        return None, None

    def nearest_airport(self, lat, lon):
        best, best_d = None, 1e18
        for a in self.airports:
            d = _haversine_miles(lat, lon, a["lat"], a["lon"])
            if d < best_d:
                best, best_d = a, d
        return best, round(best_d, 1)

    def enrich(self, job):
        country = job["country"]
        st = self.state_abbr(job.get("state", ""), country)
        inst, how = self.match_institution(job["institution"], country, job.get("city", ""), st)
        # CMS doesn't publish a country field (we assume CA); US schools do post
        # there, so fall back to the US table and correct the country
        if inst is None and job["source"] == "cms":
            inst, how = self.match_institution(job["institution"], "US", job.get("city", ""), "")
            if inst is not None:
                country = job["country"] = "US"
        lat = lon = None
        if inst:
            lat, lon = inst["lat"], inst["lon"]
            if "class" in inst:  # curated entry (Canada or US extras)
                cls = inst["class"]
                job["inst_class"] = {
                    "primarily_undergraduate": "liberal_arts",
                    "research": "research_university",
                    "comprehensive": "doctoral_professional",
                }.get(cls, cls)
            else:
                c21 = inst.get("c21")
                job["inst_class"] = C21_LABELS.get(c21, "other")
                job["carnegie"] = c21
            job["inst_match"] = how
        else:
            # fallback: any known coordinates for the job's city
            hit = self.city_idx.get(((job.get("city") or "").lower(), st))
            if hit:
                lat, lon = hit
                job["inst_match"] = "city"
            job["inst_class"] = "unknown"
        job["liberal_arts"] = job["inst_class"] == "liberal_arts"
        if lat is not None:
            ap, miles = self.nearest_airport(lat, lon)
            job["lat"], job["lon"] = lat, lon
            job["nearest_airport"] = f"{ap['name']} ({ap['iata']})" if ap["iata"] else ap["name"]
            job["airport_miles"] = miles
            job["airport_ok"] = miles <= AIRPORT_MILES
        else:
            job["nearest_airport"] = None
            job["airport_miles"] = None
            job["airport_ok"] = None  # unknown — surfaced as "?" in UI
        return job


def _haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
