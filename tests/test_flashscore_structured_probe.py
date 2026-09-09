from odds_scanner.flashscore_structured_probe import inspect_html


def test_inspect_html_keeps_only_compact_structured_evidence():
    html = b'''<!doctype html><html><head>
    <title>Home 2-1 Away - Flashscore</title>
    <meta property="og:title" content="Home v Away">
    <script type="application/ld+json">{
      "@type":"SportsEvent",
      "name":"Home - Away",
      "eventStatus":"EventCompleted",
      "homeTeam":{"@type":"SportsTeam","name":"Home"},
      "awayTeam":{"@type":"SportsTeam","name":"Away"},
      "homeScore":2,
      "awayScore":1,
      "ignoredBlob":"do not retain"
    }</script>
    <script id="app-state" type="application/json">{"huge":"blob"}</script>
    </head><body></body></html>'''
    evidence = inspect_html(html)
    assert evidence["title"] == "Home 2-1 Away - Flashscore"
    assert evidence["structured_jsonld"][0]["eventStatus"] == "EventCompleted"
    assert evidence["structured_jsonld"][0]["homeScore"] == 2
    assert evidence["structured_jsonld"][0]["awayScore"] == 1
    assert "ignoredBlob" not in evidence["structured_jsonld"][0]
    assert evidence["script_type_counts"]["application/ld+json"] == 1
    assert "app-state" in evidence["script_ids"]
