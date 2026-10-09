# Football Master Database — current-season snapshot

Scope: **50 UEFA associations / 81 domestic divisions**, taken from `uefa_55_division_scope.csv`. Sources were retrieved on 2026-10-08, with final reconciliation/QA on 2026-10-09. Calendar-year leagues use `2026`; split-year leagues use `2026-27`.

## Current authoritative tables

- `uefa_clubs_canonical.csv`: permanent club IDs, registry country, canonical name, current scoped membership status, and canonical redirect. **Use this instead of the historical `teams.csv` seed.**
- `competitions.csv`: permanent competition IDs; earlier out-of-scope IDs remain reserved.
- `countries.csv`: country registry; IN_SCOPE rows are the 54 associations. Liechtenstein is CROSS_BORDER_ONLY. Other historical countries are retained.
- `uefa_verified_memberships_2026.csv`: 1,203 memberships with competition ID, source name, season, source URL, evidence status and retrieval date. Here `country_id` is the **league association**, not necessarily the club's registry country.
- `memberships.csv`: compatible three-column projection; `team_id` references `uefa_clubs_canonical.club_id`.
- `uefa_league_coverage_2026.csv`: one row per scoped division, expected/recorded source roster counts and BLOCKED reason field.
- `research/rosters.json`: factual extracted source rosters, URLs and notes, not copied articles.
- `research/club_assignments.csv`: explicit source-name-to-ID ledger. Issued IDs never get reallocated during rebuilds.
- `research/existing_club_ids.csv`: 666 pre-existing canonical IDs/names reserved unchanged.
- `research/identity_overrides.json`: reviewed differences in spelling/abbreviations; no fuzzy match joins.

## Evidence semantics and limitations

`VERIFIED_OFFICIAL` (81 divisions) means the recorded source is the league/federation. `VERIFIED_SECONDARY` (0 active divisions) means a season-specific roster was retrieved from the recorded secondary source. It is **not equivalent to independent official certification**. Secondary rosters are usable as sourced master data, but consumers can filter to official evidence if they require a stricter admission rule.

`NOT_IN_CURRENT_SCOPED_ROSTERS` does not mean defunct or inactive: a club may play outside this research scope. Historical `teams.csv`, numeric-ID aliases and migration proposals are preserved; they do not establish current membership. Consult `QA_2026.md` for exceptions and limitations.

The 2026-10-09 official audit attempted all 66 baseline secondary divisions and completed 60 independent team-by-team comparisons. The other 6 were excluded from active scope by the user on 2026-10-09; their original review evidence is retained as history. See `research/official_roster_audit_2026_10_09.json` and `FINAL_COMPLETION_AUDIT_2026_10_09.md`. The earlier 21 official divisions retain their existing evidence.

`cup_competition_registry_2026.csv` records eleven separate cup/UEFA competition identities; no cup entrants are inferred from league membership.

## Offline verification and rebuild

```sh
python data/master/uefa_registry_audit.py
python -m unittest discover -s data/master -p test_uefa_registry.py -v
python data/master/build_uefa_registry.py
python data/master/validate_uefa_master.py --write-report
```

The rebuild uses the checked-in rosters and assignment ledger; it does not browse or refresh season facts. QA checks referential integrity, duplicates, code syntax, original ID preservation, scope completeness, source-to-membership equality and roster counts. It cannot certify future changes or independently validate licensing decisions.

No provider mappings, scanner, API, dashboard or deployment is changed by this data snapshot. No PR merge is authorized.

## User scope revision — 2026-10-09

Excluded AND-0001, AZE-0001, AZE-0002, BLR-0001, POL-0002 and RUS-0001. All 81 remaining divisions are VERIFIED_OFFICIAL, with zero active league blockers. The 1,374 canonical clubs and permanent IDs remain reserved; a club such as FC Andorra may still appear in a retained cross-border league. The exclusion ledger preserves retired roster facts separately. Poland tier 1 remains in scope. Exact canonical competition IDs are filtered at the research population boundary; unresolved provider IDs are never guessed from team country or league name. Provider mapping remains a separate limitation. Portugal cup season confirmation remains outside this six-league removal.
