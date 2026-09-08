# Current observation freshness contract

Production execution distinguishes two timestamps that must not be conflated:

- `price_changed_at`: when a bookmaker/provider last changed the price. A pre-match price can remain unchanged for minutes or hours and still be the active current quote.
- `observed_at`: when an explicitly current provider endpoint was successfully observed returning the bookmaker, market, and every required selection as active.

The legacy `as_of` gate remains the default for providers that expose a direct quote-freshness timestamp. A provider can use `observed_at` only when its adapter sets `current_feed_verified=True`, provides a non-empty `freshness_basis`, verifies pre-match status, and verifies bookmaker/market/selection activity before setting `tradable=True` and `stale=False`.

A generic fetch timestamp alone is never sufficient. In particular, opening/closing snapshots or endpoints with ambiguous current semantics cannot opt into the observation contract merely because the request was made recently.

For OddsPapi, `/v4/odds` and `/v4/odds-by-tournaments` are current-odds endpoints. Their `changedAt` and `bookmakerChangedAt` fields describe price-change time, so those timestamps are retained as `price_changed_at`; the current endpoint observation becomes `observed_at` only after active-state checks pass.
