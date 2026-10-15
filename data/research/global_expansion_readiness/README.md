# Expansion identity completion and 15:00 matchday verification

No Phase 3 expansion. No new leagues or clubs. These are the same 33 leagues and
588 staged clubs from Phase 1, Phase 2 and the Thai membership completion.

`python data/research/global_expansion_readiness/build.py` deterministically checks
hash-pinned Korean bilingual profile evidence and five official matchday aliases.
`--write` writes only this directory's derived `identity_review.json`.
The original 22/253 and 24/270 reports remain historical baselines; this current
staging report certifies **26/33 competition identities and 300/588 club identities**.
**288 clubs and 7 competitions remain unresolved.** Do not call the whole expansion
complete or activate it. Season/stage certification remains false.

`cached-matchday-preview-20261015.json` is explicitly a preview using the Oct11
snapshot: six Oct15 fixtures match both team IDs. It is NOT a fresh scan or price test.

`python data/research/global_expansion_readiness/audit.py` compares ALL 33 leagues against
retained canonical 15:00 `/fixtures` receipts, without an API request. Every league
is present even when blocked, not queried for prices, absent from the response or
waiting for the 15:00 receipt. A truncated response cannot establish completeness.
No-returned-fixtures does not establish no matches or no provider coverage.

The separate one-off `global_expansion_probe` can request prices for every returned
prematch expansion fixture only AFTER its two identities match. It uses at most
one batch of at most five verified league IDs, after a fresh account check and a
durable shared UTC-budget reservation. It does not activate the leagues, modify
the canonical daily cohort or write production prices/results. If ANY returned
expansion fixture is unmapped, or quota/response/capability evidence is inadequate,
the probe is blocked rather than sampling a smaller supposedly complete set.

The full-33-league/full-588-team gate and this bounded matchday gate are different:
the former remains BLOCKED. Passing today's returned fixtures does not certify
unseen clubs, seasons, stages, all markets or future rounds.

Workflow artifacts contain the actual readiness report, raw probe response and
strict normalized shadow snapshots. Only the new probe status report and the
shared request reservation are committed; original histories remain immutable.
