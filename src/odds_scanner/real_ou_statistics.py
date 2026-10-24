"""Research-only O/U statistics from the same quoted snapshot as the AH line.

Do not substitute a fixed total line or infer an O/U quote from final scores.
One canonical fixture contributes once: the latest prematch snapshot selected
by research_v2_pattern_stats. Both O and U are settled with split-quarter stakes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import math

from .asian_settlement import settle_asian_total


def _num(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _bucket(value):
    v = _num(value)
    if v is None:
        return "UNKNOWN"
    if v < 1.80:
        return "<1.80"
    if v > 2.20:
        return ">2.20"
    if v < 1.90:
        return "1.80-1.89"
    if v < 2.00:
        return "1.90-1.99"
    if v < 2.10:
        return "2.00-2.09"
    return "2.10-2.20"


def _quote(s):
    ou = s.get("ou") or s.get("over_under_2_5") or s.get("ou_2_5")
    if not isinstance(ou, dict) or not ou:
        return None, "MISSING_OU"
    line = _num(ou.get("line"))
    over = _num(ou.get("over_price", ou.get("over")))
    under = _num(ou.get("under_price", ou.get("under")))
    if line is None or line < 0 or abs(line * 4 - round(line * 4)) > 1e-8:
        return None, "INVALID_OU_LINE"
    if over is None or under is None or over <= 1 or under <= 1:
        return None, "INVALID_OU_TWO_SIDED_PRICE"
    try:
        observed = datetime.fromisoformat(str(s["observed_at"]).replace("Z", "+00:00"))
        kickoff = datetime.fromisoformat(str(s["kickoff"]).replace("Z", "+00:00"))
        if observed.tzinfo is None or kickoff.tzinfo is None or not observed < kickoff:
            return None, "NOT_PREMATCH"
    except (KeyError, TypeError, ValueError):
        return None, "INVALID_QUOTE_TIMESTAMP"
    if not s.get("bookmaker") or not s.get("source_semantics"):
        return None, "MISSING_PRICE_PROVENANCE"
    verified = bool(s.get("mainline_verified") is True or
                    s.get("source_semantics") == "CURRENT_ODDSPAPI_MAINLINE_TRUE_OBSERVED")
    return {
        "line": line, "over_price": over, "under_price": under,
        "observed_at": s["observed_at"], "bookmaker": s["bookmaker"],
        "source_semantics": s["source_semantics"],
        "mainline_verified": verified,
    }, "VERIFIED_MAINLINE" if verified else "PAIRED_QUOTE_MAINLINE_UNVERIFIED"


def real_ou_outcome(s, home_goals, away_goals):
    """Return settlement fields for one actual same-snapshot O/U pair."""
    quote, status = _quote(s)
    result = {"ou_real_quote_status": status, "ou_real_line": None,
              "ou_real_over_price": None, "ou_real_under_price": None,
              "ou_real_over_settlement": None, "ou_real_under_settlement": None,
              "ou_real_over_profit_units": None, "ou_real_under_profit_units": None,
              "ou_real_over_price_bucket": None, "ou_real_under_price_bucket": None,
              "ou_real_mainline_verified": False}
    if quote is None:
        return result
    over = settle_asian_total(home_goals, away_goals, quote["line"], quote["over_price"], "O")
    under = settle_asian_total(home_goals, away_goals, quote["line"], quote["under_price"], "U")
    result.update({
        "ou_real_line": quote["line"],
        "ou_real_over_price": quote["over_price"],
        "ou_real_under_price": quote["under_price"],
        "ou_real_over_price_bucket": _bucket(quote["over_price"]),
        "ou_real_under_price_bucket": _bucket(quote["under_price"]),
        "ou_real_over_settlement": over.settlement.value,
        "ou_real_under_settlement": under.settlement.value,
        "ou_real_over_profit_units": over.profit_units,
        "ou_real_under_profit_units": under.profit_units,
        "ou_real_mainline_verified": quote["mainline_verified"],
    })
    return result


def aggregate_real_ou(outcomes):
    """At most one outcome per canonical fixture, evaluated on a real O/U quote.

    WR = (FULL_WIN + HALF_WIN) / all settled bets including PUSH, exactly like AH.
    Legacy single-side rows retain their own price bucket; paired O/U win-rate
    rows group on the actual Over price bucket ONLY (Under price not a filter).
    """
    groups = defaultdict(list)
    paired_groups = defaultdict(list)
    quote_statuses = Counter()
    matched_fixtures = set()
    for row in outcomes:
        quote_statuses[row.get("ou_real_quote_status") or "NOT_EVALUATED"] += 1
        line = _num(row.get("ou_real_line"))
        if line is None:
            continue
        fixture_id = str(row.get("fixture_id") or "")
        if not fixture_id or fixture_id in matched_fixtures:
            continue
        matched_fixtures.add(fixture_id)
        # Paired markets share the same FT fixture population for one Over / Push /
        # Under bar. Split by actual Over line and Over price bucket only; the
        # Under quote is validated but never used to partition this population.
        statuses = {"FULL_WIN", "HALF_WIN", "PUSH", "HALF_LOSS", "FULL_LOSS"}
        op, up = (_num(row.get(f"ou_real_{side}_price")) for side in ("over", "under"))
        os, us = (row.get(f"ou_real_{side}_settlement") for side in ("over", "under"))
        opr, upr = (_num(row.get(f"ou_real_{side}_profit_units")) for side in ("over", "under"))
        if (op is not None and up is not None and op > 1 and up > 1
                and os in statuses and us in statuses
                and opr is not None and upr is not None):
            pair_key = (row.get("market_side"), str(row.get("ah_line")),
                        row.get("ah_price_bucket"), format(line, ".15g"),
                        _bucket(op))
            paired_groups[pair_key].append(row)
        for selection, prefix in (("OVER", "over"), ("UNDER", "under")):
            price = _num(row.get(f"ou_real_{prefix}_price"))
            state = row.get(f"ou_real_{prefix}_settlement")
            profit = _num(row.get(f"ou_real_{prefix}_profit_units"))
            if price is None or price <= 1 or profit is None or state not in {
                "FULL_WIN", "HALF_WIN", "PUSH", "HALF_LOSS", "FULL_LOSS"
            }:
                continue
            group_key = (row.get("market_side"), str(row.get("ah_line")),
                         row.get("ah_price_bucket"), format(line, ".15g"),
                         selection, _bucket(price))
            groups[group_key].append((row, state, profit))
    grouped = []
    for key, entries in groups.items():
        states = Counter(state for _, state, _ in entries)
        n = len(entries)
        wins = states["FULL_WIN"] + states["HALF_WIN"]
        profit = sum(p for _, _, p in entries)
        total_goals = sum(int(r["ft_home_goals"]) + int(r["ft_away_goals"]) for r, _, _ in entries)
        grouped.append(dict(
            zip(("market_side", "ah_line", "ah_price_bucket", "ou_line",
                 "selection", "ou_price_bucket"), key),
            n=n, full_win=states["FULL_WIN"], half_win=states["HALF_WIN"],
            push=states["PUSH"], half_loss=states["HALF_LOSS"],
            full_loss=states["FULL_LOSS"], price_win_n=wins,
            price_win_pct=round(100*wins/n, 2),
            push_pct=round(100*states["PUSH"]/n, 2),
            profit_units=round(profit, 4), roi_pct=round(100*profit/n, 2),
            avg_total_goals=round(total_goals/n, 2),
            mainline_verified_n=sum(r.get("ou_real_mainline_verified") is True
                                    for r, _, _ in entries),
            sample_label="TINY" if n < 20 else "EARLY" if n < 40 else
            "DEVELOPING" if n < 60 else "MODERATE" if n < 100 else "LARGE",
        ))
    grouped.sort(key=lambda r: (-r["n"], str(r["market_side"]), r["ou_line"], r["selection"]))
    paired = []
    for key, rows in paired_groups.items():
        n = len(rows)
        over_states = Counter(r["ou_real_over_settlement"] for r in rows)
        under_states = Counter(r["ou_real_under_settlement"] for r in rows)
        over_wins = over_states["FULL_WIN"] + over_states["HALF_WIN"]
        under_wins = under_states["FULL_WIN"] + under_states["HALF_WIN"]
        pushes = over_states["PUSH"]
        # The two selections on an Asian total are complementary including
        # half-settlements, except that whole-number pushes belong to neither.
        if pushes != under_states["PUSH"] or over_wins + under_wins + pushes != n:
            raise ValueError("Inconsistent paired Asian O/U settlement outcomes")
        paired.append(dict(
            zip(("market_side", "ah_line", "ah_price_bucket", "ou_line",
                 "over_price_bucket"), key),
            n=n, over_win_n=over_wins, under_win_n=under_wins, push_n=pushes,
            over_win_pct=round(100 * over_wins / n, 2),
            under_win_pct=round(100 * under_wins / n, 2),
            push_pct=round(100 * pushes / n, 2),
            over_full_win=over_states["FULL_WIN"],
            over_half_win=over_states["HALF_WIN"],
            over_half_loss=over_states["HALF_LOSS"],
            over_full_loss=over_states["FULL_LOSS"],
            under_full_win=under_states["FULL_WIN"],
            under_half_win=under_states["HALF_WIN"],
            under_half_loss=under_states["HALF_LOSS"],
            under_full_loss=under_states["FULL_LOSS"],
            over_roi_pct=round(100 * sum(r["ou_real_over_profit_units"] for r in rows) / n, 2),
            under_roi_pct=round(100 * sum(r["ou_real_under_profit_units"] for r in rows) / n, 2),
            mainline_verified_n=sum(r.get("ou_real_mainline_verified") is True for r in rows),
        ))
    paired.sort(key=lambda row: (-row["n"], row["ou_line"], str(row["market_side"])))
    # Completely independent O/U statistical population: neither AH side,
    # AH line, AH decimal price, nor AH core-price eligibility is a key.
    # Rows are the same exact one-per-fixture prematch Over quote and verified FT
    # outcomes; under_price is NOT used as a selection/grouping field.
    independent_groups = defaultdict(list)
    for group_key, rows in paired_groups.items():
        ou_line, over_bucket = group_key[-2:]
        independent_groups[(ou_line, over_bucket)].extend(rows)
    standalone = []
    for (ou_line, over_bucket), rows in independent_groups.items():
        n = len(rows)
        over_states = Counter(r["ou_real_over_settlement"] for r in rows)
        under_states = Counter(r["ou_real_under_settlement"] for r in rows)
        ow = over_states["FULL_WIN"] + over_states["HALF_WIN"]
        uw = under_states["FULL_WIN"] + under_states["HALF_WIN"]
        push = over_states["PUSH"]
        if push != under_states["PUSH"] or ow + uw + push != n:
            raise ValueError("O/U standalone win-rate group has inconsistent settlements")
        fixture_ids = {str(r["fixture_id"]) for r in rows}
        if len(fixture_ids) != n:
            raise ValueError("O/U standalone win-rate group counted one fixture more than once")
        standalone.append({
            "ou_line": ou_line, "over_price_bucket": over_bucket,
            "n": n, "over_win_n": ow, "under_win_n": uw, "push_n": push,
            "over_win_pct": round(100 * ow / n, 2),
            "under_win_pct": round(100 * uw / n, 2),
            "push_pct": round(100 * push / n, 2),
            "over_full_win": over_states["FULL_WIN"],
            "over_half_win": over_states["HALF_WIN"],
            "over_half_loss": over_states["HALF_LOSS"],
            "over_full_loss": over_states["FULL_LOSS"],
            "under_full_win": under_states["FULL_WIN"],
            "under_half_win": under_states["HALF_WIN"],
            "under_half_loss": under_states["HALF_LOSS"],
            "under_full_loss": under_states["FULL_LOSS"],
            "over_roi_pct": round(100 * sum(r["ou_real_over_profit_units"] for r in rows) / n, 2),
            "mainline_verified_n": sum(r.get("ou_real_mainline_verified") is True for r in rows),
            "sample_label": "TINY" if n < 20 else "EARLY" if n < 40 else
            "DEVELOPING" if n < 60 else "MODERATE" if n < 100 else "LARGE",
        })
    standalone.sort(key=lambda row: (-row["n"], row["ou_line"], row["over_price_bucket"]))

    # Joint AH x O/U LINE ONLY: preserve favorite-side direction and both
    # handicap/total lines, but DO NOT split by either market's decimal odds.
    # Sum the already-exclusive same-fixture quote groups; half settlements and
    # whole-line pushes retain their exact settlement semantics.
    joint_by_lines = defaultdict(list)
    for group_key, group_rows in paired_groups.items():
        market_side, ah_line, _, ou_line, _ = group_key
        joint_by_lines[(market_side, ah_line, ou_line)].extend(group_rows)
    joint_line_groups = []
    for (market_side, ah_line, ou_line), rows in joint_by_lines.items():
        n = len(rows)
        states_over = Counter(r["ou_real_over_settlement"] for r in rows)
        states_under = Counter(r["ou_real_under_settlement"] for r in rows)
        ow = states_over["FULL_WIN"] + states_over["HALF_WIN"]
        uw = states_under["FULL_WIN"] + states_under["HALF_WIN"]
        push = states_over["PUSH"]
        if push != states_under["PUSH"] or ow + uw + push != n:
            raise ValueError("Inconsistent AH x O/U line-only outcome aggregation")
        if len({str(r["fixture_id"]) for r in rows}) != n:
            raise ValueError("AH x O/U line-only group double-counted fixture")
        joint_line_groups.append({
            "market_side": market_side, "ah_line": ah_line, "ou_line": ou_line,
            "n": n, "over_win_n": ow, "under_win_n": uw, "push_n": push,
            "over_win_pct": round(100*ow/n, 2),
            "under_win_pct": round(100*uw/n, 2),
            "push_pct": round(100*push/n, 2),
            "over_full_win": states_over["FULL_WIN"],
            "over_half_win": states_over["HALF_WIN"],
            "over_half_loss": states_over["HALF_LOSS"],
            "over_full_loss": states_over["FULL_LOSS"],
            "under_full_win": states_under["FULL_WIN"],
            "under_half_win": states_under["HALF_WIN"],
            "under_half_loss": states_under["HALF_LOSS"],
            "under_full_loss": states_under["FULL_LOSS"],
            "over_roi_pct": round(100*sum(r["ou_real_over_profit_units"] for r in rows)/n, 2),
            "mainline_verified_n": sum(r.get("ou_real_mainline_verified") is True for r in rows),
        })
    joint_line_groups.sort(key=lambda r: (-r["n"], r["market_side"], r["ah_line"], r["ou_line"]))

    return {"real_ou_combo_by_ah_line_and_ou_line": joint_line_groups,
            "real_ou_combo_grouping": "AH_FAVORITE_SIDE_AH_LINE_AND_REAL_OU_LINE_ONLY; NO_AH_OR_OU_PRICE_BUCKET",
            "real_ou_quote_status_counts": dict(quote_statuses),
            "real_ou_paired_by_line_over_price_bucket": standalone,
            "real_ou_independent_grouping": "ACTUAL_OU_LINE_AND_OVER_DECIMAL_ODDS_BUCKET_ONLY; ALL_TRUSTED_SETTLED_PREMATCH_FIXTURES_WITH_PAIRED_QUOTE; NO_AH_CONDITION",
            "real_ou_paired_by_ah_line_price_ou_line_price_buckets": paired,
            "real_ou_paired_price_grouping": "AH_SIDE_AH_LINE_AH_BUCKET_REAL_OU_LINE_OVER_PRICE_BUCKET_ONLY; UNDER_ODDS_NOT_A_GROUPING_FILTER",
            "real_ou_settled_fixtures_with_paired_quote": len(matched_fixtures),
            "real_ou_by_ah_line_price_ou_line_price": grouped,
            "real_ou_win_rate_definition":
            "(FULL_WIN + HALF_WIN) / ALL_SETTLED_INCLUDING_PUSH; ASIAN_QUARTER_LINE; ROI_EXACT_STAKE_RETURN",
            "real_ou_population_policy":
            "LATEST_VERIFIED_PREMATCH_AH_SNAPSHOT_PER_CANONICAL_FIXTURE_WITH_REAL_PAIRED_OU_AND_FT; NO_FIXED_LINE" }
