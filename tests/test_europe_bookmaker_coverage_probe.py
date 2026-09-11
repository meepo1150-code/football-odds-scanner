from odds_scanner.europe_bookmaker_coverage_probe import quota_allows_probe, summarize_rows


def test_probe_preserves_quota_after_planned_requests():
    assert quota_allows_probe({'status':'QUOTA_AVAILABLE','request_remaining':33}) is False
    assert quota_allows_probe({'status':'QUOTA_AVAILABLE','request_remaining':34}) is True
    assert quota_allows_probe({'status':'QUOTA_EXHAUSTED','request_remaining':200}) is False


def test_summary_counts_market_coverage_without_candidate_logic():
    report = summarize_rows([
        {'country':'England','league':'Championship','bookmaker_active':True,'ah_main_count':1,'ou_main_count':1,'strict_snapshot':True,'reason':'OK'},
        {'country':'England','league':'Championship','bookmaker_active':True,'ah_main_count':0,'ou_main_count':1,'strict_snapshot':False,'reason':'AMBIGUOUS_OR_MISSING_MAIN_AH'},
        {'country':'Italy','league':'Serie B','bookmaker_active':False,'ah_main_count':0,'ou_main_count':0,'strict_snapshot':False,'reason':'BOOKMAKER_NOT_ACTIVE'},
    ])
    assert report['fixtures_seen'] == 3
    assert report['bookmaker_active_fixtures'] == 2
    assert report['fixtures_with_exactly_one_main_ah'] == 1
    assert report['fixtures_with_exactly_one_main_ou'] == 2
    assert report['fixtures_with_both_exact_mainlines'] == 1
    assert report['strict_snapshots'] == 1
    eng = next(x for x in report['league_coverage'] if x['league'] == 'England · Championship')
    assert eng['ah_main_exactly_one'] == 1
    assert eng['ou_main_exactly_one'] == 2
