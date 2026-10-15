"""Coverage metrics per fixture-slot, never per retained historical ladder line."""
from collections import defaultdict
from zoneinfo import ZoneInfo
from research.historical_backfill.reconstruct import parse_time
from research.historical_backfill.offline_stats import three_previews


def coverage_report(manifest,run):
    results={(r['fixture_id'],r['bookmaker']):r for r in run['results']}
    groups=defaultdict(list)
    for c in manifest['candidates']:
        for slot in c['missing_rounds']:
            labels=[('age_band',c['age_band']),('league',c['league']),('bookmaker',c['bookmaker']),
                    ('scan_slot',str(parse_time(slot).astimezone(ZoneInfo('Asia/Bangkok')).hour))]
            labels += [('age_window',str(n)) for n in (7,14,30) if 1<=c['age_days']<=n]
            result=results.get((c['fixture_id'],c['bookmaker']))
            rows=result.get('reconstructed',[]) if result else []
            valid=any(r.get('slot_utc') and parse_time(r['slot_utc'])==parse_time(slot)
                      and r['status']=='COMPLETE' for r in rows)
            for key in labels:groups[key].append((c['fixture_id'],bool(result),valid))
    for key in [('age_window',str(n)) for n in (7,14,30)]+[('age_band','8_14')]:groups[key]
    out=[]
    for (dimension,value),rows in sorted(groups.items()):
        tested=sum(t for _,t,_ in rows); complete=sum(v for _,_,v in rows)
        out.append(dict(dimension=dimension,value=value,planned_fixture_slots=len(rows),
            planned_unique_fixtures=len({f for f,_,_ in rows}),tested_fixture_slots=tested,
            complete_fixture_slots=complete,coverage=complete/tested if tested else None,
            status='MEASURED' if tested else 'NO_CANDIDATES' if not rows else 'NOT_TESTED'))
    return out


def statistical_preview(manifest,run,observations):
    """Condition on observed exact lines; never call the historical ladder a past mainline."""
    candidates={(c['fixture_id'],c['bookmaker']):c for c in manifest['candidates']}
    lines=defaultdict(set); observed={}
    for o in observations:
        key=(o.get('fixture_id'),o.get('bookmaker'));c=candidates.get(key)
        if not c:continue
        lines[key].add(o['ah']['home_line'])
        slot=o.get('scheduled_target_at')
        if not slot or parse_time(slot).isoformat() not in c['existing_rounds']:continue
        if not 0 <= (parse_time(o['observed_at'])-parse_time(slot)).total_seconds() <= 9000:continue
        ident=(key,parse_time(slot),o['ah']['home_line'])
        item=dict(fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],market='AH',line=o['ah']['home_line'],
            slot_utc=slot,data_origin='OBSERVED',status='COMPLETE',actual_price_timestamp=None,
            actual_observed_at=o['observed_at'],ft_status=c['ft_status'],ft_score=c['ft_score'],
            quotes={s:dict(price=o['ah'][s+'_price'],quote_at_utc=None) for s in ('home','away')})
        if ident not in observed or parse_time(o['observed_at'])<parse_time(observed[ident]['actual_observed_at']):observed[ident]=item
    backfilled=[r for item in run['results'] for r in item.get('reconstructed',[])
        if r['status']=='COMPLETE' and r['line'] in lines[(r['fixture_id'],r['bookmaker'])]]
    previews=three_previews(list(observed.values()),backfilled)
    previews.update(selection_rule='EXACT_LINES_SEEN_IN_EXISTING_OBSERVATIONS_DESCRIPTIVE_CONDITIONED_SUBSET',
                    mainline_at_past_slot_proven=False,
                    newly_discovered_database_fixtures=0,
                    added_snapshot_rows=previews['combined_offline']['snapshot_rows']-previews['observed_only']['snapshot_rows'],
                    added_distinct_fixtures_with_target_rows=previews['combined_offline']['unique_fixtures']-previews['observed_only']['unique_fixtures'],
                    no_predictive_edge_claim=True)
    return previews
