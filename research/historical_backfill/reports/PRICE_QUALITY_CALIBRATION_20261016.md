# AH price quality calibration — 16 October 2026

Cache-only Actions run: https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38827322027
Executed commit: e94565ea1aafd02da2d96af77b717f0cbcae65d3.

## Measured result

**Price Quality Gate PASS. Zero provider/API requests.** Replayed original 10 fixtures
from 10 immutable live raw bodies and verified cache receipt SHA256s. All original
163 COMPLETE line snapshots reproduced byte-for-byte at canonical record level.
46,305 reviewed-AH history entries inspected through the existing normalization path.
All 49 reviewed catalog mappings matched pinned fulltime soccer AH source catalog:
marketId, signed home handicap, home/away outcome IDs, spreads scope, playerProp=false.
Raw bookmaker/market objects expose outcomes only; active state is the individual
history entry's explicit `active` field. No official mainline flag was present.

## Selection contract

All-line extraction and immutable history are unchanged. A separate selector runs
per fixture/bookmaker/slot. Both prices must be finite decimal odds in **[1.80,2.20]**,
active=True, at/before target and strictly before kickoff, each at most 3,600 seconds old.
Market ID and exact signed quarter line must match the reviewed catalog. Invalid,
missing, stale, inactive, future/in-play and conflicting duplicate states fail closed.
Among eligible lines minimize `(home_price-2)^2 + (away_price-2)^2`; tie-break by
absolute price difference, signed line, then market ID. Ranking arithmetic is rounded
to 12 decimal places; source odds and AH lines are never rounded. Label: **BALANCED_LINE**.
No eligible line: **MAINLINE_UNRESOLVED**, with no fallback or invented price.
This is a research selection rule, not proof of the bookmaker's official mainline.

## Counts and observed comparison

- 280 reconstructed candidate line/slot rows evaluated, including unavailable states.
- 163 complete two-sided rows: **23** eligible balanced-range lines, **140** outside range.
- **19 selected** fixture-slot representatives across **10/10 fixtures**; 4 eligible lines
  not selected because another eligible line ranked better.
- **257 rejected** rows = 140 outside price range + 56 stale + 38 inactive/unknown + 23 missing.
- **6/25 slots unresolved**; selected coverage **19/25 (76%)**. No threshold was loosened.
- Compared 14 existing observations at their actual observation timestamps; 11 have
  complete same-bookmaker/exact-AH-line historical comparisons across **9 fixtures**.
  At 10 observation times with an eligible balanced line, the selected line matched
  the observed production line in all 10 cases. This is calibration evidence only.
  The 3 unavailable same-line comparisons are not silently matched to another line.
- Historical vs observed price differences are reported descriptively, not treated
  as automatic errors: provider history is captured state, not a continuous tradability feed.
- Frozen gate: all ten replayed, original 163 unchanged, at least 8 balanced fixtures,
  at least 5 paired fixtures, zero hard selection anomalies, Sporting regression exact,
  raw/cache unchanged. Full policy and evidence: `PRICE_QUALITY_CALIBRATION_20261016.json`.

## Sporting–Arouca regression

19 September 2026 **15:00 Asia/Bangkok**: home AH **-2.00**, away AH **+2.00**,
home odds **1.892**, away odds **1.990**. Both actual history quote timestamps:
**14:34:32.343 Asia/Bangkok**. It is not a 15:00 live observation.
The previous nearest-zero display example is superseded by this balanced selector.

## All calibration targets

All times below Asia/Bangkok. Odds are home / away decimal; line is home perspective.
The two quote times remain independent and are never replaced by the target time.

