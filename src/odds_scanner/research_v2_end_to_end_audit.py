"""Network-free, reproducible operational and exploratory movement evidence."""
import csv, json, random, statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from .research_v2_pattern_stats import _rows, OUTCOMES, MISSING_LEDGER
from .observation_movement import utc
from .master_mapping import load_mappings
from .research_population import exclusion_reason


def provider(row):
    explicit=row.get('provider') or row.get('source_provider')
    if explicit and explicit!='UNKNOWN':return explicit
    if str(row.get('source_semantics','')).startswith('CURRENT_ODDSPAPI_') or str(row.get('source','')).startswith('oddspapi:'):return 'oddspapi'
    fid=str(row.get('source_fixture_id') or row.get('fixture_id') or '')
    if ':' in fid:return fid.split(':',1)[0]
    return 'oddspapi' if fid.isdigit() else 'UNRESOLVED_PROVIDER'


def distribution(xs):
    xs=sorted(x for x in xs if x is not None)
    return {'n':len(xs),'min':xs[0] if xs else None,'median':statistics.median(xs) if xs else None,'max':xs[-1] if xs else None}


def bootstrap(xs):
    if not xs:return [None,None]
    rng=random.Random(20261011)
    means=sorted(sum(rng.choices(xs,k=len(xs)))/len(xs) for _ in range(2000))
    return [round(means[50],6),round(means[1949],6)]


def evaluate(outcomes):
    eligible=sorted([r for r in outcomes if r.get('observation_gap_minutes') is not None and r.get('favorite_profit_units') is not None],key=lambda r:(r.get('kickoff') or '',r['fixture_id']))
    predictions=[]
    # Each forecast uses only earlier Football Days. This is a viewed retrospective
    # walk-forward evaluation, never called untouched holdout.
    for r in eligible:
        past=[x for x in eligible if str(x.get('football_day'))<str(r.get('football_day'))]
        key=lambda x:(x.get('market_side'),x.get('ah_line'),x.get('ah_price_bucket'))
        base=[x for x in past if key(x)==key(r)]
        if len(past)<20 or len(base)<5:continue
        mu=statistics.mean(x['favorite_profit_units'] for x in base)
        move=[x for x in base if x['movement']==r['movement']]
        extended=(sum(x['favorite_profit_units'] for x in move)+10*mu)/(len(move)+10)
        y=r['favorite_profit_units']
        predictions.append({'fixture_id':r['fixture_id'],'football_day':r['football_day'],'baseline_train_n':len(base),'movement_train_n':len(move),'baseline_return_prediction':mu,'movement_return_prediction':extended,'realized_profit_units':y,'squared_error_improvement':(y-mu)**2-(y-extended)**2})
    deltas=[r['squared_error_improvement'] for r in predictions]
    families=[]
    for movement in sorted({x['movement'] for x in eligible}):
        rs=[r for r in eligible if r['movement']==movement];ys=[r['favorite_profit_units'] for r in rs]
        families.append({'movement':movement,'unique_fixture_n':len(rs),'roi_pct':round(100*statistics.mean(ys),3),'profit_mean_bootstrap95':bootstrap(ys),'settlements':dict(Counter(r['favorite_ah_settlement'] for r in rs))})
    # Family ROIs are descriptive. No p-values/promotions based on repeated subgroup search.
    return {'status':'NO_VALIDATED_INCREMENTAL_MOVEMENT_EDGE','evaluation':'RETROSPECTIVE_VIEWED_DATA_CHRONOLOGICAL_WALK_FORWARD_BY_FOOTBALL_DAY','untouched_holdout':False,'promotion_allowed':False,'unique_eligible_fixtures':len(eligible),'unique_evaluated_fixtures':len(predictions),'metric':'BASELINE_MSE_MINUS_MOVEMENT_MSE; POSITIVE_IS_BETTER','mean_squared_error_improvement':statistics.mean(deltas) if deltas else None,'improvement_bootstrap95':bootstrap(deltas),'baseline':'MARKET_SIDE + AH_LINE + PRICE_BUCKET; TRAIN_MIN_5; PRIOR_DAYS_MIN_20','movement_model':'SAME_BASELINE + MOVEMENT; SHRINKAGE_10_BASELINE_OBSERVATIONS','multiple_testing_policy':'ONE_PREDEFINED_INCREMENTAL_COMPARISON; SUBGROUPS_DESCRIPTIVE_ONLY; NO_PROMOTION_OR_EDGE_CLAIMS; NEW_UNVIEWED_PERIOD_REQUIRED','observation_gap_minutes':distribution([r['observation_gap_minutes'] for r in eligible]),'first_minutes_before_kickoff':distribution([r['first_minutes_before_kickoff'] for r in eligible]),'last_minutes_before_kickoff':distribution([r['last_minutes_before_kickoff'] for r in eligible]),'descriptive_families':families,'predictions':predictions,'limitations':['SMALL_SINGLE_PERIOD_SAMPLE','NOT_PREREGISTERED','BOOTSTRAP_FIXTURE_LEVEL_DOES_NOT_REMOVE_LEAGUE_DAY_DEPENDENCE','SOURCE_SWITCH_EXCLUDED_FROM_MOVEMENT_DELTA','LATEST_PRICE_STATE_USED; NOT_A_TRADABLE_STRATEGY']}


