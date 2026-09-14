"""Resolve the Research V2 competition universe from the live OddsPAPI tournament catalog.

This module never invents tournament IDs. It ranks target countries using a checked-in
policy, classifies leagues/cups, and emits candidates for human/research review.
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

# Strength-guided collection policy. Rank is metadata for universe construction only,
# never a match prediction feature by itself.
TARGET_COUNTRIES = {
    "England": 1, "Italy": 2, "Spain": 3, "Germany": 4, "France": 5,
    "Netherlands": 6, "Portugal": 7, "Belgium": 8, "Turkey": 9,
    "Czech Republic": 10, "Greece": 11, "Austria": 12, "Norway": 13,
    "Denmark": 14, "Switzerland": 15, "Scotland": 16, "Poland": 17,
    "Sweden": 18, "Romania": 19,
}

EUROPE_NAMES = {
    "UEFA Champions League", "UEFA Europa League", "UEFA Conference League"
}
CUP_WORDS = ("cup", "pokal", "coppa", "copa del rey", "coupe", "taça", "taca", "beker")


def classify(name: str, category: str) -> str:
    low = name.lower()
    if name in EUROPE_NAMES or category == "International Clubs" and "uefa" in low:
        return "EUROPEAN_CUP"
    if any(word in low for word in CUP_WORDS):
        return "DOMESTIC_CUP"
    return "LEAGUE"


def main() -> None:
    key = os.environ.get("ODDSPAPI_KEY")
    if not key:
        raise SystemExit("ODDSPAPI_KEY is required")
    response = requests.get(API_URL, params={"sportId": SPORT_ID, "language": "en", "apiKey": key}, timeout=45)
    response.raise_for_status()
    catalog = response.json()

    selected = []
    for row in catalog:
        name = str(row.get("tournamentName") or "")
        category = str(row.get("categoryName") or "")
        active = int(row.get("futureFixtures") or 0) + int(row.get("upcomingFixtures") or 0) + int(row.get("liveFixtures") or 0)
        is_europe = name in EUROPE_NAMES or (category == "International Clubs" and "uefa" in name.lower())
        if category not in TARGET_COUNTRIES and not is_europe:
            continue
        if active <= 0:
            continue
        selected.append({
            "country": category,
            "country_rank": TARGET_COUNTRIES.get(category),
            "tournament_id": row.get("tournamentId"),
            "tournament_name": name,
            "tournament_slug": row.get("tournamentSlug"),
            "competition_type": classify(name, category),
            "future_fixtures": int(row.get("futureFixtures") or 0),
            "upcoming_fixtures": int(row.get("upcomingFixtures") or 0),
            "live_fixtures": int(row.get("liveFixtures") or 0),
            "provider_verified": True,
        })

    selected.sort(key=lambda x: (
        0 if x["competition_type"] == "EUROPEAN_CUP" else 1,
        x["country_rank"] if x["country_rank"] is not None else 999,
        0 if x["competition_type"] == "LEAGUE" else 1,
        x["tournament_name"],
    ))
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "oddspapi",
        "sport_id": SPORT_ID,
        "classification": "UNIVERSE_CANDIDATES_NOT_AUTOMATICALLY_PROMOTED",
        "selection_policy": "PROVIDER_VERIFIED_IDS; ACTIVE_FIXTURES; STRENGTH_GUIDED_COUNTRIES; INCLUDE_DOMESTIC_AND_UEFA_CUPS",
        "candidate_count": len(selected),
        "candidates": selected,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_count": len(selected), "output": str(OUT)}))


if __name__ == "__main__":
    main()
