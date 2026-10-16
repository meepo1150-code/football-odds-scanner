"""Reproducible blocked/live evidence report; never turns prepared rows into coverage."""
import json
import os
from pathlib import Path
from research.historical_backfill.coverage_metrics import coverage_report,statistical_preview
from research.historical_backfill.isolated_runner import run,digest


def main():
    root=Path('.');base=root/'research/historical_backfill/reports'
    manifest=json.loads((base/'multiday_manifest.json').read_text())
    gate=json.loads((base/'isolated_gate_pending.json').read_text())
    # This report command is deliberately offline. A live pilot uses isolated_runner.
    result=run(manifest,[],[],gate,lambda:{},key=None)
    paths=[root/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',
           root/'data/normalized/v2_mainline_snapshots.jsonl']
    observations=[json.loads(s) for p in paths for s in p.read_text().splitlines() if s.strip()]
    output=dict(baseline_sha=manifest['baseline_sha'],manifest_sha256=digest(manifest),
        status='BLOCKED_NO_LIVE_HISTORICAL_RECOVERY',recommendation='REVISE_DO_NOT_BACKFILL_ALL_HISTORY',
        prepared_fixture_count=manifest['unique_fixture_count'],prepared_missing_target_slots=manifest['target_slots'],
        run=result,coverage=coverage_report(manifest,result),
        statistics=statistical_preview(manifest,result,observations),
        historical_ah_coverage=None,quota_before=None,quota_after=None,error_rate=None,
        real_backfilled_snapshots=0,real_backfilled_unique_fixtures=0,
        unresolved_blockers=['ISOLATED_CREDENTIAL_UNAVAILABLE','CURRENT_ACCOUNT_ENTITLEMENT_UNVERIFIED',
            'PINNED_FULL_MATCH_AH_CATALOG_REVIEW_PENDING','FRESH_PRODUCTION_HEALTH_PREFLIGHT_REQUIRED'],
        semantics_resolution=dict(mode='PROVIDER_REPORTED_SNAPSHOT',continuous_availability_proven=False,
            quote_change_time_proven=False,evidence='https://oddspapi.io/blog/bet365-historical-odds-guide-the-data-apis-and-strategy/'),
        provider_requests=0,production_modifications=0,merge=False,deploy=False)
    (base/'multiday_result.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k not in ('run','coverage','statistics')},indent=2))


if __name__=='__main__':main()
