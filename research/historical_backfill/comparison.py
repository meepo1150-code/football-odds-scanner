"""Offline reconstruction/QA, retaining every exact reviewed market line."""
from research.historical_backfill.reconstruct import reconstruct_slot,parse_time
from research.historical_backfill.offline_stats import deduplicate


def reconstruct_candidate(candidate, normalized, *, state_semantics_verified=False, max_age_seconds=3600):
    if not state_semantics_verified:
        return [dict(fixture_id=candidate['fixture_id'],status='ACTIVE_TIMESTAMP_SEMANTICS_UNVERIFIED',data_origin='BACKFILLED')]
    rows=[]
    for slot in candidate['missing_rounds']:
        if not normalized:
            rows.append(dict(fixture_id=candidate['fixture_id'],slot_utc=slot,status='NO_HISTORICAL_DATA',data_origin='BACKFILLED'))
        for market in normalized:
            if market['fixture_id']!=candidate['fixture_id'] or market['bookmaker']!=candidate['bookmaker']:
                raise ValueError('market fixture/bookmaker mismatch')
            r=reconstruct_slot(fixture_id=candidate['fixture_id'],kickoff=candidate['kickoff'],
                slot=slot,source=market['source'],bookmaker=market['bookmaker'],market='AH',
                line=market['line'],selections=market['selections'],max_age_seconds=max_age_seconds)
            r.update(league=candidate['league'],home=candidate['home'],away=candidate['away'],
                market_id=market['market_id'],ft_status=candidate['ft_status'],ft_score=candidate['ft_score'],
                quality_status=r['status'],settlement_status='READY' if r['status']=='COMPLETE' and candidate['ft_status']=='VERIFIED_EXACT_ID' else 'NOT_SETTLED',
                catalog_evidence=market['catalog_evidence'],raw_record_hash=market.get('raw_record_hash'),
                line_selection='EXACT_REVIEWED_LINE_NOT_ASSUMED_MAINLINE')
            r['actual_price_timestamp']={side:q['quote_at_utc'] for side,q in r.get('quotes',{}).items()}
            rows.append(r)
    complete=[r for r in rows if r['status']=='COMPLETE']
    deduplicate(complete) # conflicting duplicate semantic markets fail closed
    return rows


def compare_observation(observed,normalized,*,state_semantics_verified=False,max_age_seconds=3600):
    if not state_semantics_verified:return dict(status='ACTIVE_TIMESTAMP_SEMANTICS_UNVERIFIED')
    if parse_time(observed['observed_at'])>=parse_time(observed['kickoff']):raise ValueError('post kickoff observed row')
    markets=[m for m in normalized if m['fixture_id']==observed['fixture_id'] and m['bookmaker']==observed['bookmaker'] and m['line']==observed['ah']['home_line']]
    comparisons=[]
    for m in markets:
        r=reconstruct_slot(fixture_id=observed['fixture_id'],kickoff=observed['kickoff'],slot=observed['observed_at'],source=m['source'],bookmaker=m['bookmaker'],market='AH',line=m['line'],selections=m['selections'],max_age_seconds=max_age_seconds)
        comparisons.append(dict(market_id=m['market_id'],status=r['status'],
            observed_at=observed['observed_at'],scheduled_target_at=observed.get('scheduled_target_at'),
            observed_price_changed_at=observed.get('price_changed_at'),
            home_delta=r['quotes']['home']['price']-observed['ah']['home_price'] if r['status']=='COMPLETE' else None,
            away_delta=r['quotes']['away']['price']-observed['ah']['away_price'] if r['status']=='COMPLETE' else None,
            historical_quotes=r.get('quotes'),difference_is_not_automatically_error=True))
    return dict(status='COMPARED' if comparisons else 'NO_SAME_BOOKMAKER_LINE',comparisons=comparisons)
