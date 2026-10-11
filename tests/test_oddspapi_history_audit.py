from odds_scanner.oddspapi_history_audit import audit_rows


def test_audit_counts_multimarket_quarter_lines_and_ticks():
    tick={"created_at":"2026-01-17T12:00:00Z","price":1.95,"active":True}
    rows=[{
        "fixture_id":"f1","league":"Premier League",
        "one_x_two":{"home":[tick],"draw":[tick],"away":[tick]},
        "asian_handicap":[{"line":-0.75,"home":[tick],"away":[tick]}],
        "over_under":[{"line":2.75,"over":[tick],"under":[tick]}],
    }]
    out=audit_rows(rows)
    assert out["fixture_rows"]==1
    assert out["unique_fixture_ids"]==1
    assert out["coverage"]["fixtures_with_1x2_ah_ou"]==1
    assert out["coverage"]["invalid_non_quarter_lines"]==0
    assert out["coverage"]["timestamped_ticks"]==7
    assert out["asian_handicap_line_counts"]["-0.75"]==1
    assert out["over_under_line_counts"]["2.75"]==1
    assert out["promotion_allowed"] is False


def test_audit_flags_non_quarter_line_without_promoting():
    tick={"created_at":"2026-01-17T12:00:00Z","price":1.9,"active":False}
    out=audit_rows([{"fixture_id":"f","league":"L","asian_handicap":[{"line":-0.6,"home":[tick],"away":[tick]}]}])
    assert out["coverage"]["invalid_non_quarter_lines"]==1
    assert out["promotion_allowed"] is False


def test_audit_reads_legacy_and_shards_and_stamps_time(tmp_path):
    import json
    from odds_scanner.oddspapi_history_audit import write_audit
    from odds_scanner.oddspapi_history_store import LEGACY_TICKS_PATH as LEGACY
    legacy=tmp_path/LEGACY;legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({'fixture_id':'legacy'})+'\n')
    shard=legacy.with_suffix('')/'2026-10-11.jsonl';shard.parent.mkdir()
    shard.write_text(json.dumps({'fixture_id':'shard'})+'\n')
    r=write_audit(tmp_path)
    assert r['fixture_rows']==2 and r['source_archive_rows']==2
    assert r['unique_fixture_ids']==2 and r['generated_at']
    assert len(r['source_paths'])==2
