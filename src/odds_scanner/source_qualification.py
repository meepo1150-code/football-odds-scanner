from __future__ import annotations

import json
from pathlib import Path

from .provider_capabilities import capability_matrix


RESEARCH_REQUIRED = {
    "ah_variable_lines": True,
    "ou_quarter_lines": True,
    "opening_odds": True,
}

EXECUTION_REQUIRED = {
    "current_odds": True,
}


def _has_multi_season_history(provider: dict) -> bool:
    depth = str(provider.get("historical_depth", "")).lower()
    # Conservative: only explicitly observed/declared multi-season ranges qualify.
    return any(token in depth for token in ("2019/20-2024/25", "multi-season", "2004", "historical endpoint"))


def qualify_provider(provider: dict) -> dict:
    research_missing = [k for k, expected in RESEARCH_REQUIRED.items() if provider.get(k) is not expected]
    if not _has_multi_season_history(provider):
        research_missing.append("multi_season_history")
    execution_missing = [k for k, expected in EXECUTION_REQUIRED.items() if provider.get(k) is not expected]
    if provider.get("role") in {"opening_snapshot_and_forward_research", "historical_research"}:
        execution_missing.append("tradable_execution_price")
    return {
        "provider_id": provider["provider_id"],
        "research_ready": not research_missing,
        "execution_ready": not execution_missing,
        "research_missing": sorted(set(research_missing)),
        "execution_missing": sorted(set(execution_missing)),
        "api_key_required": bool(provider.get("api_key_required")),
        "zero_cost_confirmed": bool(provider.get("zero_cost_confirmed")),
        "production_status": provider.get("production_status"),
    }


def qualification_report() -> dict:
    providers = capability_matrix()["providers"]
    rows = [qualify_provider(p) for p in providers]
    zero_cost_rich = [r["provider_id"] for r in rows if r["research_ready"] and r["zero_cost_confirmed"]]
    zero_cost_execution = [r["provider_id"] for r in rows if r["execution_ready"] and r["zero_cost_confirmed"]]
    return {
        "schema_version": "1.0",
        "gate": "SOURCE_QUALIFICATION",
        "providers": rows,
        "zero_cost_rich_historical": zero_cost_rich,
        "zero_cost_execution": zero_cost_execution,
        "rich_historical_gap_open": not bool(zero_cost_rich),
        "execution_provider_gap_open": not bool(zero_cost_execution),
        "policy": "Fail closed. A scraper implementation or a provider marketing claim is not treated as a qualified dataset until actual accessible fields, history depth and price semantics are verified.",
    }


def write_report(path: Path) -> dict:
    payload = qualification_report()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
