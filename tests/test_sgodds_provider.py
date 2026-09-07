from odds_scanner.sgodds_provider import capability_summary, enumerate_downloads, parse_csv, two_way_fair_probs


def test_enumerate_downloads():
    html = '<a href="/downloads/sgodds-123-english-premier.csv">Download</a>'
    found = enumerate_downloads(html)
    assert found == {"english-premier": "https://sgodds.com/downloads/sgodds-123-english-premier.csv"}


def test_parse_variable_quarter_lines_and_health():
    csv_text = """Match,Start Time,Ah_01_Hcap,Ah_01,Ah_02_Hcap,Ah_02,Ou_hcap,Ou_01,Ou_02,Ft1X2_01,Ft1X2_02,Ft1X2_03
Alpha vs Beta,2026-09-07 19:30:00,-0.75,1.92,0.75,1.94,2.75,1.91,1.95,1.70,3.80,4.60
Gamma vs Delta,2026-09-07 21:00:00,-2.30,1.90,2.30,1.90,2.30,1.90,1.90,1.40,4.50,7.50
"""
    rows = parse_csv(csv_text, "english-premier")
    assert len(rows) == 2
    assert rows[0].ah_home_line == -0.75
    assert rows[0].ou_line == 2.75
    assert rows[1].ah_home_line is None
    assert rows[1].ou_line is None
    summary = capability_summary(rows)
    assert summary["alternate_ou_rows"] == 1
    assert summary["quarter_ou_rows"] == 1


def test_two_way_devig():
    a, b, margin = two_way_fair_probs(1.91, 1.95)
    assert abs((a + b) - 1.0) < 1e-12
    assert margin > 0
