from odds_scanner.source_qualification import qualification_report


def test_zero_cost_sources_do_not_fake_rich_historical_readiness():
    report = qualification_report()
    assert report["rich_historical_gap_open"] is True
    assert report["zero_cost_rich_historical"] == []


def test_zero_cost_sources_do_not_fake_execution_price_readiness():
    report = qualification_report()
    assert report["execution_provider_gap_open"] is True
    assert report["zero_cost_execution"] == []


def test_sgodds_is_research_only_not_execution():
    rows = {x["provider_id"]: x for x in qualification_report()["providers"]}
    row = rows["sgodds_singapore_pools_open"]
    assert row["execution_ready"] is False
    assert "tradable_execution_price" in row["execution_missing"]
