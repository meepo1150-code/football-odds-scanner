"""Import reviewed historical recovery slots into an isolated, provenance-preserving dataset.

Usage: python scripts/import_historical_artifact.py artifact.zip
Does not call the odds provider or alter live snapshots.
"""
import argparse
import json
import zipfile
from collections import Counter
from pathlib import Path

OUTPUT = Path("data/historical/reconstructed_ah_slots.jsonl")
SOURCE_RUN = "38901047977"
KEY_FIELDS = ("fixture_id", "bookmaker", "slot_utc", "market")


def import_artifact(archive, output=OUTPUT):
    with zipfile.ZipFile(archive) as z:
        report = json.loads(z.read("report.json"))
        manifest = json.loads(z.read("manifest.json"))
    if report.get("status") != "COMPLETED" or report.get("errors"):
        raise ValueError("Historical report is not clean")
    if report.get("production_writes") != 0 or report.get("research_only") is not True:
        raise ValueError("Unexpected historical artifact origin")
    if manifest.get("requested_target_slots") != 348 or manifest.get("unique_fixtures") != 61:
        raise ValueError("Unexpected source manifest; review before import")
    incoming = {}
    statuses = Counter()
    for fixture in report["results"]:
        for slot in fixture["slots"]:
            statuses[slot["status"]] += 1
            if slot["status"] != "BALANCED_LINE":
                continue
            selected = slot["selected"]
            if not selected or selected.get("official_mainline_verified") is not False:
                raise ValueError("Selected historical line provenance mismatch")
            if selected.get("line_selection") != "BALANCED_LINE" or selected.get("market") != "AH":
                raise ValueError("Unsupported selection")
            quotes = selected["quotes"]
            for side in ("home", "away"):
                quote = quotes[side]
                if quote.get("active") is not True or not 1.8 <= float(quote["price"]) <= 2.2:
                    raise ValueError("Historical price gate failed")
                if not quote.get("quote_at_utc"):
                    raise ValueError("Missing provider quote timestamp")
            row = {
                **selected,
                "source_run_id": SOURCE_RUN,
                "target_thai": slot["target_thai"],
                "target_utc": slot["target_utc"],
                "timestamp_basis": slot["timestamp_basis"],
                "mainline_verified": False,
                "promotion_eligible": False,
            }
            key = tuple(row[field] for field in KEY_FIELDS)
            if key in incoming and incoming[key] != row:
                raise ValueError("Conflicting duplicate within artifact")
            incoming[key] = row
    if statuses != Counter({"BALANCED_LINE": 105, "MAINLINE_UNRESOLVED": 163, "NOT_PREMATCH_SLOT": 80}):
        raise ValueError(f"Unexpected slot counts: {statuses}")
    existing = {}
    if output.exists():
        for line in output.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = tuple(row[field] for field in KEY_FIELDS)
            if key in existing and existing[key] != row:
                raise ValueError("Conflicting existing dataset duplicates")
            existing[key] = row
    added = replaced = unchanged = 0
    for key, row in incoming.items():
        if key not in existing:
            added += 1
        elif existing[key] == row:
            unchanged += 1
        else:
            # Only replace a prior reconstruction from the SAME source run.
            if existing[key].get("source_run_id") != SOURCE_RUN:
                raise ValueError("Refusing to overwrite a different provenance")
            replaced += 1
        existing[key] = row
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\\n" for _, row in sorted(existing.items())))
    return {"source_run_id": SOURCE_RUN, "slot_statuses": dict(statuses),
            "added": added, "replaced": replaced, "unchanged": unchanged,
            "historical_rows_total": len(existing), "live_snapshots_modified": 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(import_artifact(args.artifact, args.output), indent=2))


if __name__ == "__main__":
    main()
