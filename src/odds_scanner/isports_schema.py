from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, Any


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def hk_to_decimal(value: Any) -> float | None:
    """Convert iSports Hong Kong odds to decimal odds."""
    v = _float(value)
    if v is None or v < 0:
        return None
    return round(v + 1.0, 6)


def quarter_line(value: Any) -> float | None:
    v = _float(value)
    if v is None:
        return None
    return v if abs(v * 4 - round(v * 4)) < 1e-9 else None


@dataclass(frozen=True)
class CanonicalOddsLine:
    provider: str
    match_id: str
    company_id: str
    market: str
    line_index: int | None
    opening_line: float | None
    opening_side_a_odds: float | None
    opening_side_b_odds: float | None
    current_line: float | None
    current_side_a_odds: float | None
    current_side_b_odds: float | None
    close: bool | None
    in_play: bool | None
    odds_stage: str | None
    change_time: int | None


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "True"):
        return True
    if value in (0, "0", "false", "False"):
        return False
    return None


def normalize_ah(record: Mapping[str, Any]) -> CanonicalOddsLine:
    return CanonicalOddsLine(
        provider="isports",
        match_id=str(record.get("matchId", "")),
        company_id=str(record.get("companyId", "")),
        market="AH",
        line_index=_int(record.get("handicapIndex")),
        opening_line=quarter_line(record.get("initialHandicap")),
        opening_side_a_odds=hk_to_decimal(record.get("initialHome")),
        opening_side_b_odds=hk_to_decimal(record.get("initialAway")),
        current_line=quarter_line(record.get("instantHandicap")),
        current_side_a_odds=hk_to_decimal(record.get("instantHome")),
        current_side_b_odds=hk_to_decimal(record.get("instantAway")),
        close=_bool(record.get("close")),
        in_play=_bool(record.get("inPlay")),
        odds_stage=None if record.get("Odds Type") is None else str(record.get("Odds Type")),
        change_time=_int(record.get("changeTime")),
    )


def normalize_ou(record: Mapping[str, Any]) -> CanonicalOddsLine:
    return CanonicalOddsLine(
        provider="isports",
        match_id=str(record.get("matchId", "")),
        company_id=str(record.get("companyId", "")),
        market="OU",
        line_index=_int(record.get("handicapIndex")),
        opening_line=quarter_line(record.get("initialHandicap")),
        opening_side_a_odds=hk_to_decimal(record.get("initialOver")),
        opening_side_b_odds=hk_to_decimal(record.get("initialUnder")),
        current_line=quarter_line(record.get("instantHandicap")),
        current_side_a_odds=hk_to_decimal(record.get("instantOver")),
        current_side_b_odds=hk_to_decimal(record.get("instantUnder")),
        close=_bool(record.get("close")),
        in_play=_bool(record.get("inPlay")),
        odds_stage=None if record.get("Odds Type") is None else str(record.get("Odds Type")),
        change_time=_int(record.get("changeTime")),
    )


def normalize_market_records(records: Iterable[Mapping[str, Any]], market: str) -> list[dict]:
    normalizer = normalize_ah if market == "AH" else normalize_ou if market == "OU" else None
    if normalizer is None:
        raise ValueError("market must be AH or OU")
    out = []
    for record in records:
        row = normalizer(record)
        # Fail closed on malformed line geometry or incomplete two-sided prices.
        if row.opening_line is None or row.current_line is None:
            continue
        if row.opening_side_a_odds is None or row.opening_side_b_odds is None:
            continue
        if row.current_side_a_odds is None or row.current_side_b_odds is None:
            continue
        out.append(asdict(row))
    return out


def is_prematch_execution_eligible(row: Mapping[str, Any]) -> bool:
    """Only open, non-live, pre-match latest prices may feed the production scanner."""
    if row.get("close") is True:
        return False
    if row.get("in_play") is True:
        return False
    stage = row.get("odds_stage")
    # iSports documents 1=early, 2=pre-match closing, 3=in-play, 0=unknown.
    return stage in {"1", "2"}
