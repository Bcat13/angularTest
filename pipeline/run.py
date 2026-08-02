"""Pipeline orchestrator: fetch all sources → enrich → site/public/data/jobs.json.

Maintains state/seen.json (job id → first_seen date) so the site can badge
new postings and a future alerting step can diff runs.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sources import mathjobs
from enrich import Enricher

ROOT = Path(__file__).parent.parent
STATE = Path(__file__).parent / "state" / "seen.json"
OUT = ROOT / "site" / "public" / "data" / "jobs.json"

SOURCES = [mathjobs]


def main():
    jobs = []
    counts = {}
    for src in SOURCES:
        fetched = src.fetch()
        counts[src.__name__.split(".")[-1]] = len(fetched)
        jobs.extend(fetched)

    # dedupe across sources by (institution, title), keep first (source order = priority)
    seen_keys = set()
    deduped = []
    for j in jobs:
        key = (j["institution"].lower().strip(), j["title"].lower().strip())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(j)

    enricher = Enricher()
    for j in deduped:
        enricher.enrich(j)

    # first_seen tracking
    today = date.today().isoformat()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    new_jobs = []
    for j in deduped:
        if j["id"] not in state:
            state[j["id"]] = today
            new_jobs.append(j["id"])
        j["first_seen"] = state[j["id"]]
    STATE.write_text(json.dumps(state, indent=0, sort_keys=True))

    deduped.sort(key=lambda j: (j.get("deadline") or "9999", j["institution"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated": today, "jobs": deduped}, indent=0))

    # summary for CI logs
    n = len(deduped)
    match_default = [
        j for j in deduped
        if j["position_type"] in ("postdoc", "tenure_track") and j["airport_ok"]
    ]
    print(f"sources: {counts}")
    print(f"total US/CA jobs: {n} | new this run: {len(new_jobs)}")
    print(f"matching Elise's default filter (postdoc/TT + airport OK): {len(match_default)}")
    print(f"liberal arts institutions: {sum(1 for j in deduped if j['liberal_arts'])}")
    unmatched = [j["institution"] for j in deduped if j.get("inst_match") is None and j["inst_class"] == "unknown" and j["airport_ok"] is None]
    if unmatched:
        print(f"unmatched institutions ({len(unmatched)}): {sorted(set(unmatched))[:15]}")


if __name__ == "__main__":
    main()
