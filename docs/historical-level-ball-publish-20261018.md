# Historical level-ball publishing repair

Run 39093392850 completed recovery for 28 fixtures / 56 fixture-bookmaker
pairs on football day 2026-09-10, but its offline publish job failed with
`LEVEL_BALL_FAVORITE_UNRESOLVED`. The retained artifact contains 54
BALANCED_LINE slots, 134 unresolved slots and 36 non-prematch slots.

For validated historical AH 0, the lower decimal price in that same selected
fixture, bookmaker and target slot defines the favorite side. This applies even
when a live cohort at another observation time has a different favorite.
The provenance is `HISTORICAL_LEVEL_BALL_LOWER_DECIMAL_PRICE`; it does not claim
official mainline verification. Equal prices skip only their own slot and are
counted as `LEVEL_BALL_EQUAL_PRICE_SKIPPED` in the publication receipt.

Quote bounds, activity, timestamp freshness, identity validation, append-only
publication and frozen research promotion gates remain in force. Nonzero AH
behavior and both current Manual and Auto workflows/collectors are unchanged.

Recovery procedure: merge after passing CI, rerun only the failed publish job
of run 39093392850. Its existing workflow checks out latest main and replays
the retained artifact offline; it must not rerun the successful collector.
Then verify the publication receipt, Pages deployment and public data.

Regression coverage includes both favorite sides, opposite prior cohort sides,
equal-price slot isolation, invalid/stale quotes, immutable live observations
and idempotent artifact replay. No new provider requests are needed.
