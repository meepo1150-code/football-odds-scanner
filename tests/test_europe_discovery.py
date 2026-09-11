from odds_scanner.europe_discovery import EXPECTED, TARGETS, ah_marker_diagnostic, candidate_like, quota_allows_discovery, resolve, summarize_diagnostics

# Catalog diagnostics are descriptive only; strict discovery semantics remain unchanged.


def test_exactly_15_european_discovery_leagues():
    assert sum(len(v) for v in TARGETS.values()) == EXPECTED == 15
    assert 'USA' not in TARGETS


def test_resolve_requires_exact_country_and_alias():
    rows=[{'categoryName':'England','tournamentName':'Championship','tournamentSlug':'championship','tournamentId':101}, {'categoryName':'England','tournamentName':'League One','tournamentSlug':'league-one','tournamentId':102}]
    got=resolve(rows)
    assert [x['tournament_id'] for x in got]==[101,102]


def test_candidate_like_ignores_frozen_universe_but_not_conditions():
    s={'favorite_side':'H','favorite_fair_probability':.65,'ah':{'selected_side_line':-1.25,'selected_side_price':1.91},'ou':{'line':2.5,'over_price':1.9,'under_price':1.9}}
    c=[{'pattern_id':'X','universe':'BIG5_AH','market':'AH','pattern_key':{'favorite_side':'H','ah_line':-1.25,'ah_price_band':[1.8,2.0],'favorite_probability_band':[.6,.7]}}]
    assert candidate_like(s,c)==['X']
    s['ah']['selected_side_line']=-1.0
    assert candidate_like(s,c)==[]


def test_discovery_preserves_core_quota_reserve():
    assert quota_allows_discovery({'status':'QUOTA_AVAILABLE','request_remaining':31}) is True
    assert quota_allows_discovery({'status':'QUOTA_AVAILABLE','request_remaining':30}) is False
    assert quota_allows_discovery({'status':'QUOTA_EXHAUSTED','request_remaining':100}) is False
    assert quota_allows_discovery({'status':'USAGE_FIELDS_UNAVAILABLE'}) is False


def _catalog():
    return [{'marketId':201,'sportId':10,'period':'fulltime','playerProp':False,'marketName':'Asian Handicap','marketType':'spreads','handicap':-0.5,'outcomes':[{'outcomeId':201,'outcomeName':'1'},{'outcomeId':202,'outcomeName':'2'}]}]


def _fixture(home_marker='MISSING', away_marker='MISSING', *, active=True, unknown=False):
    def p(price, marker):
        x={'active':True,'price':price}
        if marker!='MISSING': x['mainLine']=(marker=='TRUE')
        return {'players':{'0':x}}
    markets={'201':{'marketActive':active,'outcomes':{'201':p(1.90,home_marker),'202':p(1.98,away_marker)}}}
    if unknown: markets['999']={'marketActive':True,'outcomes':{}}
    return {'bookmakerOdds':{'bet365':{'bookmakerIsActive':True,'suspended':False,'markets':markets}}}


def test_ah_marker_diagnostic_separates_catalog_coverage_from_ah_state():
    missing=ah_marker_diagnostic(_fixture(unknown=True),_catalog())
    assert missing['active_bookmaker_markets']==2
    assert missing['catalog_known_active_markets']==1
    assert missing['unknown_active_market_ids']==['999']
    assert missing['recognized_active_ah_markets']==1
    assert missing['marker_signatures']=={'H_MISSING__A_MISSING':1}
    assert missing['market_state']=='AH_PRESENT_NO_EXPLICIT_MAIN'
    true=ah_marker_diagnostic(_fixture('TRUE','TRUE'),_catalog())
    assert true['market_state']=='HAS_EXPLICIT_MAIN_AH'
    none=ah_marker_diagnostic(_fixture(active=False),_catalog())
    assert none['recognized_active_ah_markets']==0
    assert none['market_state']=='NO_RECOGNIZED_ACTIVE_AH_MARKET'
    unknown_only=_fixture(active=False,unknown=True)
    assert ah_marker_diagnostic(unknown_only,_catalog())['market_state']=='NO_RECOGNIZED_ACTIVE_AH_WITH_UNKNOWN_MARKETS'


def test_diagnostics_aggregate_unknown_market_ids_without_selecting_fallback():
    report=summarize_diagnostics([
        {'country':'England','league':'Championship','shape_key':'AH0_OU1','reason':'AMBIGUOUS_OR_MISSING_MAIN_AH','ah_marker_diagnostic':{'active_bookmaker_markets':3,'catalog_known_active_markets':2,'unknown_active_market_ids':['999'],'recognized_active_ah_markets':2,'marker_signatures':{'H_MISSING__A_MISSING':2},'market_state':'AH_PRESENT_NO_EXPLICIT_MAIN'}},
        {'country':'England','league':'Championship','shape_key':'AH1_OU1','reason':'OK','ah_marker_diagnostic':{'active_bookmaker_markets':2,'catalog_known_active_markets':2,'unknown_active_market_ids':[],'recognized_active_ah_markets':1,'marker_signatures':{'H_TRUE__A_TRUE':1},'market_state':'HAS_EXPLICIT_MAIN_AH'}},
        {'country':'Italy','league':'Serie B','shape_key':'AH0_OU1','reason':'AMBIGUOUS_OR_MISSING_MAIN_AH','ah_marker_diagnostic':{'active_bookmaker_markets':1,'catalog_known_active_markets':0,'unknown_active_market_ids':['999'],'recognized_active_ah_markets':0,'marker_signatures':{},'market_state':'NO_RECOGNIZED_ACTIVE_AH_WITH_UNKNOWN_MARKETS'}},
    ])
    assert report['unknown_active_market_ids']=={'999':2}
    assert report['ah_market_marker_signatures']=={'H_MISSING__A_MISSING':2,'H_TRUE__A_TRUE':1}
    eng=next(x for x in report['league_diagnostics'] if x['league']=='England · Championship')
    assert eng['active_bookmaker_markets']==5
    assert eng['catalog_known_active_markets']==4
    assert eng['recognized_active_ah_markets']==3
    assert eng['unknown_active_market_ids']=={'999':1}
    assert 'No fallback AH line is selected' in report['diagnostic_policy']
