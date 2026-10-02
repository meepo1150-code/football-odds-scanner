from datetime import datetime, timezone
from odds_scanner.research_v2_pattern_stats import pending_age_counts
from odds_scanner.fotmob_result_backfill import _safe_club_key


def test_pending_buckets_partition_without_guessing():
    now=datetime(2026,10,2,20,tzinfo=timezone.utc)
    rows=[{'kickoff':'2026-10-02T17:00:00Z'}, {'kickoff':'2026-10-02T17:00:01Z'},
          {'kickoff':'2026-10-03T17:00:00Z'}, {'kickoff':None},
          {'kickoff':'2026-10-02T15:00:00Z','status':'RETIRED_UNRESOLVED'}]
    assert pending_age_counts(rows,now)=={'active_overdue_ft_fixtures':1,'active_future_or_recent_ft_fixtures':2,'active_unknown_kickoff_ft_fixtures':1}


def test_sapporo_alias_is_specific_and_preserves_youth_identity():
    assert _safe_club_key('Consadole Sapporo')==_safe_club_key('Hokkaido Consadole Sapporo')
    assert _safe_club_key('Fagiano Okayama')==_safe_club_key('Fagiano Okayama FC')
    assert _safe_club_key('Consadole Sapporo U21')!=_safe_club_key('Hokkaido Consadole Sapporo')
