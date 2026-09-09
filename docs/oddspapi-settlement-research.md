# OddsPapi result + settlement research contract

This path is research-only.

1. Finished results are harvested only from the same `/fixtures` discovery payload; no fuzzy team-name matching and no extra provider request.
2. A result is accepted only for `statusId == 2` with explicit numeric full-time home/away scores.
3. Historical odds rows join to results only by exact `fixture_id`.
4. Asian handicap and total quarter-lines use the existing exact split-stake settlement engine: FULL_WIN, HALF_WIN, PUSH, HALF_LOSS, FULL_LOSS.
5. Settlement rows preserve both first retained historical price (`opening`) and latest retained price (`latest`) plus price movement. They do not relabel either timestamp as a production execution quote.
6. Every joined/settled artifact remains `promotion_eligible=false`. The 2026 OddsPapi archive is not multi-season and cannot populate the frozen production registry until a preregistered chronological validation is run on adequate data.
