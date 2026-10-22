from __future__ import annotations

from .research_population import in_scope, exclusion_reason, POLICY
import json, math, re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from .result_recovery_lifecycle import retired_ids
from .research_v2_fixture_identity import build_bridge, project
from .observation_movement import describe
from .asian_settlement import settle_asian_handicap
from .research_v2_integrity import trusted_snapshot
SNAPSHOTS=Path('data/normalized/europe_pinnacle_research_v2_snapshots.jsonl');RESULTS=Path('data/normalized/oddspapi_finished_results.jsonl');AUDIT=Path('data/normalized/europe_pinnacle_research_v2_audit.jsonl');OUTCOMES=Path('data/normalized/research_v2_pattern_outcomes.jsonl');REPORT=Path('reports/research_v2_pattern_statistics.json');MISSING_LEDGER=Path('reports/research_v2_missing_ft_ledger.json')
def _rows(path):
    if not path.exists():return []
    out=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try:x=json.loads(line)
        except (json.JSONDecodeError,TypeError):continue
        if isinstance(x,dict):out.append(x)
    if path.name==SNAPSHOTS.name:
        from .pinnwire_result_join import enrich_snapshot_names, API_FIXTURES_PATH
        return enrich_snapshot_names(out,_rows(path.with_name(API_FIXTURES_PATH.name)))
    return out
