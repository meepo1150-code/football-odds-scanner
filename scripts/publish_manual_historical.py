"""Import completed manual historical odds into Research V2 without modifying live observations.

Usage: python scripts/publish_manual_historical.py --artifact-dir research/manual_historical/output
No provider requests. Historical rows retain source/provenance and are never promoted to official mainline.
"""
import argparse
import json
import math
from collections import Counter
from pathlib import Path

from odds_scanner.historical_manual.planner import stamp
from odds_scanner.research_v2_pattern_stats import _rows, SNAPSHOTS

RECEIPT = Path("reports/manual_historical_promotion_latest.json")
VALID = "BALANCED_LINE"

def _identity(r):
    return str(r.get("fixture_id")), str(r.get("bookmaker", "")).lower()

def _slot(row):
    value = row.get("historical_target_slot_at")
    if value is None:
        return None
    return stamp(value).isoformat()

def _key(row):
    return (*_identity(row), _slot(row))

def _validate(report, manifest):
    if report.get("status") != "COMPLETED" or report.get("errors"):
        raise ValueError("SCAN_NOT_COMPLETED")
    if report.get("production_writes") != 0 or report.get("research_only") is not True:
        raise ValueError("UNTRUSTED_REPORT_ORIGIN")
    if manifest.get("scope") not in {"VERIFIED_NATIVE_SNAPSHOT_FIXTURES_ONLY", "VERIFIED_NATIVE_OR_EXTERNAL_ODDSPAPI_FIXTURES"}:
        raise ValueError("UNTRUSTED_MANIFEST_SCOPE")
    candidates = {}
    for c in manifest["candidates"]:
        key = _identity(c)
        if key in candidates:
            raise ValueError("DUPLICATE_CANDIDATE")
        candidates[key] = c
    if len(candidates) != len(report["results"]):
        raise ValueError("INCOMPLETE_RESULT_SET")
    return candidates

