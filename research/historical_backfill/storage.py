"""Historical-only immutable local storage. Never accepts production paths."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path("research/historical_backfill/data").resolve()


def append_raw(record: dict[str, Any], *, root: Path = ROOT) -> Path:
    """Content-addressed JSON files: no overwrites, no external path traversal."""
    root = root.resolve()
    if root != ROOT and ROOT not in root.parents:
        raise ValueError("historical storage must remain under isolated root")
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    dest = root / "raw" / (digest + ".json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with dest.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if dest.read_bytes() != payload:
            raise RuntimeError("hash collision or corrupt immutable historical record")
    return dest
