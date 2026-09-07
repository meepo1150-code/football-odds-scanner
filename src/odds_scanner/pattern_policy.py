from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PatternPolicy:
    research_price_min: float = 1.50
    research_price_max: float = 2.50
    tradable_price_min: float = 1.80
    tradable_price_max: float = 2.20

    min_global_train_n: int = 500
    min_league_train_n: int = 200
    min_validation_n: int = 100
    min_holdout_n: int = 100

    min_probability_edge_pp: float = 3.0
    medium_probability_edge_pp: float = 4.0
    strong_probability_edge_pp: float = 5.0
    min_ev: float = 0.03
    strong_ev: float = 0.05

    min_positive_season_share: float = 0.60
    max_single_season_profit_share: float = 0.50
    max_primary_selections_per_match: int = 1
    max_daily_selections: int = 5

    def current_price_is_tradable(self, odds: float) -> bool:
        return self.tradable_price_min <= odds <= self.tradable_price_max

    def research_price_is_supported(self, odds: float) -> bool:
        return self.research_price_min <= odds <= self.research_price_max


DEFAULT_POLICY = PatternPolicy()

STATUS_REJECTED = "REJECTED"
STATUS_WATCHLIST = "WATCHLIST"
STATUS_QUALIFIED = "QUALIFIED"
STATUS_HIGH_CONFIDENCE = "HIGH_CONFIDENCE"

REJECT_DATA = "REJECT_DATA"
REJECT_PRICE = "REJECT_PRICE"
REJECT_SAMPLE = "REJECT_SAMPLE"
REJECT_EDGE = "REJECT_EDGE"
REJECT_EV = "REJECT_EV"
REJECT_VALIDATION = "REJECT_VALIDATION"
REJECT_SEASON_STABILITY = "REJECT_SEASON_STABILITY"
REJECT_LEAGUE_STABILITY = "REJECT_LEAGUE_STABILITY"
REJECT_MULTIPLE_TESTING = "REJECT_MULTIPLE_TESTING"
REJECT_ROBUSTNESS = "REJECT_ROBUSTNESS"
REJECT_PRICE_MOVED = "REJECT_PRICE_MOVED"
REJECT_RISK = "REJECT_RISK"
REJECT_CORRELATED = "REJECT_CORRELATED"
