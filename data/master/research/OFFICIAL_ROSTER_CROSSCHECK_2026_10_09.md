# Official-source roster cross-check — 2026-10-09

## Portugal, Primeira Liga 2026/27 (PRT-0001)

Official league standings: https://www.ligaportugal.pt/competition/911/liga-portugal-betclic/round/20262027?tab=general

The official league page explicitly labels the season 2026-2027 and lists 18 clubs. Compared by club identity against the 18 memberships in `uefa_verified_memberships_2026.csv` (PRT-0001), all 18 agree. Names differ only in presentation/abbreviation, e.g. Académico / Academico de Viseu, Marítimo M. / Maritimo, SL Benfica / Benfica, and FC Famalicão / Famalicao. No promotion/relegation mismatch found.

**Outcome:** PRT-0001 is eligible for promotion from VERIFIED_SECONDARY to VERIFIED_OFFICIAL after the generator's source data and coverage ledger are updated together and the full offline build/tests pass. Do not hand-edit generated membership CSV without updating `research/rosters.json` and regenerating outputs.

## England EFL official fixture corroboration

- https://www.efl.com/competitions/efl-championship/ — official EFL 2026/27 match list, including the 9-11 October fixtures, supports the presence of clubs in Championship.
- https://www.efl.com/competitions/efl-league-one/ — official EFL 2026/27 match list, including 10 October fixtures, supports League One club placement.
- https://www.efl.com/news/2026/june/25/the-2026-27-efl-fixtures-are-here/ — EFL confirms fixture publication and competition season.

**Outcome:** These are useful independent corroboration, but no claim of complete 24/24 official cross-check is made here. ENG-0002 and ENG-0003 remain VERIFIED_SECONDARY until every club is reconciled.

## Safeguards

- This file records new evidence only; it does not change source status, memberships, scanner or deployment.
- Official-source verification must be club-by-club, not just a matching roster count.
