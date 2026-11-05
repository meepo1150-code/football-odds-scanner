# MatchLedger 5 November 2026 — QA
## Media
| File | Duration | Resolution | Video / Audio | Complete decode |
|---|---:|---|---|---|
| matchledger-full-2026-11-05.mp4 | 238.337s | 1920×1080 | H.264 / AAC | PASS |
| matchledger-short-01-2026-11-05.mp4 | 18.033s | 1080×1920 | H.264 / AAC | PASS |
| matchledger-short-02-2026-11-05.mp4 | 18.700s | 1080×1920 | H.264 / AAC | PASS |
| matchledger-short-03-2026-11-05.mp4 | 18.304s | 1080×1920 | H.264 / AAC | PASS |

- Actual downloaded MP4 files were inspected locally with FFprobe and fully decoded with FFmpeg, including the corrected full video. All 4 final hashes are in local-media-qa.json.
- Audio present, mean approximately -19.8 to -19.9 dBFS. This is instrument verification, not human listening certification.
- SRT files exist, timestamps are ordered and end before each video ends. English captions derive from measured narration sentence segments. Within-sentence caption chunks use proportional timing; they are not ASR word alignment.
- Eight full-video scene samples plus three samples from each Short were extracted and visually inspected. Names and picks fit; final full footer was moved above captions and the affected lower band re-rendered locally.
- Shorts show names immediately; picks/statistics/captions are inside the inspected central safe region. The decorative footer/ticker is outside the critical region.
- No blank interval ≥0.25s found with blackdetect. Intentional opening fades are short.
- Thumbnail inspected at 1280×720; all three covers 1080×1920. Original sports graphics; no footage or official logos.
- Full timeline chapters derive from the actual measured scene timeline.
- 16 isolated pipeline tests passed in the render workflow. No full repository suite or football API call was run for this production.

## Data
- Scan observed 2026-11-05 08:00:47.309046 UTC / 15:00:47 Bangkok. Scan Health WARNING, API errors 0.
- Scheduled competition population 36 (18 Conference League, 17 Europa League, 1 Liga II); 35 strict snapshots. One scheduled fixture lacks a strict quote: id1003448074173284.
- Discovery health reports 38 found, 36 in market response, 35 valid, 3 without valid odds. Two discovery entries beyond the scheduled population were not individually reconciled in this media-only task. Do not combine these denominators.
- Reviewed 35 unique fixture IDs, all pre-kickoff at actual ledger recording. Selected 3 AH and 0 OU. Source snapshot archive SHA256 cc8571dce89ecf93b8887017d39fffa93f77ed5e873ef77b4fbb1c3f150d09fe.
- Statistics generated 03:02:32 UTC, before the scan and prediction recording; no today fixture IDs had FT in the source results cache.
- Yesterday: exact ID FT join 5/5; no Pending or conflict on those IDs. AH 2 FW / 1 FL = 66.67%; OU 1 FW / 1 FL = 50%. All HW, Push, HL counts zero.
- Prior chat search corroborates the same five picks, originally shown at 2026-11-04T10:17:39Z; original ledger anchored by commit be50e6314b8fbf7114438b94287c8657b754d47d at 2026-11-04T10:15:19Z, before kickoff.
- Cumulative history is limited to one verified ledger day; no claim that every earlier chat was recovered. Reconstructed 3 November recap excluded.
- All picks are cautious EDITORIAL_RESEARCH_LEAN. Historical groups overlap, contexts have N=21–33, and no frozen promotion gates were changed.

## Provenance and restrictions
- Production source: dashboard artifact from run 41991286425, main snapshot commit 8a8c20f989486376176256648c317d9a9c6c488a.
- Render workflow: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/41998015175
- Isolated code review: https://github.com/meepo1150-code/football-odds-scanner/pull/464 (Draft; not merged).
- No production scanner, dashboard, core statistics, provider quota or secrets changes. No YouTube upload/publication.
- Completed: Thai report; verified known prior ledger settlement; pre-kickoff archive; full MP4; 3 Shorts; 4 SRT; thumbnail/covers; metadata; actual media QA. History coverage and scan denominator limitations are disclosed above.