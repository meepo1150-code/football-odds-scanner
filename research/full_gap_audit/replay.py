"""Validate immutable pilot cache; admit only exact verified gap identities.

This command intentionally has no live provider client. New requests require a
fresh isolated account preflight, not a stale entitlement from the old pilot.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from research.full_gap_audit.audit import BASE,LEVANTE,parse,blob,sha,save,stamp
from research.historical_backfill.isolated_runner import load_cache
from research.historical_backfill.normalizer import normalize
from research.historical_backfill.comparison import reconstruct_candidate
from research.historical_backfill.representative import select
from research.historical_backfill.revalidate import validate_catalog

def run(audit,cache,out):
    cache=cache.resolve();root=Path('research/historical_backfill/reports')
    manifest=json.loads((root/'multiday_manifest.json').read_text())
    catalog=json.loads((root/'reviewed_catalog.json').read_text())
    validate_catalog(catalog,json.loads(Path('data/normalized/oddspapi_market_catalog.json').read_text()))
    gaps=[json.loads(l) for l in (audit/'missing_slot_manifest.jsonl').read_text().splitlines()]
    eligible={(r['fixture_id'],r['bookmaker'],r['slot_utc']):r for r in gaps if r['recovery_eligible']}
    original=json.loads((root/'CONTROLLED_EXPANSION_20261016.json').read_text())
    old={(r['fixture_id'],r['bookmaker'],stamp(r['slot_utc']).isoformat()):r.get('selected') for r in original['coverage']['slots']}
    scores=defaultdict(set)
    for _,r in parse(blob(BASE,'data/normalized/oddspapi_finished_results.jsonl')):
        s=(r.get('ft_home_goals'),r.get('ft_away_goals'))
        if all(type(n) is int and n>=0 for n in s):scores[str(r.get('fixture_id'))].add(s)
    full=[];selected=[];unresolved=[];ft=[];provenance=[];new=[];queue=[];matched=set()
    for c in manifest['candidates']:
        payload=load_cache(cache,c)
        if payload is None:raise ValueError('CACHE_MISSING_NO_REFETCH')
        ms=normalize(payload,c,catalog,active_semantics_verified=True)
        rr=reconstruct_candidate(c,ms,state_semantics_verified=True)
        ss=scores[c['fixture_id']]
        ft_state=('POSTPONED_FT_BLOCKED' if c['fixture_id']==LEVANTE else 'VERIFIED_EXACT_ID' if len(ss)==1 and tuple(c.get('ft_score') or ()) in ss else 'FT_UNAVAILABLE_OR_CONFLICT')
        ft.append(dict(fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],status=ft_state,scores=[list(s) for s in sorted(ss)],baseline=BASE))
        full.extend({**r,'independent_ft_validation':ft_state} for r in rr if r['status']=='COMPLETE')
        receipt_path=cache/'cache'/(sha(c['request'])+'.json')
        receipt=json.loads(receipt_path.read_text());raw=cache/'raw'/(receipt['raw_sha256']+'.json')
        assert sha(raw.read_bytes())==receipt['raw_sha256']
        provenance.append(dict(fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],original_response_bytes_sha256=receipt['raw_sha256'],canonical_response_hash=ms[0].get('raw_record_hash') if ms else None,artifact_id=12017046429,byte_hash_verified=True))
        for slot in c['missing_rounds']:
            k=(c['fixture_id'],c['bookmaker'],stamp(slot).isoformat())
            result=select([r for r in rr if stamp(r['slot_utc'])==stamp(slot)],fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],kickoff=c['kickoff'],slot=slot,catalog=catalog)
            picked=result['selected'];prior=old.get(k)
            if bool(picked)!=bool(prior) or (picked and sha(picked)!=sha(prior)):raise ValueError('FROZEN_PRICE_REPLAY_MISMATCH')
            if picked:selected.append(dict(fixture_id=k[0],bookmaker=k[1],slot_utc=k[2],candidate=picked,ft_validation=ft_state,admission='POSTPONED_FT_BLOCKED' if k[0]==LEVANTE else 'NOT_VERIFIED_PRODUCTION_GAP' if k not in eligible else 'GAP_PRICE_CANDIDATE_NOT_IMPORTED'))
            else:unresolved.append(result)
        # Cache identities may be reusable even when the requested target differs.
        gg=[(k,g) for k,g in eligible.items() if k[:2]==(c['fixture_id'],c['bookmaker'])]
        if gg:
            rs=reconstruct_candidate({**c,'missing_rounds':[k[2] for k,g in gg]},ms,state_semantics_verified=True)
            for k,g in gg:
                matched.add(k)
                q=select([r for r in rs if stamp(r['slot_utc'])==stamp(k[2])],fixture_id=k[0],bookmaker=k[1],kickoff=c['kickoff'],slot=k[2],catalog=catalog)
                # A matched price is quarantined unless a separate staging admission is reviewed.
                queue.append(dict(deduplication_key=g['deduplication_key'],state='CACHE_VALIDATION_QUARANTINE' if q['selected'] else 'MAINLINE_UNRESOLVED',reason=q['reason']))
    for k,g in eligible.items():
        if k not in matched:queue.append(dict(fixture_id=k[0],bookmaker=k[1],slot_utc=k[2],deduplication_key=g['deduplication_key'],state='BLOCKED_FRESH_RESEARCH_CREDENTIAL_AND_PREFLIGHT_REQUIRED'))
    before=json.loads((audit/'summary.json').read_text())['baseline_observed_records']
    report=dict(status='OFFLINE_DRY_RUN_COMPLETE_LIVE_RECOVERY_BLOCKED',cache_fixtures_replayed=len(provenance),complete_all_line_records=len(full),balanced_representatives=len(selected),unresolved_pilot_slots=len(unresolved),admission_counts=dict(Counter(r['admission'] for r in selected)),ft_validation_counts=dict(Counter(r['status'] for r in ft)),verified_gap_slots_with_cached_fixture=len(matched),new_reconstructed_records=len(new),new_historical_http_requests=0,new_account_http_requests=0,estimated_unique_uncached_historical_requests=len({k[:2] for k in eligible if k not in matched}),before=dict(observed_records=before,backfilled_records=0),after=dict(observed_records=before,backfilled_records=len(new)),scan_reliability_changed=False,dashboard_impact='NONE',production_import_approved=False,historical_recovery_complete=False,raw_cache_modified=False)
    for name,rs in [('cache_full_line_staging',full),('pilot_candidate_quarantine',selected),('unresolved_pilot_slots',unresolved),('recovery_queue',queue),('validated_staging',new),('ft_validation',ft),('raw_provenance',provenance)]:save(out/(name+'.jsonl'),rs,True)
    save(out/'dry_run.json',report);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.audit,a.cache,a.output),indent=2))
