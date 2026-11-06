# MatchLedger Football — Final QA / 6 November 2026

## Final delivered media

| File | Duration | Resolution | Video / Audio | Decode |
|---|---:|---|---|---|
| matchledger-full-2026-11-06.mp4 | 365.916667 s | 1920×1080 | H.264 / AAC | PASS |
| matchledger-short-01-2026-11-06.mp4 | 16.916667 s | 1080×1920 | H.264 / AAC | PASS |
| matchledger-short-02-2026-11-06.mp4 | 18.541667 s | 1080×1920 | H.264 / AAC | PASS |
| matchledger-short-03-2026-11-06.mp4 | 18.750000 s | 1080×1920 | H.264 / AAC | PASS |

Final files were checked again after visual and pronunciation corrections. FFprobe dimensions/codecs/audio present; complete FFmpeg decode; audible level check; subtitle ordering and measured end times; abnormal black-frame detection all passed. Each of 23 full-video scenes and 12 Short scenes was sampled from the final encoded files. All contact sheets were inspected; recap and corrected matchup frames additionally inspected at full resolution. Stats and picks remain outside subtitle areas; vertical content is within the designed safe region. Home shirt is left, away shirt right. Original color-only shirts have no club crests, sponsors or maker marks.

Actual motion check compares a matchup entrance at +0.15s and +1.10s: mean pixel difference 11.4325. Shirt positions also move through explicit time-based overlay expressions. Four distinct stages per match: matchup, evidence, limitation, pick. No single static card zoomed throughout each match. Charts use a fixed 0–100% scale.

## Voice and subtitle checks

Local Kokoro British-English narration with sentence-measured caption timing. Offline tiny.en ASR transcribed all four final MP4s. Manual transcript review checked the numerical assertions: 57.02%/171, 56.47%/116, 60%/54, 57.14%/21 (event rate), 55.43%/113, 70%/31, and performance 66.67%/50%. Roman numeral speech for Willem II, the spoken 'v', kickoff clock strings and Vejle were corrected through a pronunciation lexicon. Canonical displayed team names and statistics remain unchanged. Corrections preserve scene durations and therefore actual chapters.

Limitation: automated ASR plus transcript review is not a certified native-speaker pronunciation review. Sentence-level subtitles are not word-level forced alignment. Names may retain an English neural accent. The MP4s are complete and passed the stated technical checks.

## Data checks

- Actual 15:00 Bangkok slot verified from existing repository data, collection completed 08:01:08 UTC.
- 90 strict snapshots reviewed; 86 not started at actual recording; four already-started fixtures excluded.
- Four picks recorded 11:29:52 UTC before all kickoffs; ledger hash chain passed. No backdating or replacement of existing predictions.
- Selected fixture audits: 4/4 MATCH / OK / research_population=true in the 15:00 slot.
- Statistics generated 03:03:43 UTC, before scan and before prediction recording; no post-snapshot result used for selection.
- All three verified yesterday picks shown, including the loss. Exact-ID FT settlement independently recalculated. Coverage 3/3, pending 0.
- Daily AH 66.67% (2 FW, 1 FL, N=3); daily OU N/A (N=0).
- Cumulative verified 4–5 Nov: AH 66.67% (4 FW, 2 FL, N=6); OU 50.00% (1 FW, 1 FL, N=2). All half and push counts zero.
- Chat search found no additional evidenced picks; complete recovery of every historical chat is not asserted. Unverified/reconstructed history excluded.
- Every today's selection is EDITORIAL_RESEARCH_LEAN / CAUTIOUS. No validated edge; frozen gates unchanged. Historical groups overlap, are pooled across leagues, and the two OU selections share the same cohorts.

## Remaining data limitations

Scan Health WARNING. Slot ledger counts 90 strict snapshots / 91 market-response fixtures; discovery health counts 99 discovered and 85 valid strict core-AH odds. Different populations must not be presented as complete coverage. A response fixture has no strict snapshot; other discovery rows lack usable core markets or eligibility. No API calls were added to fill gaps. Earlier chat coverage and long-run predictive validity remain unproven.

## Repository and safety

PR #463 and #464 remain open Drafts, unmerged. Today's isolated work: PR #465, also Draft and unmerged: https://github.com/meepo1150-code/football-odds-scanner/pull/465

Source main commit: 309b0705a26705199ce7bccaef0109cdfbd73c58. Historical 15:00 health commit: 1845e8a9374b3cafb1961b3f58e229d9d2d67ce6. Pre-kickoff external ledger anchor: e3751045d55d4c037848c3acb29779f04cfdf375. Hash chains are tamper-evident, not administrator-proof immutable storage.

16 focused pipeline tests passed. No scanner, Manual/Auto workflow, production secrets, quota, dashboard or core statistical engine was edited. No merge and no YouTube upload/publication occurred. Output file hashes are in checksums.json and final MP4 hashes in media-qa.json.

## Acceptance

15:00 snapshot verified; previous verified card fully reviewed; FT/settlement coverage and missing scope disclosed; separate AH/OU daily/cumulative WR; pre-kickoff ledger; Thai report; full MP4 and 3 Shorts; thumbnail/covers; English SRT; individual metadata and actual chapters; actual file paths/hashes checked; safety restrictions respected. Final media delivery COMPLETE within the evidence scope described above.
