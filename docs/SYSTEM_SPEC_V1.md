# Football Odds Scanner — System Spec V1

## Objective
Build a multi-league, multi-market football research and scanning system that identifies validated market patterns and returns at most five current opportunities. The system must prefer **no selection** over weak or forced selections.

## Core philosophy
1. Research first, production second.
2. Filter/reject before ranking.
3. Never force Top 5. Output may be 0–5 selections.
4. Opening market structure defines the historical pattern; current price determines whether the pattern is still tradable.
5. Every claim of edge must survive chronological validation, stability checks, multiple-testing controls, and realistic Asian-market settlement.
6. Rankings only order already-qualified candidates. Ranking must never rescue a failed candidate.

## Markets in scope
Primary V1 markets:
- 1X2
- Asian Handicap (AH)
- Asian Total / Over-Under (OU)

Future optional markets:
- BTTS
- Draw No Bet
- Double Chance
- first-half markets

## Market pattern identity
A pattern is described by a structured combination such as:

`league_scope × favorite_side × ah_line × ah_price_band × ou_line × ou_price_band × 1x2_probability_band × movement_state`

Example:

`GLOBAL | HOME_FAVORITE | AH=-0.75 | AH_PRICE=1.90-2.00 | OU=2.75 | OVER_PRICE=1.85-1.95 | HOME_FAIR_P=0.58-0.62`

Patterns may later be classified as:
- GLOBAL
- LEAGUE_SPECIFIC
- UNSTABLE
- REJECTED

## Price policy
### Research layer
Do not discard data only because odds fall outside the tradable range. Default research range should be broad enough to discover whether edge exists.

Suggested research range:
- 1.50–2.50 for AH/OU side prices

### Production layer
Default tradable current-price gate:
- **1.80 <= decimal odds <= 2.20**

This is a gate, not a bonus. Odds near 2.00 do not automatically receive a higher score.

A candidate is rejected if current price removes the estimated positive EV even when the historical pattern itself is valid.

## De-vig and market expectation
Raw `1 / odds` is not treated as fair probability when both market sides are available.

For two-way AH/OU markets:
1. Convert both prices to raw implied probabilities.
2. Normalize both to remove overround using proportional de-vig as the V1 baseline.
3. Store overround separately.

For 1X2, normalize H/D/A together.

## Asian settlement
Backtests must settle quarter lines correctly.

Examples:
- AH -0.25 = half stake 0, half stake -0.5
- AH -0.75 = half stake -0.5, half stake -1.0
- OU 2.25 = half stake 2.0, half stake 2.5
- OU 2.75 = half stake 2.5, half stake 3.0

Supported settlement outcomes:
- FULL_WIN
- HALF_WIN
- PUSH
- HALF_LOSS
- FULL_LOSS

ROI must use actual stake return, not binary win/loss labels.

## Data gate
A current fixture is eligible only when the required fields for the market being evaluated are present and fresh enough:
- league
- kickoff timestamp
- opening market line
- opening prices for both sides
- current market line
- current prices for both sides
- source timestamp/provenance

Missing or stale data -> `REJECT_DATA`.

## Historical sample gate
Initial thresholds are conservative defaults and must be configurable.

Suggested starting values:
- global train N >= 500
- league-specific train N >= 200
- validation N >= 100
- holdout N >= 100 where practical

Smaller samples remain research-only and cannot become production-qualified.

## Edge gate
For a market outcome, calculate historical/model probability or expected return against current de-vig market expectation.

Initial production minimum:
- probability edge >= +3 percentage points when probability is a valid representation
- or equivalent return edge for quarter-line markets

Suggested labels:
- >= +3pp: minimum edge
- >= +4pp: medium
- >= +5pp: strong

## EV gate
The final execution decision uses the current price.

For binary-style outcomes:
`EV = model_probability * current_decimal_odds - 1`

For Asian quarter-lines use expected settled return across FULL_WIN / HALF_WIN / PUSH / HALF_LOSS / FULL_LOSS.

Initial production thresholds:
- minimum EV >= +3%
- strong EV >= +5%

If the line/price moves and EV falls below threshold -> `REJECT_PRICE_MOVED`.

