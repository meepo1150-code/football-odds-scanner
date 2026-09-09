from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

LEGACY_TICKS_PATH = Path("data/normalized/oddspapi_history_ticks.jsonl")
TICKS_DIR = Path("data/normalized/oddspapi_history_ticks")


def _safe_day(value: object) -> str:
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).date().isoformat()
        except ValueError:
            pass
    return "unknown-date"


def shard_path(root: Path, row: dict) -> Path:
    return root / TICKS_DIR / f"{_safe_day(row.get('kickoff'))}.jsonl"


def iter_tick_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    legacy = root / LEGACY_TICKS_PATH
    if legacy.exists():
        paths.append(legacy)
    directory = root / TICKS_DIR
    if directory.exists():
        paths.extend(sorted(p for p in directory.glob("*.jsonl") if p.is_file()))
    return paths


def iter_rows(root: Path) -> Iterable[dict]:
    for path in iter_tick_paths(root):
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(row, dict):
                    yield row


def archived_fixture_ids(root: Path) -> set[str]:
    ids: set[str] = set()
    for row in iter_rows(root):
        fid = row.get("fixture_id")
        if fid is not None:
            ids.add(str(fid))
    return ids


def append_row(root: Path, row: dict) -> Path:
    path = shard_path(root, row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return path
