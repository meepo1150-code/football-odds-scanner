# Multi-Day Historical Recovery Pilot — BLOCKED, not a successful live test

Baseline main: `825dccf9d4b27949049ab429febb06d915bb1400`.
Original research head: `540ca7e08079421fb93deeb89f4fdbe74df1b1e8`.
Branch: `research/historical-backfill-isolated-20261015`; PR #382 remains draft.
Manifest as-of: 2026-10-15 19:54:43 Asia/Bangkok. No production integration/merge/deploy.

## Actual result versus preparation

| Measure | Result |
|---|---:|
| Prepared unique fixtures | 100 |
| Original calibration identities retained | 10 |
| Expansion candidates, gated behind calibration | 90 |
| Competitions | 29 |
| Bookmakers | Pinnacle 72; bet365 28 |
| Distinct football days present | 10 |
| Fixtures inside the preceding 30-day window | 99 |
| Original calibration retained outside window | 1, age 31 days |
| Missing target fixture-slots prepared | 235 |
| Of those: current-schedule recovery / legacy counterfactual research | 23 / 212 |
| FT available / missing / conflicting | 98 / 2 / 0 |
| Actual historical requests | **0** |
| Actual account requests | **0** |
| Real historical AH coverage | **NOT TESTED** |
| Real backfilled snapshots / fixtures | **0 / 0** |
| Quota before/after; empirical error rate | **Not measured / N/A**, not zero error rate |

`multiday_manifest.json` contains exact fixture IDs, leagues, teams, kickoff,
existing/missing slots, original observations, FT status, mapping confidence,
bookmaker, request parameters, age and Bangkok kickoff hour. Mapping requires the
same exact fixture ID, teams, kickoff and tournament in the retained fixture cache;
competition mappings must be verified and approved, with exclusions enforced.
The secondary bet365 archive lacks football_day; the day is attached only when
the exact fixture ID + kickoff resolves to one unique day in the daily fixture cache.
No team-name fuzzy match, guessed fixture ID or fabricated day is used.

The original calibration file is unchanged. One of its fixtures is older than the
new 30-day bound and is explicitly labelled rather than silently discarded.
There are no candidates on every calendar date: source snapshots have a large
gap. This is not a claim of 14–30 distinct match days or API failure during that gap.

## Age coverage: planned, not measured

| Age, calendar days before as-of in Bangkok | Prepared fixtures | Tested | Historical coverage |
|---|---:|---:|---|
| 1–7 | 31 | 0 | NOT TESTED |
| 8–14 | 0 | 0 | NO CANDIDATES |
| 15–30 | 68 | 0 | NOT TESTED |
| Outside 30, original calibration only | 1 | 0 | NOT TESTED |

Cumulative 7/14/30-day counts are 31/31/99, respectively. Disjoint age bins must not
be summed as if these cumulative windows were separate samples. Coverage output
also provides league, bookmaker and scan-slot strata. Untested coverage is JSON null,
never 0%. Kickoffs span ten Bangkok clock hours (00, 01, 02, 17–23).

## What was unblocked

The provider's worked historical example treats each entry as a timestamped captured
state and filters its active flag for historical pre-match analysis. It explicitly
describes repeated snapshots without a price change, including suspended states.
This supports **PROVIDER_REPORTED_SNAPSHOT** interpretation; it does not establish
continuous availability between records or exact bookmaker price-change time.
The runner retains latest states, including inactive states, instead of filtering
them out and resurrecting an earlier price. The prior blanket semantics blocker is
narrowed accordingly; live comparison must still validate this contract on our fixtures.

Official evidence:

- https://oddspapi.io/blog/bet365-historical-odds-guide-the-data-apis-and-strategy/
- https://oddspapi.io/en/docs/get-historical-odds
- https://oddspapi.io/us/docs/requests-and-quota
- https://oddspapi.io/en/docs/get-account

VERIFIED documentation: single fixtureId, max three bookmaker slugs, 5,000 ms
historical cooldown, account entitlement fields, no monthly historical debit.
CONTRADICTED assumption: historical remains accessible after quota exhaustion;
quota docs say it is blocked too. The blog's 4.6-second pacing is weaker than current
endpoint documentation; the runner uses at least 5.2 seconds for historical calls.
UNVERIFIED: this account's current entitlement, a complete every-change history,
and exact mainline identity at an unobserved historical slot. None is inferred.

## Isolated execution and calibration gate

`isolated_runner.py` is a manual CLI, not a workflow or production import. It reads
only `HISTORICAL_ODDSPAPI_KEY`, with no fallback to ODDSPAPI_KEY. A reviewed gate
must identify a verified dedicated subscription and credential-isolation evidence,
the exact manifest digest, semantics mode/evidence, and a reviewed market catalog
digest. Merely renaming the production key is insufficient.

Only `/account` and `/historical-odds` are callable. Requests contain exactly the
manifest fixtureId and bookmaker; no fixtures/markets calls or active-only filter.
Account bodies are never persisted (they contain api_key); only safe entitlement,
counter and subscription-fingerprint summaries are retained. HTTP redirects are
disabled, exception URLs are not logged, responses are size bounded, no retry occurs.

Cache is checked by exact request, immutable raw hash and LIVE_HTTP_200 receipt.
Original bytes are saved before quota/quality review so anomalies do not erase
evidence. Cache indexes and raw files reject symlink/path escape and corruption.
Raw/cache/run output remains ignored under `research/historical_backfill/data/`.