## Chronological validation
No random train/test split.

Required sequence:
- TRAIN
- VALIDATION
- untouched HOLDOUT

A production candidate must have positive direction in each required split. A large train gain cannot compensate for a negative holdout result.

## Season stability gate
A pattern must not depend on one anomalous season.

Initial checks:
- positive ROI in >= 60% of evaluated seasons
- median season ROI > 0
- no single season contributes > 50% of total historical profit
- no severe sign flip in recent seasons

## Cross-league stability gate
For a GLOBAL pattern:
- it should remain positive across multiple leagues
- no single league should dominate total profit excessively

If the effect is concentrated but repeatable in one league, classify it as `LEAGUE_SPECIFIC` rather than forcing global status.

## Multiple-testing gate
The engine may evaluate thousands of combinations, therefore raw p-values or best historical ROI are insufficient.

Required controls:
- false-discovery-rate correction (Benjamini-Hochberg baseline)
- untouched holdout
- minimum effect size
- minimum sample size
- bootstrap/permutation robustness where computationally feasible

## Robustness gate
A valid pattern should not disappear when the arbitrary bin boundary moves slightly.

Test neighboring structures/buckets, for example:
- odds band +/- 0.05 or 0.10
- adjacent AH/OU line where logically comparable
- nearby probability band

Patterns that work only in a razor-thin bucket receive an overfit penalty or rejection.

## Movement gate
Opening structure identifies the historical pattern. Current market state determines execution.

Track at minimum:
- AH line movement
- AH price movement
- OU line movement
- OU price movement
- 1X2 shortening/drifting where available

Movement classes:
- SUPPORTIVE
- NEUTRAL
- EDGE_REDUCED
- EDGE_GONE

`EDGE_GONE` -> reject.

## Risk gate
Qualified patterns should also report:
- max drawdown
- longest losing streak
- return variance
- worst season
- recent-period performance

Risk does not create edge; it only penalizes or rejects otherwise-qualified patterns.

## Correlation / duplicate exposure gate
Do not treat several bets from one match as independent when they arise from the same market structure.

Default production policy:
- maximum 1 primary selection per match
- optional second selection only if explicitly proven to add independent EV

If several markets qualify, select the one with the strongest validated execution value after risk adjustment.

## Candidate statuses
- `REJECTED`
- `WATCHLIST`
- `QUALIFIED`
- `HIGH_CONFIDENCE`

## Production pipeline
`ALL FIXTURES`
-> Data Gate
-> Tradable Price Gate
-> Match to validated historical pattern
-> Sample Gate
-> Edge Gate
-> EV Gate
-> Train/Validation/Holdout Gate
-> Season Stability
-> Cross-League Stability
-> Multiple Testing
-> Robustness
-> Movement
-> Risk
-> Correlation/Deduplication
-> Rank qualified candidates
-> Return **0–5** selections

If zero survive, output:

`NO QUALIFYING BETS`

## Ranking
Ranking applies only after all hard gates pass.

Initial conceptual score:

`quality_score = edge_strength + ev_strength + statistical_confidence + sample_strength + season_stability + league_stability + clv_quality - robustness_penalty - risk_penalty`

Exact weights must be validated, versioned, and never optimized against the untouched holdout.

## Top-5 rule
- Maximum display count: 5
- Never backfill failed candidates
- No minimum selection count
- A day with 0 selections is valid and expected

## V1 implementation order
1. Extend normalized schema with AH and OU opening/current/closing fields.
2. Implement exact Asian settlement engine.
3. Build joint market-structure pattern keys.
4. Add multi-league dataset adapters.
5. Add train/validation/holdout pattern research.
6. Add season + league stability reports.
7. Add multiple-testing + robustness audit.
8. Build validated-pattern registry.
9. Replace legacy 1X2 scanner with production Market Pattern Scanner.
10. Dashboard exposes funnel counts, reject reasons, qualified candidates, and Top 5.

## Legacy P1 status
The existing 1X2 bucket engine is retained as a pipeline/data-validation prototype. Its candidates are not production selections and must not be promoted directly into the final scanner.