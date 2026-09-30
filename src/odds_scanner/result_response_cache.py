"""Bounded cache of original result-provider responses with retrieval provenance."""
from __future__ import annotations
import json
from datetime import date, datetime, timezone
from pathlib import Path

CACHE = Path('data/cache/fotmob')


def read(path):
    try:
        row=json.loads(path.read_text())
        stamp=datetime.fromisoformat(row['fetched_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None or not isinstance(row.get('payload'),dict):return None
        return row,stamp
    except (OSError,ValueError,KeyError,TypeError):return None


def fetch_day(root, day, fetch, now=None, provider="fotmob"):
    if provider not in {"fotmob", "espn"}: raise ValueError("Unsupported cache provider")
    now=now or datetime.now(timezone.utc)
    parsed=date.fromisoformat(day)  # Reject path-like input before touching disk.
    path=root/'data/cache'/provider/f'{parsed.isoformat()}.json'
    cached=read(path)
    ttl=86400 if (now.date()-parsed).days >= 2 else 3600
    if cached and 0 <= (now-cached[1]).total_seconds() < ttl:
        return cached[0]['payload'], {'source':'CACHE','fetched_at':cached[0]['fetched_at'],'requests':0}
    try:
        payload=fetch(day)
        if not isinstance(payload,dict) or not isinstance(payload.get('leagues'),list):
            raise ValueError('Result response has no leagues list; existing cache preserved')
    except Exception as exc:
        # Final historical scores remain usable evidence during a provider outage.
        # Caller records this as stale fallback, never as a live successful request.
        if cached and cached[1] <= now:
            return cached[0]['payload'], {'source':'STALE_CACHE_AFTER_REQUEST_FAILURE','fetched_at':cached[0]['fetched_at'],'requests':1,'error':f'{type(exc).__name__}: {exc}'}
        raise
    row={'schema_version':'1.0','provider':provider,'requested_day':day,'fetched_at':now.isoformat(),'payload':payload}
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    return payload, {'source':'NETWORK','fetched_at':row['fetched_at'],'requests':1}


def merge_cache(staged,root):
    for provider in ('fotmob','espn'):
        cache=Path('data/cache')/provider
        for source in (staged/cache).glob('*.json'):
            new=read(source)
            if not new:continue
            target=root/cache/source.name;old=read(target)
            if not old or new[1]>old[1]:
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(source.read_text())
