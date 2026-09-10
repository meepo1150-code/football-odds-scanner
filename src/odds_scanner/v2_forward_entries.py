from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .v2_mainline_observer import match_candidates

PREREG_PATH = Path("reports/v2_forward_preregistration.json")
CANDIDATE_PATH = Path("reports/v2_research_candidates.json")
SNAPSHOTS_PATH = Path("data/normalized/v2_mainline_snapshots.jsonl")
ENTRIES_PATH = Path("data/normalized/v2_forward_entries.jsonl")
REPORT_PATH = Path("reports/v2_forward_entry_status.json")


def _load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _forward_start(prereg: dict) -> datetime | None:
    # The cadence amendment supersedes the original preregistration timestamp.
    # Requiring amended_at prevents engineering observations made before the
    # 12-hour split-batch policy was frozen from becoming entries.
    return _utc(prereg.get("amended_at"))


def _entry_from_snapshot(snapshot: dict, candidate_id: str) -> dict:
    market = "OU" if candidate_id.startswith("FD_OU") else "AH"
    if market == "AH":
        selection = snapshot.get("favorite_side")
        line = (snapshot.get("ah") or {}).get("selected_side_line")
        price = (snapshot.get("ah") or {}).get("selected_side_price")
    else:
        selection = "U"
        line = (snapshot.get("ou") or {}).get("line")
        price = (snapshot.get("ou") or {}).get("under_price")
    return {
        "candidate_id": candidate_id,
        "fixture_id": snapshot.get("fixture_id"),
        "universe": snapshot.get("universe"),
        "league": snapshot.get("league"),
        "country": snapshot.get("country"),
        "kickoff": snapshot.get("kickoff"),
        "home": snapshot.get("home"),
        "away": snapshot.get("away"),
        "bookmaker": snapshot.get("bookmaker"),
        "entry_observed_at": snapshot.get("observed_at"),
        "entry_source_semantics": snapshot.get("source_semantics"),
        "mainline_verified": snapshot.get("mainline_verified") is True,
        "market": market,
        "selection": selection,
        "entry_line": line,
        "entry_price": price,
        "favorite_side": snapshot.get("favorite_side"),
        "favorite_fair_probability": snapshot.get("favorite_fair_probability"),
        "entry_policy": "FIRST_QUALIFYING_SCHEDULED_OBSERVATION_AFTER_AMENDED_PREREGISTRATION",
        "stake_units": 1.0,
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_eligible": False,
    }


def build_forward_entries(root: Path = Path(".")) -> dict:
    generated_at = datetime.now(timezone.utc)
    prereg = _load_json(root / PREREG_PATH)
    catalog = _load_json(root / CANDIDATE_PATH)
    if not isinstance(prereg, dict) or not isinstance(catalog, dict):
        return _write_report(root, {
            "schema_version": "1.1",
            "status": "FROZEN_INPUT_UNAVAILABLE",
            "generated_at": generated_at.isoformat(),
            "production_promotion_allowed": False,
        })

    forward_start = _forward_start(prereg)
    frozen_ids = [str(x) for x in (prereg.get("candidate_ids") or [])]
    candidates = [c for c in (catalog.get("candidates") or []) if isinstance(c, dict)]
    catalog_ids = [str(c.get("pattern_id")) for c in candidates]
    collection = prereg.get("collection_policy") or {}
    if (
        forward_start is None
        or prereg.get("classification") != "VALIDATION_V2_FORWARD_PAPER_PREREGISTRATION"
        or prereg.get("paper_label") != "PAPER_RESEARCH_ONLY"
        or collection.get("scheduled_cadence_hours") != 12
        or collection.get("scheduled_runs_per_day") != 2
        or len(frozen_ids) != 3
        or set(frozen_ids) != set(catalog_ids)
    ):
        return _write_report(root, {
            "schema_version": "1.1",
            "status": "PREREGISTRATION_DRIFT",
            "generated_at": generated_at.isoformat(),
            "production_promotion_allowed": False,
        })

    existing = _load_jsonl(root / ENTRIES_PATH)
    by_key: dict[tuple[str, str], dict] = {}
    duplicate_existing = 0
    for row in existing:
        key = (str(row.get("candidate_id") or ""), str(row.get("fixture_id") or ""))
        if not all(key):
            continue
        if key in by_key:
            duplicate_existing += 1
            continue
        # Existing entries are immutable. Never rebuild them from newer snapshots.
        by_key[key] = row

    snapshots = _load_jsonl(root / SNAPSHOTS_PATH)
    admissible: list[dict] = []
    for snap in snapshots:
        observed_at = _utc(snap.get("observed_at"))
        kickoff = _utc(snap.get("kickoff"))
        if observed_at is None or kickoff is None:
            continue
        if observed_at < forward_start or observed_at >= kickoff:
            continue
        if snap.get("mainline_verified") is not True:
            continue
        if snap.get("source_semantics") != "CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED":
            continue
        admissible.append(snap)
    admissible.sort(key=lambda r: (
        _utc(r.get("observed_at")) or datetime.max.replace(tzinfo=timezone.utc),
        str(r.get("fixture_id") or ""),
    ))

    added = 0
    for snap in admissible:
        for candidate_id in match_candidates(snap, candidates):
            key = (str(candidate_id), str(snap.get("fixture_id") or ""))
            if not key[1] or key in by_key:
                continue
            by_key[key] = _entry_from_snapshot(snap, str(candidate_id))
            added += 1

    ordered = sorted(by_key.values(), key=lambda r: (
        str(r.get("entry_observed_at") or ""),
        str(r.get("candidate_id") or ""),
        str(r.get("fixture_id") or ""),
    ))
    entries_path = root / ENTRIES_PATH
    entries_path.parent.mkdir(parents=True, exist_ok=True)
    entries_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in ordered),
        encoding="utf-8",
    )

    counts = Counter(str(r.get("candidate_id")) for r in ordered)
    return _write_report(root, {
        "schema_version": "1.1",
        "classification": "VALIDATION_V2_FORWARD_ENTRY_LEDGER_STATUS",
        "status": "COLLECTING_FORWARD_EVIDENCE",
        "generated_at": generated_at.isoformat(),
        "forward_start": prereg.get("amended_at"),
        "snapshots_seen": len(snapshots),
        "admissible_post_amendment_snapshots": len(admissible),
        "entries_total": len(ordered),
        "entries_added_this_run": added,
        "entries_by_candidate": {cid: int(counts.get(cid, 0)) for cid in frozen_ids},
        "duplicate_existing_rows_ignored": duplicate_existing,
        "entry_policy": "FIRST_QUALIFYING_SCHEDULED_OBSERVATION_AFTER_AMENDED_PREREGISTRATION",
        "existing_entries_are_immutable": True,
        "retroactive_entry_creation_allowed": False,
        "better_price_reselection_allowed": False,
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_promotion_allowed": False,
    })


def _write_report(root: Path, payload: dict) -> dict:
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_forward_entries(), ensure_ascii=False))
