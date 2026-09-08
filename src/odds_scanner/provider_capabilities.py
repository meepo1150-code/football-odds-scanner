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
        ah_variable_lines=True, ou_variable_lines=False, ou_quarter_lines=False,
        opening_odds=True, closing_odds=False, movement_history=False, current_odds=False,
        api_key_required=False, zero_cost_confirmed=True,
        redistribution_status="derived upstream data; do not assume redistribution rights",
        production_status="ACTIVE_LIMITED",
        source_url="https://www.football-data.co.uk/data.php",
        note="Variable AH but only O/U 2.5; unsuitable for 2.25/2.75 total-line claims.",
    ),
    ProviderCapability(
        provider_id="sgodds_singapore_pools_open",
        role="opening_snapshot_and_forward_research",
        historical_depth="public opening-odds downloads observed from roughly Oct 2025 onward",
        league_scope="12 leagues in live provider health probe",
        ah_variable_lines=True, ou_variable_lines=True, ou_quarter_lines=False,
        opening_odds=True, closing_odds=False, movement_history=False, current_odds=False,
        api_key_required=False, zero_cost_confirmed=True,
        redistribution_status="no explicit raw-data redistribution permission confirmed",
        production_status="OPENING_ONLY_NOT_EXECUTION_PRICE",
        source_url="https://sgodds.com/football/data",
        note="Opening snapshot only. AH quarter-lines observed, but O/U only whole-half lines; never an execution feed.",
    ),
    ProviderCapability(
        provider_id="infersports_keyless",
        role="candidate_current_execution",
        historical_depth="opening endpoint and recent results documented; no qualified multi-season archive",
        league_scope="provider-documented football coverage",
        ah_variable_lines=True, ou_variable_lines=True, ou_quarter_lines=True,
        opening_odds=True, closing_odds=False, movement_history=True, current_odds=True,
        api_key_required=False, zero_cost_confirmed=True,
        redistribution_status="API terms apply; health probe stores metadata only",
        production_status="GITHUB_RUNNER_UNREACHABLE",
        source_url="https://api.infersports.dev",
        note="Current two-sided Asian markets documented, but GitHub-hosted runner timed out before any quote was returned.",
    ),
    ProviderCapability(
        provider_id="5dollarfootballapi_free",
        role="short_history_and_current_market_visibility",
        historical_depth="Free: last 3 months of results and odds; Community: 12 months",
        league_scope="Free: Big 5 European top divisions, Bet365",
        ah_variable_lines=True, ou_variable_lines=True, ou_quarter_lines=True,
        opening_odds=True, closing_odds=True, movement_history=False, current_odds=True,
        api_key_required=True, zero_cost_confirmed=True,
        redistribution_status="product use/cache allowed under provider terms; raw-feed redistribution prohibited; public free use requires attribution",
        production_status="ACTIVE_RESEARCH_EXECUTION_FRESHNESS_UNVERIFIED",
        source_url="https://5dollarfootballapi.com/docs",
        note="Key is active and historical quarter-line collection works. Scheduled-fixture closing is the latest pre-match snapshot, but the Free summary endpoint has no per-quote timestamp. Full recorded_at tick history is Ultra-only, so production execution remains fail-closed.",
    ),
    ProviderCapability(
        provider_id="oddspapi_free",
        role="candidate_current_execution_and_tick_history",
        historical_depth="provider documents full per-fixture historical price snapshots; historical-odds endpoint is unmetered",
        league_scope="soccer catalog includes major European leagues and many bookmakers including Bet365, Pinnacle, Singbet and SBOBet",
        ah_variable_lines=True, ou_variable_lines=True, ou_quarter_lines=True,
        opening_odds=True, closing_odds=True, movement_history=True, current_odds=True,
        api_key_required=True, zero_cost_confirmed=True,
        redistribution_status="provider terms apply; only normalized health/research outputs should be persisted until redistribution terms are audited",
        production_status="FREE_KEY_REQUIRED_LIVE_PROBE_PENDING",
        source_url="https://oddspapi.io/us/docs/get-odds",
        note="Free tier is documented at 250 metered requests/month with no card; historical-odds calls are unmetered. Current selections expose bookmakerChangedAt/changedAt, active/suspended flags, price, limit and mainLine. Dynamic market catalog supplies handicap and outcome labels, avoiding hard-coded IDs. Must pass a real GitHub-runner Bet365 probe before scanner integration.",
    ),
    ProviderCapability(
        provider_id="odds_api_io",
        role="dormant_current_execution_candidate",
        historical_depth="provider-dependent",
        league_scope="documented football coverage",
        ah_variable_lines=True, ou_variable_lines=True, ou_quarter_lines=True,
        opening_odds=False, closing_odds=False, movement_history=False, current_odds=True,
        api_key_required=True, zero_cost_confirmed=False,
        redistribution_status="provider terms apply",
        production_status="FREE_SIGNUP_PAUSED_2026_09_08",
        source_url="https://odds-api.io/",
        note="Parser was built from documented timestamped Spread/Totals schema, but the live account dashboard states new free API keys are paused indefinitely. Do not use in the zero-cost production path unless free signup reopens.",
    ),
    ProviderCapability(
        provider_id="isports_historical_all",
        role="candidate_rich_historical",
        historical_depth="plan-dependent historical endpoint",
        league_scope="provider API coverage",
        ah_variable_lines=True, ou_variable_lines=True, ou_quarter_lines=True,
        opening_odds=True, closing_odds=True, movement_history=False, current_odds=True,
        api_key_required=True, zero_cost_confirmed=False,
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
        ah_variable_lines=True, ou_variable_lines=True, ou_quarter_lines=True,
        opening_odds=True, closing_odds=True, movement_history=True, current_odds=True,
        api_key_required=True, zero_cost_confirmed=False,
        redistribution_status="provider terms/Pro plan apply",
        production_status="KEY_REQUIRED_NOT_CONNECTED",
        source_url="https://tipsme.hk/en/developers/docs/odds",
        note="Pro documentation advertises Asian handicap, O/U, 1X2, opening/closing prices and complete movement history.",
    ),
)


def capability_matrix() -> dict:
    rows = [asdict(x) for x in PROVIDERS]
    return {
        "schema_version": "1.4",
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
                "operational_from_github_runner": True,
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
