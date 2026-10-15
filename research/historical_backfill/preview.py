"""Offline historical AH backfill preview. Reads a local JSON file only.

Usage:
  python -m research.historical_backfill.preview --input /path/to/sample.json
No network, no writes, no production imports. Input must be a JSON list of AH records.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.historical_backfill.reconstruct import reconstruct_slot, parse_time
from research.historical_backfill.validate import validate_ah_record

BANGKOK = ZoneInfo("Asia/Bangkok")
SLOT_HOURS = (0, 15, 18, 21)


def slots_for_fixture(kickoff: str, days_back: int = 2) -> list[str]:
    if days_back < 0 or days_back > 30:
        raise ValueError("days_back must be 0..30")
    local_kickoff = parse_time(kickoff).astimezone(BANGKOK)
    start = local_kickoff.date() - timedelta(days=days_back)
    result = []
    for i in range(days_back + 1):
        day = start + timedelta(days=i)
        for hour in SLOT_HOURS:
            local = datetime(day.year, day.month, day.day, hour, tzinfo=BANGKOK)
            if local < local_kickoff:
                result.append(local.isoformat())
    return result


def preview(records: list[dict], max_age_seconds: int = 3600) -> dict:
    if not isinstance(records, list):
        raise ValueError("input must be an array")
    summary = Counter()
    fixture_ids = set()
    for record in records:
        item = validate_ah_record(record)
        fixture_ids.add((item["source"], item["fixture_id"]))
        for slot in slots_for_fixture(item["kickoff_utc"]):
            result = reconstruct_slot(
                fixture_id=item["fixture_id"], kickoff=item["kickoff_utc"], slot=slot,
                source=item["source"], bookmaker=item["bookmaker"], market="AH",
                line=item["line"], selections={
                    "home": item["home_ticks"], "away": item["away_ticks"]
                }, max_age_seconds=max_age_seconds,
            )
            summary[result["status"]] += 1
    return {
        "mode": "OFFLINE_DRY_RUN",
        "source_rows": len(records),
        "distinct_source_fixtures": len(fixture_ids),
        "slots_evaluated": sum(summary.values()),
        "complete": summary["COMPLETE"],
        "missing": summary["NO_HISTORICAL_DATA"],
        "writes": 0,
        "api_requests": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="local JSON array, never a URL")
    parser.add_argument("--max-age-seconds", type=int, default=3600)
    args = parser.parse_args()
    if "://" in args.input:
        parser.error("URL inputs prohibited")
    with open(args.input, encoding="utf-8") as stream:
        records = json.load(stream)
    print(json.dumps(preview(records, args.max_age_seconds), indent=2))


if __name__ == "__main__":
    main()
