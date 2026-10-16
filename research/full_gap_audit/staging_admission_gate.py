"""Strict, offline staging admission gate for verified historical AH candidates.

Never imports to production. Fails closed when identity, quote time or both
prices are not independently proven. Input JSONL rows are explicitly reviewed
recovery outputs, NOT the missing-slot manifest itself.
"""
import argparse
import hashlib
import json
from pathlib import Path

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def review(manifest, candidates):
    missing={r['deduplication_key']:r for r in manifest if r.get('recovery_eligible') is True}
    accepted=[];rejected=[];seen=set()
    for row in candidates:
        key=row.get('deduplication_key')
        reason=None
        if key not in missing:reason='NOT_IN_VERIFIED_MANIFEST'
        elif key in seen:reason='DUPLICATE_CANDIDATE'
        elif row.get('fixture_id')!=missing[key]['fixture_id'] or row.get('target_slot_utc')!=missing[key]['slot_utc']:
            reason='IDENTITY_OR_SLOT_MISMATCH'
        elif row.get('bookmaker')!='pinnacle' or row.get('market')!='FULL_MATCH_AH':
            reason='UNSUPPORTED_BOOKMAKER_OR_MARKET'
        elif row.get('source')!='HISTORICAL_ODDSPAPI' or not row.get('raw_response_sha256'):
            reason='NO_RAW_SOURCE_PROVENANCE'
        elif row.get('line_selection') not in ('BALANCED_LINE','MAINLINE_UNRESOLVED'):
            reason='UNVERIFIED_LINE_SELECTION'
        elif row.get('line_selection')=='MAINLINE_UNRESOLVED':
            reason='NO_RESOLVED_REPRESENTATIVE_LINE'
        else:
            try:
                from datetime import datetime
                t=datetime.fromisoformat(row['quote_timestamp'])
                slot=datetime.fromisoformat(row['target_slot_utc'])
                kickoff=datetime.fromisoformat(missing[key]['kickoff_utc'])
                hp=float(row['home_decimal']);ap=float(row['away_decimal'])
                line=float(row['home_line'])
                if t.tzinfo is None or slot.tzinfo is None or kickoff.tzinfo is None or not slot<=t<kickoff:
                    reason='INVALID_QUOTE_TIME'
                elif not (1.8<=hp<=2.2 and 1.8<=ap<=2.2 and abs(line)<100):
                    reason='INVALID_BALANCED_AH_QUOTES'
            except (ValueError,TypeError,KeyError,OverflowError):
                reason='INVALID_PRICE_OR_TIMESTAMP'
        if reason:
            rejected.append({'deduplication_key':key,'reason':reason})
        else:
            seen.add(key)
            accepted.append(row)
    return {'accepted':accepted,'rejected':rejected,'manifest_eligible':len(missing),'admitted':len(accepted),'rejected_count':len(rejected),'production_import_approved':False,'historical_api_calls':0}

def read(path):
    with open(path,encoding='utf-8') as fh:
        return [json.loads(s) for s in fh if s.strip()]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--candidates',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if not a.output.resolve().is_relative_to(Path(__file__).resolve().parent):
        raise SystemExit('RESEARCH_OUTPUT_ONLY')
    result=review(read(a.manifest),read(a.candidates))
    if a.output.exists():raise SystemExit('OUTPUT_ALREADY_EXISTS')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('accepted','rejected')}))
if __name__=='__main__':main()
