from odds_scanner.football_data_schema_probe import inspect_dataset


def test_inspect_dataset_detects_early_and_closing_market_columns():
    headers = [
        "FTHG", "FTAG", "FTR",
        "AvgH", "AvgD", "AvgA", "MaxH", "MaxD", "MaxA",
        "Avg>2.5", "Avg<2.5", "Max>2.5", "Max<2.5",
        "AHh", "AvgAHH", "AvgAHA", "MaxAHH", "MaxAHA",
        "AvgCH", "AvgCD", "AvgCA", "MaxCH", "MaxCD", "MaxCA",
        "AvgC>2.5", "AvgC<2.5", "MaxC>2.5", "MaxC<2.5",
        "AHCh", "AvgCAHH", "AvgCAHA", "MaxCAHH", "MaxCAHA",
    ]
    row = {c: "2.0" for c in headers}
    row.update({"FTHG": "2", "FTAG": "1", "FTR": "H", "AHh": "-0.5", "AHCh": "-0.75"})
    out = inspect_dataset(headers, [row])
    assert out["has_early_1x2"] is True
    assert out["has_closing_1x2"] is True
    assert out["has_early_ou25"] is True
    assert out["has_closing_ou25"] is True
    assert out["has_early_ah"] is True
    assert out["has_closing_ah"] is True
    assert out["ah_early_unique_lines"] == ["-0.5"]
    assert out["ah_closing_unique_lines"] == ["-0.75"]


def test_inspect_dataset_fails_closed_when_closing_columns_missing():
    out = inspect_dataset(["AvgH", "AvgD", "AvgA", "AHh", "AvgAHH", "AvgAHA"], [])
    assert out["has_early_1x2"] is True
    assert out["has_closing_1x2"] is False
    assert out["has_closing_ah"] is False
