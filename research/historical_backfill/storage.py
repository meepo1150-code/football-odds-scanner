"""Historical-only content-addressed immutable storage, including exact response bytes."""
import hashlib
import json
from pathlib import Path

ROOT=Path('research/historical_backfill/data').resolve()


def append_bytes(payload: bytes, *, root=None):
    root=(ROOT if root is None else root).resolve()
    if root!=ROOT and ROOT not in root.parents:raise ValueError('historical storage must remain under isolated root')
    if not isinstance(payload,bytes):raise ValueError('raw bytes required')
    raw=root/'raw';raw.mkdir(parents=True,exist_ok=True)
    if raw.resolve()!=raw:raise ValueError('raw directory symlink prohibited')
    dest=raw/(hashlib.sha256(payload).hexdigest()+'.json')
    if dest.is_symlink():raise ValueError('raw file symlink prohibited')
    try:
        with dest.open('xb') as stream:stream.write(payload)
    except FileExistsError:
        if dest.read_bytes()!=payload:raise RuntimeError('corrupt immutable historical record')
    return dest


def append_raw(record, *, root=None):
    payload=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    return append_bytes(payload,root=root)
