"""Offline, read-only inventory of legacy and sharded historical odds by tournament.

Run: python scripts/audit_league_archive.py
Never infers tournament IDs from league names, and never deletes source rows.
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWN_BIG5 = {8: "LaLiga", 17: "Premier League", 23: "Serie A", 34: "Ligue 1", 35: "Bundesliga"}
FILES = [ROOT / "data/normalized/oddspapi_history_ticks.jsonl"]
FILES += sorted((ROOT / "data/normalized/oddspapi_history_ticks").rglob("*.jsonl"))

def inventory():
    counts = Counter()
    unknown = Counter()
    review_fixtures = []
    seen = set()
    errors = []
    for path in FILES:
        if not path.is_file():
            continue
        with path.open(encoding="utf-8") as stream:
            for lineno, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"{path.relative_to(ROOT)}:{lineno}:invalid_json")
                    continue
                fid = str(row.get("fixture_id") or "")
                raw_id = row.get("tournament_id")
                try:
                    tid = int(raw_id)
                except (TypeError, ValueError):
                    tid = None
                label = row.get("league") or "UNKNOWN"
                bucket = "KEEP_BIG5" if tid in KNOWN_BIG5 else "REVIEW_UNKNOWN_ID"
                counts[(bucket, str(raw_id), str(label))] += 1
                if bucket != "KEEP_BIG5":
                    unknown[(str(raw_id), str(label))] += 1
                    review_fixtures.append({"fixture_id": fid, "tournament_id": raw_id, "league": label, "kickoff": row.get("kickoff"), "home": row.get("home"), "away": row.get("away"), "source": str(path.relative_to(ROOT))})
                if fid:
                    seen.add(fid)
    result_path = ROOT / "data/normalized/oddspapi_finished_results.jsonl"
    result_ids = set()
    if result_path.exists():
        with result_path.open(encoding="utf-8") as stream:
            for lineno, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    result = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"{result_path.relative_to(ROOT)}:{lineno}:invalid_json")
                    continue
                if isinstance(result, dict) and result.get("fixture_id") is not None:
                    result_ids.add(str(result["fixture_id"]))
    return {"schema_version": "1.1", "mode": "READ_ONLY_NO_DELETION",
            "results_total_unique": len(result_ids),
            "results_joinable_to_archive": len(result_ids & seen),
            "results_not_in_archive": len(result_ids - seen),
            "warning": "Results outside archived fixtures have no tournament ID in this cache; do not delete without a verified fixture-to-tournament mapping.",
            "total_rows": sum(counts.values()), "unique_fixture_ids": len(seen),
            "league_breakdown": [{"decision": k[0], "tournament_id": k[1], "league": k[2], "rows": n}
                                 for k, n in sorted(counts.items())],
            "unclassified_rows": sum(unknown.values()),
            "review_fixtures": review_fixtures, "errors": errors}

if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2, ensure_ascii=False))
