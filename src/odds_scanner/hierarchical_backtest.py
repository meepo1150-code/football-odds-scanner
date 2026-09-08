from __future__ import annotations
from collections import defaultdict
from dataclasses import asdict, dataclass

from .asian_settlement import settle_asian_handicap, settle_asian_total
from .pattern_policy import DEFAULT_POLICY
from .robust_stats import profit_diagnostics
from .settlement_ev import settlement_distribution


def _band(value: float, width: float) -> tuple[float, float]:
    lo = int(value / width) * width
    return round(lo, 4), round(lo + width, 4)


def _movement(value) -> float | None:
    if value is None or value == "":
        return None
    x = float(value)
    return round(x * 4) / 4 if abs(x * 4 - round(x * 4)) < 1e-8 else None


def _row_movement(row: dict, canonical: str, legacy: str) -> float | None:
    value = row.get(canonical)
    if value is None:
        value = row.get(legacy)
    return _movement(value)


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
    ah_line_move: float | None = None
    ou_line_move: float | None = None

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
        if self.ah_line_move is not None:
            parts.append(f"AHMOVE={self.ah_line_move:+.2f}")
        if self.ou_line_move is not None:
            parts.append(f"OUMOVE={self.ou_line_move:+.2f}")
        return "|".join(parts)


def _ou_keys_for(row: dict, ou_side: str, ou_price: float) -> list[HierarchicalPatternKey]:
    fav = row["favorite_side"]
    ah = float(row["favorite_ah_line"])
    ou = float(row["ou_line"])
    ah_price = float(row["favorite_ah_price"])
    fav_p = float(row["favorite_fair_probability"])
    keys = [
        HierarchicalPatternKey("AH_OU", fav, ah, ou, ou_side),
        HierarchicalPatternKey("AH_OU_PRICE", fav, ah, ou, ou_side, _band(ah_price, .10), _band(ou_price, .10)),
        HierarchicalPatternKey("AH_OU_PRICE_1X2", fav, ah, ou, ou_side, _band(ah_price, .10), _band(ou_price, .10), _band(fav_p, .05)),
    ]
    ah_move = _row_movement(row, "ah_line_move", "ah_line_movement")
    ou_move = _row_movement(row, "ou_line_move", "ou_line_movement")
    if ou_move is not None:
        keys.append(HierarchicalPatternKey("OU_MOVE", fav, ah, ou, ou_side, ou_line_move=ou_move))
    if ah_move is not None and ou_move is not None:
        keys.append(HierarchicalPatternKey("AH_OU_MOVE", fav, ah, ou, ou_side, ah_line_move=ah_move, ou_line_move=ou_move))
    return keys


def _obs(row: dict, ah_profit: float, ou_profit: float, ah_settlement: str, ou_settlement: str | None) -> dict:
    return {
        "season": row["season"],
        "date": str(row.get("date") or ""),
        "fixture_id": str(row.get("fixture_id") or ""),
        "ah_profit": ah_profit,
        "ou_profit": ou_profit,
        "ah_settlement": ah_settlement,
        "ou_settlement": ou_settlement,
    }


def _diagnostics(obs: list[dict], field: str, seed_label: str) -> dict:
    ordered = sorted(obs, key=lambda x: (x["date"], x["fixture_id"]))
    return profit_diagnostics(
        [float(x[field]) for x in ordered],
        [str(x["season"]) for x in ordered],
        seed_label=seed_label,
    )


