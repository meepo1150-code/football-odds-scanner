"""Unified AH observation upsert for current and reconstructed historical quotes.

Never changes original provider rows. Both sources contribute to one canonical
slot view; a reconstructed quote replaces a current quote for an identical
fixture/bookmaker/market/slot key, as explicitly requested.
"""
import json
from pathlib import Path

HISTORICAL = Path("data/historical/reconstructed_ah_slots.jsonl")
UNIFIED = Path("data/normalized/unified_ah_observations.jsonl")


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def key(row):
    return (str(row["fixture_id"]), str(row["bookmaker"]).lower(),
            str(row["market"]).upper(), str(row["slot_utc"]))


def merge(live, historical):
    index = {}
    for row in live:
        k = key(row)
        if k in index and index[k] != row:
            raise ValueError("Conflicting duplicate live AH slot")
        index[k] = row
    for row in historical:
        if row.get("line_selection") != "BALANCED_LINE":
            raise ValueError("Historical quote not reviewed")
        if row.get("provenance") != "HISTORICAL_RECONSTRUCTED":
            raise ValueError("Historical provenance missing")
        if row.get("mainline_verified") is not False:
            raise ValueError("Historical mainline must not be fabricated")
        if row.get("market") != "AH":
            raise ValueError("Unexpected historical market")
        q = row.get("quotes", {})
        if not all(isinstance(q.get(side), dict) and
                   q[side].get("quote_at_utc") and
                   isinstance(q[side].get("price"), (int, float)) and
                   q[side]["price"] > 1 for side in ("home", "away")):
            raise ValueError("Missing provider quote or timestamp")
        # Explicit historical precedence for the identical slot, while
        # retaining the previous value in the source files.
        index[key(row)] = row
    return [index[k] for k in sorted(index)]


def build(root=Path(".")):
    live_path = root / "data/normalized/live_ah_observations.jsonl"
    historical_path = root / HISTORICAL
    live = read_jsonl(live_path)
    historical = read_jsonl(historical_path)
    combined = merge(live, historical)
    target = root / UNIFIED
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n"
                              for x in combined))
    return {"live_rows": len(live), "historical_rows": len(historical),
            "unified_rows": len(combined), "source_live_present": live_path.exists()}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
