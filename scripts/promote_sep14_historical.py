"""Promote reviewed Sep-14 Historical AH quotes into canonical Research V2 snapshots.

No HTTP requests. Historical slot != bookmaker quote timestamp.
The old canonical file remains recoverable from Git and the workflow backup artifact.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

DAY = "2026-09-14"
SOURCE = Path("data/normalized/europe_pinnacle_research_v2_snapshots.jsonl")
RECEIPT = Path("reports/sep14_historical_promotion.json")
BKK = ZoneInfo("Asia/Bangkok")
ALLOWED_SLOTS = {
    "2026-09-14T08:00:00+00:00",
    "2026-09-14T11:00:00+00:00",
    "2026-09-14T14:00:00+00:00",
    "2026-09-14T17:00:00+00:00",
}

def dt(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone required: " + str(value))
    return parsed

def football_day(kickoff):
    local = dt(kickoff).astimezone(BKK)
    if local.hour < 6:
        local -= timedelta(days=1)
    return local.date().isoformat()

def jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]

def plan(report, manifest, originals):
    if report.get("status") != "COMPLETED" or report.get("errors") or report.get("production_writes") != 0:
        raise ValueError("Research artifact is not a clean completed run")
    candidates = manifest.get("candidates", [])
    if len(candidates) != 21 or len(report.get("results", [])) != 21:
        raise ValueError("Unexpected historical candidate population")
    by_id = {c["fixture_id"]: c for c in candidates}
    if len(by_id) != 21:
        raise ValueError("Duplicate manifest fixture IDs")
    eligible = {fid: c for fid, c in by_id.items() if football_day(c["kickoff"]) == DAY}
    if len(eligible) != 20:
        raise ValueError("Expected exactly 20 verified football-day fixtures")
    historical = {r["fixture_id"]: r for r in report["results"]}
    if set(historical) != set(by_id):
        raise ValueError("Report and manifest fixture IDs differ")
    old = defaultdict(list)
    for row in originals:
        if str(row.get("fixture_id")) in eligible and row.get("football_day") == DAY:
            old[str(row["fixture_id"])].append(row)
    if set(old) != set(eligible):
        raise ValueError("Missing original canonical fixture evidence: " + repr(sorted(set(eligible)-set(old))))
    generated = []
    slot_counts = Counter()
    for fid, c in sorted(eligible.items()):
        identities = {(x.get("home"), x.get("away"), x.get("kickoff"), x.get("league")) for x in old[fid]}
        expected = (c["home"], c["away"], c["kickoff"], c["league"])
        if identities != {expected}:
            raise ValueError("Identity conflict: " + fid)
        base = old[fid][-1]
        if str(base.get("bookmaker")).lower() != str(c.get("bookmaker")).lower():
            raise ValueError("Bookmaker mismatch: " + fid)
        slots = historical[fid].get("slots", [])
        if len(slots) != 4 or {s["slot_utc"] for s in slots} != ALLOWED_SLOTS:
            raise ValueError("Unexpected slot manifest: " + fid)
        for slot in slots:
            if slot.get("status") != "BALANCED_LINE":
                slot_counts[str(slot.get("status"))] += 1
                continue
            selected = slot.get("selected") or {}
            quotes = selected.get("quotes") or {}
            home, away = quotes.get("home") or {}, quotes.get("away") or {}
            line = float(selected["line"])
            hp, ap = float(home["price"]), float(away["price"])
            ht, at = dt(home["quote_at_utc"]), dt(away["quote_at_utc"])
            slot_time, kickoff = dt(slot["slot_utc"]), dt(c["kickoff"])
            if (selected.get("status") != "COMPLETE" or
                selected.get("fixture_id") != fid or
                selected.get("bookmaker") != c["bookmaker"] or
                selected.get("line_selection") != "BALANCED_LINE" or
                slot.get("official_mainline_verified") is not False or
                any(q.get("active") is not True for q in (home, away)) or
                abs(line * 4 - round(line * 4)) > 1e-8 or
                not (1.80 <= hp <= 2.20 and 1.80 <= ap <= 2.20) or
                not (ht <= slot_time and at <= slot_time and slot_time < kickoff)):
                raise ValueError("Untrusted selected quote: " + fid + " " + slot["slot_utc"])
            fav = base.get("favorite_side")
            if fav not in ("H", "A"):
                raise ValueError("Unknown favorite side: " + fid)
            # A bookmaker quote timestamp is evidence of a PRICE CHANGE, not
            # evidence that a collector observed the market at the target slot.
            row = dict(base)
            row.update({
                "provider": "oddspapi",
                "observed_at": max(ht, at).isoformat(),
                "scheduled_target_at": slot["slot_utc"],
                "source_semantics": "HISTORICAL_BALANCED_LINE_AS_OF_SLOT",
                "mainline_verified": False,
                "historical_target_slot_at": slot["slot_utc"],
                "historical_quote_home_at": ht.isoformat(),
                "historical_quote_away_at": at.isoformat(),
                "historical_provenance": "ODDSPAPI_RECONSTRUCTED_FROM_RUN_38860129483",
                "historical_market_id": selected.get("market_id"),
                "research_only": True,
                # No time-aligned historical 1X2 or OU was recovered.
                "one_x_two": {},
                "ou": {},
                "favorite_fair_probability": None,
                "ah": {
                    "home_line": line, "away_line": -line,
                    "home_price": hp, "away_price": ap,
                    "selected_side_line": line if fav == "H" else -line,
                    "selected_side_price": hp if fav == "H" else ap,
                    "opposite_side_price": ap if fav == "H" else hp,
                },
            })
            generated.append(row)
            slot_counts["BALANCED_LINE"] += 1
    if slot_counts["BALANCED_LINE"] != 52 or len(generated) != 52:
        raise ValueError("Expected exactly 52 verified balanced slots")
    retained = [x for x in originals if not (str(x.get("fixture_id")) in eligible and x.get("football_day") == DAY)]
    before = len(originals) - len(retained)
    if before < 20:
        raise ValueError("Unexpectedly small original snapshot cohort")
    receipt = {
        "date": DAY, "source_run": 38860129483,
        "verified_football_day_fixtures": len(eligible),
        "promoted_fixture_ids": sorted(eligible),
        "excluded_out_of_day_fixture_ids": sorted(set(by_id)-set(eligible)),
        "replaced_original_rows": before,
        "historical_balanced_slots": len(generated),
        "slot_status_counts": dict(slot_counts),
        "original_snapshot_sha256": hashlib.sha256(
            "".join(json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n" for x in originals).encode()
        ).hexdigest(),
        "formula_changed": False, "historical_api_requests": 0,
        "official_mainline_claimed": False,
    }
    return retained + generated, receipt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--root", default=".", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = args.root
    source = root / SOURCE
    original_bytes = source.read_bytes()
    with __import__("zipfile").ZipFile(args.artifact) as z:
        report = json.loads(z.read("sep14/results/report.json"))
        manifest = json.loads(z.read("sep14/manifest.json"))
    rows, receipt = plan(report, manifest, jsonl(source))
    receipt["original_file_sha256"] = hashlib.sha256(original_bytes).hexdigest()
    receipt["promoted_snapshot_rows"] = len(rows)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    if not args.dry_run:
        ids = set(receipt["promoted_fixture_ids"])
        kept_lines = [line for line in original_bytes.decode("utf-8").splitlines(keepends=True)
                      if not (str(json.loads(line).get("fixture_id")) in ids and
                              json.loads(line).get("football_day") == DAY)]
        if len(kept_lines) != len(rows) - 52:
            raise ValueError("Original-line preservation mismatch")
        new_lines = [json.dumps(x, ensure_ascii=False, separators=(",", ":")) + "\n" for x in rows[-52:]]
        source.write_text("".join(kept_lines + new_lines), encoding="utf-8")
        target = root / RECEIPT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
