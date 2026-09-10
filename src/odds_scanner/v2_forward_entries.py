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
        "entry_policy": "FIRST_QUALIFYING_SCHEDULED_OBSERVATION_AFTER_PREREGISTRATION",
        "stake_units": 1.0,
        "paper_label": "PAPER_RESEARCH_ONLY",
        "production_eligible": False,
    }


def build_forward_entries(root: Path = Path(".")) -> dict:
    generated_at = datetime.now(timezone.utc)
    prereg = _load_json(root / PREREG_PATH)
    catalog = _load_json(root / CANDIDATE_PATH)
    if not isinstance(prereg, dict) or not isinstance(catalog, dict):
        payload = {
            "schema_version": "1.0",
            "status": "FROZEN_INPUT_UNAVAILABLE",
            "generated_at": generated_at.isoformat(),
            "production_promotion_allowed": False,
        }
        return _write_report(root, payload)

    locked_at = _utc(prereg.get("created_at"))
    frozen_ids = prereg.get("candidate_ids") or []
    candidates = catalog.get("candidates") or []
    catalog_ids = [str(c.get("pattern_id")) for c in candidates if isinstance(c, dict)]
    if locked_at is None or len(frozen_ids) != 3 or set(map(str, frozen_ids)) != set(catalog_ids):
        payload = {
            "schema_version": "1.0",
            "status": "PREREGISTRATION_DRIFT",
            "generated_at": generated_at.isoformat(),
            "production_promotion_allowed": False,
        }
        return _write_report(root, payload)

    existing = _load_jsonl(root / ENTRIES_PATH)
    by_key: dict[tuple[str, str], dict] = {}
    for row in existing:
        key = (str(row.get("candidate_id")), str(row.get("fixture_id")))
        if key[0] and key[1] and key not in by_key:
            by_key[key] = row

    snapshots = _load_jsonl(root / SNAPSHOTS_PATH)
    admissible = []
    for snap in snapshots:
        observed_at = _utc(snap.get("observed_at"))
        kickoff = _utc(snap.get("kickoff"))
        if observed_at is None or kickoff is None:
            continue
        if observed_at <= locked_at or observed_at >= kickoff:
            continue
        if snap.get("mainline_verified") is not True:
            continue
        admissible.append(snap)
    admissible.sort(key=lambda r: (_utc(r.get("observed_at")) or datetime.max.replace(tzinfo=timezone.utc), str(r.get("fixture_id"))))

    added = 0
    for snap in admissible:
        for candidate_id in match_candidates(snap, candidates):
            key = (candidate_id, str(snap.get("fixture_id")))
            if key in by_key:
                continue
            by_key[key] = _entry_from_snapshot(snap, candidate_id)
            added += 1

    ordered = sorted(
        by_key.values(),
        key=lambda r: (str(r.get("entry_observed_at")), str(r.get("candidate_id")), str(r.get("fixture_id"))),
    )
    entries_path = root / ENTRIES_PATH
    entries_path.parent.mkdir(parents=True, exist_ok=True)
    entries_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in ordered),
        encoding="utf-8",
    )

    counts = Counter(str(r.get("candidate_id")) for r in ordered)
    payload = {
        "schema_version": "1.0",
        "classification": "VALIDATION_V2_FORWARD_ENTRY_LEDGER_STATUS",
        "status": "COLLECTING_FORWARD_EVIDENCE",
        "generated_at": generated_at.isoformat(),
        "preregistration_created_at": prereg.get("created_at"),
        "snapshots_seen": len(snapshots),
        "admissible_post_prereg_snapshots": len(admissible),
        "entries_total": len(ordered),
        "entries_added_this_run": added,
        "entries_by_candidate": {str(cid): int(counts.get(str(cid), 0)) for cid in frozen_ids},
        "entry_policy": "FIRST_QUALIFYING_SCHEDULED_OBSERVATION_AFTER_PREREGISTRATION",
        "existing_entries_are_immutable": True,
        "production_promotion_allowed": False,
    }
    return _write_report(root, payload)


def _write_report(root: Path, payload: dict) -> dict:
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_forward_entries(), ensure_ascii=False))
