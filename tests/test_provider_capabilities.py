from odds_scanner.provider_capabilities import capability_matrix, providers_supporting


def test_active_free_sources_do_not_claim_quarter_total_history_without_keyed_probe():
    providers = capability_matrix()["providers"]
    active_free = [
        p for p in providers
        if p["zero_cost_confirmed"] and p["production_status"] in {"ACTIVE_LIMITED", "OPENING_ONLY_NOT_EXECUTION_PRICE"}
    ]
    assert active_free
    assert all(not p["ou_quarter_lines"] for p in active_free)


def test_sgodds_is_opening_only_not_current_execution_price():
    providers = capability_matrix()["providers"]
    sg = next(p for p in providers if p["provider_id"] == "sgodds_singapore_pools_open")
    assert sg["opening_odds"] is True
    assert sg["current_odds"] is False
    assert sg["production_status"] == "OPENING_ONLY_NOT_EXECUTION_PRICE"


def test_rich_historical_quarter_total_sources_are_key_gated():
    rich = [p for p in providers_supporting(ou_quarter_lines=True) if "rich_historical" in p["role"]]
    assert {p["provider_id"] for p in rich} == {"isports_historical_all", "tipsme_pro"}
    assert all(p["api_key_required"] for p in rich)
    assert all(p["production_status"] == "KEY_REQUIRED_NOT_CONNECTED" for p in rich)


def test_current_price_capability_is_distinct_from_execution_readiness():
    current = providers_supporting(current_odds=True)
    ids = {p["provider_id"] for p in current}
    assert "sgodds_singapore_pools_open" not in ids
    assert {"infersports_keyless", "5dollarfootballapi_free", "oddspapi_free", "odds_api_io", "isports_historical_all", "tipsme_pro"}.issubset(ids)
    infer = next(p for p in current if p["provider_id"] == "infersports_keyless")
    assert infer["production_status"] == "GITHUB_RUNNER_UNREACHABLE"
    five = next(p for p in current if p["provider_id"] == "5dollarfootballapi_free")
    assert five["zero_cost_confirmed"] is True
    assert five["production_status"] == "ACTIVE_RESEARCH_EXECUTION_FRESHNESS_UNVERIFIED"
    op = next(p for p in current if p["provider_id"] == "oddspapi_free")
    assert op["zero_cost_confirmed"] is True
    assert op["production_status"] == "FREE_KEY_REQUIRED_LIVE_PROBE_PENDING"
    paused = next(p for p in current if p["provider_id"] == "odds_api_io")
    assert paused["zero_cost_confirmed"] is False
    assert paused["production_status"] == "FREE_SIGNUP_PAUSED_2026_09_08"


def test_movement_history_capability_is_explicit_not_execution_claim():
    movement = providers_supporting(movement_history=True)
    ids = {p["provider_id"] for p in movement}
    assert {"infersports_keyless", "oddspapi_free", "tipsme_pro"}.issubset(ids)
    infer = next(p for p in movement if p["provider_id"] == "infersports_keyless")
    assert infer["production_status"] == "GITHUB_RUNNER_UNREACHABLE"
