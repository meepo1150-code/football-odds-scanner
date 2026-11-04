# Football Daily — isolated video production

This package does not modify scanners, provider quota, production data, schedules or the dashboard. Run from repository root with Python 3.11+, FFmpeg/ffprobe and DejaVu Sans installed.

## One command after installation

```bash
python -m pip install -r youtube_prediction/requirements.txt
python -m youtube_prediction.pipeline --input daily.json --output output/2026-11-04 --ledger private-archive/predictions.jsonl --fixtures data/normalized/research_v2_daily_fixtures.jsonl --results data/normalized/oddspapi_finished_results.jsonl
```

Use a new output directory. Input must contain `date` (Bangkok episode date), timezone-aware `published_at`, `source_type: REVIEWED_PREDICTION`, and `predictions`. Each prediction requires `id`, exact `fixture_id`, exact `home`/`away`/`kickoff`, `market: AH|OU`, `selection: HOME|AWAY|OVER|UNDER`, and finite quarter-grid `line`. AH line is from the **selected side's perspective**. Labels are generated from canonical fields; free-text labels cannot alter displayed picks. One pick per fixture/market is allowed. Episode date admits that date and next calendar date for overnight fixtures; operator must ensure the intended football-day window.

`example.json` is an empty reviewed-input template, not fabricated football data. An empty list produces a truthful no-input briefing, not a claim that an automated analysis found no qualifying matches. Reviewed predictions must be supplied by the analysis step; this package **does not implement or relax the scanner's prediction/validation strategy**.

## Integrity and results

New picks must be recorded before actual kickoff using the machine clock. Claimed publication time alone cannot backdate a pick. Exact fixture ID, teams and kickoff must match the supplied trusted fixture cache. Conflicting identities are rejected for selected fixtures. Repeated identical records are idempotent; altered predictions and duplicate fixture markets are rejected. A file lock serializes writers; chained hashes detect edits. This is tamper-evident, **not immutable against an administrator rewriting the entire file or truncating its tail**. A protected external append-only archive or externally anchored head hash is still required for independent proof of pre-match publication. No historical picks are imported without such proof.

The results file must be the trusted reviewed FT cache, not user-generated guesses. Scores join only by exact fixture ID; missing FT stays PENDING; conflicting scores stop production. Results from the prior episode date are shown in full, including losses and pending matches. AH and OU WR are separate:

`(full wins + 0.5 half wins) / (full wins + 0.5 half wins + full losses + 0.5 half losses)`

Pushes and pending results are excluded. Counts and decisive units accompany WR. This is a settlement-weighted rate, not probability of profit or evidence of predictive edge.

## Artifacts and quality

Produces 1920x1080 H.264/AAC MP4, English neural narration (Edge TTS), gently animated original graphics, original procedural ambient music, burned subtitles and SRT, 1280x720 thumbnail, metadata, script, timeline, report, results and checksummed manifest. Audio length determines scene duration; recaps paginate instead of truncating picks. FFprobe validates dimensions/duration/audio and FFmpeg decodes the entire output. Subtitles use TTS word-boundary timestamps grouped into short phrases; pronunciation, exact subtitle timing, and content quality still need listening review. External TTS requires connectivity and has no guaranteed SLA. Music uses no third-party samples; see generated license statement.

No output is uploaded automatically. A failed render may leave already archived predictions: they intentionally remain in the record. Retry identical input into a fresh output directory with the same ledger; do not delete predictions to improve reported performance.

## Private YouTube OAuth

Create a Desktop OAuth client with YouTube Data API enabled. Keep client credentials and tokens outside the repository. Run locally where an interactive browser can complete account consent:

```bash
python -m youtube_prediction.upload --directory output/2026-11-04 --client-secret /secure/client-secret.json --token /secure/youtube-token.json
```

The uploader requests `youtube.force-ssl` because caption upload needs it. It verifies artifact checksums and always sends `privacyStatus: private`; no public switch exists. Thumbnail/caption failures leave an upload receipt to prevent duplicate videos; resolve partial uploads in Studio. If the initial video request ends ambiguously, inspect Studio before retrying. OAuth and a real account upload remain untested until channel credentials/consent are available.

Official references:
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- https://developers.google.com/youtube/data/reference/rest/v3/captions/insert

## Tests

```bash
python -m unittest discover -s tests -p test_youtube_prediction_pipeline.py -v
```

Production readiness still requires a supplied real reviewed prediction set, protected external ledger anchoring, a full episode with real pre-match picks and subsequent FT, listening QA, and authorized private-upload verification. Do not merge as fully production-ready until these gates pass.
