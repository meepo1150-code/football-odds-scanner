# Functional recovery checkpoint

Fixes: distinguish overdue (>=3h), future/recent and unknown kickoff pending states in the statistics summary; scope exclusions are separate from integrity quarantine. Reopen exactly one archived identity after verified team-alias review, rather than reopening the entire exhausted backlog.

Consadole Sapporo is Hokkaido Consadole Sapporo (official club naming: https://www.jleague.jp/en/club/sapporo/ and https://global.consadole-sapporo.jp/). Existing FotMob cache contains event 6189153, Hokkaido Consadole Sapporo–Fagiano Okayama FC, League Cup, kickoff 2026-09-29 10:00 UTC, explicit normal FT 1–2. Snapshot pinnwire:1637183975 has the same opponent, exact kickoff and Japan League Cup. Targeted reopening additionally pins provider event and competition; all existing uniqueness, FT, score and conflict rules remain enforced. No score is hardcoded in recovery code.

Offline replay reused the original cached provider response and recovered one canonical result. Statistical population 353 -> 354. Asian settlement remains authoritative. Raw snapshots preserved. Tests 373 pass before publication. Actual workflow, generated artifacts and deployment require separate verification.

Remaining known external blockers: PinnWire 429, historical PropLine quarantine without verified replacement odds, forward candidate samples 10/4/0 below150. These are not GREEN simply because CI succeeds.
