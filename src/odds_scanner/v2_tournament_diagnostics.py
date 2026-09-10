from __future__ import annotations

import json
import os
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, SPORT_ID, _get
from .v2_mainline_observer import TARGETS, TARGETS_PATH, _load_json

OUTPUT = Path("reports/v2_tournament_diagnostics.json")

# Diagnostic-only search hints. These never select or promote a tournament;
# they only surface provider metadata for human/exact-alias review.
SEARCH_HINTS = {
    "Portugal": ("primeira", "liga portugal", "portugal"),
    "Belgium": ("jupiler", "pro league", "belgium"),
    "Turkey": ("super lig", "superliga", "turkey", "turkiye"),
    "Scotland": ("premiership", "scotland"),
}


def _missing_targets(selected: list[dict]) -> list[tuple[str, str]]:
    actual = {(str(x.get("universe")), str(x.get("country"))) for x in selected if isinstance(x, dict)}
    expected = [(universe, country) for universe, countries in TARGETS.items() for country in countries]
    return [(universe, country) for universe, country in expected if (universe, country) not in actual]


def _search_text(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().replace("-", " ").replace("_", " ").split())


def _candidate_rows(rows: list[dict], missing: list[tuple[str, str]]) -> list[dict]:
    missing_countries = {country for _, country in missing}
    out: list[dict] = []
    seen: set[tuple[object, object, object]] = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("tournamentId") is None:
            continue
        category = str(row.get("categoryName") or "")
        haystack = _search_text(" ".join([category, str(row.get("categorySlug") or ""), str(row.get("tournamentName") or ""), str(row.get("tournamentSlug") or "")]))
        matched_for = []
        for country in sorted(missing_countries):
            hints = SEARCH_HINTS.get(country, (_search_text(country),))
            if category == country or any(_search_text(hint) in haystack for hint in hints):
                matched_for.append(country)
        if not matched_for:
            continue
        key = (row.get("tournamentId"), row.get("tournamentName"), row.get("categoryName"))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "matched_for": matched_for,
                "category_name": row.get("categoryName"),
                "category_slug": row.get("categorySlug"),
                "tournament_id": row.get("tournamentId"),
                "tournament_name": row.get("tournamentName"),
                "tournament_slug": row.get("tournamentSlug"),
                "future_fixtures": row.get("futureFixtures"),
                "upcoming_fixtures": row.get("upcomingFixtures"),
            }
        )
    out.sort(key=lambda x: (str(x.get("matched_for")), str(x.get("category_name")), str(x.get("tournament_name")), int(x.get("tournament_id") or 0)))
    return out


def diagnose(root: Path = Path(".")) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    target_payload = _load_json(root / TARGETS_PATH) or {}
    selected = target_payload.get("tournaments") if isinstance(target_payload, dict) else []
    if not isinstance(selected, list):
        selected = []
    missing = _missing_targets(selected)
    if not missing:
        payload = {
            "schema_version": "1.1",
            "status": "TARGETS_ALREADY_COMPLETE",
            "generated_at": now,
            "requests_attempted": 0,
            "missing_targets": [],
            "candidate_tournament_rows": [],
        }
    else:
        key = os.getenv(ENV_KEY)
        if not key:
            payload = {
                "schema_version": "1.1",
                "status": "API_KEY_NOT_CONFIGURED",
                "generated_at": now,
                "requests_attempted": 0,
                "missing_targets": [{"universe": u, "country": c} for u, c in missing],
                "candidate_tournament_rows": [],
            }
        else:
            try:
                rows = _rows(_get("/tournaments", key, {"sportId": SPORT_ID, "language": "en"}))
                payload = {
                    "schema_version": "1.1",
                    "status": "UNRESOLVED_TARGET_METADATA_CAPTURED",
                    "generated_at": now,
                    "requests_attempted": 1,
                    "missing_targets": [{"universe": u, "country": c} for u, c in missing],
                    "candidate_tournament_rows": _candidate_rows(rows, missing),
                    "selection_performed": False,
                }
            except Exception as exc:
                payload = {
                    "schema_version": "1.1",
                    "status": "TOURNAMENT_DIAGNOSTIC_UNAVAILABLE",
                    "generated_at": now,
                    "requests_attempted": 1,
                    "missing_targets": [{"universe": u, "country": c} for u, c in missing],
                    "candidate_tournament_rows": [],
                    "errors": [f"{type(exc).__name__}: {exc}"],
                }
    path = root / OUTPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(diagnose(), ensure_ascii=False))
