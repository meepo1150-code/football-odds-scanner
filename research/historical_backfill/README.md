# Historical backfill: isolated staged multi-day pilot

Status: **10-FIXTURE LIVE PILOT COMPLETED**. 163 complete snapshots across 19/25 target fixture-slots; 90 additional candidates remain unexecuted.
Measured evidence: `reports/LIVE_PILOT_20261016.md` and `.json`.
Current evidence: `reports/MULTIDAY_REPORT.md`, `multiday_manifest.json`,
`multiday_result.json` and `multiday_baseline.json`. The original 10-fixture reports
and candidate_manifest.json remain frozen calibration evidence from the prior task.
The user's 2026-10-15 pilot instructions supersede this branch's earlier blanket
OddsPapi ban. Offline OddsPapi imports are permitted. Live access remains gated.

## Run offline

From repository root, with Python 3.11+ and no third-party dependencies:

```sh
PYTHONPATH=src:. python -m unittest discover -s research/historical_backfill -p 'test_*.py'
PYTHONPATH=src:. python -m research.historical_backfill.pilot
```

The builder verifies Git blob identities against `reports/baseline.json`; it refuses
inputs from another baseline. Obtain that commit's inputs for reproducibility.
Offline reports are restricted to `research/historical_backfill/reports/`.
The new manual `isolated_runner.py` has a bounded HTTP client, accepts only
`HISTORICAL_ODDSPAPI_KEY`, and never reads/falls back to the production credential.
An environment-bound manual workflow now exists on this research branch only; see `reports/ENVIRONMENT_PILOT_20261015.md`. No production scheduler hook or integration has been added.
The existing production Asian settlement module is imported read-only.

## Files and contracts

- `candidates.py`: exact OddsPapi fixture ID + teams + kickoff + tournament evidence;
  verified official domestic competition allowlist minus user exclusions. Cups are
  deliberately outside this initial selector. Unique fixtures across bookmaker groups.
- `normalizer.py`: offline v4 payloads; same bookmaker, reviewed full-match AH market
  catalog, exact home-signed quarter line, two explicit outcome IDs, player `0` only.
  Never guess an ID, line, side, mainline, or market scope from a number or name.
- `reconstruct.py`: last state at/before slot, strictly before kickoff; both sides
  independently timestamped. Unknown/inactive/invalid latest states block older ticks.
  Equal-time conflicting states fail closed. Default max age **3,600 seconds per side**
  is provisional, not empirically calibrated. No interpolation or closing substitution.
- `storage.py`: original response bytes can be preserved by `append_bytes`; canonical
  records by `append_raw`. SHA256-addressed exclusive creation, dedup, corruption and
  symlink checks. Raw data stays ignored under `data/raw/`; do not commit raw responses.
- `comparison.py`: snapshot metadata, missing-data/FT status and actual-observation-time
  comparison for the same bookmaker and exact AH line. Deltas alone are not errors.
- `offline_stats.py`: observed/backfilled/combined descriptive previews; observed precedence
  on identical fixture/slot/bookmaker/semantic market/line. Provider market IDs remain
  provenance, not an extra sample dimension. Conflicting duplicates raise an error.
- `pilot.py`: actual pinned evidence, manifest, zero-request blocked report. The gate
  flags on low-level adapter/comparison functions are caller assertions for offline
  testing only; they do not establish provider permission or authorize network calls.
- `multiday.py`: 10 original calibration identities plus up to 90 further exact-ID
  fixtures, pinned Git blob verification, 30-day filter, bookmaker/day/kickoff strata.
- `isolated_runner.py`: cache-first manual execution, dedicated-subscription evidence,
  fresh account/entitlement checks, per-response before/after quota comparison, immediate
  stop on 429/errors/anomalies, no retries, 10-fixture quality gate before expansion.
- `coverage_metrics.py`: fixture-slot coverage by 7/14/30-day windows, disjoint age bins,
  league/bookmaker/slot; conditioned same-line offline statistics without mainline claims.

All successful reconstructed records carry BACKFILLED provenance, two actual entry
creation timestamps, slot, source/bookmaker, line, teams, league, kickoff, quality,
FT and settlement-readiness. They must never claim an observation by the live scanner.
Observed source price-change times are unknown where absent, never replaced by fetch time.

## Slot interpretation and sample limits

Only 15:00/18:00/21:00 and **next calendar day's 00:00** for the football day are targets.
Slots at/after kickoff are excluded. Missing targets before the current schedule existed
are counterfactual research targets, not evidence of a failed production scan.
Only explicit `scheduled_target_at` within the production 150-minute recovery window
assigns an observed round; extra legacy hours and unslotted observations stay separate.

The pilot is selected for missingness and diversity, so its WR is selection-biased.
Multiple sides, lines and rounds of one fixture are correlated, not independent outcomes.
Backfill adds time observations; it cannot add independent FT matches when fixtures
already exist. Market-ladder backfill and observed mainline statistics are not comparable
without a preregistered common line-selection rule. No edge or promotion claim is allowed.

## Live gate and prepared requests

See `reports/MULTIDAY_REPORT.md` for current evidence and the original
`reports/API_COST_SAFETY.md` for the earlier audit. The endpoint's documented zero monthly debit does not
remove account exhaustion, cooldown, active-state semantics or credential isolation risks.
Only a gated, manually scoped execution may consume these requests. The checked-in pending gate remains fail-closed. The Actions wrapper supplies live
subscription evidence and the reviewed 49-market catalog only after checks pass.
Never add the pilot to production scheduler, collector, quota or recovery logic.
Do not merge/deploy production integration in this task.
