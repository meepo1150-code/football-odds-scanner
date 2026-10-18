# Replay all retained historical cache offline

Historical run 39094936689 saved 122 new response receipts before its runtime
budget stopped the collector. Its plan also had 161 preexisting usable cached
fixture-bookmaker pairs, but the collector's result-finalization loop was never
reached. The first partial import could see only the 27 balanced slots in the
original report, not all saved raw/cache evidence.

Publish Retained Historical Artifact now has an explicit `replay_saved_cache`
option. It restores the exact immutable Actions cache key belonging to the
selected source artifact's run and attempt, with no broad restore fallback.
No collector, provider key or provider transport is used.

Offline reconstruction checks the reviewed catalog SHA, request identity,
raw response SHA, fixture identity and complete-through-target fetch time.
It processes every available cached candidate in the original full manifest,
retains already processed results, and writes a separate derived report. The
original artifact, raw cache and STOPPED status are preserved. Missing and
rejected quotes are not invented. Existing append-only publication and conflict
gates still apply; previously imported rows remain idempotent.

The receipt records cached/added/unprocessed pair counts and zero replay
provider requests. All three scanner workflows and collectors remain unchanged.
