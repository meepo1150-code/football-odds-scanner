import json
from odds_scanner.web_result_evidence import import_evidence, EVIDENCE_PATH
from odds_scanner.pinnwire_result_join import SNAPSHOTS_PATH
from odds_scanner.oddspapi_result_cache import RESULTS_PATH

def _assert_sources(ev):
    for source in ev["sources"]:
        source["assertion"]={k:ev[k] for k in ("home","away","kickoff","ft_home_goals","ft_away_goals","status")}
        source["assertion"].update(verification_method="MANUAL_WEB_REVIEW",source_title="Alpha v Beta final result")
    return ev

def _write(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("".join(json.dumps(x)+"\n" for x in rows))

def test_official_evidence_imports_and_trusted_result_is_preserved(tmp_path):
    _write(tmp_path/SNAPSHOTS_PATH,[{"provider":"pinnwire","fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z"}])
    ev={"fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z","ft_home_goals":2,"ft_away_goals":1,"status":"FT","source_url":"https://club.example/match","retrieved_at":"2026-09-25T00:00:00Z","sources":[{"url":"https://club.example/match","tier":"A_OFFICIAL"}]}
    _write(tmp_path/EVIDENCE_PATH,[_assert_sources(ev)])
    r=import_evidence(tmp_path); assert r["results_added"]==1 and not r["quarantine"]
    _write(tmp_path/RESULTS_PATH,[{"fixture_id":"pinnwire:a","ft_home_goals":4,"ft_away_goals":0,"result_source":"API_FOOTBALL"}])
    r=import_evidence(tmp_path); assert r["skipped_trusted"]==["pinnwire:a"]
    row=json.loads((tmp_path/RESULTS_PATH).read_text().splitlines()[0]); assert row["ft_home_goals"]==4

def test_weak_single_source_and_identity_mismatch_are_quarantined(tmp_path):
    _write(tmp_path/SNAPSHOTS_PATH,[{"provider":"pinnwire","fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z"}])
    weak={"fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z","ft_home_goals":2,"ft_away_goals":1,"status":"FT","source_url":"https://scores.example/m","retrieved_at":"2026-09-25T00:00:00Z","sources":[{"url":"https://scores.example/m","tier":"B_REPUTABLE"}]}
    _write(tmp_path/EVIDENCE_PATH,[_assert_sources(weak)])
    assert import_evidence(tmp_path)["quarantine"][0]["reason"]=="INSUFFICIENT_SOURCE_CORROBORATION"
    weak["sources"].append({"url":"https://other.example/m","tier":"B_REPUTABLE"}); weak["home"]="Wrong"
    _write(tmp_path/EVIDENCE_PATH,[_assert_sources(weak)])
    assert import_evidence(tmp_path)["quarantine"][0]["reason"]=="IDENTITY_MISMATCH_OR_UNKNOWN_FIXTURE"


# Exact identity expansion must never cross a changed opponent or kickoff.
def test_evidence_expands_to_exact_duplicate_provider_ids(tmp_path):
    snaps=[
      {"provider":"pinnwire","fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z"},
      {"provider":"pinnwire","fixture_id":"pinnwire:b","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z"},
      {"provider":"pinnwire","fixture_id":"pinnwire:c","home":"Alpha","away":"Other","kickoff":"2026-09-24T12:00:00Z"},
    ]
    _write(tmp_path/SNAPSHOTS_PATH,snaps)
    ev={"fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z","ft_home_goals":2,"ft_away_goals":1,"status":"FT","source_url":"https://club.example/m","retrieved_at":"2026-09-25T00:00:00Z","sources":[{"url":"https://club.example/m","tier":"A_OFFICIAL"}]}
    _write(tmp_path/EVIDENCE_PATH,[_assert_sources(ev)])
    r=import_evidence(tmp_path)
    assert r["accepted_rows"]==2 and r["results_added"]==2
    ids={json.loads(x)["fixture_id"] for x in (tmp_path/RESULTS_PATH).read_text().splitlines()}
    assert ids=={"pinnwire:a","pinnwire:b"}


def _evidence():
    return _assert_sources({"fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z","ft_home_goals":2,"ft_away_goals":1,"status":"FT","source_url":"https://club.example/match","retrieved_at":"2026-09-25T00:00:00Z","sources":[{"url":"https://club.example/match","tier":"A_OFFICIAL"}]})


def test_reviewed_batches_import_without_rewriting_old_evidence(tmp_path):
    _write(tmp_path/SNAPSHOTS_PATH,[{"provider":"pinnwire","fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z"}])
    _write(tmp_path/EVIDENCE_PATH,[])
    original=(tmp_path/EVIDENCE_PATH).read_bytes()
    batch=tmp_path/EVIDENCE_PATH.parent/'web_result_evidence_20261013.jsonl'
    _write(batch,[_evidence()])
    first=import_evidence(tmp_path)
    assert first['results_added']==1 and len(first['evidence_files'])==2
    assert import_evidence(tmp_path)['results_added']==0
    assert (tmp_path/EVIDENCE_PATH).read_bytes()==original


def test_source_assertion_rejections():
    from odds_scanner.web_result_evidence import _quality
    mutations=[
        ("home","Alpha U21","SOURCE_IDENTITY_MISMATCH"),
        ("away","Beta II","SOURCE_IDENTITY_MISMATCH"),
        ("ft_home_goals",3,"SOURCE_SCORE_MISMATCH"),
        ("ft_away_goals",True,"SOURCE_SCORE_MISMATCH"),
        ("status","HT","SOURCE_RESULT_NOT_FINAL"),
        ("kickoff","2026-09-24T12:01:00Z","SOURCE_KICKOFF_MISMATCH"),
        ("match_date","2026-09-25","SOURCE_DATE_MISMATCH"),
        ("verification_method","AUTOMATIC","INVALID_VERIFICATION_METHOD"),
        ("source_title","","MISSING_SOURCE_TITLE"),
    ]
    for key,value,reason in mutations:
        e=_evidence(); e["sources"][0]["assertion"][key]=value
        assert _quality(e)==(False,reason)
    for malformed in (None,[],"bad"):
        e=_evidence();e["sources"][0]["assertion"]=malformed
        assert _quality(e)==(False,"MISSING_SOURCE_ASSERTIONS")


def test_tier_b_date_assertions_and_duplicate_host():
    from copy import deepcopy
    from odds_scanner.web_result_evidence import _quality
    e=_evidence();s=e["sources"][0];s["tier"]="B_REPUTABLE"
    s["assertion"].pop("kickoff");s["assertion"]["match_date"]="2026-09-24"
    other=deepcopy(s);other["url"]="https://scores.example/match";e["sources"].append(other)
    assert _quality(e)==(True,"TIER_B_TWO_INDEPENDENT_SOURCES")
    other["url"]="https://www.club.example/other"
    assert _quality(e)==(False,"DUPLICATE_SOURCE_HOST")


def test_idempotency_and_legacy_missing_provenance_preserves_cache(tmp_path):
    e=_evidence()
    _write(tmp_path/SNAPSHOTS_PATH,[dict(e,provider="pinnwire")])
    _write(tmp_path/EVIDENCE_PATH,[e])
    assert import_evidence(tmp_path)["results_added"]==1
    assert import_evidence(tmp_path)["results_added"]==0
    before=(tmp_path/RESULTS_PATH).read_bytes()
    e["sources"][0].pop("assertion")
    _write(tmp_path/EVIDENCE_PATH,[e])
    report=import_evidence(tmp_path)
    assert report["accepted_rows"]==0
    assert report["quarantine"][0]["reason"]=="MISSING_SOURCE_ASSERTIONS"
    assert (tmp_path/RESULTS_PATH).read_bytes()==before
    assert report["existing_results_revalidated"] is False
    assert report["api_requests_used"]==0 and report["validation_relaxed"] is False


def test_competition_context_prevents_cross_competition_identity_expansion():
    from odds_scanner.web_result_evidence import _same_identity
    e={'home':'Alpha','away':'Beta','kickoff':'2026-10-03T14:00:00Z','competition':'FA Cup'}
    assert _same_identity(e,{**e,'league':'FA Cup'})
    assert not _same_identity(e,{**e,'league':'League Cup'})


def test_provenance_comes_from_each_matched_fixture_not_last_snapshot(tmp_path):
    e=_evidence()
    _write(tmp_path/SNAPSHOTS_PATH,[
        dict(e,provider='pinnwire',canonical_competition_id='league-a',home_club_id='home-a',away_club_id='away-a'),
        dict(e,fixture_id='other:b',provider='other',canonical_competition_id='league-a',home_club_id='home-b',away_club_id='away-b'),
        dict(e,fixture_id='other:c',home='Unrelated',provider='unrelated',canonical_competition_id='wrong',home_club_id='wrong',away_club_id='wrong'),
    ])
    _write(tmp_path/EVIDENCE_PATH,[e])
    assert import_evidence(tmp_path)['results_added']==2
    rows={r['fixture_id']:r for r in map(json.loads,(tmp_path/RESULTS_PATH).read_text().splitlines())}
    assert rows['pinnwire:a']['provider']=='pinnwire'
    assert rows['pinnwire:a']['home_club_id']=='home-a'
    assert rows['other:b']['provider']=='other'
    assert rows['other:b']['home_club_id']=='home-b'
    assert all(r['canonical_competition_id']=='league-a' for r in rows.values())


def test_existing_verified_web_provenance_repair_is_audited_and_idempotent(tmp_path):
    from odds_scanner.web_result_evidence import PROVENANCE_CORRECTIONS_PATH
    e=_evidence()
    _write(tmp_path/SNAPSHOTS_PATH,[dict(e,provider='pinnwire',home_club_id='verified-home')])
    _write(tmp_path/EVIDENCE_PATH,[e])
    old={'fixture_id':'pinnwire:a','provider':'wrong','home_club_id':'wrong','ft_home_goals':2,'ft_away_goals':1,'result_source':'WEB_EVIDENCE_TIER_A_OFFICIAL','retrieved_at':'original-time'}
    _write(tmp_path/RESULTS_PATH,[old])
    assert import_evidence(tmp_path)['provenance_rows_corrected']==1
    audit=tmp_path/PROVENANCE_CORRECTIONS_PATH
    correction=json.loads(audit.read_text())
    assert correction['previous_row']==old
    corrected=json.loads((tmp_path/RESULTS_PATH).read_text())
    assert corrected['provider']=='pinnwire' and corrected['home_club_id']=='verified-home'
    assert corrected['retrieved_at']=='original-time' and corrected['ft_home_goals']==2
    before=audit.read_bytes()
    assert import_evidence(tmp_path)['provenance_rows_corrected']==0
    assert audit.read_bytes()==before
