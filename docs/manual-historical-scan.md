# Manual Historical Scan — Thai time

GitHub Actions → **Manual Historical Scan (Thai Time)** → **Run workflow**.
No scheduler. Manual Current-Day Odds Observation and Auto Scan are unchanged.
Collection has read-only repository permissions and creates an artifact. A separate
write-enabled publication job validates that artifact, appends verified historical
rows and rebuilds statistics/Dashboard when `publish_to_dashboard` is selected.

## Inputs and calendar semantics

- `start_day`, `end_day`: inclusive **football-day labels**, `YYYY-MM-DD`, 1–7 days.
- `times_thai`: 1–8 distinct `HH:MM` values, separated by commas.
- Timezone is always `Asia/Bangkok`, never the browser/runner timezone.
- **00:00 through 05:59:59 belongs to the previous football day. 06:00 starts a new day.**
- Choosing day September 14 and time `01:45` means **September 15 01:45 +07:00**,
  equivalent to **September 14 18:45 UTC**. `05:59` rolls forward too; `06:00` does not.
- Default day September 14 targets: September 14 15:00/18:00/21:00 and September 15 00:00 BKK.
- Fixture membership is based on the timezone-converted **kickoff**, not UTC date,
  collection date, or an unverified legacy day label. Differences from original
  `football_day` values are recorded, never rewritten in the source data.
- Targets must be past and strictly before each fixture's kickoff. The manual
  workflow can recover a past target even when the match has not kicked off yet.
  A target at/after kickoff is `NOT_PREMATCH_SLOT`, never an in-play price.

## API semantics

The historical endpoint does **not** take a target date/time. Requests are exactly
`/v4/historical-odds?fixtureId=<verified ID>&bookmakers=<slug>`.
The requested Thai instants are converted to UTC for local reconstruction against
timezone-aware provider `createdAt` values. They are not sent as fabricated API
parameters. One fixture/book request supplies any number of target times.

Only exact native OddsPapi observation IDs from pinned checkout source rows are
eligible. Manifest records path, line number, line SHA256, identity, kickoff and
original observations. No fuzzy matching, fixture discovery or catalog API calls.
Coverage is **known native fixtures**, not every fixture that existed that day.

## Modes and safety

- **plan** (default): manifest, cache coverage and request estimate. Zero provider HTTP.
- **cache-only**: replay available verified cache; misses are explicitly
  `CACHE_MISS_NO_REQUEST`, not claims that the provider has no history. Zero provider HTTP.
- **recover**: explicitly confirm live requests. Process **all verified candidates**
  in the selected range, fetching every cache miss with no internal request-count
  cap (no 25-default or 50-maximum). Provider pacing, entitlement and health
  window stop conditions still apply. The workflow retains its 30-minute timeout;
  an interruption is not a claim that the entire date range completed. Saved
  cache and per-candidate progress allow a later manual rerun to avoid refetching.
  This change does not add automatic continuation or discover unmapped fixtures.

Historical cache is hash checked and reused when it covers the requested targets.
For growing history, `fetched_at` must be at or after every requested prematch
target. A later target requires a fresh response only if no receipt covers it;
the old receipt and raw bytes remain intact, and a new immutable revision is added.
A pre-kickoff 404 is not permanent for later target times. Legacy research runners
without `--allow-growing-history` retain their old post-kickoff-only policy.

The first non-plan run bootstraps the
reviewed September 15–17 artifact from run `38867737713` (90-day retention), then
subsequent runs use main-branch Actions cache. An unavailable seed fails closed;
it must not silently refetch previously recovered history. Actions cache can be
evicted, so artifacts retain **newly fetched** raw bytes/receipts for 90 days as recovery evidence,
not permanent storage. Restore sources require review when their retention ends.
Cache-only replays do not duplicate the 1GB seed in every artifact/cache version.
The baseline seed remains in its original reviewed artifact; no permanent/free
storage guarantee is made. Monitor GitHub storage before large repeated recovery.

New historical requests use only `HISTORICAL_ODDSPAPI_KEY` in environment
`historical-research`. The `ODDSPAPI_KEY` probe remains account-only, and the
existing distinct-subscription check against that reference account remains.
Current Manual/Auto now reference repository `HISTORICAL_ODDSPAPI_KEY`; environment
secrets can override the same name, so the old probe does **not** prove separation
from the actual current scanner. Reports explicitly label that limitation.
This repair does not change either key, add account failover, or impose a new
credential requirement. The historical transport allows only `/account` and
`/historical-odds`, both unmetered per provider documentation. Before/after account
checks remain; any usage change stops further history calls without claiming
the change came from historical requests. No secret value is printed or persisted.
This manual workflow has **no production clock
blackout**: the pilot's target-minus-15 / target-plus-150-minute rule unnecessarily
blocked independent manual research (e.g. run `38894926278` at 18:37 BKK).

Existing account/quota and 5.2-second pacing gates remain. Fresh production health
is retained as an honest baseline, including an existing FAIL, only after distinct
active subscriptions are proven. Existing FAIL is never relabeled PASS. Stale or
invalid health, worsening severity, or new production issues stop further history
requests. Default safety.health_check without account isolation retains strict
pilot behavior. Shared/missing/expired accounts still fail closed.

