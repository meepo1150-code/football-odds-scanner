"""Pinned-data offline manifest builder. No network or production writes."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from research.historical_backfill.candidates import select_candidates
from research.historical_backfill.offline_stats import three_previews
from research.historical_backfill.reconstruct import parse_time

BASELINE='2ff67333b5c65bd1d4ca24020750a7260f59201e'
RESEARCH_HEAD='ba8bd821341e35ece16e6b7b774b023df6da8b95'
REPORTS=Path('research/historical_backfill/reports')


def read_jsonl(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def build(root):
    paths=['data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',
           'data/normalized/research_v2_daily_fixtures.jsonl',
           'data/normalized/oddspapi_finished_results.jsonl',
           'data/master/provider_mappings.csv','data/master/competitions.csv','config/league_selection_v1.json']
    evidence=json.loads((root/REPORTS/'baseline.json').read_text())
    for p in paths:
        data=(root/p).read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if blob!=evidence['input_git_blobs'][p]:
            raise ValueError('Input no longer matches pinned baseline: '+p)
    before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    snapshots,fixtures,results=[read_jsonl(root/p) for p in paths[:3]]
    mappings,competitions=[list(csv.DictReader((root/p).open())) for p in paths[3:5]]
    excluded=json.loads((root/paths[5]).read_text())['user_excluded_competition_ids']
    candidates,rejections,eligible=select_candidates(snapshots,fixtures,results,mappings,competitions,excluded)
    keyed={}
    for c in candidates:
        for r in snapshots:
            if r['fixture_id']!=c['fixture_id'] or r['bookmaker']!=c['bookmaker']:continue
            slot=r.get('scheduled_target_at')
            if not slot or parse_time(slot).isoformat() not in c['existing_rounds']:continue
            ah=r['ah'];key=(c['fixture_id'],c['bookmaker'],parse_time(slot),ah['home_line'])
            item=dict(fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],market='AH',
                line=ah['home_line'],slot_utc=slot,actual_observed_at=r['observed_at'],
                actual_price_timestamp=None,data_origin='OBSERVED',status='COMPLETE',
                ft_status=c['ft_status'],ft_score=c['ft_score'],
                quotes={s:dict(price=ah[s+'_price'],quote_at_utc=None) for s in ('home','away')})
            if key not in keyed or parse_time(r['observed_at'])<parse_time(keyed[key]['actual_observed_at']):keyed[key]=item
    after={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
    assert before==after,'Production input mutated'
    return dict(baseline_sha=BASELINE,research_original_head=RESEARCH_HEAD,
        status='BLOCKED_LIVE_PILOT',recommendation='REVISE',actual_api_requests=0,
        candidates=candidates,eligible_fixture_bookmaker_groups=eligible,rejections=rejections,
        missing_slots=sum(len(c['missing_rounds']) for c in candidates),
        historical_ah_coverage=None,backfilled_slots=0,quality_passed_fixtures=0,
        untested_slots=sum(len(c['missing_rounds']) for c in candidates),
        observed_vs_backfilled_comparison='NOT_RUN_NO_MATCHED_HISTORICAL_PAYLOAD',
        statistics=three_previews(list(keyed.values()),[]),
        observed_round_selection='EARLIEST_ACTUAL_OBSERVATION_PER_EXACT_SLOT_LINE',
        price_change_timestamps='UNAVAILABLE_FOR_OBSERVED_ROWS_NOT_INFERRED',
        blockers=['HISTORICAL_ACTIVE_AS_OF_SEMANTICS_NOT_PROVEN','COMPLETE_TICK_CADENCE_NOT_GUARANTEED',
                  'NO_ISOLATED_CREDENTIAL_OR_MANUAL_SECRET_BOUND_RUNNER','ACCOUNT_SNAPSHOT_IS_NOT_LIVE_PREFLIGHT'],
        expansion_gate='CLOSED_NO_MEASURED_LIVE_COST_LATENCY_OR_COVERAGE',
        input_sha256=before,production_inputs_unchanged=True,zero_coverage_is_not_proven_absence=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');args=parser.parse_args()
    root=Path(args.root).resolve();report=build(root)
    out=root/REPORTS;out.mkdir(parents=True,exist_ok=True)
    (out/'pilot.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'candidate_manifest.json').write_text(json.dumps(report['candidates'],indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','actual_api_requests','eligible_fixture_bookmaker_groups','missing_slots','backfilled_slots','production_inputs_unchanged')}))


if __name__=='__main__':main()
