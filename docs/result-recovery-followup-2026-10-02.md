# Result recovery follow-up — 2026-10-02 14:00 Asia/Bangkok

PR #238 (51a021f3b566d86a29d926841c0239fc87e34279) and PR #239 (244e60034f95c9c806c68f776442d53d6429c210) are merged. Local suite: 351 passed. PR CI 36953259769 and main CI 36975835537 succeeded.

## Actual verification
- Free backfill 36953114167 after #238 added one FotMob and one ESPN result.
- Free backfill 36975835498 after #239 added the verified Wuxi result. Its FotMob source event is 5207189; exact opponent and kickoff match the original PinnWire observation.
- Canonical result is FT 1–0; derived settlement for home −0.5 @1.877 is FULL_WIN, +0.877 units. Exact O/U 2.5 settles UNDER.
- Direct deployed-browser check on football day 2026-09-29 shows Wuxi Wugou vs Ningbo Professional, FT 1–0, ทีมต่อ ชนะราคา, original quote −0.5 @1.877 and WR sample counts.
- Deployment 36975886112 succeeded. Deployed operational output and canonical/derived outputs were checked, not just action status.
- Research-only Flashscore step now skips 955 unrelated candidates and performs zero requests when no relevant exact mapping exists. It used to attempt 20 unrelated fixtures per run.
- Source and target conflict IDs are excluded before requests. Identity keys are recomputed from team/kickoff fields instead of trusting an old hash. Corrupt conflict evidence fails closed.
- Raw snapshots, odds, timestamps and original names were not changed.

## Counts and remaining blockers
| Metric | Earlier checkpoint | Verified latest |
|---|---:|---:|
| Settled fixtures | 392 | 395 |
| Core price settled | 369 | 372 |
| Canonical unresolved FT | 544 | 541 |
| Active unresolved | 105 | 102 |
| Archived unresolved | 439 | 439 |
| Raw / verified / quarantine snapshots | 1312 / 1226 / 86 | unchanged |
| Recovered legacy odds | 0 | 0 |
| Movement fixtures / numeric deltas | 117 / 684 | unchanged |
| Forward samples | 10 / 4 / 0 | unchanged; minimum 150 |
| October 2 valid scans | 0 | 0 at this pre-evening check |

Twenty active API-Football identities have missing original home/away names and no matching provider-ID metadata in the local fixture cache. Do not infer their opponents from nearby kickoff times. Other unresolved fixtures need verified external evidence. PinnWire's last health remains RATE_LIMITED; API-Football remains ACCOUNT_SUSPENDED; historical PropLine recovery still waits for reliable historical odds. No provider health has been promoted from a successful workflow alone.

The ten-component matrix in result-integrity-completion-audit-2026-10-02.md remains applicable, with the FT counts updated above. Daily free recovery and evening scan schedules remain enabled. This follow-up does not claim the remaining backlog is solved or that future scheduled jobs ran punctually.

Benefit: relevant requests and one more verifiable historical result. Trade-off: unrelated daily fixture discovery is now opt-in; uncertain identities stay unresolved to avoid contaminated statistics.
