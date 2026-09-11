from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .oddspapi_discovery import _rows
from .oddspapi_provider import ENV_KEY, _catalog, _get, _outcome_lookup, _player, _quarter
from .v2_mainline_observer import CATALOG_PATH, TARGETS_PATH, _load_json, split_target_batches, targets_complete

REPORT_PATH = Path("reports/v2_ah_marker_probe.json")
MIN_BATCH_COOLDOWN_SECONDS = 1.25


def _active_player(outcome: dict | None) -> dict | None:
    if not isinstance(outcome, dict):
        return None
    p = _player(outcome)
    return p if p and p.get("active") is True else None


def _selections(meta: dict, market_data: dict) -> dict[str, dict]:
    names = _outcome_lookup(meta)
    out: dict[str, dict] = {}
    for outcome_id, outcome in (market_data.get("outcomes") or {}).items():
        p = _active_player(outcome)
        label = names.get(str(outcome_id), "").strip().lower()
        if p and label:
            out[label] = p
    return out


def _marker(player: dict | None) -> str:
    if not isinstance(player, dict) or "mainLine" not in player:
        return "MISSING"
    return "TRUE" if player.get("mainLine") is True else "FALSE"


def ah_marker_shape(fixture: dict, markets_catalog: list[dict], *, bookmaker: str = "bet365") -> dict:
    book = (fixture.get("bookmakerOdds") or {}).get(bookmaker)
    if not isinstance(book, dict):
        return {"ah_markets": 0, "signatures": {}, "both_true_lines": []}
    catalog = _catalog(markets_catalog)
    signatures: Counter[str] = Counter()
    both_true_lines: list[float] = []
    market_rows: list[dict] = []
    for market_id, market_data in (book.get("markets") or {}).items():
        meta = catalog.get(str(market_id))
        if not isinstance(meta, dict) or not isinstance(market_data, dict) or market_data.get("marketActive") is not True:
            continue
        mname = str(meta.get("marketName") or "").lower()
        if "asian handicap" not in mname:
            continue
        line = _quarter(meta.get("handicap"))
        if line is None:
            continue
        selections = _selections(meta, market_data)
        hp = selections.get("home") or selections.get("1")
        ap = selections.get("away") or selections.get("2")
        signature = f"H_{_marker(hp)}__A_{_marker(ap)}"
        signatures[signature] += 1
        if hp and ap and hp.get("mainLine") is True and ap.get("mainLine") is True:
            both_true_lines.append(float(line))
        market_rows.append({
            "line": float(line),
            "signature": signature,
            "home_price": hp.get("price") if hp else None,
            "away_price": ap.get("price") if ap else None,
        })
    return {
        "ah_markets": len(market_rows),
        "signatures": dict(sorted(signatures.items())),
        "both_true_lines": sorted(both_true_lines),
        "markets": sorted(market_rows, key=lambda x: x["line"]),
    }


def probe_from_env(root: Path = Path("."), *, sleep_fn=time.sleep) -> dict:
    generated_at = datetime.now(timezone.utc)
    key = os.getenv(ENV_KEY)
    catalog = _load_json(root / CATALOG_PATH)
    targets_payload = _load_json(root / TARGETS_PATH)
    targets = (targets_payload or {}).get("tournaments") if isinstance(targets_payload, dict) else None
    if not key:
        return _write(root, {"schema_version": "1.1", "status": "API_KEY_NOT_CONFIGURED", "generated_at": generated_at.isoformat(), "promotion_allowed": False})
    if not isinstance(catalog, list) or not isinstance(targets, list) or not targets_complete(targets):
        return _write(root, {"schema_version": "1.1", "status": "LOCKED_INPUT_UNAVAILABLE", "generated_at": generated_at.isoformat(), "promotion_allowed": False})

    requests_attempted = 0
    aggregate: Counter[str] = Counter()
    fixture_shape_counts: Counter[str] = Counter()
    universe_counts: dict[str, Counter[str]] = {}
    samples: list[dict] = []
    batch_reports: list[dict] = []
    for batch_index, (universe, batch_rows) in enumerate(split_target_batches(targets)):
        if batch_index > 0:
            sleep_fn(MIN_BATCH_COOLDOWN_SECONDS)
        ids = ",".join(str(x["tournament_id"]) for x in batch_rows)
        requests_attempted += 1
        try:
            fixtures = _rows(_get("/odds-by-tournaments", key, {"tournamentIds": ids, "bookmakers": "bet365", "language": "en", "verbosity": 3}))
        except Exception as exc:
            return _write(root, {"schema_version": "1.1", "status": "CURRENT_BATCH_UNAVAILABLE", "generated_at": generated_at.isoformat(), "requests_attempted": requests_attempted, "failed_universe": universe, "errors": [f"{type(exc).__name__}: {exc}"], "batch_cooldown_seconds": MIN_BATCH_COOLDOWN_SECONDS, "promotion_allowed": False})
        batch_reports.append({"universe": universe, "fixture_rows": len(fixtures), "tournament_count": len(batch_rows)})
        ucounter: Counter[str] = Counter()
        for fixture in fixtures:
            shape = ah_marker_shape(fixture, catalog)
            for signature, count in shape["signatures"].items():
                aggregate[signature] += int(count)
                ucounter[signature] += int(count)
            fixture_key = f"AH_MARKETS_{shape['ah_markets']}__BOTH_TRUE_{len(shape['both_true_lines'])}"
            fixture_shape_counts[fixture_key] += 1
            if len(samples) < 30 and shape["ah_markets"]:
                samples.append({"fixture_id": fixture.get("fixtureId"), "universe": universe, "start_time": fixture.get("startTime"), **shape})
        universe_counts[universe] = ucounter

    payload = {
        "schema_version": "1.1",
        "classification": "VALIDATION_V2_AH_MAINLINE_MARKER_DIAGNOSTIC",
        "status": "PROBE_COMPLETE",
        "generated_at": generated_at.isoformat(),
        "requests_attempted": requests_attempted,
        "batch_cooldown_seconds": MIN_BATCH_COOLDOWN_SECONDS,
        "batch_reports": batch_reports,
        "ah_market_marker_signatures": dict(sorted(aggregate.items())),
        "fixture_shape_counts": dict(sorted(fixture_shape_counts.items())),
        "by_universe_marker_signatures": {u: dict(sorted(c.items())) for u, c in universe_counts.items()},
        "samples": samples,
        "interpretation_guardrail": "Diagnostic only. This probe must not select alternative lines, rewrite historical main lines, alter frozen candidate thresholds, or retroactively change the preregistered both-sides-mainLine=true admissibility rule.",
        "paper_research_only": True,
        "promotion_allowed": False,
    }
    return _write(root, payload)


def _write(root: Path, payload: dict) -> dict:
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(probe_from_env(), ensure_ascii=False))
