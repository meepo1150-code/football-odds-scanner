from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, SPORT_ID, _get
from .v2_mainline_observer import TARGETS, TARGETS_PATH, _load_json

OUTPUT = Path("reports/v2_tournament_diagnostics.json")


def _missing_targets(selected: list[dict]) -> list[tuple[str, str]]:
    actual = {(str(x.get("universe")), str(x.get("country"))) for x in selected if isinstance(x, dict)}
    expected = [(universe, country) for universe, countries in TARGETS.items() for country in countries]
    return [(universe, country) for universe, country in expected if (universe, country) not in actual]


def _country_rows(rows: list[dict], missing: list[tuple[str, str]]) -> list[dict]:
    wanted = {country for _, country in missing}
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict) or str(row.get("categoryName") or "") not in wanted:
            continue
        if row.get("tournamentId") is None:
            continue
        out.append(
            {
                "category_name": row.get("categoryName"),
                "tournament_id": row.get("tournamentId"),
                "tournament_name": row.get("tournamentName"),
                "tournament_slug": row.get("tournamentSlug"),
            }
        )
    out.sort(key=lambda x: (str(x.get("category_name")), str(x.get("tournament_name")), int(x.get("tournament_id") or 0)))
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
            "schema_version": "1.0",
            "status": "TARGETS_ALREADY_COMPLETE",
            "generated_at": now,
            "requests_attempted": 0,
            "missing_targets": [],
            "country_tournament_rows": [],
        }
    else:
        key = os.getenv(ENV_KEY)
        if not key:
            payload = {
                "schema_version": "1.0",
                "status": "API_KEY_NOT_CONFIGURED",
                "generated_at": now,
                "requests_attempted": 0,
                "missing_targets": [{"universe": u, "country": c} for u, c in missing],
                "country_tournament_rows": [],
            }
        else:
            try:
                rows = _rows(_get("/tournaments", key, {"sportId": SPORT_ID, "language": "en"}))
                payload = {
                    "schema_version": "1.0",
                    "status": "UNRESOLVED_TARGET_METADATA_CAPTURED",
                    "generated_at": now,
                    "requests_attempted": 1,
                    "missing_targets": [{"universe": u, "country": c} for u, c in missing],
                    "country_tournament_rows": _country_rows(rows, missing),
                }
            except Exception as exc:
                payload = {
                    "schema_version": "1.0",
                    "status": "TOURNAMENT_DIAGNOSTIC_UNAVAILABLE",
                    "generated_at": now,
                    "requests_attempted": 1,
                    "missing_targets": [{"universe": u, "country": c} for u, c in missing],
                    "country_tournament_rows": [],
                    "errors": [f"{type(exc).__name__}: {exc}"],
                }
    path = root / OUTPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(diagnose(), ensure_ascii=False))
