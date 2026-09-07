from __future__ import annotations
from dataclasses import dataclass


def _band(value: float, width: float) -> tuple[float, float]:
    lo = int(value / width) * width
    return round(lo, 4), round(lo + width, 4)


@dataclass(frozen=True)
class MarketPatternKey:
    league_scope: str
    favorite_side: str
    ah_line: float
    ah_price_band: tuple[float, float]
    ou_line: float
    ou_side: str
    ou_price_band: tuple[float, float]
    favorite_fair_probability_band: tuple[float, float]
    movement_state: str = "OPENING_ONLY"

    @classmethod
    def from_values(
        cls,
        *,
        league_scope: str,
        favorite_side: str,
        ah_line: float,
        ah_price: float,
        ou_line: float,
        ou_side: str,
        ou_price: float,
        favorite_fair_probability: float,
        movement_state: str = "OPENING_ONLY",
        price_width: float = 0.10,
        probability_width: float = 0.05,
    ) -> "MarketPatternKey":
        return cls(
            league_scope=league_scope,
            favorite_side=favorite_side,
            ah_line=ah_line,
            ah_price_band=_band(ah_price, price_width),
            ou_line=ou_line,
            ou_side=ou_side,
            ou_price_band=_band(ou_price, price_width),
            favorite_fair_probability_band=_band(favorite_fair_probability, probability_width),
            movement_state=movement_state,
        )

    def label(self) -> str:
        return (
            f"{self.league_scope}|{self.favorite_side}|AH={self.ah_line:+.2f}"
            f"|AH@{self.ah_price_band[0]:.2f}-{self.ah_price_band[1]:.2f}"
            f"|{self.ou_side}{self.ou_line:.2f}@{self.ou_price_band[0]:.2f}-{self.ou_price_band[1]:.2f}"
            f"|FAVP={self.favorite_fair_probability_band[0]:.2f}-{self.favorite_fair_probability_band[1]:.2f}"
            f"|MOVE={self.movement_state}"
        )
