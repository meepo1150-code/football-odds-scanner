#!/usr/bin/env python3
"""Offline, non-mutating admission audit of controlled historical expansion report."""
import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path

def timestamp(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

def inspect(report):
    slots = report["coverage"]["slots"]
    admitted, rejected = [], []
    keys = set()
    for row in slots:
        selected = row.get("selected")
        if not selected:
            rejected.append({"fixture_id": row["fixture_id"], "slot_utc": row["slot_utc"], "reason": "MAINLINE_UNRESOLVED"})
            continue
        reasons = []
        quotes = selected.get("quotes") or {}
        try:
            target, kickoff = timestamp(row["slot_utc"]), timestamp(row["kickoff_utc"])
            if target >= kickoff:
                reasons.append("TARGET_NOT_BEFORE_KICKOFF")
            for side in ("home", "away"):
                quote = quotes[side]
                price = float(quote["price"])
                observed = timestamp(quote["quote_at_utc"])
                if not quote.get("active"): reasons.append(side.upper()+"_INACTIVE")
                if not 1.8 <= price <= 2.2: reasons.append(side.upper()+"_PRICE_OUT_OF_RANGE")
                if not (0 <= (target-observed).total_seconds() <= 3600): reasons.append(side.upper()+"_QUOTE_TIME_INVALID")
                if observed >= kickoff: reasons.append(side.upper()+"_AFTER_KICKOFF")
            if not (float(selected["line"])*4).is_integer():
                reasons.append("NON_QUARTER_LINE")
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            reasons.append("INVALID_FIELDS:"+type(exc).__name__)
        if selected.get("line_selection") != "BALANCED_LINE": reasons.append("WRONG_SELECTION")
        if selected.get("data_origin") != "BACKFILLED": reasons.append("WRONG_ORIGIN")
        if not selected.get("raw_record_hash"): reasons.append("NO_SOURCE_HASH")
        key = (row["fixture_id"],row["slot_utc"],row["bookmaker"])
        if key in keys: reasons.append("DUPLICATE_REPRESENTATIVE")
        keys.add(key)
        if reasons:
            rejected.append({"fixture_id":row["fixture_id"],"slot_utc":row["slot_utc"],"reason":";".join(reasons)})
        else:
            admitted.append({"fixture_id":row["fixture_id"],"slot_utc":row["slot_utc"],"bookmaker":row["bookmaker"],"line":selected["line"],"home_price":quotes["home"]["price"],"away_price":quotes["away"]["price"],"home_quote_at_utc":quotes["home"]["quote_at_utc"],"away_quote_at_utc":quotes["away"]["quote_at_utc"],"raw_record_hash":selected["raw_record_hash"],"ft_status":selected.get("ft_status"),"origin":"HISTORICAL_BACKFILL"})
    return {"status":"RESEARCH_ADMISSION_ONLY","source_slots":len(slots),"price_valid_representatives":len(admitted),"rejected_or_unresolved":len(rejected),"ft_status_counts":dict(collections.Counter(x["ft_status"] for x in admitted)),"production_reconciliation":"NOT_RUN_REQUIRES_PINNED_PRODUCTION_LEDGER","production_import_approved":False,"admitted":admitted,"rejected":rejected}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("report",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=inspect(json.loads(args.report.read_text()))
    result["input_sha256"]=hashlib.sha256(args.report.read_bytes()).hexdigest()
    output=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    if args.output: args.output.write_text(output)
    else: print(output)

if __name__=="__main__": main()