def _num(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None
def _group_key(key,value):
    # Valid quarter-grid lines are numerically identical across JSON int/float/string.
    # This only formats a validated line; it never rounds an invalid market line.
    if key=='ah_line':
        number=_num(value)
        if number is not None and abs(number*4-round(number*4))<=1e-9:
            return '0' if number==0 else format(number,'.15g')
    return str(value)

def _score(r):
    h,a=r.get('ft_home_goals'),r.get('ft_away_goals')
    if type(h) is not int or type(a) is not int:return None
    return (h,a) if h>=0 and a>=0 else None
def _prematch_order(row):
    """Timestamp ordering is chronological across UTC offsets; missing is unsafe."""
    from .research_v2_slots import stamp
    observed, kickoff = stamp(row.get('observed_at')), stamp(row.get('kickoff'))
    if observed is None or kickoff is None or observed >= kickoff:
        return None
    ah = row.get('ah') or {}
    if not isinstance(ah, dict):return None
    side = row.get('favorite_side')
    hl,al,hp,ap,sl,sp = (_num(ah.get(k)) for k in
        ('home_line','away_line','home_price','away_price','selected_side_line','selected_side_price'))
    if any(x is None for x in (hl,al,hp,ap,sl,sp)) or side not in ('H','A'):return None
    if abs(hl+al)>1e-9 or abs(sl*4-round(sl*4))>1e-9 or min(hp,ap)<=1:return None
    if abs(sl-(hl if side=='H' else al))>1e-9 or abs(sp-(hp if side=='H' else ap))>1e-9:return None
    return (observed, str(row.get('provider') or ''), str(row.get('source_fixture_id') or row.get('fixture_id') or ''))
def _prob_bucket(v):
    p=_num(v)
    if p is None:return 'UNKNOWN'
    lo=int((p*100)//5)*5;return f'{lo:02d}-{lo+4:02d}%'
def _price_bucket(v):
    x=_num(v)
    if x is None:return 'UNKNOWN'
    if x<1.80:return '<1.80'
    if x>2.20:return '>2.20'
    if x<1.90:return '1.80-1.89'
    if x<2.00:return '1.90-1.99'
    if x<2.10:return '2.00-2.09'
    return '2.10-2.20'
def _core(v):
    x=_num(v);return x is not None and 1.80<=x<=2.20
def _ou25(s,h,a):
    # Goal-frequency statistics require FT only; priced returns require an exact,
    # identifiable prematch 2.5 quote. Never relabel a mainline alternate total.
    ou=s.get('ou') or s.get('over_under_2_5') or s.get('ou_2_5') or {}
    over=under=None
    reason='MISSING_QUOTE'
    quote_time=None
    if isinstance(ou,dict) and ou:
        line=_num(ou.get('line'))
        op=_num(ou.get('over_price',ou.get('over')))
        up=_num(ou.get('under_price',ou.get('under')))
        reason='NOT_EXACT_2_5' if line!=2.5 else 'INVALID_TWO_SIDED_PRICES'
        if line==2.5 and op is not None and up is not None and op>1 and up>1:
            reason='UNVERIFIED_PROVENANCE_OR_TIMESTAMP'
            try:
                observed=datetime.fromisoformat(str(s.get('observed_at')).replace('Z','+00:00'))
                kickoff=datetime.fromisoformat(str(s.get('kickoff')).replace('Z','+00:00'))
                valid_time=observed.tzinfo is not None and kickoff.tzinfo is not None and observed<kickoff
            except (TypeError,ValueError):valid_time=False
            if valid_time and s.get('source_semantics') and s.get('bookmaker'):
                over,under=op,up;quote_time=s['observed_at'];reason='VERIFIED_EXACT_2_5_PREMATCH'
    total=h+a
    return {'ou25_over_price':over,'ou25_under_price':under,'ou25_quote_status':reason,'ou25_observed_at':quote_time,'ou25_bookmaker':s.get('bookmaker') if over is not None else None,'ou25_source_semantics':s.get('source_semantics') if over is not None else None,'ou25_result':'OVER' if total>2.5 else 'UNDER','total_goals':total}
def _result_index(rows):
    g=defaultdict(list)
    for r in rows:
        if r.get('fixture_id') and _score(r) is not None:g[str(r['fixture_id'])].append(r)
    idx={};ambiguous=set()
    for fid,items in g.items():
        scores={_score(x) for x in items}
        if len(scores)==1:idx[fid]=items[-1]
        else:ambiguous.add(fid)
    for fid in ambiguous:
        idx.pop(fid, None)  # Conflicted provider IDs must never settle a canonical fixture.
    return idx,ambiguous
def _price_result(s):return {'FULL_WIN':'WIN','HALF_WIN':'HALF_WIN','PUSH':'PUSH','HALF_LOSS':'HALF_LOSS','FULL_LOSS':'LOSS'}.get(s,'UNSETTLED')
def _movement(first,last):
    if str(first.get('favorite_side') or '').upper()!=str(last.get('favorite_side') or '').upper():return 'FAVORITE_SWITCH'
    fa,la=first.get('ah') or {},last.get('ah') or {};fl,ll=_num(fa.get('selected_side_line')),_num(la.get('selected_side_line'));fp,lp=_num(fa.get('selected_side_price')),_num(la.get('selected_side_price'))
    if fl is None or ll is None:return 'AH_LINE_UNKNOWN'
    line='AH_LINE_UNCHANGED' if ll==fl else ('AH_FAVORITE_LINE_STRONGER' if ll<fl else 'AH_FAVORITE_LINE_WEAKER')
    if fp is None or lp is None:return line
    price='PRICE_FLAT' if abs(lp-fp)<.005 else ('PRICE_DOWN' if lp<fp else 'PRICE_UP')
    return f'{line}__{price}'
def _wilson(w,n):
    if not n:return [None,None]
    z=1.959963984540054;p=w/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;m=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return [round(100*(c-m),2),round(100*(c+m),2)]
def _sample(n):return 'VERY_LOW' if n<30 else 'DEVELOPING' if n<100 else 'MODERATE' if n<300 else 'STRONG_300_PLUS'
def _signal(n,roi,ci):
    return 'DESCRIPTIVE_ONLY'  # WR vs 50% is not an AH return benchmark.
def pending_age_counts(rows, now):
    counts={'active_overdue_ft_fixtures':0,'active_future_or_recent_ft_fixtures':0,'active_unknown_kickoff_ft_fixtures':0}
    for row in rows:
        if row.get('status') in {'RETIRED_UNRESOLVED','POSTPONED','CANCELLED','ABANDONED'} or row.get('retired_from_active_queue'):continue
        try:
            kickoff=datetime.fromisoformat(str(row.get('kickoff')).replace('Z','+00:00'))
            if kickoff.tzinfo is None:raise ValueError('timezone required')
        except (ValueError,TypeError):
            counts['active_unknown_kickoff_ft_fixtures']+=1
            continue
        key='active_overdue_ft_fixtures' if (now-kickoff).total_seconds()>=10800 else 'active_future_or_recent_ft_fixtures'
        counts[key]+=1
    return counts


def build(root=Path('.')):
    raw_snaps=_rows(root/SNAPSHOTS)
    # Never replace established statistics with a partial FT import when the
    # canonical price-snapshot population is absent. This is a hard safety gate.
    previous_path = root/REPORT
    if not raw_snaps and previous_path.exists():
        previous = json.loads(previous_path.read_text(encoding='utf-8'))
        if int(previous.get('settled_fixtures') or 0) > 0:
            return previous
    snaps=[x for x in raw_snaps if trusted_snapshot(x)];quarantined_snapshots=len(raw_snaps)-len(snaps);audits=_rows(root/AUDIT);results,ambiguous=_result_index(_rows(root/RESULTS));ag={(str(x.get('fixture_id')),str(x.get('observed_at'))):x for x in audits};grouped=defaultdict(list)
    scope_excluded=[x for x in snaps if not in_scope(x)]
    snaps=[x for x in snaps if in_scope(x)]
    blocked_results={str(x.get('fixture_id')) for x in _rows((root/RESULTS).with_suffix('.conflicts.jsonl'))}
    # Reviewed official home/away disagreements quarantine the odds identity;
    # even a symmetric final score cannot repair a mislabeled snapshot.
    from .research_v2_fixture_identity import utc
    for review in _rows(root/'data/research/selected_fixture_identity_conflicts.jsonl'):
        source=review.get('source') or {}
        if source.get('tier')!='A_OFFICIAL' or source.get('verification_method')!='MANUAL_WEB_REVIEW':continue
        exact=[s for s in snaps if s.get('fixture_id')==review.get('fixture_id')]
        if (exact and all((s.get('home'),s.get('away'),s.get('league'),utc(s.get('kickoff')))==
                         (review.get('home'),review.get('away'),review.get('league'),utc(review.get('kickoff'))) for s in exact)
            and (source.get('home'),source.get('away'),utc(source.get('kickoff')))==
                (review.get('away'),review.get('home'),utc(review.get('kickoff')))):
            blocked_results.add(str(review['fixture_id']))
    raw_provider_unresolved = len({str(s.get("fixture_id")) for s in snaps if str(s.get("fixture_id")) not in results or str(s.get("fixture_id")) in blocked_results})
    mapping, identity_report = build_bridge(snaps)
    # A result on an ID reused across different kickoff identities cannot
    # settle either date merely because it is the latest retained snapshot.
    blocked_results.update(r['fixture_id'] for r in identity_report['rejected']
                           if r.get('reason') == 'INCONSISTENT_IDENTITY' and r.get('fixture_id'))
    provider_fixture_ids = len({str(s.get('fixture_id')) for s in snaps})
    cross_provider_ids = {b['canonical_fixture_id'] for b in identity_report['bridges']
                          if len({r['provider'] for r in b['members']}) > 1}
    duplicate_ids = {b['canonical_fixture_id'] for b in identity_report['bridges']} - cross_provider_ids
    snaps = project(snaps, mapping)
    from .verified_fixture_lifecycle import verified_statuses
    lifecycle = {mapping.get(fid,fid):r for fid,r in verified_statuses(root,raw_snaps).items()}
    # Map exact source IDs only through the verified bridge. A conflict under
    # either source ID blocks the whole canonical match.
    results, ambiguous = _result_index(project(_rows(root/RESULTS), mapping))
    blocked_results = {mapping.get(fid, fid) for fid in blocked_results}
    for fid in blocked_results:results.pop(fid,None)
    ip = root/'reports/research_v2_fixture_identity.json'
    ip.parent.mkdir(parents=True,exist_ok=True)
    ip.write_text(json.dumps(identity_report,ensure_ascii=False,indent=2)+'\n')
    invalid_selection = [s for s in snaps if _prematch_order(s) is None]
    for s in snaps:
        if s.get('fixture_id') and _prematch_order(s) is not None:grouped[str(s['fixture_id'])].append(s)
    for ss in grouped.values():ss.sort(key=_prematch_order)
    retired={mapping.get(fid,fid) for fid in retired_ids(root)}
    outcomes=[];missing=0;missing_by_provider=Counter();unique_by_provider=Counter();excluded_derivative=0;missing_rows=[]
    for fid,ss in sorted(grouped.items()):
        provider=str(ss[-1].get('provider') or ('oddspapi' if str(ss[-1].get('source_semantics','')).startswith('CURRENT_ODDSPAPI_') else 'UNRESOLVED_PROVIDER'))
        unique_by_provider[provider]+=1
        last=ss[-1]
        derivative=bool(re.search(r'\((?:corners?|bookings?|cards?)\)',str(last.get('home') or '')+' '+str(last.get('away') or ''),re.I))
        if derivative:
            excluded_derivative+=1
            continue
        r=results.get(fid) if fid not in ambiguous else None
        if not r:
            missing+=1
            missing_by_provider[provider]+=1
            missing_rows.append({'fixture_id':fid,'provider':provider,'football_day':last.get('football_day'),'league':last.get('league'),'kickoff':last.get('kickoff'),'home':last.get('home'),'away':last.get('away'),'status':'IDENTITY_CONFLICT' if fid in ambiguous or fid in blocked_results else 'RETIRED_UNRESOLVED' if fid in retired else 'MISSING_FT','country':last.get('country'),'canonical_competition_id':last.get('canonical_competition_id'),'required_identity':'EXACT_FIXTURE_OR_VERIFIED_TEAM_LEAGUE_KICKOFF'})
            missing_rows[-1]['retired_from_active_queue']=fid in retired
            if fid in lifecycle and fid not in ambiguous and fid not in blocked_results:
                missing_rows[-1].update(status=lifecycle[fid]['status'],lifecycle_source_url=lifecycle[fid]['source']['url'])
            continue
        s=ss[-1];h,a=_score(r);fav=str(s.get('favorite_side') or '').upper();ah=s.get('ah') or {};one=s.get('one_x_two') or {};au=ag.get((str(s.get('source_fixture_id') or fid),str(s.get('observed_at'))),{});settle=None;profit_units=None;dog_profit_units=None
        try:
            settled=settle_asian_handicap(h,a,float(ah.get('selected_side_line')),float(ah.get('selected_side_price')),fav);settle=settled.settlement.value;profit_units=settled.profit_units
        except (TypeError,ValueError):pass
        try:
            dog_side='A' if fav=='H' else 'H' if fav=='A' else None
            if dog_side:
                dog=settle_asian_handicap(h,a,-float(ah.get('selected_side_line')),float(ah.get('opposite_side_price',ah.get('away_price') if fav=='H' else ah.get('home_price'))),dog_side);dog_profit_units=dog.profit_units
        except (TypeError,ValueError):pass
        price=ah.get('selected_side_price');market_side='HOME_FAVORITE' if fav=='H' else 'AWAY_FAVORITE' if fav=='A' else 'UNKNOWN'
        outcomes.append({'fixture_id':fid,'football_day':s.get('football_day'),'league':s.get('league'),'home':s.get('home'),'away':s.get('away'),'favorite_side':fav,'market_side':market_side,'favorite_team':s.get('home') if fav=='H' else s.get('away') if fav=='A' else None,'underdog_team':s.get('away') if fav=='H' else s.get('home') if fav=='A' else None,'favorite_1x2_price':one.get('home') if fav=='H' else one.get('away') if fav=='A' else None,'favorite_fair_probability':s.get('favorite_fair_probability'),'favorite_probability_bucket':_prob_bucket(s.get('favorite_fair_probability')),'ah_line':ah.get('selected_side_line'),'ah_price':price,'ah_price_bucket':_price_bucket(price),'ah_core_price':_core(price),'scan_count':len(ss),'first_ah_line':(ss[0].get('ah') or {}).get('selected_side_line'),'first_ah_price':(ss[0].get('ah') or {}).get('selected_side_price'),**describe(ss),'kickoff':s.get('kickoff'),'last_observed_at':s.get('observed_at'),'match_status':au.get('eligibility_status','UNCLASSIFIED'),'ft_home_goals':h,'ft_away_goals':a,'favorite_ah_settlement':settle,'favorite_profit_units':profit_units,'underdog_profit_units':dog_profit_units,'price_result':_price_result(settle),'price_winner_side':'FAVORITE' if settle in ('FULL_WIN','HALF_WIN') else 'UNDERDOG' if settle in ('FULL_LOSS','HALF_LOSS') else 'PUSH' if settle=='PUSH' else 'UNSETTLED','price_winner_home_away':('HOME' if fav=='H' else 'AWAY') if settle in ('FULL_WIN','HALF_WIN') else ('AWAY' if fav=='H' else 'HOME') if settle in ('FULL_LOSS','HALF_LOSS') else 'PUSH' if settle=='PUSH' else 'UNSETTLED','source_fixture_id':s.get('source_fixture_id'),'source_provider':s.get('provider'),'result_source_fixture_id':r.get('source_fixture_id'),'result_join':'VERIFIED_CROSS_PROVIDER_IDENTITY' if fid in cross_provider_ids else 'VERIFIED_PROVIDER_FALLBACK_ALIAS' if fid in duplicate_ids else 'EXACT_FIXTURE_ID_ONLY','research_only':True,**_ou25(s,h,a)})
    # Preserve previously settled fixtures when a fresh snapshot selection is partial.
    # New verified FT results use the existing settlement logic above; no new formula.
    prior_outcomes=_rows(root/OUTCOMES)
    current_by_id={str(row['fixture_id']):row for row in outcomes}
    for old in prior_outcomes:
        fid=str(old.get('fixture_id') or '')
        if fid and fid not in current_by_id:
            current_by_id[fid]=old
    outcomes=list(current_by_id.values())
    settled_ids=set(current_by_id)
    missing_rows=[row for row in missing_rows if str(row['fixture_id']) not in settled_ids]
    missing=len(missing_rows)
    retired_missing=sorted(r['fixture_id'] for r in missing_rows if r['fixture_id'] in retired)
    ledger=root/MISSING_LEDGER;ledger.parent.mkdir(parents=True,exist_ok=True);ledger.write_text(json.dumps({'schema_version':'1.0','missing_ft_count':len(missing_rows),'excluded_derivative_markets':excluded_derivative,'fixtures':missing_rows},ensure_ascii=False,indent=2),encoding='utf-8')
    p=root/OUTCOMES;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in outcomes),encoding='utf-8')
    def aggregate(keys,core_only=False):
        groups=defaultdict(list)
        for x in outcomes:
            if core_only and not x['ah_core_price']:continue
            groups[tuple(_group_key(k,x.get(k,'UNKNOWN')) for k in keys)].append(x)
        out=[]
        for vals,rs in groups.items():
            pc=Counter(x['price_result'] for x in rs);n=sum(pc[x] for x in ('WIN','HALF_WIN','PUSH','HALF_LOSS','LOSS'));favwin=pc['WIN']+pc['HALF_WIN'];dogwin=pc['LOSS']+pc['HALF_LOSS'];ci=_wilson(favwin,n);profits=[_num(x.get('favorite_profit_units')) for x in rs];profits=[x for x in profits if x is not None];profit=sum(profits);roi=(100*profit/len(profits)) if profits else None;dogprofits=[_num(x.get('underdog_profit_units')) for x in rs];dogprofits=[x for x in dogprofits if x is not None];dogprofit=sum(dogprofits);dogroi=(100*dogprofit/len(dogprofits)) if dogprofits else None
            out.append({**dict(zip(keys,vals)),'n':len(rs),'settled_n':n,'full_win':pc['WIN'],'half_win':pc['HALF_WIN'],'push':pc['PUSH'],'half_loss':pc['HALF_LOSS'],'full_loss':pc['LOSS'],'favorite_price_win_n':favwin,'underdog_price_win_n':dogwin,'favorite_price_win_pct':round(100*favwin/n,2) if n else None,'underdog_price_win_pct':round(100*dogwin/n,2) if n else None,'push_pct':round(100*pc['PUSH']/n,2) if n else None,'favorite_profit_units':round(profit,4),'favorite_roi_pct':round(roi,2) if roi is not None else None,'underdog_profit_units':round(dogprofit,4) if dogprofits else None,'underdog_roi_pct':round(dogroi,2) if dogroi is not None else None,'favorite_win_wilson95_low':ci[0],'favorite_win_wilson95_high':ci[1],'sample_label':_sample(n),'signal_label':_signal(n,roi,ci)})
        return sorted(out,key=lambda x:-x['n'])
    def aggregate_ou(keys,core_only=False):
        groups=defaultdict(list)
        for x in outcomes:
            if core_only and not x['ah_core_price']:continue
            groups[tuple(_group_key(k,x.get(k,'UNKNOWN')) for k in keys)].append(x)
        out=[]
        for vals,rs in groups.items():
            n=len(rs);over=sum(x.get('ou25_result')=='OVER' for x in rs);under=sum(x.get('ou25_result')=='UNDER' for x in rs);priced=[x for x in rs if x.get('ou25_over_price') is not None and x.get('ou25_under_price') is not None]
            op=[x['ou25_over_price']-1 if x.get('ou25_result')=='OVER' else -1 for x in priced];up=[x['ou25_under_price']-1 if x.get('ou25_result')=='UNDER' else -1 for x in priced]
            out.append({**dict(zip(keys,vals)),'n':n,'over_2_5_n':over,'under_2_5_n':under,'over_2_5_pct':round(100*over/n,2) if n else None,'under_2_5_pct':round(100*under/n,2) if n else None,'ou25_priced_n':len(priced),'over_2_5_profit_units':round(sum(op),4) if op else None,'over_2_5_roi_pct':round(100*sum(op)/len(op),2) if op else None,'under_2_5_profit_units':round(sum(up),4) if up else None,'under_2_5_roi_pct':round(100*sum(up)/len(up),2) if up else None,'sample_label':_sample(n)})
        return sorted(out,key=lambda x:-x['n'])
    baseline=aggregate(['market_side','ah_line'],True);bmap={(x['market_side'],x['ah_line']):x.get('favorite_price_win_pct') for x in baseline};by_state=aggregate(['market_side','ah_line','ah_price_bucket'],True)
    for x in by_state:
        b=bmap.get((x['market_side'],x['ah_line']));x['baseline_favorite_price_win_pct']=b;x['difference_vs_line_baseline_pp']=round(x['favorite_price_win_pct']-b,2) if b is not None and x['favorite_price_win_pct'] is not None else None
    payload={'schema_version':'2.9','population_policy':POLICY,'scope_excluded_snapshot_rows':len(scope_excluded),'scope_excluded_fixture_ids':sorted({str(x.get('fixture_id')) for x in scope_excluded}),'scope_exclusion_counts':dict(Counter(exclusion_reason(x) for x in scope_excluded)),'provider_fixture_ids':provider_fixture_ids,'raw_unresolved_provider_fixture_ids':raw_provider_unresolved,'fixture_identity_bridges':identity_report['bridges'],'collapsed_provider_fixture_ids':identity_report['collapsed_provider_ids'],'snapshot_selection':'LATEST_VERIFIED_OBSERVATION_THEN_SOURCE_FIXTURE_ID_TIEBREAK','classification':'RESEARCH_V2_AH_MARKET_STATE_STATISTICS','statistical_population_policy':'VERIFIED_FT_ONLY; RAW UNRESOLVED FIXTURES QUARANTINED AND EXCLUDED','generated_at':datetime.now(timezone.utc).isoformat(),'research_only':True,'recommendation_semantics':False,'signal_policy':'DESCRIPTIVE_ONLY; NO EDGE TEST FROM WIN RATE; FROZEN PROMOTION GATES UNCHANGED','primary_market':'ASIAN_HANDICAP','core_ah_decimal_odds_range':[1.80,2.20],'price_buckets':['1.80-1.89','1.90-1.99','2.00-2.09','2.10-2.20'],'one_x_two_role':'CONTEXT_FAIR_PROBABILITY_ONLY','price_win_definition':'ASIAN_HANDICAP_SETTLEMENT_ONLY','ou25_source':'EXACT_2_5_TWO_SIDED_PREMATCH_WITH_PROVENANCE_ONLY','ou25_frequency_population':'VERIFIED_FT_GROUPED_BY_AH_STATE; PRICED_RETURNS_USE_SEPARATE_VERIFIED_QUOTE_N','ou25_quote_status_counts':dict(Counter(x['ou25_quote_status'] for x in outcomes)),'snapshot_rows':len(snaps),'raw_snapshot_rows':len(raw_snaps),'quarantined_snapshot_rows':quarantined_snapshots,'quarantine_policy':'LEGACY_PROPLINE_EXCLUDED; VERIFIED_PINNACLE_TWO_SIDED_CORE_MAINLINE_ALLOWED','unique_snapshot_fixtures':len(grouped),'settled_fixtures':len(outcomes),'core_price_settled_fixtures':sum(x['ah_core_price'] for x in outcomes),'missing_result_fixtures':0,'raw_unresolved_ft_fixtures':missing,'active_unresolved_ft_fixtures':missing-len(retired_missing),'retired_unresolved_ft_fixtures':len(retired_missing),'retired_unresolved_fixture_ids':retired_missing,'excluded_missing_ft_from_statistical_population':missing,'excluded_derivative_markets_from_ft_completeness':excluded_derivative,'eligible_statistical_fixtures':len(outcomes),'ft_completeness_pct':100.0,'missing_result_fixtures_by_provider':{},'unique_snapshot_fixtures_by_provider':dict(sorted(unique_by_provider.items())),'pinnwire_missing_result_fixtures':0,'non_pinnwire_missing_result_fixtures':0,'raw_unresolved_ft_by_provider':dict(sorted(missing_by_provider.items())),'raw_pinnwire_unresolved_ft':missing_by_provider.get('pinnwire',0),'raw_non_pinnwire_unresolved_ft':missing-missing_by_provider.get('pinnwire',0),'ambiguous_result_fixtures':len(ambiguous),'baseline_by_market_side_line':baseline,'market_state_by_side_line_price':by_state,'market_state_by_side_line_price_probability':aggregate(['market_side','ah_line','ah_price_bucket','favorite_probability_bucket'],True),'market_state_by_side_line_price_movement':aggregate(['market_side','ah_line','ah_price_bucket','movement'],True),'all_by_movement':aggregate(['movement']),'over_under_2_5_by_ah_line':aggregate_ou(['market_side','ah_line'],True),'over_under_2_5_by_ah_line_price':aggregate_ou(['market_side','ah_line','ah_price_bucket'],True)}
    payload['identity_group_semantics']='PROVIDER_LOCAL_FIXTURE_IDS_PLUS_VERIFIED_BRIDGES; UNLINKED_PROVIDER_IDS_MAY_REFER_TO_SAME_REAL_MATCH'
    payload['snapshot_selection']='LATEST_VALID_STRICT_PREMATCH_OBSERVATION_UTC_THEN_PROVIDER_SOURCE_ID_TIEBREAK'
    payload['invalid_statistical_snapshot_rows']=len(invalid_selection)
    payload['wr_definition']='(FULL_WIN + HALF_WIN) / ALL_SETTLED_INCLUDING_PUSH; HALF_WIN_IS_POSITIVE_RETURN_EVENT; SEE_SEPARATE_HALF_COUNTS_AND_ROI'
    payload['ft_completeness_denominator']=len(outcomes)+missing
    payload['ft_completeness_pct']=round(100*len(outcomes)/(len(outcomes)+missing),2) if len(outcomes)+missing else None
    payload['ft_completeness_population']='ALL_ELIGIBLE_IDENTITY_GROUPS_INCLUDING_RETIRED_AND_CONFLICTED; NOT_VERIFIED_SUBSET_ONLY'
    payload['statistical_subset_ft_completeness_pct']=100.0 if outcomes else None
    payload['identity_conflict_ft_fixtures']=sum(r['status']=='IDENTITY_CONFLICT' for r in missing_rows)
    payload['verified_non_ft_lifecycles']={fid:{'status':r['status'],'source_url':r['source']['url']} for fid,r in lifecycle.items()}
    payload['postponed_cancelled_abandoned_fixtures']=sum(r['status'] in {'POSTPONED','CANCELLED','ABANDONED'} for r in missing_rows)
    payload['verified_cross_provider_canonical_fixtures']=len(cross_provider_ids)
    payload['verified_same_provider_duplicate_fixtures']=len(duplicate_ids)
    payload['unlinked_provider_fixture_groups']=len(grouped)-identity_report['bridged_matches']
    payload['movement_classification_counts']=dict(Counter(x['movement'] for x in outcomes))
    payload['line_grouping_semantics']='EXACT_NUMERIC_QUARTER_LINE; INT_FLOAT_STRING_AND_SIGNED_ZERO_EQUIVALENT; NO_INVALID_LINE_ROUNDING'
    payload['price_bucket_intervals']=['[1.80,1.90)','[1.90,2.00)','[2.00,2.10)','[2.10,2.20]']
    payload.update(pending_age_counts(missing_rows,datetime.now(timezone.utc)))
    # Monotonic FT safety: partial result imports must never reduce settled coverage.
    if (root/REPORT).exists():
        prior=json.loads((root/REPORT).read_text(encoding='utf-8'))
        if int(prior.get('settled_fixtures') or 0)>int(payload.get('settled_fixtures') or 0):
            return prior
    q=root/REPORT;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');return payload
if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False))
