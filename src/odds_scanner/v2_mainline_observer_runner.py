from __future__ import annotations

import json
import time
from collections.abc import Callable

from . import v2_mainline_observer as observer
from .oddspapi_discovery import _rows
from .oddspapi_fixture_refs import normalize_fixture_ref
from .oddspapi_provider import _get as raw_get

ODDS_BATCH_MIN_COOLDOWN_SECONDS = 1.25


def make_paced_get(
    delegate: Callable,
    *,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    minimum_cooldown_seconds: float = ODDS_BATCH_MIN_COOLDOWN_SECONDS,
    exact_refs: dict[str, dict] | None = None,
):
    """Pace repeated /odds-by-tournaments calls and optionally preserve exact IDs.

    OddsPapi documents a 1000ms endpoint cooldown. We use 1.25s to leave a
    deterministic safety margin without adding any request or retry. When
    ``exact_refs`` is supplied, exact external provider fixture IDs already
    present in the current payload are retained as identity metadata only.
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
            if path == "/odds-by-tournaments" and exact_refs is not None:
                for fixture in _rows(payload):
                    ref = normalize_fixture_ref(fixture)
                    if ref:
                        exact_refs[str(ref["fixture_id"])] = ref
            return payload
        finally:
            if path == "/odds-by-tournaments":
                last_finished = clock()

    return paced


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
    observer._get = make_paced_get(raw_get, exact_refs=exact_refs)
    try:
        report = observer.observe_from_env()
        if isinstance(report, dict):
            enriched = _enrich_current_snapshots(exact_refs, report.get("observed_at"))
            report["odds_batch_min_cooldown_seconds"] = ODDS_BATCH_MIN_COOLDOWN_SECONDS
            report["odds_batch_rate_limit_policy"] = "WAIT_AFTER_PREVIOUS_ODDS_BY_TOURNAMENTS_COMPLETES_NO_AUTOMATIC_RETRY"
            report["exact_external_fixture_ids_seen"] = len(exact_refs)
            report["strict_snapshots_enriched_with_exact_external_ids"] = enriched
            report["external_id_policy"] = "CURRENT_ODDSPAPI_EXTERNALPROVIDERS_EXACT_IDS_ONLY_NO_NAME_MATCHING"
            path = observer.REPORT_PATH
            if path.exists():
                path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        observer._get = original


if __name__ == "__main__":
    print(json.dumps(observe_with_rate_limit_safety(), ensure_ascii=False))
