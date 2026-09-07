from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProviderCapability:
    provider_id: str
    role: str
    historical_depth: str
    league_scope: str
    ah_variable_lines: bool
    ou_variable_lines: bool
    ou_quarter_lines: bool
    opening_odds: bool
    closing_odds: bool
    movement_history: bool
    current_odds: bool
    api_key_required: bool
    zero_cost_confirmed: bool
    redistribution_status: str
    production_status: str
    source_url: str
    note: str


PROVIDERS = (
    ProviderCapability(
        provider_id="football_data_big5",
        role="historical_research",
        historical_depth="2019/20-2024/25 in current normalized Big-5 pipeline",
        league_scope="Big 5 European top divisions",
        ah_variable_lines=True,
        ou_variable_lines=False,
        ou_quarter_lines=False,
        opening_odds=True,
        closing_odds=False,
        movement_history=False,
        current_odds=False,
        api_key_required=False,
        zero_cost_confirmed=True,
        redistribution_status="derived upstream data; do not assume redistribution rights",
        production_status="ACTIVE_LIMITED",
        source_url="https://www.football-data.co.uk/data.php",
        note="Current breadth source supports variable AH but only O/U 2.5; unsuitable for research claims about 2.25/2.75 total lines.",
    ),
    ProviderCapability(
        provider_id="sgodds_singapore_pools_open",
        role="opening_snapshot_and_forward_research",
        historical_depth="public opening-odds downloads observed from roughly Oct 2025 onward",
        league_scope="12 leagues in live provider health probe",
        ah_variable_lines=True,
        ou_variable_lines=True,
        ou_quarter_lines=False,
        opening_odds=True,
        closing_odds=False,
        movement_history=False,
        current_odds=False,
        api_key_required=False,
        zero_cost_confirmed=True,
        redistribution_status="no explicit raw-data redistribution permission confirmed",
        production_status="OPENING_ONLY_NOT_EXECUTION_PRICE",
        source_url="https://sgodds.com/football/data",
        note="Provider page labels these files Opening Odds Data by League. Live probe found AH quarter-lines but O/U only 1.5/2.5/3.5/4.5. Never use this source as a current tradable execution-price feed.",
    ),
    ProviderCapability(
        provider_id="isports_historical_all",
        role="candidate_rich_historical",
        historical_depth="plan-dependent historical endpoint",
        league_scope="provider API coverage",
        ah_variable_lines=True,
        ou_variable_lines=True,
        ou_quarter_lines=True,
        opening_odds=True,
        closing_odds=True,
        movement_history=False,
        current_odds=True,
        api_key_required=True,
        zero_cost_confirmed=False,
        redistribution_status="provider terms/plan apply",
        production_status="KEY_REQUIRED_NOT_CONNECTED",
        source_url="https://www.isportsapi.com/docs.html?id=62",
        note="Historical Odds (All) documents initial/final prices across all handicap and goal lines in 0.25 increments.",
    ),
    ProviderCapability(
        provider_id="tipsme_pro",
        role="candidate_rich_historical_and_movement",
        historical_depth="provider plan/data coverage",
        league_scope="provider API coverage",
        ah_variable_lines=True,
        ou_variable_lines=True,
        ou_quarter_lines=True,
        opening_odds=True,
        closing_odds=True,
        movement_history=True,
        current_odds=True,
        api_key_required=True,
        zero_cost_confirmed=False,
        redistribution_status="provider terms/Pro plan apply",
        production_status="KEY_REQUIRED_NOT_CONNECTED",
        source_url="https://tipsme.hk/en/developers/docs/odds",
        note="Pro documentation advertises Asian handicap, O/U, 1X2, opening/closing prices and complete movement history.",
    ),
)


def capability_matrix() -> dict:
    rows = [asdict(x) for x in PROVIDERS]
    return {
        "schema_version": "1.1",
        "providers": rows,
        "research_requirements": {
            "rich_joint_pattern_engine": {
                "ah_variable_lines": True,
                "ou_quarter_lines": True,
                "opening_odds": True,
                "multi_season_history": True,
            },
            "current_scanner": {
                "exact_line_and_price": True,
                "two_sided_prices_for_devig": True,
                "freshness_required": True,
                "opening_snapshot_is_not_current": True,
            },
        },
    }


def providers_supporting(*, ou_quarter_lines: bool = False, movement_history: bool = False, current_odds: bool = False) -> list[dict]:
    rows = capability_matrix()["providers"]
    if ou_quarter_lines:
        rows = [r for r in rows if r["ou_quarter_lines"]]
    if movement_history:
        rows = [r for r in rows if r["movement_history"]]
    if current_odds:
        rows = [r for r in rows if r["current_odds"]]
    return rows


def write_capability_matrix(path: Path) -> dict:
    payload = capability_matrix()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