def produce(report, manifest, original):
    candidates = _validate(report, manifest)
    templates = {}
    for c in candidates.values():
        key = _identity(c)
        matches = [o for o in original if _identity(o) == key
                   and (o.get("home"), o.get("away"), o.get("league")) ==
                       (c["home"], c["away"], c["league"])
                   and stamp(o["kickoff"]) == stamp(c["kickoff"])
                   and o.get("favorite_side") in ("H", "A")
                   and o.get("data_origin") != "BACKFILLED"]
        sides = {m["favorite_side"] for m in matches}
        if len(sides) > 1:
            raise ValueError("MISSING_OR_AMBIGUOUS_FAVORITE_IDENTITY")
        if not sides:
            # Native exact-ID observations from pinned manifest sources may
            # not yet exist in the published Research V2 dataset.
            native = bool(c.get('observations')) and any(
                e.get('path') in {
                    'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',
                    'data/normalized/v2_mainline_snapshots.jsonl',
                    'data/research/pre_sep14_historical_originals.jsonl',
                    'data/research/pre_sep15_17_historical_originals.jsonl',
                } and e.get('sha256') and e.get('line')
                for e in c.get('evidence', []))
            external = any(
                e.get('mapping_source', '').startswith('ODDSPAPI_') and (
                    e.get('evidence_url', '').startswith('https://') or (
                        e.get('mapping_source') == 'ODDSPAPI_NATIVE_FIXTURES_RECEIPT'
                        and e.get('response_id') and e.get('sha256')))
                for e in c.get('evidence', []))
            if not (native or external):
                raise ValueError('NEW_FIXTURE_REQUIRES_EXTERNAL_PROVIDER_EVIDENCE')
            templates[key] = None
        else:
            templates[key] = matches[-1]
    incoming = {}
    counts = Counter()
    for result in report["results"]:
        key = _identity(result)
        c = candidates.get(key)
        if c is None or any(result.get(k) != c.get(k) for k in ("football_day", "home", "away", "kickoff")):
            raise ValueError("RESULT_MANIFEST_MISMATCH")
        expected = {stamp(t["target_utc"]).isoformat() for t in c["targets"]}
        actual = [stamp(s["target_utc"]).isoformat() for s in result["slots"]]
        if len(actual) != len(expected) or set(actual) != expected:
            raise ValueError("SLOT_MANIFEST_MISMATCH")
        for slot in result["slots"]:
            counts[slot["status"]] += 1
            if slot["status"] != VALID:
                continue
            s = slot.get("selected") or {}
            target = stamp(slot["target_utc"])
            kickoff = stamp(c["kickoff"])
            if (s.get("line_selection") != VALID or s.get("market") != "AH"
                    or s.get("official_mainline_verified") is not False
                    or s.get("fixture_id") != c["fixture_id"]
                    or s.get("bookmaker") != c["bookmaker"]
                    or stamp(s["slot_utc"]) != target
                    or target >= kickoff
                    or not s.get("market_id")):
                raise ValueError("UNVERIFIED_SELECTED_LINE")
            hl = s.get("home_line")
            al = s.get("away_line")
            q = s.get("quotes") or {}
            if (type(hl) not in (float, int) or not math.isfinite(hl)
                    or abs(hl*4-round(hl*4)) > 1e-8
                    or type(al) not in (float, int) or abs(hl+al) > 1e-8):
                raise ValueError("INVALID_AH_LINE")
            times = []
            prices = []
            for side in ("home", "away"):
                quote = q.get(side) or {}
                price = quote.get("price")
                if (quote.get("active") is not True or type(price) not in (int, float)
                        or not math.isfinite(price) or not 1.8 <= price <= 2.2):
                    raise ValueError("INVALID_QUOTE")
                qt = stamp(quote["quote_at_utc"])
                if qt > target or qt >= kickoff or (target - qt).total_seconds() > 3600:
                    raise ValueError("QUOTE_TIMESTAMP_OUT_OF_RANGE")
                times.append(qt)
                prices.append(price)
            home, away = prices
            base = templates[key]
            # No fabricated pre-match favorite: for a new verified fixture the
            # negative AH side is the handicap favorite; level ball is unknown.
            if base is None:
                if hl == 0:
                    raise ValueError("LEVEL_BALL_FAVORITE_UNRESOLVED")
                fav = "H" if hl < 0 else "A"
                row = {k: c[k] for k in ("fixture_id", "home", "away", "league", "kickoff")}
                favorite_basis = "HISTORICAL_NEGATIVE_AH_HANDICAP"
            else:
                fav = base["favorite_side"]
                row = dict(base)
                favorite_basis = "VERIFIED_OBSERVED_COHORT"
            row.update(provider="oddspapi", bookmaker=c["bookmaker"], football_day=c["football_day"],
                observed_at=max(times).isoformat(), scheduled_target_at=target.isoformat(),
                historical_target_slot_at=target.isoformat(), historical_quote_home_at=times[0].isoformat(),
                historical_quote_away_at=times[1].isoformat(),
                historical_provenance="ODDSPAPI_MANUAL_HISTORICAL_"+str(report.get("run_url") or "UNKNOWN"),
                historical_market_id=s.get("market_id"), historical_raw_record_hash=s.get("raw_record_hash"),
                historical_timestamp_basis="PROVIDER_HISTORY_ENTRY_CREATED_AT_NOT_LIVE_COLLECTION",
                source_semantics="HISTORICAL_BALANCED_LINE_AS_OF_SLOT", data_origin="BACKFILLED",
                mainline_verified=False, promotion_eligible=False, research_only=True,
                one_x_two={}, ou={}, favorite_fair_probability=None,
                favorite_side=fav, favorite_side_basis=favorite_basis,
                ah={"home_line":hl, "away_line":al, "home_price":home, "away_price":away,
                    "selected_side_line":hl if fav=="H" else al,
                    "selected_side_price":home if fav=="H" else away,
                    "opposite_side_price":away if fav=="H" else home})
            for field in ("scan_id", "scan_run_id", "schedule_lag_minutes", "actual_observed_at"):
                row.pop(field, None)
            k = _key(row)
            if k in incoming and incoming[k] != row:
                raise ValueError("CONFLICTING_INCOMING_SLOT")
            incoming[k] = row
    return incoming, dict(counts)

def publish(report, manifest, root=Path(".")):
    path = root/SNAPSHOTS
    original = _rows(path)
    incoming, counts = produce(report, manifest, original)
    prior = {}
    for row in original:
        k = _key(row)
        if k[-1] is not None and row.get("data_origin") == "BACKFILLED":
            if k in prior and prior[k] != row:
                raise ValueError("CONFLICTING_EXISTING_BACKFILL")
            prior[k] = row
    add, unchanged, conflict = [], 0, 0
    for k, row in incoming.items():
        old = prior.get(k)
        if old is None:
            add.append(row)
        elif {a:v for a,v in old.items() if a!="historical_provenance"} == {a:v for a,v in row.items() if a!="historical_provenance"}:
            unchanged += 1
        else:
            conflict += 1
    if conflict:
        raise ValueError("EXISTING_SLOT_CONFLICT_REQUIRES_REVIEW")
    receipt = {"status": "PROMOTED" if add else "NO_NEW_ROWS",
               "source_run": report.get("run_url"), "slot_statuses": counts,
               "added": len(add), "unchanged": unchanged,
               "conflicts": 0, "before":len(original),"after":len(original)+len(add),
               "historical_market": "AH_BALANCED_LINE_NOT_OFFICIAL_MAINLINE",
               "production_live_observations_modified":0,"api_requests":0}
    if add:
        with path.open("a", encoding="utf-8") as fh:
            for row in sorted(add, key=_key):
                fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":"))+"\n")
    target = root/RECEIPT
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n")
    return receipt

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-dir",type=Path,required=True)
    a = p.parse_args()
    base = a.artifact_dir
    report = json.loads((base/"report.json").read_text())
    manifest = json.loads((base/"manifest.json").read_text())
    print(json.dumps(publish(report, manifest),ensure_ascii=False,indent=2))

if __name__ == "__main__":
    main()
