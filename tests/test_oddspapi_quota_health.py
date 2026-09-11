from odds_scanner.oddspapi_quota_health import summarize_account


def _account(limit=250, count=25):
    return {"subscriptions": [{
        "is_active": True,
        "price": 0,
        "currency": "USD",
        "request_limit": limit,
        "request_count": count,
        "rate_limit": 1,
        "sport_ids": [10, 11],
        "bookmakers": {"bet365": {}, "other": {}},
    }]}


def test_available_quota_reports_remaining_and_required_capabilities():
    out = summarize_account(_account(250, 25))
    assert out["status"] == "QUOTA_AVAILABLE"
    assert out["request_remaining"] == 225
    assert out["quota_exhausted"] is False
    assert out["rate_limit"] == 1
    assert out["soccer_sport_id_10_allowed"] is True
    assert out["bet365_allowed"] is True
    assert out["allowed_sport_count"] == 2
    assert out["allowed_bookmaker_count"] == 2
    assert abs(out["usage_fraction"] - 0.1) < 1e-12


def test_exhausted_quota_is_explicit():
    out = summarize_account(_account(250, 250))
    assert out["status"] == "QUOTA_EXHAUSTED"
    assert out["request_remaining"] == 0
    assert out["quota_exhausted"] is True


def test_account_summary_does_not_expose_lists_identifiers_or_keys():
    account = _account()
    account["api_key"] = "secret"
    account["subscriptions"][0]["id"] = "subscription-secret"
    out = summarize_account(account)
    assert "api_key" not in out
    assert "id" not in out
    assert "sport_ids" not in out
    assert "bookmakers" not in out
