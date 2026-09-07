from __future__ import annotations
from collections import defaultdict
from dataclasses import asdict, dataclass

from .asian_settlement import settle_asian_handicap, settle_asian_total
from .pattern_policy import DEFAULT_POLICY


def _band(value: float, width: float) -> tuple[float, float]:
    lo = int(value / width) * width
    return round(lo, 4), round(lo + width, 4)


@dataclass(frozen=True)
class HierarchicalPatternKey:
    family: str
    favorite_side: str
    ah_line: float
    ou_line: float | None = None
    ou_side: str | None = None
    ah_price_band: tuple[float, float] | None = None
    ou_price_band: tuple[float, float] | None = None
    favorite_probability_band: tuple[float, float] | None = None

    def label(self) -> str:
        parts = [self.family, self.favorite_side, f"AH={self.ah_line:+.2f}"]
        if self.ou_line is not None:
            parts.append(f"{self.ou_side}{self.ou_line:.2f}")
        if self.ah_price_band is not None:
            parts.append(f"AH@{self.ah_price_band[0]:.2f}-{self.ah_price_band[1]:.2f}")
        if self.ou_price_band is not None:
            parts.append(f"OU@{self.ou_price_band[0]:.2f}-{self.ou_price_band[1]:.2f}")
        if self.favorite_probability_band is not None:
            parts.append(f"FAVP={self.favorite_probability_band[0]:.2f}-{self.favorite_probability_band[1]:.2f}")
        return "|".join(parts)


def _keys_for(row: dict, ou_side: str, ou_price: float) -> list[HierarchicalPatternKey]:
    fav = row["favorite_side"]
    ah = float(row["favorite_ah_line"])
    ou = float(row["ou_line"])
    ah_price = float(row["favorite_ah_price"])
    fav_p = float(row["favorite_fair_probability"])
    keys = [
        HierarchicalPatternKey("AH_LINE", fav, ah),
        HierarchicalPatternKey("AH_OU", fav, ah, ou, ou_side),
        HierarchicalPatternKey("AH_OU_PRICE", fav, ah, ou, ou_side, _band(ah_price, 0.10), _band(ou_price, 0.10)),
        HierarchicalPatternKey("AH_OU_PRICE_1X2", fav, ah, ou, ou_side, _band(ah_price, 0.10), _band(ou_price, 0.10), _band(fav_p, 0.05)),
    ]
    return keys


def build_hierarchical_report(rows: list[dict], *, test_seasons: set[str] | None = None, min_n: int = 20) -> dict:
    tests = set(test_seasons or {"2324", "2425", "2526"})
    groups: dict[tuple[str, HierarchicalPatternKey], list[dict]] = defaultdict(list)

    for row in rows:
        ah_price = float(row["favorite_ah_price"])
        if not DEFAULT_POLICY.research_price_is_supported(ah_price):
            continue
        ah = settle_asian_handicap(int(row["home_goals"]), int(row["away_goals"]), float(row["favorite_ah_line"]), ah_price, row["favorite_side"])
        split = "test" if row["season"] in tests else "train"
        for ou_side, ou_price in (("O", float(row["over_price"])), ("U", float(row["under_price"]))):
            if not DEFAULT_POLICY.research_price_is_supported(ou_price):
                continue
            total = settle_asian_total(int(row["home_goals"]), int(row["away_goals"]), float(row["ou_line"]), ou_price, ou_side)
            for key in _keys_for(row, ou_side, ou_price):
                groups[(split, key)].append({"season": row["season"], "ah_profit": ah.profit_units, "ou_profit": total.profit_units})

    buckets = []
    for (split, key), obs in groups.items():
        if len(obs) < min_n:
            continue
        n = len(obs)
        by_season = {}
        for season in sorted({x["season"] for x in obs}):
            vals = [x for x in obs if x["season"] == season]
            by_season[season] = {
                "n": len(vals),
                "ah_roi": round(sum(x["ah_profit"] for x in vals) / len(vals), 6),
                "ou_roi": round(sum(x["ou_profit"] for x in vals) / len(vals), 6),
            }
        buckets.append({
            "split": split,
            "family": key.family,
            "pattern": key.label(),
            "pattern_key": asdict(key),
            "n": n,
            "ah_roi": round(sum(x["ah_profit"] for x in obs) / n, 6),
            "ou_roi": round(sum(x["ou_profit"] for x in obs) / n, 6),
            "seasons": by_season,
        })

    buckets.sort(key=lambda x: (x["family"], x["split"], -x["n"], -x["ou_roi"]))
    family_counts = {}
    for family in {b["family"] for b in buckets}:
        family_counts[family] = sum(1 for b in buckets if b["family"] == family)
    return {
        "schema_version": "1.0",
        "engine": "HIERARCHICAL_MULTI_MARKET_BACKTEST",
        "source_rows": len(rows),
        "test_seasons": sorted(tests),
        "min_n": min_n,
        "family_counts": family_counts,
        "buckets": buckets,
        "warning": "Exploratory hierarchy only; promotion requires paired audit and robustness gates.",
    }
