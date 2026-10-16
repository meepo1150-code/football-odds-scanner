# Historical staging — partial production reconciliation (2026-10-16)

**Read-only research evidence. NOT an import approval.**

Compared 129 selected `BALANCED_LINE` rows in `research/historical_backfill/reports/CONTROLLED_EXPANSION_20261016.json` (research branch) with two production files on `main`:

- `data/normalized/research_v2_slot_ledger.jsonl`: 97 ledger entries, 74 unique scheduled UTC targets.
- `data/normalized/v2_mainline_snapshots.jsonl`: 555 mainline observations.

## Results

| Check | Yes | No |
|---|---:|---:|
| Candidate's fixture ID + bookmaker occurs anywhere in v2 mainline observations | 10 | 119 |
| Candidate's exact UTC target exists anywhere in research-v2 slot ledger | 47 | 82 |
| Candidate has exact-ID verified FT | 128 | 1 |

**These are independent checks and must not be added together.** The ledger is *round-level*, not fixture-level, so a ledger match **does not prove** the candidate fixture was scanned. Conversely, a fixture/bookmaker match in v2 mainline history **does not prove** that the target slot has a matching observed quote. The two files are not a complete authoritative inventory of all production odds history; absence in either file is not evidence of an actual missed scan.

The FT-missing candidate is Levante UD–Athletic Bilbao (`id1000000872478578`, 2026-09-16T08:00:00Z). Postponement has been reported, but the production lifecycle status has **not** been changed by this audit. Do not settle this candidate.

## Admission gate

- 129 price-selected research candidates remain **NOT APPROVED FOR IMPORT**.
- No claim of 119 missed scans or 82 unscanned rounds is supported.
- Next required check: fixture-level production snapshots across all live collectors, historical slot identity and exact quote timestamp; authoritative lifecycle status and FT settlement; idempotent before/after counts.
- No provider requests, no production writes, no merge or deployment were performed in this reconciliation.
