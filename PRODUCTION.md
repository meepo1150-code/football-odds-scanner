# Production activation

The code path is production-wired and fail-closed. It does not publish a candidate unless a frozen validated pattern exists and a current Bet365 multi-market row passes execution safety, exact structure, the configurable 1.80–2.20 tradability band, and positive settlement-based EV in train/validation/holdout.

## One external credential

Create a free 5DollarFootballAPI key and add it to this repository as the GitHub Actions secret `FIVE_DOLLAR_FOOTBALL_API_KEY`. The key must never be committed to the repository.

After the secret exists, run **Live Odds Scan** manually once. The same workflow then runs automatically at 05:00 and 10:00 UTC each day. It writes `reports/today.json`; GitHub Pages consumes that report.

If the secret/provider is unavailable, the workflow writes a fail-closed status with zero candidates. It never reuses stale picks.

## Interpretation

`NO_VALIDATED_PATTERNS` is a valid production state, not an error. It means historical validation has not found a robust pattern. `NO_QUALIFYING_MATCHES` means robust patterns exist but no current price survived all gates. The scanner never fills a five-pick quota.
