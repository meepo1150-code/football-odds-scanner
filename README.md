# Football Odds Scanner

Personal deterministic research system for studying bookmaker 1X2 prices, calibration, flat-stake ROI and opening-to-closing line movement.

## Phase status
- P0 data adapter: implemented for Football-Data.co.uk Premier League CSVs.
- P1 backtest foundation: implemented with 0.10 odds buckets, proportional de-vig, train/test season split, ROI and CLV proxy.
- P2 scanner foundation: implemented against current fixture CSV, but intentionally only uses patterns that survive the held-out test filter.
- P3 dashboard foundation: static GitHub Pages dashboard.

## Run
```bash
python -m pip install -e '.[dev]'
pytest -q
python -m odds_scanner.pipeline
```

## Methodology guardrails
- Test seasons are held out (latest 3 configured seasons).
- No pattern is called an edge solely from in-sample ROI.
- Market expected probability is proportional de-vig of the full 1X2 book.
- Flat-stake ROI uses the same chosen opening odds field as the bucket.
- Data-source/schema failures should fail rather than silently fabricate data.

## Data source
Football-Data.co.uk historical European results/odds and current fixture CSV. Verify provider terms and schema before production use.