def build_hierarchical_report(rows: list[dict], *, test_seasons: set[str] | None = None, min_n: int = 20) -> dict:
    tests = set(test_seasons or {"2324", "2425", "2526"})
    groups: dict[tuple[str, HierarchicalPatternKey], list[dict]] = defaultdict(list)
    for row in rows:
        ah_price = float(row["favorite_ah_price"])
        if not DEFAULT_POLICY.research_price_is_supported(ah_price):
            continue
        ah = settle_asian_handicap(
            int(row["home_goals"]), int(row["away_goals"]),
            float(row["favorite_ah_line"]), ah_price, row["favorite_side"],
        )
        split = "test" if row["season"] in tests else "train"
        ah_line = float(row["favorite_ah_line"])
        base_obs = _obs(row, ah.profit_units, 0.0, ah.settlement.value, None)
        ah_key = HierarchicalPatternKey("AH_LINE", row["favorite_side"], ah_line)
        groups[(split, ah_key)].append(base_obs)
        ah_move = _row_movement(row, "ah_line_move", "ah_line_movement")
        if ah_move is not None:
            # Exactly one AH movement observation per match. It must not be created
            # once for Over and again for Under.
            move_key = HierarchicalPatternKey("AH_MOVE", row["favorite_side"], ah_line, ah_line_move=ah_move)
            groups[(split, move_key)].append(base_obs)

        for ou_side, ou_price in (("O", float(row["over_price"])), ("U", float(row["under_price"]))):
            if not DEFAULT_POLICY.research_price_is_supported(ou_price):
                continue
            total = settle_asian_total(
                int(row["home_goals"]), int(row["away_goals"]),
                float(row["ou_line"]), ou_price, ou_side,
            )
            for key in _ou_keys_for(row, ou_side, ou_price):
                groups[(split, key)].append(_obs(row, ah.profit_units, total.profit_units, ah.settlement.value, total.settlement.value))

    buckets = []
    ah_only_families = {"AH_LINE", "AH_MOVE"}
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
                "ou_roi": None if key.family in ah_only_families else round(sum(x["ou_profit"] for x in vals) / len(vals), 6),
                "ah_settlements": settlement_distribution(x["ah_settlement"] for x in vals),
                "ou_settlements": None if key.family in ah_only_families else settlement_distribution(x["ou_settlement"] for x in vals),
            }
        pattern = key.label()
        ah_diag = _diagnostics(obs, "ah_profit", f"{split}|{pattern}|AH")
        ou_diag = None if key.family in ah_only_families else _diagnostics(obs, "ou_profit", f"{split}|{pattern}|OU")
        buckets.append({
            "split": split,
            "family": key.family,
            "pattern": pattern,
            "pattern_key": asdict(key),
            "n": n,
            "ah_roi": round(sum(x["ah_profit"] for x in obs) / n, 6),
            "ou_roi": None if key.family in ah_only_families else round(sum(x["ou_profit"] for x in obs) / n, 6),
            "ah_settlements": settlement_distribution(x["ah_settlement"] for x in obs),
            "ou_settlements": None if key.family in ah_only_families else settlement_distribution(x["ou_settlement"] for x in obs),
            "ah_diagnostics": ah_diag,
            "ou_diagnostics": ou_diag,
            "seasons": by_season,
        })
    buckets.sort(key=lambda x: (x["family"], x["split"], -x["n"], -(x["ou_roi"] or -999.0)))
    family_counts = {f: sum(1 for b in buckets if b["family"] == f) for f in {b["family"] for b in buckets}}
    return {
        "schema_version": "1.4",
        "engine": "HIERARCHICAL_MULTI_MARKET_BACKTEST",
        "source_rows": len(rows),
        "test_seasons": sorted(tests),
        "min_n": min_n,
        "family_counts": family_counts,
        "buckets": buckets,
        "empirical_diagnostics": {
            "bootstrap_ci95": True,
            "deterministic_sign_flip_null": True,
            "chronological_max_drawdown": True,
            "longest_losing_streak": True,
            "worst_season_roi": True,
            "season_abs_concentration": True,
            "promotion_gate_changed": False,
        },
        "warning": "Exploratory hierarchy only; promotion requires paired audit and frozen robustness gates. Empirical diagnostics enrich evidence but do not retroactively alter the registered holdout gate.",
    }
