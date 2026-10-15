# Environment-bound manual pilot evidence — 15 October 2026

Run: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38759484682
Commit: b835f466c6e14daca602a9cb1fa257633e617fdc
Actual research preflight: 2026-10-15 22:21:09.551973 Asia/Bangkok.

## Measured facts

- GitHub environment `historical-research` contains `HISTORICAL_ODDSPAPI_KEY`.
- Research account connection succeeded; active soccer/Pinnacle entitlement verified.
- Research request count 0 / 250; production before-count 186 / 250.
- Active subscription fingerprints differ. This is direct subscription-isolation evidence;
  it is not a provider guarantee about every infrastructure-level rate limit.
- Reviewed cached provider catalog: 49 explicit fulltime soccer Asian Handicap markets,
  signed home handicap -6 through +6 in quarter steps, with explicit outcomes 1 and 2.
- Three actual account requests attempted: production-before 200, research 200,
  production-after 429. Historical requests 0; market-catalog requests 0; billable requests 0.
- The live historical endpoint has NOT been tested; endpoint authorization remains pending.
- Coverage NOT MEASURED (0 of 10 attempted), AH prices unavailable, recovered snapshots 0.
- Safety gate stopped at PRODUCTION_HEALTH_STALE before any historical request.
  Monitor timestamp 15:05:50.556076 UTC was older than the unchanged 900-second gate.
  The runner also retains its production quiet-window restriction; this gate was not reached.
- Production after-count is NOT VERIFIED because the follow-up account response was 429.
- Offline safety tests in actual Actions run: 75 passed.

## Corrections after the run

The new Actions account-probe wrapper omitted the endpoint's 1000ms cooldown across
steps. Added a 1.2-second pre-request wait and a no-retry-on-429 regression test.
The failed run was not rerun and no historical requests were retried.
Empty cache saves are now skipped; no historical body existed to cache in this run.

## Workflow scope and next valid run

The original run used a research-branch override of `research.yml`. That file and
`global-expansion-readiness.yml` have since been restored byte-for-byte to their
original definitions. Current manual entrypoint: `historical-research-pilot.yml`.
For dispatch before registering the new path on main, the research branch also
has an exact-branch manual sibling job in `global-expansion-matchday-probe.yml`.
Its original main-only probe job is unchanged and skips research-branch dispatches.
The historical sibling uses read-only contents permission, its own concurrency,
`historical-research`, and the dedicated secret. Main has not been modified.
No new scheduled trigger, merge, deploy or production collector change is included.
Research history has no production-key fallback. Separate production account-only
steps verify subscription identity and request count; no raw account is persisted.

A later manual pilot requires fresh real Production Health, an open quiet window,
and fresh account checks. Do not loosen the gate, relabel timestamps, claim historical
coverage from preparation, or initiate expansion to the other 90 fixtures.
