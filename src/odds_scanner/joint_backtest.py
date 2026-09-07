from __future__ import annotations
from collections import defaultdict
from dataclasses import asdict

from .asian_settlement import settle_asian_handicap, settle_asian_total
from .market_pattern import MarketPatternKey
from .pattern_policy import DEFAULT_POLICY


def _devig_two(a: float, b: float) -> tuple[float, float]:
    ia, ib = 1.0 / a, 1.0 / b
    s = ia + ib
    return ia / s, ib / s


def _split_name(season: str, test_seasons: set[str]) -> str:
    return "test" if season in test_seasons else "train"


def _round(x: float | None, n: int = 6):
    return None if x is None else round(x, n)


def build_joint_report(
    rows: list[dict],
    *,
    test_seasons: set[str] | None = None,
    min_n: int = 20,
    league_scope: str = "GLOBAL",
) -> dict:
    tests = set(test_seasons or {"2324", "2425", "2526"})
    groups: dict[tuple[str, MarketPatternKey], list[dict]] = defaultdict(list)
    skipped_price = 0

    for row in rows:
        ah_price = float(row["favorite_ah_price"])
        if not DEFAULT_POLICY.research_price_is_supported(ah_price):
            skipped_price += 1
            continue
        for ou_side, ou_price, other_price in (
            ("O", float(row["over_price"]), float(row["under_price"])),
            ("U", float(row["under_price"]), float(row["over_price"])),
        ):
            if not DEFAULT_POLICY.research_price_is_supported(ou_price):
                continue
            key = MarketPatternKey.from_values(
                league_scope=league_scope,
                favorite_side=row["favorite_side"],
                ah_line=float(row["favorite_ah_line"]),
                ah_price=ah_price,
                ou_line=float(row["ou_line"]),
                ou_side=ou_side,
                ou_price=ou_price,
                favorite_fair_probability=float(row["favorite_fair_probability"]),
            )
            ah = settle_asian_handicap(
                int(row["home_goals"]), int(row["away_goals"]),
                float(row["favorite_ah_line"]), ah_price, row["favorite_side"],
            )
            total = settle_asian_total(
                int(row["home_goals"]), int(row["away_goals"]),
                float(row["ou_line"]), ou_price, ou_side,
            )
            ou_market_share = _devig_two(ou_price, other_price)[0]
            groups[(_split_name(row["season"], tests), key)].append({
                "season": row["season"],
                "ah_profit": ah.profit_units,
                "ou_profit": total.profit_units,
                "ou_market_share": ou_market_share,
                "favorite_win": 1 if (
                    (row["favorite_side"] == "H" and row["home_goals"] > row["away_goals"])
                    or (row["favorite_side"] == "A" and row["away_goals"] > row["home_goals"])
                ) else 0,
            })

    buckets = []
    for (split, key), obs in groups.items():
        if len(obs) < min_n:
            continue
        n = len(obs)
        ah_profit = sum(x["ah_profit"] for x in obs)
        ou_profit = sum(x["ou_profit"] for x in obs)
        season_roi: dict[str, dict[str, float | int]] = {}
        for season in sorted({x["season"] for x in obs}):
            vals = [x for x in obs if x["season"] == season]
            season_roi[season] = {
                "n": len(vals),
                "ah_roi": _round(sum(x["ah_profit"] for x in vals) / len(vals)),
                "ou_roi": _round(sum(x["ou_profit"] for x in vals) / len(vals)),
            }
        buckets.append({
            "split": split,
            "pattern": key.label(),
            "pattern_key": asdict(key),
            "n": n,
            "favorite_win_rate": _round(sum(x["favorite_win"] for x in obs) / n),
            "ah_profit_units": _round(ah_profit),
            "ah_roi": _round(ah_profit / n),
            "ou_profit_units": _round(ou_profit),
            "ou_roi": _round(ou_profit / n),
            "ou_market_fair_share": _round(sum(x["ou_market_share"] for x in obs) / n),
            "seasons": season_roi,
        })

    buckets.sort(key=lambda b: (b["split"], b["ou_roi"], b["n"]), reverse=True)
    return {
        "schema_version": "1.0",
        "engine": "JOINT_AH_OU_PATTERN_BACKTEST",
        "source_rows": len(rows),
        "test_seasons": sorted(tests),
        "min_n": min_n,
        "skipped_ah_price_rows": skipped_price,
        "market_capability_note": (
            "Current GitHub mirror provides variable Asian Handicap lines but totals only at 2.5. "
            "The engine accepts arbitrary quarter total lines when a future provider supplies them."
        ),
        "warning": (
            "Exploratory pattern mining only. ROI is not evidence of a deployable edge until paired "
            "train/test robustness, multiple-testing correction, and untouched holdout gates pass."
        ),
        "buckets": buckets,
    }
