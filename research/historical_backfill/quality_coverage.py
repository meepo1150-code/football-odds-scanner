"""Descriptive coverage after applying balanced-line price selection."""
from collections import defaultdict, Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from research.historical_backfill.reconstruct import parse_time
from research.historical_backfill.representative import select, POLICY


def coverage(manifest, result, catalog, now=None):
    now=now or datetime.now(timezone.utc)
    bkk=ZoneInfo('Asia/Bangkok')
    index={(r['fixture_id'],r['bookmaker']):r for r in result['results']}
    groups=defaultdict(list);slots=[];fixtures=[];counts=Counter()
    for c in manifest['candidates']:
        item=index.get((c['fixture_id'],c['bookmaker']))
        age=(now.astimezone(bkk).date()-parse_time(c['kickoff']).astimezone(bkk).date()).days
        band='0_7' if age<=7 else '8_14' if age<=14 else '15_30' if age<=30 else '31_plus'
        fixture_slots=[]
        for slot in c['missing_rounds']:
            rs=[r for r in item.get('reconstructed',[]) if parse_time(r['slot_utc'])==parse_time(slot)] if item else []
            pick=select(rs,fixture_id=c['fixture_id'],bookmaker=c['bookmaker'],kickoff=c['kickoff'],slot=slot,catalog=catalog)
            if not item:pick.update(status='NOT_TESTED',reason='FIXTURE_NOT_EVALUATED')
            slots.append(pick);fixture_slots.append(pick);counts.update(pick['rejection_counts'])
            record=dict(fixture_id=c['fixture_id'],tested=bool(item),
                ah=bool(item and item['historical_ah_available']),
                usable=sum(r['status']=='COMPLETE' for r in rs),balanced=pick['status']=='BALANCED_LINE')
            labels=[('league',c['league']),('football_day',c['football_day']),('age_band_actual',band),
                    ('scan_slot_bangkok',str(parse_time(slot).astimezone(bkk).hour)),('bookmaker',c['bookmaker'])]
            labels += [('age_window_actual',str(n)) for n in (7,14,30) if 0<=age<=n]
            for label in labels:groups[label].append(record)
        fixtures.append(dict(fixture_id=c['fixture_id'],home=c['home'],away=c['away'],league=c['league'],
            kickoff=c['kickoff'],football_day=c['football_day'],bookmaker=c['bookmaker'],age_days_actual=age,
            tested=bool(item),historical_ah_available=bool(item and item['historical_ah_available']),
            target_slots=len(fixture_slots),balanced_slots=sum(s['status']=='BALANCED_LINE' for s in fixture_slots),
            usable_line_snapshots=sum(r['status']=='COMPLETE' for r in item.get('reconstructed',[])) if item else 0))
    breakdown=[]
    for (dimension,value),rows in sorted(groups.items()):
        tested=sum(r['tested'] for r in rows);selected=sum(r['balanced'] for r in rows)
        breakdown.append(dict(dimension=dimension,value=value,planned_fixtures=len({r['fixture_id'] for r in rows}),
            tested_fixtures=len({r['fixture_id'] for r in rows if r['tested']}),
            ah_fixtures=len({r['fixture_id'] for r in rows if r['ah']}),planned_fixture_slots=len(rows),
            tested_fixture_slots=tested,balanced_slots=selected,usable_line_snapshots=sum(r['usable'] for r in rows),
            coverage_of_tested=selected/tested if tested else None,
            coverage_of_planned=selected/len(rows) if rows else None))
    return dict(policy=POLICY,as_of=now.isoformat(),planned_fixtures=len(fixtures),tested_fixtures=len(result['results']),
        ah_fixtures=sum(f['historical_ah_available'] for f in fixtures),balanced_fixtures=sum(f['balanced_slots']>0 for f in fixtures),
        target_slots=len(slots),balanced_slots=sum(s['status']=='BALANCED_LINE' for s in slots),
        unresolved_slots=sum(s['status']=='MAINLINE_UNRESOLVED' for s in slots),
        untested_slots=sum(s['status']=='NOT_TESTED' for s in slots),
        usable_line_snapshots=sum(f['usable_line_snapshots'] for f in fixtures),
        rejected_lines=sum(counts.values()),rejection_counts=dict(counts),fixtures=fixtures,slots=slots,breakdown=breakdown)
