from odds_scanner.audit import build_audit


def bucket(split, roi, gap, clv, n=100, win=0.60, expected=0.50):
    return {"split": split, "side": "H", "odds_low": 1.8, "odds_high": 1.9, "n": n,
            "flat_stake_roi": roi, "calibration_gap_pp": gap, "avg_clv": clv,
            "win_rate": win, "market_expected": expected}


def test_audit_requires_positive_train_and_test():
    report={"rows":200,"test_seasons":["2526"],"buckets":[bucket("train",.05,3,.01), bucket("test",-.02,2,.01,n=40)]}
    audit=build_audit(report)
    assert audit["candidate_count"] == 0


def test_audit_marks_consistent_candidate():
    report={"rows":200,"test_seasons":["2526"],"buckets":[bucket("train",.05,3,-.01), bucket("test",.04,2,.01,n=40)]}
    audit=build_audit(report)
    assert audit["candidate_count"] == 1
    assert audit["candidates"][0]["status"] == "CONSISTENT_POSITIVE_RESEARCH_CANDIDATE"
