from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from . import multiseason_market_research as base
from .asian_settlement import settle_asian_total
from .settlement_ev import settlement_distribution

LEAGUES = {
    "Eredivisie": "eredivisie",
    "Primeira Liga": "primeira-liga",
    "Jupiler Pro League": "jupiler-league",
    "Super Lig": "super-lig",
    "Scottish Premiership": "scottish-premiership",
}
OU_LINE = 2.5
REPORT_PATH = Path("reports/third_universe_ou_validation.json")
CANDIDATE_REGISTRY_PATH = Path("reports/third_universe_ou_pattern_registry_candidate.json")


def _normalize_match(row: dict, *, season: str, league: str) -> list[dict]:
    hg, ag = base._int(row, "FTHG"), base._int(row, "FTAG")
    h, d, a = base._float(row, "AvgH"), base._float(row, "AvgD"), base._float(row, "AvgA")
    ah_home = base._float(row, "AHh")
    over, under = base._float(row, "Avg>2.5"), base._float(row, "Avg<2.5")
    close_over, close_under = base._float(row, "AvgC>2.5"), base._float(row, "AvgC<2.5")
    required = (hg, ag, h, d, a, ah_home, over, under, close_over, close_under)
    if any(x is None for x in required):
        return []
    assert hg is not None and ag is not None
    assert h is not None and d is not None and a is not None and ah_home is not None
    assert over is not None and under is not None and close_over is not None and close_under is not None
    if min(h, d, a, over, under, close_over, close_under) <= 1.0:
        return []
    if not base._on_quarter_grid(ah_home):
        return []

    fh, _, fa = base._fair_1x2(h, d, a)
    favorite_side = "H" if fh >= fa else "A"
    favorite_p = fh if favorite_side == "H" else fa
    selected_ah_line = ah_home if favorite_side == "H" else -ah_home
    probability_band = base._band(favorite_p, base.PROB_WIDTH)

    out = []
    for side, price, opposite, close_price in (
        ("O", over, under, close_over),
        ("U", under, over, close_under),
    ):
        try:
            settled = settle_asian_total(hg, ag, OU_LINE, price, side)
        except ValueError:
            continue
        price_band = base._band(price, base.PRICE_WIDTH)
        out.append({
            "season": season,
            "league": league,
            "date": (row.get("Date") or "").strip(),
            "home": (row.get("HomeTeam") or "").strip(),
            "away": (row.get("AwayTeam") or "").strip(),
            "ft_home_goals": hg,
            "ft_away_goals": ag,
            "favorite_side": favorite_side,
            "favorite_probability": round(favorite_p, 8),
            "favorite_probability_band": list(probability_band),
            "ah_line": selected_ah_line,
            "ou_side": side,
            "ou_line": OU_LINE,
            "ou_price": price,
            "ou_opposite_price": opposite,
            "ou_price_band": list(price_band),
            "closing_ou_price": close_price,
            "price_move": round(close_price - price, 6),
            "settlement": settled.settlement.value,
            "profit_units": round(settled.profit_units, 8),
            "source_semantics": "FOOTBALL_DATA_FIRST_COLLECTED_AFTER_MARKET_OPENING_NOT_TRUE_OPEN",
            "promotion_eligible": False,
        })
    return out


