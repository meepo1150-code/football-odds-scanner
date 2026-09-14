"""Resolve Research V2 senior competition candidates from OddsPAPI.

Provider IDs are never invented. The resolver intentionally excludes women/youth/reserve
competitions and lower-tier noise before human/coverage review.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = "https://api.oddspapi.io/v4/tournaments"
SPORT_ID = 10
OUT = Path("reports/oddspapi_tournament_universe_candidates.json")

TARGET_COUNTRIES = {
    "England": 1, "Italy": 2, "Spain": 3, "Germany": 4, "France": 5,
    "Netherlands": 6, "Portugal": 7, "Belgium": 8, "Turkey": 9,
    "Czech Republic": 10, "Greece": 11, "Austria": 12, "Norway": 13,
    "Denmark": 14, "Switzerland": 15, "Scotland": 16, "Poland": 17,
    "Sweden": 18, "Romania": 19,
}
EUROPE_NAMES = {"UEFA Champions League", "UEFA Europa League", "UEFA Conference League"}
CUP_WORDS = ("cup", "pokal", "coppa", "copa del rey", "coupe", "taça", "taca", "beker")
EXCLUDE_WORDS = (
    "women", "woman", "female", "u17", "u18", "u19", "u20", "u21", "u23",
    "youth", "junior", "primavera", "reserve", "reserves", "amateur",
)

# Deliberately broad senior tiers. Pinnacle coverage is the next gate.
MAX_LEAGUE_TIERS = {
    "England": 4, "Italy": 2, "Spain": 2, "Germany": 3, "France": 2,
    "Netherlands": 2, "Portugal": 2, "Belgium": 2, "Turkey": 2,
    "Czech Republic": 2, "Greece": 2, "Austria": 2, "Norway": 2,
    "Denmark": 2, "Switzerland": 2, "Scotland": 2, "Poland": 2,
    "Sweden": 2, "Romania": 2,
}


def classify(name: str, category: str) -> str:
    low = name.lower()
    if name in EUROPE_NAMES:
        return "EUROPEAN_CUP"
    if any(word in low for word in CUP_WORDS):
        return "DOMESTIC_CUP"
    return "LEAGUE"


def excluded(name: str) -> bool:
    low = name.lower()
    return any(word in low for word in EXCLUDE_WORDS)


def tier_hint(name: str, country: str) -> int | None:
    low = name.lower()
    if country == "England":
        return {"premier league": 1, "championship": 2, "league one": 3, "league two": 4}.get(low)
    if country == "Italy": return {"serie a": 1, "serie b": 2}.get(low)
    if country == "Spain": return 1 if low == "laliga" else (2 if "laliga 2" in low or "segunda" in low else None)
    if country == "Germany": return 1 if low == "bundesliga" else (2 if "2. bundesliga" in low else (3 if "3. liga" in low else None))
    if country == "France": return 1 if low == "ligue 1" else (2 if low == "ligue 2" else None)
    # For remaining countries, keep obvious top/second divisions for coverage review.
    second_markers = ("2.", "division 2", "second", "eerste divisie", "liga 2", "1. division", "championship")
    if any(x in low for x in second_markers): return 2
    return 1


def main() -> None:
    key = os.environ.get("ODDSPAPI_KEY")
    if not key:
        raise SystemExit("ODDSPAPI_KEY is required")
    response = requests.get(API_URL, params={"sportId": SPORT_ID, "language": "en", "apiKey": key}, timeout=45)
    response.raise_for_status()
    catalog = response.json()

    selected = []
    rejected = {"non_target": 0, "inactive": 0, "women_youth_reserve": 0, "lower_tier": 0}
    for row in catalog:
        name = str(row.get("tournamentName") or "")
        category = str(row.get("categoryName") or "")
        active = sum(int(row.get(k) or 0) for k in ("futureFixtures", "upcomingFixtures", "liveFixtures"))
        is_europe = name in EUROPE_NAMES
        if category not in TARGET_COUNTRIES and not is_europe:
            rejected["non_target"] += 1; continue
        if active <= 0:
            rejected["inactive"] += 1; continue
        if excluded(name):
            rejected["women_youth_reserve"] += 1; continue
        ctype = classify(name, category)
        tier = None if ctype != "LEAGUE" else tier_hint(name, category)
        if ctype == "LEAGUE" and (tier is None or tier > MAX_LEAGUE_TIERS.get(category, 1)):
            rejected["lower_tier"] += 1; continue
        selected.append({
            "country": category,
            "country_rank": TARGET_COUNTRIES.get(category),
            "tournament_id": row.get("tournamentId"),
            "tournament_name": name,
            "tournament_slug": row.get("tournamentSlug"),
            "competition_type": ctype,
            "tier": tier,
            "future_fixtures": int(row.get("futureFixtures") or 0),
            "upcoming_fixtures": int(row.get("upcomingFixtures") or 0),
            "live_fixtures": int(row.get("liveFixtures") or 0),
            "provider_verified": True,
        })

    selected.sort(key=lambda x: (0 if x["competition_type"] == "EUROPEAN_CUP" else 1, x["country_rank"] or 999, x["competition_type"], x["tier"] or 99, x["tournament_name"]))
    payload = {
        "schema_version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "oddspapi", "sport_id": SPORT_ID,
        "classification": "SENIOR_UNIVERSE_CANDIDATES_NOT_AUTOMATICALLY_PROMOTED",
        "selection_policy": "PROVIDER_VERIFIED_ACTIVE; MEN_SENIOR; STRENGTH_GUIDED; MAJOR_LEAGUES_AND_CUPS; PINNACLE_COVERAGE_PENDING",
        "candidate_count": len(selected), "rejected_counts": rejected, "candidates": selected,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_count": len(selected), "rejected_counts": rejected, "output": str(OUT)}))


if __name__ == "__main__":
    main()
