# Result recovery and reviewed retirement — 1 October 2026

The user authorized removing unresolved fixtures after repeated failed recovery. PR #234 implements removal from active recovery queues and the active scan timeline while retaining raw snapshots, historical reports and per-fixture retirement evidence. No settled results or raw observations are deleted.

## Recovery performed

The latest real ESPN pass recovered Madrid CFF–Alavés (canonical `pinnwire:1637095196`, ESPN `401882505`) through accent normalization only: both teams and exact UTC kickoff `2026-09-26T16:30:00+00:00` agree. ESPN explicitly reports normal FT, period 2, score 1–0. No alias based on approximate kickoff, no fuzzy matching and no inferred score were used. Team category markers remain intact and duplicate normalized identities fail closed.

Local verification: 2 requests, 10 cache hits, 1 result added. Recalculation raised settled 352→353 and core-price settled 330→331.

## Retirement gate and evidence

Every automatically retired fixture must:

- remain unresolved after at least four distinct source-evidence rounds;
- have been checked against at least two sources;
- have at least 24 hours between first and latest attempts;
- have a kickoff at least 72 hours in the past;
- have one consistent local identity and both team names;
- not have a result-conflict ledger entry requiring separate review.

The attempt history is reconstructed from versioned FotMob/ESPN reports and the snapshots/results at those exact repository commits. Historical direct-fetch commits prove completed requests; their commit timestamps are recording times, never represented as source quote timestamps. New cached responses count only once per distinct retrieval evidence and must postdate match maturity. Source failures and stale fallback do not create attempts. Push-retry merges deduplicate attempts again before review.

Evidence: `data/normalized/result_recovery_attempts.json`. Reproducible bootstrap: `scripts/bootstrap_result_recovery_history.py`. Retirement reasons and fixture identities: `data/normalized/research_v2_retired_fixtures.jsonl`. Remaining active cases: `reports/result_recovery_review.json`.

## Actual local review

| Metric | Before | After |
|---|---:|---:|
| Matured unresolved | 509 | 508 |
| Recovered normal-time FT | — | 1 |
| Removed from active queue | 0 | 437 |
| Remaining active matured backlog | 509 | 71 |
| Future/recent fixtures retained | 76 | 76 |
| Settled statistical fixtures | 352 | 353 |
| Core-price settled fixtures | 330 | 331 |
| Raw observations deleted | 0 | 0 |
| Settled results deleted | 0 | 0 |

All 437 locally eligible fixtures have ten distinct evidence rounds in the reconstructed history, from FotMob and ESPN. The remaining 71 comprise 49 that do not yet meet age/evidence gates, 20 with missing team identity and two separately quarantined AET results requiring verified 90-minute scores.

## Statistical effect

Retirement does **not** turn a missing result into a win/loss and does **not** improve WR. Unresolved fixtures were already outside the settled statistical denominator. Regression tests verify identical AH and O/U statistical groups before/after retirement of an unresolved fixture. Only the newly recovered real FT changes settlement statistics. Raw unresolved totals remain reported separately from active pending and archived counts, preserving visibility of missing-data/selection bias.

Known exact results can reactivate an archived fixture; it is displayed and included in settlement again. Primary free-source backfills skip retired IDs to avoid repeatedly spending requests on exhausted cases. Automatic review runs after result collection and after canonical merge, so a result recovered in the same run prevents retirement.

The full suite passes 336 tests; data assertions pass. Deployment/run verification is appended below.

## GitHub runner and deployed artifact verification

PR #234 merged as `0ecdb6c84f06260df12093c0814ed9aac2205bba`. Free-result run 36809129368 recovered the accent-normalized exact-identity result, with 2 requests and 10 cache hits. Later scheduled run 36828852588 added no result and retired two additional age/evidence-qualified fixtures. At 07:11 UTC, 439 are archived and 69 matured unresolved remain active, plus 76 future/recent fixtures. Raw unresolved remains 584.

Actual public deployment manifest: run 36828956620, source `d9b9ba2cb58697b1c4f7ee4cea75e801ea840a87`. Downloaded deployed HTML, statistics, operational audit, raw snapshots, canonical results, verified result bridge, and conflict ledger. Executed actual deployed JavaScript pure functions in Node: 1,298 raw / 1,212 trusted observations; 439 archived fixtures excluded from the active timeline; recovered Madrid CFF FT 1–0 present; 353 settled / 331 core; active unresolved 145 + archived 439 = raw unresolved 584; AH -1.5 with FT 1–0 correctly settles FULL_LOSS. All assertions pass.

The full local regression suite was rerun: 336 passed. Interactive browser rendering/click behavior was not verified; the deployed data and actual JavaScript functions were verified.

Latest deployed provider report: PinnWire AVAILABLE (research only), PropLine AVAILABLE (fallback, no usable current-day output), OddsPapi quota 248/250 remaining. Forward settled sample sizes remain 10/4/0 against minimum 150; PAPER_RESEARCH_ONLY. Legacy price recovery remains unavailable (0 promoted); 86 snapshots remain quarantined. Retirement of unresolved FT does not repair legacy odds or establish an unbiased complete sample.
