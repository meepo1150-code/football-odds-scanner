from odds_scanner.oddspapi_quota_health import summarize_account


def _account(limit=250, count=25):
    return {"subscriptions": [{
        "is_active": True,
        "price": 0,
        "currency": "USD",
        "request_limit": limit,
        "request_count": count,
        "rate_limit": 1,
        "sport_ids": [10],
        "bookmakers": {"bet365": {}},
    }]}


def test_available_quota_reports_remaining():
    out = summarize_account(_account(250, 25))
    assert out["status"] == "QUOTA_AVAILABLE"
    assert out["request_remaining"] == 225
    assert out["quota_exhausted"] is False
    assert abs(out["usage_fraction"] - 0.1) < 1e-12


def test_exhausted_quota_is_explicit():
    out = summarize_account(_account(250, 250))
    assert out["status"] == "QUOTA_EXHAUSTED"
    assert out["request_remaining"] == 0
    assert out["quota_exhausted"] is True


def test_account_summary_does_not_expose_subscription_identifiers_or_keys():
    account = _account()
    account["api_key"] = "secret"
    account["subscriptions"][0]["id"] = "subscription-secret"
    out = summarize_account(account)
    assert "api_key" not in out
    assert "id" not in out
