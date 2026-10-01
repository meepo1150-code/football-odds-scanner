# Alternative sources worklist — 1 October 2026 (Bangkok)

| Priority | Problem | Work performed | Status / remaining blocker | Automatic continuation |
|---|---|---|---|---|
| 1 | Current AH sources unavailable | Rechecked existing InferSports on actual responses; fixed live `id` shape and rejected past kickoff despite scheduled label; no execution promotion | HEALTH_ONLY: observed stale odds with empty markets. PinnWire cooldown and OddsPapi exhaustion skipped | Scheduled health checks and existing guarded collectors |
| 2 | Unresolved FT backlog | Added keyless ESPN full-time recovery, exact unique home/away/kickoff bridge, original-response cache, staging and conflict-safe merge | Local live run recovered 7 results, 0 ambiguous; runner evidence appended below | ESPN now part of four daily free-result runs |
| 3 | Alternative result score integrity | OpenLigaDB now accepts explicit `resultTypeKind=After90Minutes`, rejects conflicting 90-minute scores, never ranks scores by display order | Implemented and regression-tested against actual source shape | Applies on every existing OpenLigaDB backfill |
| 4 | Stale capability labels | Replaced obsolete “key missing” and historical “unreachable” assertions with qualification gates and references to live health reports | Static documented capability remains separate from current availability | Daily provider-health rebuild |
| 5 | Scan frequency and overnight coverage | Prior PR #231 fixes midnight-to-06:00 inclusion and bounds recovery checks to existing scan slots | Implemented; provider availability still external | Slot recovery checks suppress duplicate provider calls |
| 6 | Dashboard integrity | Verify deployed result counts, quarantine exclusions, O/U sample N and actual AH settlement after new source | Artifact checks below; interactive browser remains unavailable | Pages follows result/collector workflow completion |
| 7 | Legacy quarantine | All 84 require verified historical Pinnacle prices at original observation times | WAITING_EXTERNAL_DATA; no evidence to promote | Archive recheck on rebuild |
| 8 | Forward validation | Continue exact settlement, CLV and risk tracking without lowering 150 minimum | COLLECTING; 10 / 4 / 0 settled | Existing forward schedules |

## Source findings

- ESPN's actual public scoreboard response was retrieved from `https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard`. The first inspected date returned 91 events. Normal FT is explicitly labelled `STATUS_FULL_TIME`, completed, period 2. AET/Pen/in-progress and noninteger scores are rejected. This is a results-only integration, not an odds or execution source. Public availability has no guaranteed SLA.
- InferSports returned real event IDs under `id`; its `scheduled` label included kickoffs already in the past. A checked odds response had `stale=true`, `as_of=2026-09-30T05:01:15Z` and `odds=[]`. It cannot qualify as a current AH fallback from that evidence. No stale quote was collected into Research V2.
- OpenLigaDB live Bundesliga response explicitly distinguished `HalfTime` from `After90Minutes`. The old highest-order-result strategy was removed. No existing canonical results were labelled OpenLigaDB at inspection, so no historical scores needed revocation for this change.
- [Pinnodds official docs](https://pinnodds.com/docs) offer authenticated free-trial access, not a confirmed perpetual zero-cost path. No alternate-host demo call was used to work around PinnWire's quota.
- [TheStatsAPI official site](https://www.thestatsapi.com/) advertises a seven-day trial. It was not promoted as a sustainable free replacement and no account/subscription was created.

## Tests and live local evidence

329 tests passed. Added cases cover normal-time FT acceptance, AET/Pen rejection, exact timestamp mismatch, conflicting provider copies, persistent-cache reuse, blocked-result exclusion, past-kickoff rejection and explicit OpenLigaDB normal-time selection.

The live ESPN batch used 11 requests, had no request failures and recovered 7 verified bridges. Staged results preserve ESPN event ID, UID/competition identity, teams, kickoff, scores, full status and retrieval timestamp. Raw responses remain separately cached. Local recalculation changed settled 336→343, core-price 314→321 and raw unresolved 525→518, with data assertions passing. No raw odds observations or quarantine rules changed.

## GitHub runner and morning follow-through

The first GitHub ESPN run, committed as `48e350a`, reproduced **7 recovered results**, **11 requests**, **0 ambiguities**. The next scheduled run reused **9 cache days**, made **2 requests** and recovered **1 further result**. There are **8 ESPN-sourced canonical results**. These are actual verified bridges, not synthetic tests or inferred scores.

At **09:40 Bangkok on 1 October**, PinnWire recovered after its cooldown. Run **36806892995** made **one request** and produced **76 new Research V2 observations** for Football Day 1 October, including **25 matches after midnight** on 2 October. This directly verifies the repaired overnight collection path. Pages run **36806933287** published the new observations. PinnWire remains RESEARCH_ONLY, not execution-qualified.

Counts after this collection: raw **1,298**, usable **1,212**, quarantined **86**, recovered legacy **0**, settled **352**, core-price settled **330**, movement **110 fixtures / 652 deltas**. Total unresolved **585** splits into **509 matured** and **76 new future/recent fixtures**; the increase reflects new collection rather than lost results. Forward samples remain **10 / 4 / 0**.

A separate dashboard issue was found: a failed conflict-ledger download was converted to an empty list. PR #233 requires a validated ledger, pauses rendering with an explicit integrity message if unavailable, and rejects boolean score values. Its tests cover failed requests, malformed JSON, invalid ledger records and a legitimate empty ledger. The full suite passes **330 tests**. Browser interaction remains unverified.

## Latest verified state — 09:44 Bangkok, 1 October

**OddsPapi quota is now confirmed available: 0 used / 250 limit, 250 remaining**, from an actual unmetered account request at `2026-10-01T02:43:54.452756+00:00`. This supersedes the exhausted status in earlier sections. The quota job now refreshes the operational audit too, preventing contradictory provider-health reports. No metered OddsPapi odds request was spent merely to verify the reset.

PR #233 is merged. Final Pages deployment **36807208579** publishes source `13305f8bd15d78e57db0c9395390df9caa7ca28f`. Downloaded live artifacts contain the required-quarantine guard, QUOTA_AVAILABLE in both quota and operational reports, 1,212 trusted observations and 76 current-Football-Day observations. Actual deployed JavaScript rejects an unavailable ledger, excludes both blocked result IDs and retains correct Asian -1.5 settlement on a 1–0 FT score.

The new 76 observations passed numeric two-sided, opposite-line, quarter-line and pre-match checks; **70** have selected AH prices in 1.80–2.20. They remain Research V2 observations, not evidence of execution readiness or a betting edge.

Remaining external/data limits: 509 matured unresolved fixtures, 84 unrecovered historical PropLine observations, forward sample requirements and unverified browser interaction. Sustainable independent free AH redundancy is still partial despite today's restored PinnWire and refreshed OddsPapi quota. See `reports/morning_verification_20261001.json` for machine-readable final evidence.