Production account usage can legitimately rise due to concurrent live collectors.
Report the actual delta without attributing it to historical requests; subscription
identity/entitlement changes or counter decreases still fail. Production key is
never routed to the historical endpoint. The workflow verifies tracked production
data/reports/config inputs unchanged after every run; repository write permission
is still absent. No automatic retries after 429 or transport/provider errors.

Actual HTTP accounting is separate from quota usage. For H new historical calls
in one successful runner: H historical + (2H+3) account = **3H+3 HTTP**. Cached-only
replay, `cache-only` and `plan` perform zero provider calls. The documented historical/account endpoints are not
monthly-quota-billable; this does not waive entitlement/rate limits. Attempts
are recorded before transport, including failures; tests inject fake transport
and never count as live provider evidence.

## Price quality and output

Reuses the pilot's reviewed full-time AH catalog, normalizer, latest-state
reconstructor, balanced-line selector and safety primitives. Ported from
`research/historical-backfill-isolated-20261015`; no wholesale branch merge.

- Each target must strictly precede kickoff.
- Latest known state at/before target wins; no rollback past an inactive tick.
- Preserve exact quarter line and both prices; no interpolated quotes/timestamps.
- `BALANCED_LINE`: both odds 1.80–2.20, both entry ages ≤3600 seconds, deterministic
  nearest-to-2.00 ranking. **Not verified Official Mainline.**
- Distinguish no AH history, no qualifying fresh line, cache miss, and non-prematch target.
- No invented OU/1X2, no settlement/profit claims, promotion disabled.

Run summary and artifact include `manifest.json`, `report.json`, `RESULT.md`,
all exact reconstructed AH lines, actual per-side history-entry timestamps,
original-price comparisons at actual observation times, status/coverage counts,
request receipts, raw cache and run URL. A history-entry creation timestamp is
not guaranteed bookmaker-change time or a live observation at the target.

## 18 October repair and usage

Run `39028824886` selected 17 October 18:00 at 18:28 Bangkok. Its first failure was
`FIXTURE_HAS_NOT_KICKED_OFF`, with zero historical and account requests. One
upcoming fixture caused the previous runner to reject the entire football day.
The manual workflow now opts into target-covered growing cache instead; its old
offline research callers keep their original default.

To collect: choose `start_day`/`end_day`, `times_thai`, bookmaker, **recover**, and
tick `confirm_live_requests`; keep `publish_to_dashboard` enabled to publish.
Default **plan** only previews the request manifest and will not collect prices.
Plan no longer depends on the old seed artifact/cache being downloadable.

Each selected target must already be past. For example football day 17 October
and `18:00` means 17 October 18:00; `00:00` means 18 October 00:00. A run before
that midnight must not request it yet. Input failures now expose fixed actionable
codes such as `TARGETS_MUST_BE_IN_THE_PAST`, without provider exception text.

The manual runner stops further requests after a 20-minute runtime budget,
leaving time inside the 30-minute job for cache/artifact saving. A stopped run
remains STOPPED, is not published as complete, and can be rerun manually with the
same inputs to reuse completed requests. This is a time budget, not a fixture
count cap or an automatic retry; other research runners have no new default limit.

The publication job preserves exact identities even for excluded/non-prematch
slots, so one excluded slot cannot break import of other verified rows. If main
advances while publishing, it rebuilds offline from the **same artifact** on fresh
main, up to three push attempts. It never copies stale raw files over new live
observations and never reruns the historical collector during a publish retry.

Provider references checked 18 October 2026:
- https://oddspapi.io/us/docs/get-historical-odds — upcoming/live history grows;
  only finished/cancelled responses have deterministic ETags; 5-second cooldown.
- https://oddspapi.io/us/docs/requests-and-quota — historical calls are free,
  account calls unmetered; exhausted subscriptions can still be rejected for history.

Remaining limits: known verified fixture IDs only; full-time AH balanced-line
reconstruction only (not Current Odds, Official Mainline, OU or 1X2 recovery).
Missing/unqualified source history stays explicit. Cache/seed artifact retention,
account separation/entitlements, rate limits and the 30-minute workflow timeout
remain genuine external constraints. A passing mock/CI run does not prove a live
historical scan or actual current/historical account separation.

## Verification

`python -m pytest -q tests/test_manual_historical.py` is network-free.
Acceptance run: September 15–17, both books, `cache-only`; compare to the reviewed
52-fixture/58-pair experiment without issuing new provider requests.

Verified locally October 16, 2026 against the real pinned artifact: 183 hash-verified
cache receipts imported; requested cohort 52 fixtures / 58 bookmaker pairs / 232
targets, all 58 cache hits. Exactly 169 BALANCED_LINE, 47 MAINLINE_UNRESOLVED,
16 NOT_PREMATCH_SLOT, 24 bookmaker pairs complete at all four targets. Zero
historical/account/provider requests. Native snapshot file hashes before/after:
`fd3666d56f6e504dd15c0fe1d3e8e14660aed108d032680e0a2eca9b0ea7604a`
and `199722610cc357d42e47ab53980f88ac1d226c8e8a77ba9fcf8d957129fde372`.
39 new tests and 914 full offline tests passed at the initial implementation;
exact final-head CI remains the deployment gate.
