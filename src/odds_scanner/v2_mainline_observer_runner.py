from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Callable

from . import v2_mainline_observer as observer
from .oddspapi_discovery import _rows
from .oddspapi_fixture_refs import normalize_fixture_ref
from .oddspapi_provider import _get as raw_get
from .v2_ah_marker_probe import ah_marker_shape

ODDS_BATCH_MIN_COOLDOWN_SECONDS = 1.25


def make_paced_get(
    delegate: Callable,
    *,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    minimum_cooldown_seconds: float = ODDS_BATCH_MIN_COOLDOWN_SECONDS,
    exact_refs: dict[str, dict] | None = None,
    captured_fixtures: list[dict] | None = None,
):
    """Pace repeated /odds-by-tournaments calls and preserve same-response evidence.

    OddsPapi documents a 1000ms endpoint cooldown. We use 1.25s to leave a
    deterministic safety margin without adding any request or retry. Exact
    external provider IDs and optional marker diagnostics are captured only from
    the same current payload already fetched by the observer.
    """
    last_finished: float | None = None

    def paced(path: str, key: str, params: dict | None = None, timeout: int = 20):
        nonlocal last_finished
        if path == "/odds-by-tournaments" and last_finished is not None:
            remaining = minimum_cooldown_seconds - (clock() - last_finished)
            if remaining > 0:
                sleeper(remaining)
        try:
            payload = delegate(path, key, params, timeout)
            if path == "/odds-by-tournaments":
                fixtures = _rows(payload)
                if captured_fixtures is not None:
                    captured_fixtures.extend(x for x in fixtures if isinstance(x, dict))
                if exact_refs is not None:
                    for fixture in fixtures:
                        ref = normalize_fixture_ref(fixture)
                        if ref:
                            exact_refs[str(ref["fixture_id"])] = ref
            return payload
        finally:
            if path == "/odds-by-tournaments":
                last_finished = clock()

    return paced


def summarize_ah_markers(fixtures: list[dict], catalog: list[dict], *, sample_limit: int = 20) -> dict:
    """Summarize AH player-level mainLine markers without selecting any line."""
    aggregate: Counter[str] = Counter()
    fixture_shapes: Counter[str] = Counter()
    samples: list[dict] = []
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            continue
        shape = ah_marker_shape(fixture, catalog)
        for signature, count in (shape.get("signatures") or {}).items():
            aggregate[str(signature)] += int(count)
        fixture_key = f"AH_MARKETS_{int(shape.get('ah_markets') or 0)}__BOTH_TRUE_{len(shape.get('both_true_lines') or [])}"
        fixture_shapes[fixture_key] += 1
        if len(samples) < sample_limit and int(shape.get("ah_markets") or 0) > 0:
            samples.append({
                "fixture_id": fixture.get("fixtureId"),
                "tournament_id": fixture.get("tournamentId"),
                "start_time": fixture.get("startTime"),
                "ah_markets": shape.get("ah_markets"),
                "signatures": shape.get("signatures"),
                "both_true_lines": shape.get("both_true_lines"),
            })
    return {
        "ah_market_marker_signatures": dict(sorted(aggregate.items())),
        "ah_fixture_shape_counts": dict(sorted(fixture_shapes.items())),
        "ah_marker_samples": samples,
    }


def _enrich_current_snapshots(exact_refs: dict[str, dict], observed_at: str | None) -> int:
    """Attach exact provider IDs only to snapshots created by this observer run."""
    path = observer.SNAPSHOTS_PATH
    if not path.exists() or not observed_at or not exact_refs:
        return 0
    rows: list[dict] = []
    changed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("observed_at") == observed_at:
            ref = exact_refs.get(str(row.get("fixture_id") or ""))
            external = ref.get("external_providers") if isinstance(ref, dict) else None
            if isinstance(external, dict) and external:
                row["external_providers"] = external
                row["external_provider_mapping_source"] = "ODDSPAPI_CURRENT_EXTERNALPROVIDERS_EXACT_IDS"
                changed += 1
        rows.append(row)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )
    return changed


def observe_with_rate_limit_safety():
    original = observer._get
    exact_refs: dict[str, dict] = {}
    captured_fixtures: list[dict] = []
    observer._get = make_paced_get(raw_get, exact_refs=exact_refs, captured_fixtures=captured_fixtures)
    try:
        report = observer.observe_from_env()
        if isinstance(report, dict):
            enriched = _enrich_current_snapshots(exact_refs, report.get("observed_at"))
            catalog = observer._load_json(observer.CATALOG_PATH)
            marker_report = summarize_ah_markers(captured_fixtures, catalog if isinstance(catalog, list) else [])
            report["odds_batch_min_cooldown_seconds"] = ODDS_BATCH_MIN_COOLDOWN_SECONDS
            report["odds_batch_rate_limit_policy"] = "WAIT_AFTER_PREVIOUS_ODDS_BY_TOURNAMENTS_COMPLETES_NO_AUTOMATIC_RETRY"
            report["exact_external_fixture_ids_seen"] = len(exact_refs)
            report["strict_snapshots_enriched_with_exact_external_ids"] = enriched
            report["external_id_policy"] = "CURRENT_ODDSPAPI_EXTERNALPROVIDERS_EXACT_IDS_ONLY_NO_NAME_MATCHING"
            report.update(marker_report)
            report["ah_marker_diagnostics_policy"] = "SAME_CURRENT_PAYLOAD_ONLY_DIAGNOSTIC_NO_LINE_SELECTION_NO_ADMISSIBILITY_CHANGE"
            path = observer.REPORT_PATH
            if path.exists():
                path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        observer._get = original


if __name__ == "__main__":
    print(json.dumps(observe_with_rate_limit_safety(), ensure_ascii=False))
