import pytest
from odds_scanner.research_population import exclusion_reason, in_scope

@pytest.mark.parametrize('league', ['Egypt - 2nd Division B', 'Argentina - Liga Pro Reserves'])
def test_reviewed_exact_league_excluded(league):
    assert exclusion_reason({'league':league}) == 'REVIEWED_LEAGUE_OUT_OF_SCOPE'

@pytest.mark.parametrize('league', ['Egypt - 2nd Division A', 'Mongolia - Premier League', 'Israel - Ligat Leumit', 'International - Friendlies', 'Oman - Cup'])
def test_do_not_infer_low_tier_from_country_or_missing_result(league):
    assert in_scope({'league':league})