def load_mirror(mirror_root: Path) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    files = []
    for season in base.SEASONS:
        for league, directory in LEAGUES.items():
            path = mirror_root / "data" / directory / f"season-{season}.csv"
            if not path.exists():
                files.append({"season": season, "league": league, "status": "MISSING", "path": str(path)})
                continue
            raw = path.read_bytes()
            sha256 = hashlib.sha256(raw).hexdigest()
            reader = csv.DictReader(raw.decode("utf-8-sig", errors="replace").splitlines())
            total = 0
            normalized = 0
            for source_row in reader:
                total += 1
                items = _normalize_match(source_row, season=season, league=league)
                rows.extend(items)
                normalized += len(items)
            files.append({"season": season, "league": league, "status": "OK", "rows": total, "normalized_observations": normalized, "sha256": sha256})
    try:
        import subprocess
        mirror_commit = subprocess.check_output(["git", "-C", str(mirror_root), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        mirror_commit = None
    return rows, {"mirror_commit": mirror_commit, "files": files}


def _key(row: dict) -> tuple:
    return (
        row["favorite_side"],
        float(row["ah_line"]),
        row["ou_side"],
        tuple(row["ou_price_band"]),
        tuple(row["favorite_probability_band"]),
    )


def _pid(key: tuple) -> str:
    raw = json.dumps(key, sort_keys=True, separators=(",", ":"))
    return "FD_OU25_" + hashlib.sha1(raw.encode()).hexdigest()[:12].upper()


def _phase_stats(rows: list[dict], seed: int) -> dict:
    ci = base._bootstrap_ci(rows, seed=seed)
    return {
        "n": len(rows),
        "roi": round(base._roi(rows), 6),
        "profit_units": round(sum(float(r["profit_units"]) for r in rows), 6),
        "bootstrap_roi_ci95": [round(ci[0], 6), round(ci[1], 6)],
        "settlement_distribution": settlement_distribution(r["settlement"] for r in rows),
    }


def validate(rows: list[dict]) -> tuple[dict, dict]:
    groups: dict[tuple, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        phase = base._phase(str(row["season"]))
        if phase:
            groups[_key(row)][phase].append(row)

    tested = []
    pvalues = []
    for i, (key, phases) in enumerate(sorted(groups.items(), key=lambda kv: str(kv[0]))):
        train = phases.get("train", [])
        validation = phases.get("validation", [])
        if len(train) < base.MIN_N["train"] or base._roi(train) <= 0:
            continue
        pid = _pid(key)
        p = base._sign_flip_p(validation, seed=99000 + i) if len(validation) >= base.MIN_N["validation"] else 1.0
        pvalues.append((pid, p))
        tested.append((pid, key, phases, p))
    qvals = base._bh(pvalues)

    candidates = []
    registry_patterns = []
    for i, (pid, key, phases, p) in enumerate(tested):
        train = phases.get("train", [])
        validation = phases.get("validation", [])
        holdout = phases.get("holdout", [])
        q = qvals.get(pid, 1.0)
        all_eval = validation + holdout
        league_rois = {}
        for league in LEAGUES:
            lr = [r for r in all_eval if r["league"] == league]
            if lr:
                league_rois[league] = {"n": len(lr), "roi": round(base._roi(lr), 6)}
        positive_share = (sum(v["roi"] > 0 for v in league_rois.values()) / len(league_rois)) if league_rois else 0.0
        season_rois = {}
        for season in sorted(base.VALIDATION | base.HOLDOUT):
            phase_name = base._phase(season)
            sr = [r for r in phases.get(phase_name or "", []) if r["season"] == season]
            if sr:
                season_rois[season] = round(base._roi(sr), 6)

        gates = {
            "train_n": len(train) >= base.MIN_N["train"],
            "validation_n": len(validation) >= base.MIN_N["validation"],
            "holdout_n": len(holdout) >= base.MIN_N["holdout"],
            "train_roi_positive": base._roi(train) > 0,
            "validation_roi_positive": base._roi(validation) > 0 if validation else False,
            "holdout_roi_positive": base._roi(holdout) > 0 if holdout else False,
            "validation_fdr": q <= base.FDR_Q,
            "cross_league_count": len(league_rois) >= base.MIN_CROSS_LEAGUES,
            "positive_league_share": positive_share >= base.MIN_POSITIVE_LEAGUE_SHARE,
            "validation_seasons_positive": all(season_rois.get(s, 0) > 0 for s in base.VALIDATION),
            "holdout_season_positive": season_rois.get("2526", 0) > 0,
        }
        passed = all(gates.values())
        fav_side, ah_line, ou_side, price_band, prob_band = key
        phase_stats = {
            "train": _phase_stats(train, 4100 + i),
            "validation": _phase_stats(validation, 4200 + i),
            "holdout": _phase_stats(holdout, 4300 + i),
        }
        candidate = {
            "pattern_id": pid,
            "status": "GLOBAL_ROBUST_RESEARCH_CANDIDATE" if passed else "REJECT",
            "market": "OU",
            "pattern_key": {
                "favorite_side": fav_side,
                "ah_line": ah_line,
                "ou_side": ou_side,
                "ou_line": OU_LINE,
                "ou_price_band": list(price_band),
                "favorite_probability_band": list(prob_band),
            },
            "train_n": len(train),
            "validation_n": len(validation),
            "holdout_n": len(holdout),
            "p_validation_sign_flip": round(p, 8),
            "q_validation_bh": round(q, 8),
            "phase_stats": phase_stats,
            "league_stats_validation_plus_holdout": league_rois,
            "positive_league_share": round(positive_share, 6),
            "season_rois": season_rois,
            "gates": gates,
        }
        candidates.append(candidate)
        if passed:
            registry_patterns.append({
                "pattern_id": pid,
                "pattern": f"OU {ou_side} 2.5 | favorite {fav_side} AH {ah_line:+g} | price {price_band[0]:.2f}-{price_band[1]:.2f} | fair-p {prob_band[0]:.2f}-{prob_band[1]:.2f}",
                "market": "OU",
                "pattern_key": candidate["pattern_key"],
                "train_n": len(train),
                "validation_n": len(validation),
                "holdout_n": len(holdout),
                "q_validation_bh": round(q, 8),
                "settlement_distributions": {pname: phase_stats[pname]["settlement_distribution"] for pname in ("train", "validation", "holdout")},
                "status": "GLOBAL_ROBUST_RESEARCH_CANDIDATE",
                "promotion_eligible": False,
            })

    report = {
        "schema_version": "1.0",
        "classification": "THIRD_UNIVERSE_OU25_CONFIRMATION",
        "preregistered_split": {"train": sorted(base.TRAIN), "validation": sorted(base.VALIDATION), "holdout": sorted(base.HOLDOUT)},
        "holdout_policy": "2025/26 O/U performance preregistered before evaluation; do not retune after viewing holdout",
        "thresholds": {
            "min_n": base.MIN_N,
            "fdr_q": base.FDR_Q,
            "cross_league_min": base.MIN_CROSS_LEAGUES,
            "positive_league_share_min": base.MIN_POSITIVE_LEAGUE_SHARE,
            "price_bucket_width": base.PRICE_WIDTH,
            "favorite_probability_bucket_width": base.PROB_WIDTH,
        },
        "normalized_observations": len(rows),
        "train_positive_patterns_entering_validation": len(tested),
        "promoted_patterns": len(registry_patterns),
        "candidates": candidates,
        "production_promotion_allowed_by_this_run": False,
    }
    registry = {
        "schema_version": "1.3-candidate",
        "pattern_count": len(registry_patterns),
        "patterns": registry_patterns,
        "promotion_scope": "CANDIDATE_ONLY_REQUIRES_SEPARATE_PRODUCTION_AUDIT",
    }
    return report, registry


def run(root: Path, mirror_root: Path) -> dict:
    rows, provenance = load_mirror(mirror_root)
    report, registry = validate(rows)
    report["league_universe"] = LEAGUES
    report["provenance"] = provenance
    registry["source"] = "football-data.co.uk via pinned GitHub mirror; third independent league universe; O/U 2.5 early averages are first-collected, not true opening"
    rp = root / REPORT_PATH
    cp = root / CANDIDATE_REGISTRY_PATH
    rp.parent.mkdir(parents=True, exist_ok=True)
    cp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    cp.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "normalized_observations": len(rows),
        "tested": report["train_positive_patterns_entering_validation"],
        "promoted_candidates": report["promoted_patterns"],
        "mirror_commit": provenance.get("mirror_commit"),
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--mirror-root", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    args = p.parse_args()
    print(run(args.root, args.mirror_root))
