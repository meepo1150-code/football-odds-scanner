# System audit and maintenance — 17 October 2026

Baseline: `5c0ad86` (latest main fetched at start). Bangkok time.
Overall: **FAIL for automatic collection acceptance; WARNING for remaining data operations.**
A passing CI or Pages deployment is not a successful odds observation.

## Scorecard and evidence

| System | Observed health | Evidence / limitation |
|---|---|---|
| Four-round Auto | FAIL | All five retained Auto receipts are DELAYED, 0 paid requests; no validated Oct16 manifest. Oct16/1800 has no receipt. |
| Midnight ownership | Verified | Oct16/0000 targets Oct17 00:00 Bangkok and retains Oct16 fixture set. No policy change. |
| Manual | Regression PASS | Workflow and collector/shared quota/provider hashes locked by tests; unchanged. No manual live scan requested for this audit. |
| Fixture preparation | Pending live acceptance | Immutable manifest, follow-up exact-ID filtering, no manual supplement relabeling. First valid scheduled preparation still required. |
| Primary quota | Stale | Last stored observation Oct16 04:40Z: 191/250 used, 59 remaining then. Not current available quota. Reserve 10 unchanged. |
| Secondary account | Disabled pending evidence | GitHub Settings verified HISTORICAL_ODDSPAPI_KEY at repository and historical-research environment scope. Account-only audit added; no current odds request or history substitution. |
| Recovery/SLA | FAIL externally | Latest run 38958228242 created 19:53:27Z for 17:00Z target. Collector at 19:53:44Z correctly refused late prices. Retry wakeups depend on the same delayed GitHub scheduler. |
| AH/OU/timestamps | Offline PASS | Same extractors as Manual; recovered cached batches retain original timestamps. Last-observation reporting corrected to max actual batch observation. |
| Raw persistence | Offline PASS, hardening applied | Exact-record append union and immutable manifest conflict gate; now validates all incoming files before any append. Raw history untouched. |
| Master/mapping | Structural PASS | 50 associations / 81 divisions / 1,203 active clubs / 92 mapped competitions; validator reports no unmapped active clubs. This does not prove every provider market is available today. |
| FT/settlement/stats | WARNING | Latest exact-ID backfill run 38988807722 succeeded with 0 eligible candidates/0 requests; stored missing-FT ledger has 4 rows (postponed, 2 identity conflicts, 1 missing FT). Never infer scores. |
| Dashboard/Monitor | Deployment PASS, collection not PASS | Pages 38982254517 successful. Monitor reports FT_DELAY, FT_IDENTITY_CONFLICT, UNMATCHED_IDENTITY_CANDIDATES, LATEST_SCAN_WARNING. |
| CI/security/concurrency | Repairs tested | Offline regression + master gates; secret URL exception text removed from Auto; shared Manual/Auto concurrency preserved. |
| ChatGPT alerts | Configuration restored | Existing alerts were disabled; re-enabled 17 Oct. Checks at 00:30/15:30/18:30/21:30 Bangkok. Delivery still requires future observation. Supported GitHub webhook is PR-only, not Actions completion. |

## Bugs and fixes

- **P0 potential data loss:** overnight result workflow restored stale result cache after resetting to fresh main, unlike the free-result workflow. Use existing conflict-aware `result_artifact_merge` and rebuild derived outputs. Tests cover concurrent additions and conflicting score quarantine. This is a proven code risk, not a claim that historical loss has been measured.
- **P1 quota false rejection:** complete cached schedule was narrowed only after reserving all master tournaments. Narrow before preflight when complete retained evidence exists; test proves a 92-tournament registry/one fixture needs one request and preserves reserve 10. No cap bypass. Without a complete cache, conservative whole-universe grant remains.
- **P1 exception disclosure risk:** Auto serialized provider exception text that could contain a credential URL. Persist exception class only. No actual secret leak is alleged.
- **P1 timestamp reporting:** last loop batch may be older than a previously fetched batch during cache reconciliation. Report maximum actual response observation, preserving every original per-quote timestamp.
- **P1 partial publication risk:** validate every incoming JSONL/report before appending any evidence; malformed tail cannot leave an incomplete merge.
- **P2 test isolation:** three PinnWire tests redirected only report/snapshot paths but wrote health history in the checkout. Run those tests in temporary working directories. Production provider behavior unchanged.

## Secondary failover design / gate

Account audit calls only `/account` once per available key. Raw account JSON and credentials are never persisted. Explicit active subscription IDs are compared via hashes; equal hashes mean a shared ledger, different hashes mean distinct subscription identifiers only. Neither proves independent entitlement or current endpoint access.

Fallback remains **DISABLED** until current endpoint entitlement and independent metering are verified. Enabling it later requires: ledger keyed by verified subscription identity (same subscription shares budget); atomic reservation under shared collector concurrency; same-slot request receipt/cache lookup; unknown outcomes block replay; primary auth/rate-limit/quota failures never automatically consume secondary quota; only current endpoint active prematch responses qualify. Historical endpoint output must retain historical provenance and cannot fill current observations.

No fallback route is wired into Manual or Auto by this maintenance patch. Benefit: protects quota and observation integrity. Trade-off: no secondary coverage until evidence is sufficient.

## Remaining risks and backlog

1. P1: GitHub cron/queue delay exceeds 30 minutes. No repository change can guarantee an external scheduler SLA. Independent dispatch service would require an actual configured service and credentials; none invented or purchased.
2. P1: first real validated Auto 15:00 preparation and 18/21/00 observations remain acceptance gates. A dry run cannot meet them.
3. P1: broad baseline ~9 requests/round ×4 would be ~36/day, incompatible with 250/month. Preserve guards and report incomplete coverage; do not promise whole-month breadth.
4. P1: no verified Actions-completion ChatGPT push; scheduled alerts enabled, future delivery unverified.
5. P1: missing/conflicting FT remain quarantined pending exact-ID evidence. Do not fuzzy-match or force settlements.
6. P2: separate staged global-expansion leagues are not certified by active production master totals; no expansion or research promotion in this change.
7. P2: unknown durable grant outcomes deliberately prevent retry; this trades coverage for avoiding duplicate paid requests.

Frozen research validation, Manual modules, historical raw data, schedule targets and provider secret values are unchanged. No billable odds API call is authorized by this audit workflow.
