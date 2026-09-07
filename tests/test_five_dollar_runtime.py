from datetime import datetime, timezone
from odds_scanner.five_dollar_provider import parse_fixture_odds
from odds_scanner.execution_safety import execution_snapshot_status


def test_latest_pre_match_observation_can_pass_execution_safety():
    fixture={'status':'scheduled','kickoff_utc':'2026-09-08T12:00:00Z','teams':{'home':{'name':'A'},'away':{'name':'B'}},'league':{'name':'EPL'}}
    odds={'data':{'bookmakers':[{'slug':'bet365','odds':{'1x2':{'closing':{'home':1.7,'draw':3.8,'away':4.6}},'asian_handicap':{'closing':{'line':-0.75,'home':1.92,'away':1.94}},'goal_line':{'closing':{'line':2.75,'over':1.91,'under':1.95}}}}]}}
    row=parse_fixture_odds(fixture,odds,observed_at='2026-09-07T12:00:00+00:00')
    assert row.ou_line == 2.75
    assert row.ah_home_line == -0.75
    assert row.source.endswith('latest_pre_match')
    ok, reason=execution_snapshot_status(row, now=datetime(2026,9,7,12,10,tzinfo=timezone.utc))
    assert ok is True
    assert reason == 'EXECUTION_SAFE'
