# 2026-11-04 editorial edition

Five genuine editorial leans recorded from the 08:00 UTC / 15:00 Bangkok scan. `daily.json` preserves canonical fixture IDs, names, kickoff times and exact selections. `evidence.json` contains the matching dashboard groups. `prediction-ledger.jsonl` records actual pre-kickoff creation time and hash chain. No production pattern promotion is implied.

`previous-chat-recap.json` is separately reconstructed from retrieved chat context with original message timestamps and exact-ID cached FT evidence. It is **not** inserted into the pre-match ledger retroactively. All eight prior selections are included (five main, two additional, one reserve). No cumulative audited WR is claimed.

`analysis-th.md` is the Thai analysis, including limitations and unselected fixtures. For every selection, inspect counts as well as percentages. Dashboard groups overlap; do not treat them as independent evidence.

## Broadcast render

Requires FFmpeg, ffprobe, Nimbus Sans fonts (`fonts-urw-base35` on Debian/Ubuntu), Python dependencies, and downloaded public Kokoro model/voice files. Rendering is fully local; no episode text or audio is sent to a TTS API.

```bash
python -m youtube_prediction.broadcast \
  --episode youtube_prediction/episodes/2026-11-04 \
  --output /absolute/path/new-output \
  --model /secure-models/kokoro-v1.0.onnx \
  --voices /secure-models/voices-v1.0.bin
```

Kokoro model: https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1
Model publisher/license: https://huggingface.co/hexgrad/Kokoro-82M (Apache-2.0).
Runtime: https://github.com/thewh1teagle/kokoro-onnx (MIT).
Voice: built-in `bm_george`, generic British English synthesis, no public-figure impersonation.
Captions follow separately measured narration sentence segments. Not word-level forced alignment.

Broadcast art and copy are reviewed for this episode. The edition renderer currently contains date-specific copy; do not substitute another day's input without reviewing/replacing the storyboard. The general JSON pipeline remains separate. No upload is implicit. YouTube metadata defaults to private.