| Match | Target time | Home AH | Home / away odds | Actual home / away quote time |
|---|---|---:|---:|---|
| Mosta FC — Gzira United FC | 14/10/2026 15:00:00 | MAINLINE_UNRESOLVED | — | — |
| Mosta FC — Gzira United FC | 14/10/2026 21:00:00 | +0 | 1.934 / 1.826 | 14/10/2026 20:23:04 / 14/10/2026 20:23:04 |
| Bandirmaspor — Sivasspor | 13/10/2026 18:00:00 | -0.5 | 2.009 / 1.847 | 13/10/2026 17:54:16 / 13/10/2026 17:44:19 |
| GKS Katowice — Wieczysta Krakow | 12/10/2026 15:00:00 | -0.25 | 1.826 / 2.07 | 12/10/2026 14:48:15 / 12/10/2026 14:48:15 |
| GKS Katowice — Wieczysta Krakow | 12/10/2026 18:00:00 | -0.25 | 1.84 / 2.06 | 12/10/2026 17:30:52 / 12/10/2026 17:30:52 |
| GKS Katowice — Wieczysta Krakow | 13/10/2026 00:00:00 | -0.5 | 2.05 / 1.847 | 12/10/2026 23:33:37 / 12/10/2026 23:33:37 |
| Sporting CP — FC Arouca | 19/09/2026 15:00:00 | -2 | 1.892 / 1.99 | 19/09/2026 14:34:32 / 19/09/2026 14:34:32 |
| Sporting CP — FC Arouca | 19/09/2026 18:00:00 | -2 | 1.877 / 2.02 | 19/09/2026 17:35:54 / 19/09/2026 17:38:37 |
| Sporting CP — FC Arouca | 19/09/2026 21:00:00 | -2 | 1.9 / 1.99 | 19/09/2026 20:52:39 / 19/09/2026 20:52:39 |
| Sporting CP — FC Arouca | 20/09/2026 00:00:00 | -2 | 1.833 / 2.07 | 19/09/2026 23:54:15 / 19/09/2026 23:54:15 |
| AFC Wimbledon — Milton Keynes Dons | 17/09/2026 15:00:00 | +0.25 | 1.826 / 2.08 | 17/09/2026 14:01:54 / 17/09/2026 14:01:54 |
| AFC Wimbledon — Milton Keynes Dons | 17/09/2026 18:00:00 | MAINLINE_UNRESOLVED | — | — |
| AFC Wimbledon — Milton Keynes Dons | 18/09/2026 00:00:00 | +0 | 2.009 / 1.877 | 17/09/2026 23:59:04 / 17/09/2026 23:32:55 |
| Levante UD — Athletic Bilbao | 16/09/2026 15:00:00 | +0.25 | 2.02 / 1.909 | 16/09/2026 14:52:28 / 16/09/2026 14:52:28 |
| Levante UD — Athletic Bilbao | 16/09/2026 18:00:00 | MAINLINE_UNRESOLVED | — | — |
| Levante UD — Athletic Bilbao | 16/09/2026 21:00:00 | MAINLINE_UNRESOLVED | — | — |
| Grasshopper Club Zurich — FC Sion | 15/09/2026 15:00:00 | MAINLINE_UNRESOLVED | — | — |
| Grasshopper Club Zurich — FC Sion | 15/09/2026 18:00:00 | +0.5 | 2.04 / 1.869 | 15/09/2026 17:15:12 / 15/09/2026 17:15:12 |
| Red Star FC — FC Metz | 14/09/2026 15:00:00 | -0.25 | 2.08 / 1.819 | 14/09/2026 14:14:41 / 14/09/2026 14:09:42 |
| Red Star FC — FC Metz | 14/09/2026 18:00:00 | -0.25 | 2.1 / 1.806 | 14/09/2026 17:54:24 / 14/09/2026 17:54:24 |
| Red Star FC — FC Metz | 14/09/2026 21:00:00 | MAINLINE_UNRESOLVED | — | — |
| Red Star FC — FC Metz | 15/09/2026 00:00:00 | +0 | 1.833 / 2.07 | 14/09/2026 23:57:54 / 14/09/2026 23:57:54 |
| SC Paderborn 07 — TSG Hoffenheim | 20/09/2026 21:00:00 | +0.75 | 2.009 / 1.917 | 20/09/2026 20:33:47 / 20/09/2026 20:40:28 |
| SC Paderborn 07 — TSG Hoffenheim | 21/09/2026 00:00:00 | +0.75 | 1.892 / 2.029 | 20/09/2026 23:48:55 / 20/09/2026 23:54:53 |
| Olympiacos Piraeus B — Athens Kallithea FC | 14/10/2026 15:00:00 | +0.5 | 1.854 / 1.9 | 14/10/2026 14:49:12 / 14/10/2026 14:49:12 |

## Boundaries

No raw response, Production data, collector, scheduler or dashboard modification.
No merge/deploy. Manual only, exact research ref and historical-research environment.
Raw/cache before/after hashes and observed comparisons are in the JSON evidence.
Expansion is gated again in the workflow and entrypoint, bound to exact manifest,
catalog and immutable cache; the original ten must be cache hits, never refetched.
A new expansion run is reported separately and is not implied by this calibration PASS.
