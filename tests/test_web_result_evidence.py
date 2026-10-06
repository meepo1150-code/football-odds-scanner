import json
from odds_scanner.web_result_evidence import import_evidence, EVIDENCE_PATH
from odds_scanner.pinnwire_result_join import SNAPSHOTS_PATH
from odds_scanner.oddspapi_result_cache import RESULTS_PATH

def _write(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("".join(json.dumps(x)+"\n" for x in rows))

def test_official_evidence_imports_and_trusted_result_is_preserved(tmp_path):
    _write(tmp_path/SNAPSHOTS_PATH,[{"provider":"pinnwire","fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z"}])
    ev={"fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z","ft_home_goals":2,"ft_away_goals":1,"status":"FT","source_url":"https://club.example/match","retrieved_at":"2026-09-25T00:00:00Z","sources":[{"url":"https://club.example/match","tier":"A_OFFICIAL"}]}
    _write(tmp_path/EVIDENCE_PATH,[ev])
    r=import_evidence(tmp_path); assert r["results_added"]==1 and not r["quarantine"]
    _write(tmp_path/RESULTS_PATH,[{"fixture_id":"pinnwire:a","ft_home_goals":4,"ft_away_goals":0,"result_source":"API_FOOTBALL"}])
    r=import_evidence(tmp_path); assert r["skipped_trusted"]==["pinnwire:a"]
    row=json.loads((tmp_path/RESULTS_PATH).read_text().splitlines()[0]); assert row["ft_home_goals"]==4

def test_weak_single_source_and_identity_mismatch_are_quarantined(tmp_path):
    _write(tmp_path/SNAPSHOTS_PATH,[{"provider":"pinnwire","fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z"}])
    weak={"fixture_id":"pinnwire:a","home":"Alpha","away":"Beta","kickoff":"2026-09-24T12:00:00Z","ft_home_goals":2,"ft_away_goals":1,"status":"FT","source_url":"https://scores.example/m","retrieved_at":"2026-09-25T00:00:00Z","sources":[{"url":"https://scores.example/m","tier":"B_REPUTABLE"}]}
    _write(tmp_path/EVIDENCE_PATH,[weak])
    assert import_evidence(tmp_path)["quarantine"][0]["reason"]=="INSUFFICIENT_SOURCE_CORROBORATION"
    weak["sources"].append({"url":"https://other.example/m","tier":"B_REPUTABLE"}); weak["home"]="Wrong"
    _write(tmp_path/EVIDENCE_PATH,[weak])
    assert import_evidence(tmp_path)["quarantine"][0]["reason"]=="IDENTITY_MISMATCH_OR_UNKNOWN_FIXTURE"
