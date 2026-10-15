# API cost and safety evidence — checked 2026-10-15

Overall: **BLOCKED_LIVE_PILOT**. Actual provider requests in this task: **0**.

| Question | Status | Evidence / limit |
|---|---|---|
| Historical depth | VERIFIED | Official endpoint notes say January 2026 onward; fixture completeness is not guaranteed. Example response dates in 2025 do not establish earlier coverage. |
| AH, both sides | VERIFIED capability; pilot UNVERIFIED | Existing pinned archive audit reports 322 fixtures with AH; actual pilot fixtures have not been queried. Exact full-match scope and signed line require catalog evidence. |
| Tick timestamps | VERIFIED field; semantics UNVERIFIED | `createdAt` denotes history entry creation, not documented exact bookmaker action time or continuous availability. |
| Fixture batching | VERIFIED single-ID contract | Singular required `fixtureId`; up to three bookmaker slugs. No fixture-array parameter is documented. |
| Monthly debit | VERIFIED documentation | Current quota page excludes historical calls from the counter. Older provider blog pages describe billable history; current endpoint-specific quota docs take precedence. No live before/after measurement yet. |
| Cooldown / 429 | VERIFIED / partly UNVERIFIED | Historical cooldown 5,000 ms, including 304. General subscription exhaustion returns 429. Shared-key scope, detailed cooldown error shape and Retry-After guarantees are not documented here. |
| Exhausted account | VERIFIED | Historical also becomes blocked; account remains accessible. |
| Plan / account | VERIFIED cached only | 11:19:11 UTC account report: active, 184/250 used, 66 remaining; soccer and bet365 allowed. This is not current live preflight, and candidate bookmaker entitlement must be checked separately. |
| Tick cadence / active | UNVERIFIED | No guarantee of every change or sampling interval; `active` is described as currently active. A change-log/as-of interpretation must be established before old-slot reconstruction is accepted. Do not request only active entries and lose suspension events. |
| Internal analysis/storage | INFERENCE, no standalone redistribution | Terms prohibit standalone resale/repackaging/redistribution; provider promotes model/backtest use. No explicit retention duration grant identified. Keep raw private and resolve any ambiguous intended usage before expansion. |

Sources (official):

- https://oddspapi.io/en/docs/get-historical-odds
- https://oddspapi.io/us/docs/requests-and-quota
- https://oddspapi.io/us/legal/terms
- https://oddspapi.io/blog/what-is-oddspapi/

Pinned repository evidence:

- `reports/oddspapi_quota_health.json` at baseline SHA in baseline.json.
- `reports/oddspapi_history_audit.json`: 738 unique archived fixtures; 322 AH;
  tick interval reported Jan 13–Jun 1, 2026. Pilot candidates are Sep–Oct;
  this audit is not candidate-level cache proof or a new successful pilot.
- Historical normalization in `src/odds_scanner/oddspapi_history_archive.py`
  preserves active flags. Existing cache does not prove v4 historical state semantics.

## Concrete request envelope, withheld

The candidate manifest contains ten exact `GET /v4/historical-odds` request parameter
objects, one fixture and its observed bookmaker each. No fixtures/markets calls are
planned. Maximum ten historical attempts total, no retries for this pilot. Cache must
be checked by exact fixture + bookmaker + filters first; 304 requires a retained body.
Use at least 5.2 seconds between calls, stop immediately on any 429 or quota/health
anomaly. A future runner must count attempts including errors, keep exact raw bytes
and metadata without key-bearing URLs, and reserve a quiet window outside production
scan/recovery activity. It must not read or write the production quota ledger.

Before any live call: establish historical active/time semantics, verify the exact
candidate bookmaker/market catalog and account state through an isolated authorized
execution environment, and verify there is no overlap with a production request.
No local credential or isolated manual secret-bound runner is available in this task.
The production key was neither read nor used. Creating a secret-bound workflow was
not necessary for offline completion and has not been done.

No approval can substitute for missing provider semantics. After evidence resolves
the gate, execute only the reviewed 10-request envelope; do not expand automatically.