Before each uncached fixture: fresh account/entitlement/counter check. After its
response: account check again; changed count, limit or subscription stops execution.
Any 429 stops immediately without retry. 403/auth errors, schema/identity conflicts,
invalid timestamps/prices and production health degradation also stop. A 404 records
no history without inventing data. Account requests are counted separately from
historical attempts and paced at least 1.1 seconds; all requests count in the audit.

Only the first ten fixtures run initially. Expansion requires all ten evaluated,
at least eight with AH, at least five with a same-bookmaker/line comparison, at least
five with a complete missing slot, and zero invalid reconstructed rows. These
conservative thresholds are fixed before real fetches; they are research quality
gates, not proof of a betting edge. `--expand` permits the remaining prepared fixtures
only after this gate. Maximum 100 unique fixtures, one historical attempt per uncached
fixture, with health checks after every ten and before each request.

Production protection blocks requests from 15 minutes before each 00/15/18/21 target
through the full 150-minute recovery window. A health report must be <=15 minutes old;
new issues or worse status stop execution. If a quiet window closes, stop and preserve
cache; a later manual run can reuse completed evidence. No scheduler is added.

## Remaining blockers and actual execution evidence

The actual CLI invocation stopped before any network attempt with
`ISOLATED_CREDENTIAL_NOT_CONFIGURED`. Environment presence checks found neither the
isolated Historical credential nor an accessible production key. No secret was
extracted from GitHub or requested in chat, and no secret-bound workflow was created.

The pinned full-match AH market catalog still needs review before execution. The
9 MB cached catalog could not be retrieved through the connector (Transport closed).
No replacement `/markets` call was made. The empty catalog and pending gate shipped
with this branch deliberately prevent live execution even after a credential appears.
The cached account report (184/250 at 18:19 Bangkok) is not a current preflight.

Last retained production scan: 18:20:12 Bangkok for the 18:00 slot, status WARNING,
43 fixtures found, 38 with valid odds. Retained monitor: 19:39:41 Bangkok, WARNING
with FT_DELAY, FT_IDENTITY_CONFLICT, UNMATCHED_IDENTITY_CANDIDATES and LATEST_SCAN_WARNING.
That initial monitor became stale for live authorization. A later read returned a
fresh monitor at 20:05:14 Bangkok with the same WARNING state and issue set, recorded
in `multiday_production_safety.json`; no new degradation was reported there.
Since no provider call occurred, there is
no measured before/after quota change or live workload effect. Do not claim a fresh
production-health pass or historical success from this cached evidence.

## Offline statistics

Observed-only: **86 target snapshot rows across 53 unique fixtures** in the selected
sample. Unslotted/extra legacy-hour observations remain separate. A fixture's two
sides and repeated lines/rounds are correlated, not independent match outcomes.

| Price band | Settled side observations | Unique fixtures | Half-stake WR, pushes excluded |
|---|---:|---:|---:|
| [1.80,1.90) | 52 | 34 | 46.32% |
| [1.90,2.00) | 51 | 27 | 40.70% |
| [2.00,2.10) | 48 | 31 | 60.44% |
| [2.10,2.20] | 12 | 8 | 63.64% |

These are descriptive, missingness-selected samples, not validation of an edge.
The existing production Asian settlement module is imported unchanged; half wins,
half losses and pushes remain distinct. Backfilled-only has no rows. Combined Offline
is currently identical to Observed-only. Added snapshot rows and added fixtures: zero.
No new independent database fixture can be created by this pilot because every candidate
already exists. Once tested, report separately any increase in fixtures with usable
target-slot/statistical observations; do not call that discovery of a new match.

For any eventual comparison, use exact lines present in the original observed dataset
as a labelled conditioned subset. Historical ladder lines are not retrospectively
declared mainlines. Quote differences are diagnostics, not automatic errors; the
runner compares at actual observation time as well as reconstructing missing target
slots. Maximum quote age is provisionally one hour per side; no interpolation or
post-kickoff tick can fill a slot. Full provenance and exact lines remain intact.

## QA, reproducibility and decision

71 local tests pass, including synthetic 100-fixture selection, calibration identity
preservation, simulated 10-to-20 staged execution, cache reuse/corruption, HTTP429,
quota anomaly, entitlement failure, quiet windows, stale/degraded health, exact mapping,
timestamp/active states, dedup, settlement, bands and no-live-coverage labelling.
Synthetic transport tests are explicitly TEST_INJECTED_CLIENT, never live evidence.
The real blocked CLI and actual pinned-data manifest/report generation completed.
Inputs are checked against the current baseline Git blob identities and SHA256 values.
Full repository CI results are linked in the updated PR; do not substitute older CI.

To reproduce the offline preparation from the pinned baseline inputs:

```sh
PYTHONPATH=src:. python -m research.historical_backfill.multiday --fixtures data/normalized/research_v2_daily_fixtures.jsonl --as-of 2026-10-15T12:54:43Z
PYTHONPATH=src:. python -m research.historical_backfill.multiday_report
PYTHONPATH=src:. python -m unittest discover -s research/historical_backfill -p 'test_*.py'
```

Decision: **REVISE — do not expand to all historical data.** Benefit: the prepared
sample, isolated runner and measurement pipeline can test real recovery without
altering production. Trade-off: credential/catalog/health gates mean the requested
empirical proof is still absent. Risks: incomplete history, missing age strata,
conditioned line selection, stale quotes, account restrictions and correlated samples.
Next prerequisite is safe isolated execution plus reviewed pinned market metadata;
then complete the real ten-fixture calibration before any of the 90 expansion requests.
