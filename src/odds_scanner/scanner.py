from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _write_today(root: Path, payload: dict) -> dict:
    p = root / "reports/today.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def scan(root: Path) -> dict:
    """Fail-closed production scanner entrypoint.

    The legacy exploratory 1X2 bucket scanner is intentionally retired. Only
    patterns in the frozen validated registry may reach current-market matching.
    A current multi-market provider adapter will be added separately; until then
    a non-empty registry reports PROVIDER_REQUIRED rather than inventing picks.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    registry_path = root / "reports/pattern_registry.json"
    if not registry_path.exists():
        return _write_today(root, {
            "schema_version": "2.0",
            "status": "REGISTRY_UNAVAILABLE",
            "generated_at": generated_at,
            "matches_scanned": 0,
            "qualifying": 0,
            "candidates": [],
            "reason": "Validated pattern registry has not been generated.",
        })

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    patterns = registry.get("patterns", [])
    if not patterns:
        return _write_today(root, {
            "schema_version": "2.0",
            "status": "NO_VALIDATED_PATTERNS",
            "generated_at": generated_at,
            "matches_scanned": 0,
            "patterns_available": 0,
            "qualifying": 0,
            "candidates": [],
            "message": "NO QUALIFYING BETS",
            "reason": "No historical pattern passed the frozen train-validation-holdout and cross-league gates.",
        })

    return _write_today(root, {
        "schema_version": "2.0",
        "status": "CURRENT_MULTIMARKET_PROVIDER_REQUIRED",
        "generated_at": generated_at,
        "matches_scanned": 0,
        "patterns_available": len(patterns),
        "qualifying": 0,
        "candidates": [],
        "reason": "Validated patterns exist, but the current AH/O-U line+price provider adapter is not yet available. Scanner fails closed.",
    })
