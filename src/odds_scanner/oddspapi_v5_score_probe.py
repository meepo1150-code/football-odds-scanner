from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .oddspapi_history_archive import BIG5_TOURNAMENTS, _rows
from .oddspapi_provider import ENV_KEY, SPORT_ID, USER_AGENT
from .oddspapi_result_join import normalize_result

BASE_V5 = "https://api.oddspapi.io/v5"
REPORT_PATH = Path("reports/oddspapi_v5_score_probe.json")
PROBE_FROM = "2026-02-08T00:00:00Z"
PROBE_TO = "2026-02-09T00:00:00Z"


def _get_v5(path: str, key: str, params: dict | None = None, timeout: int = 20):
    query = dict(params or {})
    query["apiKey"] = key
    url = BASE_V5 + path + "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def inspect_fixture_payload(payload) -> dict:
    fixtures = _rows(payload)
    finished_big5: list[dict] = []
    provider_key_counts: Counter[str] = Counter()
    score_shape_counts: Counter[str] = Counter()
    normalized: list[dict] = []

    for fixture in fixtures:
        try:
            tid = int(fixture.get("tournamentId"))
        except (TypeError, ValueError):
            continue
        if fixture.get("statusId") != 2 or tid not in BIG5_TOURNAMENTS:
            continue
        finished_big5.append(fixture)
        providers = fixture.get("externalProviders")
        if isinstance(providers, dict):
            provider_key_counts.update(str(k) for k, v in providers.items() if v not in (None, ""))
        scores = fixture.get("scores")
        if isinstance(scores, dict):
            score_shape_counts.update(str(k) for k in scores.keys())
        result = normalize_result(fixture)
        if result:
            normalized.append(result)

    samples = []
    for fixture in finished_big5[:3]:
        item = {
            "fixture_id": str(fixture.get("fixtureId")),
            "home": fixture.get("participant1Name"),
            "away": fixture.get("participant2Name"),
            "score_keys": sorted((fixture.get("scores") or {}).keys()) if isinstance(fixture.get("scores"), dict) else [],
        }
        result = normalize_result(fixture)
        if result:
            item["normalized_result"] = result
        samples.append(item)

    return {
        "fixture_rows": len(fixtures),
        "finished_big5_rows": len(finished_big5),
        "explicit_ft_result_rows": len(normalized),
        "score_top_level_key_counts": dict(sorted(score_shape_counts.items())),
        "external_provider_key_counts": dict(sorted(provider_key_counts.items())),
        "samples": samples,
    }


def run_probe(root: Path = Path(".")) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    key = os.getenv(ENV_KEY)
    if not key:
        report = {
            "schema_version": "1.0",
            "classification": "ODDSPAPI_V5_SCORE_SCHEMA_PROBE",
            "status": "API_KEY_NOT_CONFIGURED",
            "generated_at": generated_at,
            "requests_attempted": 0,
            "promotion_allowed": False,
        }
    else:
        try:
            payload = _get_v5(
                "/fixtures",
                key,
                {
                    "sportId": SPORT_ID,
                    "from": PROBE_FROM,
                    "to": PROBE_TO,
                    "limit": 300,
                    "language": "en",
                },
            )
            report = {
                "schema_version": "1.0",
                "classification": "ODDSPAPI_V5_SCORE_SCHEMA_PROBE",
                "status": "OK",
                "generated_at": generated_at,
                "api_version": "v5",
                "requests_attempted": 1,
                "probe_window": {"from": PROBE_FROM, "to": PROBE_TO},
                **inspect_fixture_payload(payload),
                "promotion_allowed": False,
            }
        except Exception as exc:
            report = {
                "schema_version": "1.0",
                "classification": "ODDSPAPI_V5_SCORE_SCHEMA_PROBE",
                "status": "UNAVAILABLE",
                "generated_at": generated_at,
                "api_version": "v5",
                "requests_attempted": 1,
                "probe_window": {"from": PROBE_FROM, "to": PROBE_TO},
                "errors": [f"{type(exc).__name__}: {exc}"],
                "promotion_allowed": False,
            }
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(run_probe())
