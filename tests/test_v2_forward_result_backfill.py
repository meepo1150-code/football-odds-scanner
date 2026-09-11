from datetime import datetime, timezone

from odds_scanner.v2_forward_result_backfill import select_result_candidates

NOW = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)


def _entry(fixture_id="fx1", kickoff="2026-09-12T08:00:00Z", flashscore_id="abc"):
    row = {
        "candidate_id": "C1",
        "fixture_id": fixture_id,
        "kickoff": kickoff,
        "home": "Home",
        "away": "Away",
    }
    if flashscore_id is not None:
        row["external_providers"] = {"flashscoreId": flashscore_id}
    return row


def test_only_mature_exact_flashscore_ids_are_selected():
    rows = [
        _entry("mature", "2026-09-12T08:00:00Z", "m1"),
        _entry("too-soon", "2026-09-12T10:30:00Z", "m2"),
        _entry("no-id", "2026-09-12T08:00:00Z", None),
    ]
    out = select_result_candidates(rows, set(), now=NOW)
    assert [x["fixture_id"] for x in out] == ["mature"]
    assert out[0]["external_providers"] == {"flashscoreId": "m1"}


def test_existing_result_is_not_requested_again():
    out = select_result_candidates([_entry()], {"fx1"}, now=NOW)
    assert out == []


def test_duplicate_candidate_entries_for_same_fixture_request_once():
    rows = [_entry("fx1"), {**_entry("fx1"), "candidate_id": "C2"}]
    out = select_result_candidates(rows, set(), now=NOW)
    assert len(out) == 1


def test_no_team_or_date_discovery_without_exact_external_id():
    row = _entry(flashscore_id=None)
    row["home"] = "Very Famous Club"
    row["away"] = "Another Famous Club"
    out = select_result_candidates([row], set(), now=NOW)
    assert out == []
