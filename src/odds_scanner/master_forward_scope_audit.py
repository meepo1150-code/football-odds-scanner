"""Network-free forward-scope replay; archives and historic statistical scope remain intact."""
import hashlib,json
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from .master_scan_scope import approved_competitions,forward_mappings,scan_scope_reason,filter_scan_targets
from .research_population import exclusion_reason
from .research_v2_pattern_stats import _rows


def build(root=Path('.')):
    targets=json.loads((root/'reports/europe_discovery_tournaments.json').read_text())['tournaments']
    old=[r for r in targets if not exclusion_reason(r,provider='oddspapi')]
    approved=filter_scan_targets(targets)
    breakdown=defaultdict(Counter)
    for row in _rows(root/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl'):
        provider=row.get('provider') or ('oddspapi' if str(row.get('source_semantics','')).startswith('CURRENT_ODDSPAPI_') else 'UNKNOWN')
        reason=exclusion_reason(row,provider=provider) or scan_scope_reason(row,provider=provider) or 'ALLOWLISTED'
        breakdown[(str(row.get('football_day')),provider)][reason]+=1
    paths=['data/normalized/europe_pinnacle_research_v2_snapshots.jsonl',
        'data/normalized/europe_pinnacle_research_v2_audit.jsonl',
        'data/normalized/oddspapi_finished_results.jsonl','reports/pattern_registry.json']
    policies={'approved_divisions':81,'domestic_cups':8,'uefa_club_competitions':3,
        'senior_national_competitions':'NOT_ALLOWLISTED','outside_master':'REJECT_NEW_QUOTES',
        'unmapped_provider':'BLOCK_BEFORE_HTTP_ODDS_CALLS','historical_statistics':'REVIEWED_RESEARCH_SCOPE_UNCHANGED'}
    result={'generated_at':datetime.now(timezone.utc).isoformat(),'classification':'MASTER_FORWARD_ALLOWLIST_PREFLIGHT',
        'verdict':'OFFLINE_GATES_PASS; LIVE_OBSERVATION_PENDING; FALLBACK_COVERAGE_REDUCED',
        'api_requests_used':0,'raw_deleted':0,'approved_competitions':len(approved_competitions()),
        'verified_provider_competition_mappings':len(forward_mappings()),'policies':policies,
        'old_target_count':len(targets),'old_after_reviewed_exclusions':len(old),
        'verified_existing_discovery_targets':len(approved),
        'blocked_targets':[dict(r,reason=scan_scope_reason(r,provider='oddspapi')) for r in old if scan_scope_reason(r,provider='oddspapi')],
        'producer_enforcement':{'europe_discovery':'FILTER_BEFORE_ODDS_BATCHES','europe_pinnacle_discovery':'FILTER_BEFORE_ACCOUNT_OR_ODDS',
            'v2_mainline_observer':'FILTER_BEFORE_ODDS_BATCHES','propline':'NO_VERIFIED_SPORT_KEYS; CATALOG_AND_STATIC_FALLBACK_BLOCKED; ROWS_RECHECKED',
            'pinnwire':'NO_VERIFIED_LEAGUE_IDS; GLOBAL_PREMATCH_FETCH_BLOCKED','five_dollar_live':'NO_VERIFIED_LEAGUE_IDS; FIXTURE_AND_ODDS_FETCH_BLOCKED',
            'sgodds_live':'NO_VERIFIED_COMPETITION_IDS; MARKET_FETCH_BLOCKED','daily_fixture_result_sync':'LOCAL_ONLY_METADATA_FROM_EXISTING_RAW; NO_NEW_ODDS',
            'historical_archives_and_ft_recovery':'HISTORICAL_IDENTITIES_RETAINED; NO_RETROACTIVE_ALLOWLIST'},
        'replay_by_day_provider':[{'football_day':d,'provider':p,'snapshot_counts':dict(counts)} for (d,p),counts in sorted(breakdown.items())],
        'preserved_artifact_sha256':{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
        'coverage_limitations':['The 47 verified targets in the current discovery file are a subset of the 92 registered mappings.',
            'Primary rotating cohorts remain limited to five tournaments per weekend slot and ten per weekday slot.',
            'Unsupported providers intentionally contribute no new quotes until verified mappings are recorded.',
            'Historical country/name labels do not authorize new provider-ID mappings.']}
    out=root/'reports/master_allowlist_preflight.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    report=build();print(json.dumps({k:v for k,v in report.items() if k!='replay_by_day_provider'}))