def build(root=Path('.')):
    snapshots=_rows(root/'data/normalized/europe_pinnacle_research_v2_snapshots.jsonl')
    outcomes=_rows(root/OUTCOMES)
    missing=json.loads((root/MISSING_LEDGER).read_text()).get('fixtures',[])
    mappings=load_mappings(root/'data/master/provider_mappings.csv')
    competitions={r['competition_id']:r for r in csv.DictReader((root/'data/master/competitions.csv').open())}
    countries={r['country_id']:r for r in csv.DictReader((root/'data/master/countries.csv').open())}
    latest={str(r.get('fixture_id')):r for r in snapshots}
    now=datetime.now(timezone.utc);triage=[]
    for r in missing:
        source=latest.get(str(r['fixture_id']),{})
        p=provider(source or r);cid=source.get('canonical_competition_id') or mappings.get((p,'competition',str(source.get('tournament_id'))))
        country=source.get('country') or r.get('country')
        # Exact master country/name equality is identity evidence, not fuzzy matching.
        candidates=[c for c in competitions.values() if c['competition_name']==r.get('league') and countries.get(c['country_id'],{}).get('country_name')==country]
        if not cid and len(candidates)==1:cid=candidates[0]['competition_id']
        ko=utc(r.get('kickoff'));state=r['status'] if r['status'] in {'IDENTITY_CONFLICT','POSTPONED','CANCELLED','ABANDONED','RETIRED_UNRESOLVED'} else 'ACTIVE_OVERDUE' if ko and (now-ko).total_seconds()>=10800 else 'FUTURE_OR_RECENT'
        reason=exclusion_reason(source)
        triage.append({**r,'provider':p,'country':country or 'UNRESOLVED_COUNTRY','canonical_competition_id':cid or 'UNRESOLVED_CANONICAL_COMPETITION','lifecycle':state,'exclusion_reason':reason,'identity_status':'EXACT_MASTER_COMPETITION' if cid else 'UNRESOLVED_IDENTITY','policy':'OUTSIDE_MASTER_IS_NOT_USER_CANCELLED; GERMANY_3_LIGA_RETAINED'})
    grouped=Counter((r['lifecycle'],r['provider'],r['country'],r['canonical_competition_id'],r['league']) for r in triage)
    report={'generated_at':now.isoformat(),'research_only':True,'raw_deleted':0,'settled_fixtures':len(outcomes),'movement_classification_counts':dict(Counter(r['movement'] for r in outcomes)),'movement_evaluation':evaluate(outcomes),'ft_triage_counts':dict(Counter(r['lifecycle'] for r in triage)),'ft_triage_groups':[dict(zip(('lifecycle','provider','country','canonical_competition_id','league'),key),n=n) for key,n in sorted(grouped.items())],'ft_triage':triage,'scope':{'trusted_exclusions':json.loads((root/'reports/research_v2_pattern_statistics.json').read_text())['scope_excluded_snapshot_rows'],'raw_deleted':0,'user_cancelled_active_pending':sum(bool(r['exclusion_reason']) for r in triage)},'scan_strategy':{'selected':'PRIMARY_PLUS_SAME_FIXTURE_FOLLOWUP; DAILY_STABLE_ODDSPAPI_COHORT','canonical_hours_weekday_bangkok':[15,18,21,0],'canonical_hours_weekend_bangkok':[15,18,21,0],'midnight_belongs_to_previous_football_day':True,'schedule_version':'BKK_28_SLOTS_V4','schedule_effective_day':'2026-10-13','on_time_tolerance_minutes':30,'missed_backfill':False,'minimum_request_spacing_minutes':15,'oddspapi_requests_per_run_max':2,'oddspapi_requests_per_utc_day_max':8,'oddspapi_research_requests_per_utc_month_max':240,'account_limit':250,'account_safety_reserve':10,'account_gate':'READ_UNMETERED_ACCOUNT_BEFORE_BILLABLE_REQUESTS; SHARED_ACCOUNT_REMAINING_AND_RESERVE_GATE','propline':'UNMETERED_REQUESTS_NOT_ASSUMED; FREE_FALLBACK_CATALOG_PLUS_SPORT_CALLS; NO_AUTOMATIC_HTTP_RETRY; STOP_ON_429_401_403','cron_timing_guaranteed':False,'alternatives':[{'mode':'ONE_DAILY_SCAN','benefit':'lower request count and broader price-state sampling','cost':'no same-day movement evidence'}, {'mode':'PRIMARY_PLUS_FOLLOWUP','benefit':'comparable same-source snapshots; chosen','cost':'smaller stable paid cohort; delays reduce prekickoff coverage'}, {'mode':'KICKOFF_RELATIVE','benefit':'more comparable horizons','cost':'per-fixture scheduling and extra batches; not enabled without measured free budget'}]}}
    p=root/'reports/research_v2_end_to_end_audit.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

if __name__=='__main__':print(json.dumps({k:v for k,v in build().items() if k not in ('ft_triage','movement_evaluation')}))
