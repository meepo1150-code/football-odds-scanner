# Football Odds Scanner evidence correction — 2026-10-11

Baseline main: db596bc5de668004ac31c7c827dde66426b6d316. The September handoff is historical, not the current task list. PR309 is already merged. No raw archive, FT evidence, production registry or frozen promotion gate is changed.

## Corrected evidence

672 settled provider-local/verified-bridge identity groups: 505 SINGLE_OBSERVATION; 167 have comparable prematch observations. With same-source contract validation, 42 unchanged AH/price, 125 line/price/favorite changes. These are not 672 globally deduplicated canonical matches: unlinked cross-provider IDs remain explicitly unresolved. Cross-feed price differences do not become movement.

The original 547 'flat' outcomes included 505 observations with no comparison. Distinct times, same source fixture, bookmaker, source semantics, market and period, and strict observed-at < kickoff are required. Source-switch and favorite-switch flags remain separate; uncomparable numeric deltas are null.

Viewed-data walk-forward evaluation trains on earlier Football Days only. 167 comparable groups yield only 15 eligible test forecasts given baseline cell minimums. Baseline MSE minus movement MSE = -0.03055 (bootstrap 95% -0.07480 to +0.00694). No validated incremental benefit or betting edge. Subgroup Asian ROI is descriptive only; one incremental comparison is reported, no multiple-search promotion. This is not an untouched holdout. Quarter-line returns and pushes use actual Asian settlement; WR vs 50% candidate labels are removed.

## Collection timing and requests

11 October: 7 recorded targets, 2 ON_TIME, 5 LATE; on-time coverage 28.6%, DEGRADED_TIMING. The 20:00/21:00 requests at 22:03/22:04 are actual late observations, never historical target prices. Existing raw evidence remains intact.

Future collection attempts only the latest elapsed target, records superseded targets MISSED, and enforces at least 15 minutes between attempts including dispatch. GitHub cron remains best-effort. Existing canonical weekday 18:00/21:00; weekend 12:00/15:00/18:00/19:00/20:00/21:00/22:00 Bangkok retained; no frequency increase.

Chosen method: primary plus same-source follow-up. OddsPapi rotates a stable daily cohort instead of different competitions each round. Billable caps unchanged: at most 2 requests/run, 6/UTC day, 180/research UTC month, also checked against live unmetered account remaining and reserve. Account quota is shared across other workflows; 180 is not a universal account budget. Last account receipt was 114 remaining, requiring a fresh health receipt. A single daily scan improves breadth at lower cost but cannot measure same-day movement. Kickoff-relative scans improve comparable horizons but require more scheduling/batches and are not enabled without measured budget.

PropLine reports actual HTTP attempts separately from OddsPapi billable counts; per-request timeout20 seconds, total transport budget240 seconds, automatic retry cap zero; stop immediately on catalog/sport 429/401/403; persisted cooldown honors numeric or date Retry-After. Prices are timestamped after response collection, not before a potentially slow fetch. Workflow success never implies source healthy. API-Football account suspension remains an external blocker. PinnWire report freshness is shown separately from its last HTTP429.

## FT and scope

Baseline unresolved: active overdue54, future/recent56, retired249. Age counts legitimately change with clock time. Latest offline triage groups by provider/country/canonical competition with UNRESOLVED identity where an exact mapping is absent. The54 old active overdue cases do not match reviewed exclusions: no bulk deletion or retirement was performed. Germany3.Liga is outside the81-division master, not user-cancelled; retain active recovery. Existing exact-ID, verified identity, full-time, conflict quarantine and cache freshness gates stay active. Cache reuse never fabricates a new recovery attempt.

242 trusted observations excluded from current statistical scope, no raw deletion. Poland1.Liga accounts for four current-day observations: frontend now consumes a backend-generated policy receipt, reconciling70/127 to66/123. Archive filter preserves access to retired/out-of-scope observations. Missing policy/quarantine receipts fail closed. Unresolved cross-provider identities remain provider-local groups, not confirmed unique real matches.

Daily sync workflow deliberately performs local-only coverage without billable discovery. The report now says LOCAL_ONLY_NOT_REQUESTED, not API_KEY_NOT_CONFIGURED; no secret is requested or exposed. Other workflows with a configured account can still use the guarded adapter.

## Delivery verification

Regression coverage: singleton/duplicate/inplay observations, same contract and source switches, latest-slot-only recovery,15-minute spacing,429 catalog stop, daily stable budget and caps, full Asian settlement, frontend scope agreement on actual offline raw data. Full suite and exact PR-head CI must pass before merge. New offline audit workflow rebuilds all derived evidence without raw edits or provider calls; Pages also rebuilds before deploy so reports are from one checkout. Historical archive audit now measures current archive and stamps its audit time rather than retaining47-row evidence.

Post-deploy browser acceptance: Timeline, historical line-only/price buckets, WR and N, Asian settlement five-way counts/ROI, OU2.5 frequency vs separate priced N, archive/core/FT/future filters, canonical/source counts and health freshness. Remaining external FT/source blocks must stay visible. NO_VALIDATED_PATTERNS remains the production status. Deployment completion and browser evidence are recorded separately from workflow success.
