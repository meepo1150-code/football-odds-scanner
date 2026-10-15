"""Conservative OddsPapi v4 offline adapter. Catalog required; no ID/name guessing."""
import hashlib
import json
from research.historical_backfill.reconstruct import finite, parse_time


def normalize(payload, candidate, catalog, *, active_semantics_verified=False):
    if payload.get('fixtureId') != candidate['fixture_id']:
        raise ValueError('fixture ID mismatch')
    if not active_semantics_verified:
        raise ValueError('ACTIVE_TIMESTAMP_SEMANTICS_UNVERIFIED')
    markets = payload.get('bookmakers',{}).get(candidate['bookmaker'],{}).get('markets',{})
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    result=[]
    # This mapping must be prepared from the pinned official market catalog, with
    # full-match scope and signed HOME line explicitly reviewed. Never infer from IDs.
    for meta in catalog:
        if meta.get('review_status') != 'VERIFIED_FULL_MATCH_AH_HOME_LINE':continue
        line=meta['home_line']
        if not finite(line) or abs(line*4-round(line*4))>1e-8:raise ValueError('invalid quarter line')
        market=markets.get(str(meta['market_id']))
        if not market:continue
        sides={}
        for side in ('home','away'):
            raw=market.get('outcomes',{}).get(str(meta[side+'_outcome_id']),{}).get('players',{}).get('0',[])
            if not isinstance(raw,list):raise ValueError('unsupported ticks shape')
            ticks=[]
            for tick in raw:
                timestamp=parse_time(tick['createdAt']).isoformat()
                # Invalid/inactive latest states are retained to prevent rollback.
                ticks.append(dict(created_at=timestamp,price=tick.get('price'),active=tick.get('active'),id=tick.get('id')))
            sides[side]=ticks
        result.append(dict(fixture_id=candidate['fixture_id'],market='AH',market_id=str(meta['market_id']),
            line=line,bookmaker=candidate['bookmaker'],source='oddspapi',selections=sides,
            raw_timestamp_semantics='HISTORY_ENTRY_CREATED_AT',raw_record_hash=digest,
            raw_hash_basis='CANONICAL_JSON_NOT_ORIGINAL_RESPONSE_BYTES',catalog_evidence=meta['evidence']))
    return result
