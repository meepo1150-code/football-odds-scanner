# Validation — 2026-11-04

Base inspected: main `aba46c9236969f05489ff7ce877f3e9f46b94fc0`.
Initial PR #463 head: `986ac22835f9fe6c48ffbd47ec55aa77919b9aea`.
No AGENTS.md found in the repository tree. Project handoff read; old September progress treated as historical, integrity rules retained.

## Audit findings fixed

- Original code trusted caller-supplied publication time, allowing late insertion: new records also require actual system time before kickoff.
- Direct ledger calls skipped validation: validation now runs inside the append operation.
- Invalid market, side, NaN/infinite/non-quarter line and duplicate fixture-market picks now fail closed.
- Free-form display labels could contradict picks: labels now derive from market/side/line.
- Ledger writes are serialized and hash chained; altered records rejected.
- Original cards silently truncated teams and recaps: measured text fitting and pagination replace truncation.
- Original generator silently succeeded without FFmpeg: renderer now fails instead.
- Original results were not implemented: added exact fixture-ID settlement and separate AH/OU daily/cumulative weighted WR with all outcomes retained.
- Original visual-only output replaced with neural narration, timed captions, original music, animated cards, MP4 decoding QA, thumbnail and private-only OAuth uploader.

## Real data audit

Trusted existing FT cache: 3,252 distinct fixture IDs; explicit nonnegative scores; no conflicting duplicate scores found by the adapter. These are existing repository records, not newly independently verified website results.
Fixture cache: 7,351 rows / 7,336 IDs. 15 IDs have differing stored home/away/kickoff identity tuples. Selected conflicting identities are blocked; unrelated historical conflicts do not block an empty briefing. Production source records were not modified.
No real prediction ledger existed in PR #463; its sole input was a synthetic example. That example was replaced with an empty input template. No retrospective predictions were invented.

## Executed checks

`PYTHONPATH=src:. python -m pytest tests/test_youtube_prediction_pipeline.py tests/test_asian_settlement.py -q`

18 passed (14 isolated pipeline tests + 4 existing Asian settlement tests).

Real 1080p MP4 rendering executed with English en-US-GuyNeural narration, original procedural music, captions, five editorial sections and no fabricated picks. Full FFmpeg decode passed. Frame contact sheet inspected; subtitle/footer overlap found in first render and corrected by moving captions upward. Final render uses provider word-boundary subtitle timestamps.

## Remaining acceptance gates

- Real approved pre-match predictions and independently anchored historical archive are absent. The rendered episode truthfully says no reviewed predictions supplied; this is a real media test, **not** a completed live prediction/results episode.
- Current file hash chain is tamper-evident, not administrator-proof immutable storage. External append-only anchoring is still required.
- Daily input adapter is strict but the football analysis/review step itself is not automated here. Frozen scanner gates remain unchanged.
- OAuth consent/channel credentials unavailable; real private upload, thumbnail and caption API operations untested. No upload or public publication performed.
- No claim of human listening/ASR pronunciation verification. Audio presence, duration and decode are tested; final editorial listening remains necessary.
- Full existing repository suite not run; focused tests and existing settlement tests pass. No production code, data, old workflow, quota or dashboard edits.

PR remains Draft. Do not merge as fully production-ready.
