from odds_scanner.provider_capabilities import capability_matrix, providers_supporting


def test_active_free_sources_do_not_claim_quarter_total_history():
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


def test_rich_quarter_total_sources_are_explicitly_key_gated():
    rich = providers_supporting(ou_quarter_lines=True)
    assert rich
    assert all(p["api_key_required"] for p in rich)
    assert all(p["production_status"] == "KEY_REQUIRED_NOT_CONNECTED" for p in rich)


def test_current_price_sources_exclude_opening_only_sgodds():
    current = providers_supporting(current_odds=True)
    ids = {p["provider_id"] for p in current}
    assert "sgodds_singapore_pools_open" not in ids
    assert ids == {"isports_historical_all", "tipsme_pro"}


def test_movement_history_is_not_silently_assumed():
    movement = providers_supporting(movement_history=True)
    assert [p["provider_id"] for p in movement] == ["tipsme_pro"]
