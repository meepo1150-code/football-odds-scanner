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

## Current edition: 4 November 2026

The initial empty media test is superseded by a real reviewed edition: five pre-kickoff selections from the 15:00 Bangkok scan (08:00 UTC), plus all eight retrieved prior-chat selections with exact-ID FT evidence. Evidence, Thai analysis, and the new ledger are in `episodes/2026-11-04`. Yesterday's recap is explicitly separate from the new ledger; it is not retroactively inserted.

Current production data inspected at main `4d2f01b2a2756ad8a389f4fa4d4a779f0e311859`. The scan was observed at 08:00:47–50 UTC and the historical statistics predate it. Selected names/kickoffs were cross-checked against fixture listings; no live odds requests were made.

## Executed checks

`PYTHONPATH=src:. python -m pytest tests/test_youtube_prediction_pipeline.py tests/test_asian_settlement.py -q`

20 passed (16 isolated pipeline tests + 4 existing Asian settlement tests). Contract tests reject changes between the reviewed storyboard, ledger and recap.

Actual final media: 181.9 seconds, 1920×1080, H.264/AAC, 16 scenes. Full FFmpeg decode passed. Frame inspection found subtitle interference; layouts were moved above the caption safe area and rendered again. Thumbnail is 1280×720. Captions derive from measured local narration sentence segments. Original procedural music and generic club-colour graphics avoid third-party footage and crests.

Final narration uses Kokoro ONNX `bm_george` entirely locally. An external TTS attempt was blocked by automatic approval review, so no external TTS is required by this broadcast renderer. Local automated ASR sanity checking confirmed the numerical result and selection content; proper-name transcription is imperfect. This is not human listening certification.

## Remaining acceptance gates

- Today's selections are editorial research leans, not validated predictive edges. Small and overlapping historical groups are disclosed in the Thai report. Frozen scanner validation gates are unchanged.
- File hash chains are tamper-evident, not administrator-proof immutable storage. A GitHub commit anchors this edition; stronger external append-only storage remains future work.
- The reviewed broadcast storyboard is date-specific and fails closed on different selections. Daily football analysis and editorial review are not yet fully automated; the general JSON renderer remains separate.
- OAuth consent/channel credentials unavailable; real private upload, thumbnail and caption API operations remain untested. No upload or public publication performed.
- Full existing repository suite not run; focused tests and existing settlement tests pass. No production scan code/data, old workflow, quota or dashboard edits.

PR remains Draft. Do not merge as fully production-ready.
