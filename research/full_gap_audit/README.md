# Historical gap audit — RESEARCH ONLY / NOT COMPLETE RECOVERY

Baseline: `b6976e2f667ab7e245e4e091f6ef352bd6b65d15` (main at task start).
Research parent: `564ec452b50725fb7b472b9f1c1068790a57beee`.
Cutoff: **16 October 2026, 08:52:42 Asia/Bangkok**, retained after session reset
for reproducibility. Later end-day slots are future/not due, not missing.
Earliest retained verified live AH: **10 September 2026, 20:38:29 Bangkok**.
Earlier archive dates are imported history, not live collection dates. This is
the earliest retained quote evidence, not proof that no earlier request ran.

## Measured results

| Measure | Count |
|---|---:|
| Inventory provider-local identities, including discovery-only | 7,382 |
| Identities with production observation/attempt/cohort evidence | 1,546 |
| Candidate fixture-slot matrix rows | 59,191 |
| Proven elapsed expected fixture-slots, **lower bound only** | 960 |
| Complete AH within that lower-bound population | 840 |
| Failed attempts after kickoff | 22 |
| Explicit no-price / inactive bookmaker | 1 |
| Expected but insufficient AH-specific evidence | 27 |
| Expected but quarantined/unmatched price semantics | 70 |
| Unknown-evidence matrix rows across the broader inventory | 32,545 |
| Complete AH slots across all matrix rows, including unknown expectation | 1,116 |
| Normalized observed rows present at baseline | 2,721 |
| Additional Git-history-only evidence rows, **not restored to production** | 323 |
| AH ladder pairs decoded from retained current raw responses | 4,361 |

Provider-local identities are **not** a count of unique real matches. Cross-provider
IDs remain unlinked without authoritative ID evidence; names are never fuzzy-joined.
The full expected-slot denominator and global missing count remain **unknown**.
The 23-row manifest is a retained-evidence price-deficit queue, not a claim that
only 23 gaps exist in the entire project. Its 22 failures are all FA Cup at
20:00 Bangkok on 3 October; recovery attempted after kickoff. The other slot is
FC RFS–SK Super Nova, 15 October 18:00, bookmaker inactive. `NO_PRICE` is not a
claim that no scan ran. No `MISSING_SLOT` was inferred solely from absent files.

## Cache and price-quality result

The existing Actions artifact **12017046429**, run **38830015043**, was downloaded
and its ZIP SHA256 verified:
`d369bc49ec75ea7de0102261004b6df19446cc6c3042dd562c6d5bd74f89b593`.
Every one of 100 immutable original-response byte hashes was checked. Replayed
all exact reviewed AH lines, preserving source entry timestamps and active state:

- **1,176** complete all-line records; **129** balanced representatives; **106**
  unresolved pilot targets. Frozen representative selections match on replay.
- **0** cached fixture/bookmaker identities match the verified price-deficit queue.
- Of 129 selected candidates, 128 are not verified gaps and one is postponed.
  None are imported. These are quarantined research candidates, not duplicates
  assumed to be live observations or approved promotion candidates.
- Both prices must be 1.80–2.20; selection minimizes squared distance to 2.00.
  Label is `BALANCED_LINE`, never an unsupported official-mainline claim.
  The unchanged 3,600-second quote-age threshold is provisional.
- Independent exact-ID FT check against the pinned result cache: **98** pilot
  identities verified, **1 postponed**, **1 unavailable/conflicted**. The latter
  is `id1000003572513212` (Bet365); no FT is inferred.

Levante–Athletic (`id1000000872478578`) is postponed and excluded from settlement.
Official LaLiga notice dated 17 September schedules it for **21 October 2026,
20:00 Europe/Madrid / 18:00 UTC**. Provider historical kickoff and quotes remain
unchanged; no historical prices are moved to the new match date.

Sources:
- https://www.levanteud.com/en/news/the-match-between-levante-ud-and-athletic-club-has-been-suspended
- https://www.laliga.com/es-CA/noticias/nota-informativa-sobre-la-disputa-del-levante-ud-athletic-club-correspondiente-a-la-jornada-6-de-laliga-ea-sports
- Existing pinned `data/research/verified_fixture_lifecycle.jsonl` exact-ID record.

## Dry run, blockers and trade-offs

Before: **2,721 observed / 0 admitted backfilled**.
After: **2,721 observed / 0 admitted backfilled**.
New settlement-eligible backfills: **0**. Dashboard/statistical change: **none**.
Live reliability history: **unchanged**. Production promotion: **not approved**.

**0 new Historical API calls and 0 account calls.** An upper bound of **23 unique
fixture/bookmaker requests** remains, plus fresh unmetered preflight/pacing checks.
The local runtime has no dedicated research credential. GitHub Environment secrets
cannot be read through this connector. The existing research workflow is bound to
another research branch and its old pilot manifest. Reusing it would not prove
that these 23 targets were requested under this validated manifest; editing any
workflow is explicitly prohibited in this task. No key was extracted, no production
key used and no workflow dispatched. This step is blocked, not silently completed.

Conservative membership avoids fake gaps and quota waste; the trade-off is a partial
denominator and unrecoverable certainty for older cohorts whose evidence was not
retained. Git history and checked Actions logs do not prove completeness of all
external/expired artifacts. No betting-edge, ROI improvement or production readiness
claim follows from this audit.

## Deliverable map

All paths below are under `results/`. Large JSONL files may be gzip-compressed
without changing their uncompressed content; `gzip -dc FILE.jsonl.gz` reads them.

1. `pinned-b6976e2f/fixture_inventory.jsonl[.gz]`: IDs, kickoff versions, membership,
   per-fixture expected slots and actual status counts.
2. `pinned-b6976e2f/expected_actual_matrix.jsonl[.gz]`: every candidate fixture-slot,
   policy deployment instant, exact evidence path/commit/line/hash, actual AH rounds.
3. `pinned-b6976e2f/missing_slot_manifest.jsonl`: 23 deduplicated price deficits.
4. `cache-dry-run/recovery_queue.jsonl`: manifest-only recovery queue and blocker.
5. `cache-dry-run/raw_provenance.jsonl`: original byte and canonical response hashes.
6. `cache-dry-run/cache_full_line_staging.jsonl[.gz]`: 1,176 reconstructed research
   records, BACKFILLED/HISTORICAL_RECONSTRUCTED, without production admission.
7. `cache-dry-run/pilot_candidate_quarantine.jsonl[.gz]` and
   `unresolved_pilot_slots.jsonl[.gz]`: all 129 candidates and 106 unresolved targets.
8. `cache-dry-run/ft_validation.jsonl` and `dry_run.json`: FT and before/after.
9. `pinned-b6976e2f/source_versions.jsonl`, `source_inventory.json`, `summary.json`:
   pinned source versions, exclusions and policy timeline.
10. `VALIDATION.md`: tests, idempotency, CI limitations and production isolation.

## Reproduction

From this repository root, Python 3.11+:

```sh
PYTHONPATH=src:. python -m research.full_gap_audit.audit --output research/full_gap_audit/results/reproduced
PYTHONPATH=src:. python -m research.full_gap_audit.replay --audit research/full_gap_audit/results/reproduced --cache /absolute/path/to/extracted-artifact --output research/full_gap_audit/results/replayed
PYTHONPATH=src:. python -m pytest -q research/full_gap_audit research/historical_backfill
```

Outputs are exclusive-created and conflict on differing existing bytes. Re-run the
same commands to verify idempotency. No command here authorizes production writes,
live API calls, merge or deployment. Final stop remains isolated staging/dry run.
