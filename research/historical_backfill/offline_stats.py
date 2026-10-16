"""Offline descriptive stats. Snapshot observations are not independent fixtures."""
from collections import Counter
from odds_scanner.asian_settlement import settle_asian_handicap
from research.historical_backfill.reconstruct import finite, parse_time

BANDS=((1.8,1.9),(1.9,2.0),(2.0,2.1),(2.1,2.2))


def identity(r):
    return (r['fixture_id'],parse_time(r['slot_utc']),r['bookmaker'],r['market'],r['line'])


def deduplicate(rows):
    groups={}
    for r in rows:
        key=identity(r)
        if key in groups and groups[key] != r:
            raise ValueError('conflicting duplicate snapshot')
        groups[key]=r
    return list(groups.values())


def preview_statistics(rows):
    rows=deduplicate(rows)
    for r in rows:
        if r.get('status')!='COMPLETE':continue
        if not finite(r['line']) or abs(r['line']*4-round(r['line']*4))>1e-8:
            raise ValueError('invalid AH line')
        if r.get('data_origin')=='BACKFILLED':
            at,ko=parse_time(r['slot_utc']),parse_time(r['kickoff_utc'])
            if at>=ko:raise ValueError('post kickoff slot')
            for side in ('home','away'):
                q=r['quotes'][side];ts=parse_time(q['quote_at_utc'])
                if ts>at or ts>=ko or q.get('active') is not True:
                    raise ValueError('invalid backfilled quote state')
        elif r.get('data_origin')!='OBSERVED':
            raise ValueError('data origin required')
    out=[]
    for lo,hi in BANDS:
        selected=[]
        for r in rows:
            score=r.get('ft_score')
            if r.get('status')!='COMPLETE' or r.get('ft_status')!='VERIFIED_EXACT_ID' or not isinstance(score,list) or len(score)!=2 or not all(type(n) is int and n>=0 for n in score):continue
            for side in ('home','away'):
                p=r['quotes'][side]['price']
                if finite(p) and lo<=p and (p<hi or hi==2.2 and p==hi):
                    line=r['line'] if side=='home' else -r['line']
                    bet=settle_asian_handicap(*score,line,p,'H' if side=='home' else 'A')
                    selected.append((r,bet))
        counts=Counter(b.settlement.value for _,b in selected)
        wins=counts['FULL_WIN']+0.5*counts['HALF_WIN']
        losses=counts['FULL_LOSS']+0.5*counts['HALF_LOSS']
        out.append(dict(band=f'[{lo:.2f},{hi:.2f}'+(']' if hi==2.2 else ')'),
            selection_observations=len(selected),fixture_slot_markets=len({identity(r) for r,_ in selected}),
            unique_fixtures=len({r['fixture_id'] for r,_ in selected}),settlements=dict(counts),
            win_rate_half_stake_excluding_pushes=wins/(wins+losses) if wins+losses else None,
            profit_units=sum(b.profit_units for _,b in selected)))
    return dict(snapshot_rows=len(rows),unique_fixtures=len({r['fixture_id'] for r in rows}),bands=out,
                inference='DESCRIPTIVE_ONLY_NO_INDEPENDENCE_OR_EDGE_CLAIM')


def three_previews(observed,backfilled):
    observed=deduplicate(observed);backfilled=deduplicate(backfilled)
    present={identity(r) for r in observed}
    added=[r for r in backfilled if identity(r) not in present]
    return dict(observed_only=preview_statistics(observed),backfilled_only=preview_statistics(backfilled),
                combined_offline=preview_statistics(observed+added),observed_precedence_overlaps=len(backfilled)-len(added))
