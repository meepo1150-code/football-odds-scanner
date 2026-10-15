# Historical backfill: isolated 10-fixture pilot preparation

Status: **BLOCKED_LIVE_PILOT — REVISE**. No successful live pilot is claimed.
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
Outputs are restricted to `research/historical_backfill/reports/`. No workflow,
network client, credential reader, provider request, production hook or integration exists.
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
- `statistics.py`: observed/backfilled/combined descriptive previews; observed precedence
  on identical fixture/slot/bookmaker/semantic market/line. Provider market IDs remain
  provenance, not an extra sample dimension. Conflicting duplicates raise an error.
- `pilot.py`: actual pinned evidence, manifest, zero-request blocked report. The gate
  flags on low-level adapter/comparison functions are caller assertions for offline
  testing only; they do not establish provider permission or authorize network calls.

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

See `reports/API_COST_SAFETY.md` and `reports/candidate_manifest.json`. No runnable
network command is included. The endpoint's documented zero monthly debit does not
remove account exhaustion, cooldown, active-state semantics or credential isolation risks.
Only a subsequent gated, manually scoped execution may consume these requests.
Never add the pilot to production scheduler, collector, quota or recovery logic.
Do not merge/deploy production integration in this task.
