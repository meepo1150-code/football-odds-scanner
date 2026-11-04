# Football Prediction YouTube — isolated MVP

Experimental video production, **not** a change to the odds scanner. No collector, workflow, API quota, or dashboard behavior is changed.

## Contract

- Input: externally reviewed `daily.json` with an ISO-8601 publication timestamp, immutable prediction IDs, fixture IDs, kickoff timestamps, selections and optional verified previous-day results.
- No predictions are fabricated from odds. The scanner's `NO_VALIDATED_PATTERNS` state must not be turned into a recommendation.
- Published records are append-only using `ledger.jsonl`; repeated IDs with altered payloads are rejected.
- FT summaries are derived from the ledger, never selectively selected winners. Unsettled games remain PENDING.
- The video is a visual-only MVP; **no synthetic commentary or YouTube upload in v1**.

## Run

```bash
python -m pip install Pillow
python youtube_prediction/pipeline.py --input youtube_prediction/example.json --output /tmp/football-video --ledger /tmp/football-predictions.jsonl
# requires ffmpeg on PATH to produce video.mp4
```

Output: `video.mp4`, `thumbnail.png`, `metadata.json`, `manifest.json`. Uses original rendered graphics and no match footage.

## Next gates

1. Build an explicit approved prediction adapter: NEVER treat market snapshots as predictions.
2. Join fixture-ID-based finished scores and Asian settlement (including half wins/losses/push).
3. Add verified English TTS with subtitles and audio QA.
4. Add upload connector with OAuth, private-first, operator approval, and platform disclosure checks.
5. Continuous visual/audio checks and true fixture tests.

Do not publish sample content: `example.json` is synthetic and labeled as such.
