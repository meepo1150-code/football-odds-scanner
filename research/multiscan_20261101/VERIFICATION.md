# Verification and research boundaries

- Base data commit: `3b055dd067629cc134dd834df7afcd4f331182dc`.
- Protocol committed locally as `6653535` before outcome summaries were computed; mirrored as a separate protocol commit on the research branch.
- Existing offline regression: **1,010 passed**.
- UEFA master validation: passed; **27 master tests passed**. Initial invocation lacked `PYTHONPATH=src`; rerun with the correct import path passed.
- Research regressions/invariants: **9 passed**, including quarter settlements, side freezing, 05:00 boundary, no future slot substitution, price range, one fixture per strategy/market and strict pre-kickoff observations.
- Independent rerun: core CSV outputs byte-identical; every JSON output reproducible within numerical tolerance. Large CSVs use deterministic gzip.
- Dashboard: public HTML fetched successfully (HTTP 200); source references the same primary snapshots, result cache and slot ledger. Rendered UI and deployed data completeness were not independently reconciled; no dashboard changes were made.
- No provider/API requests, no production files modified. The new CI workflow runs only offline research on pull requests, has read-only permissions and no secrets.

## What these reports establish

Observed coverage losses, actual Asian-settlement benchmark returns, matched price-only differences and exploratory incremental FT prediction tests. All source data under `data/` are inventoried by SHA-256; quality flags and exclusions are retained. Historical recovery and archived ticks are separated from live receipt evidence.

## What they do not establish

No production betting edge, optimal two-slot schedule, trusted closing-line value, complete historical billing savings, actual availability of all training FT labels, or full reconstruction of deleted history/expired Actions artifacts. Model loss intervals are conditional on the fitted model and do not bootstrap the entire training process. Missing data and provider/bookmaker regimes limit generalization. Archive results are not evidence of executable live prices. Family-adjusted q-values appear in individual reports; `all_inference_bh.json` is the global correction across the live-study tests. Separate archive sensitivity is not part of that claim family and is not promoted.

No model-derived EV bet is selected because the frozen validated registry is empty. The fixed favorite/Over policy is an explicitly disclosed descriptive benchmark. A/C/D choose the first price-range-eligible observation; FT is used only for settlement, never eligibility. A/B raw aggregate ROIs compare different populations; paired deltas must be used to assess timing.
