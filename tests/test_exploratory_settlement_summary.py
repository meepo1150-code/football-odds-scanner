from odds_scanner.exploratory_settlement_summary import summarize


def test_summary_is_descriptive_and_never_promotes():
    rows=[{"settled_markets":[{"market":"AH","selection":"HOME","line":-0.75,"opening":{"profit_units":0.45}},{"market":"AH","selection":"HOME","line":-0.75,"opening":{"profit_units":-1.0}}]}]
    out=summarize(rows)
    assert out["promotion_allowed"] is False
    assert out["classification"]=="DESCRIPTIVE_ONLY_NOT_VALIDATED"
    assert out["cells"][0]["n"]==2
    assert out["cells"][0]["opening_flat_stake_roi"]==-0.275
