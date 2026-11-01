# Report 5 — Schedule comparison


EXPLORATORY / NO PROVEN EDGE. Flat stake 1 unit, price 1.80–2.20; AH contemporaneous favorite, OU Over. This benchmark is not a validated betting strategy. WR uses winning/losing stake fractions; pushes excluded. CLV unavailable: last observed quote is not a verified closing quote. All times Asia/Bangkok; football-day cutoff 05:00.

Operational window: scheduled time through +15 minutes, entry at actual receipt. B is therefore an 18:15-deadline experiment, NOT an exact-18:00 decision. No substitute from later scans. A/C enter first available scheduled observation; B enters at 18; D first observation in T-3 to T-1, fixed before outcomes.

|Strategy|Market|Available fixtures|Bets with FT|WR|ROI|Profit|Max DD|Longest loss run|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|A|AH|1586|1516|50.34%|-2.40%|-36.39600000000001|63.525499999999994|13|
|A|OU|1586|1537|50.70%|-2.34%|-36.00600000000001|71.86|8|
|B|AH|1185|1111|49.85%|-3.12%|-34.69100000000001|59.25000000000003|15|
|B|OU|1185|1130|50.93%|-1.78%|-20.156500000000005|46.84700000000004|8|
|C|AH|1548|1479|49.94%|-3.04%|-44.91100000000001|66.55250000000004|13|
|C|OU|1548|1498|50.60%|-2.48%|-37.13250000000001|70.29099999999997|8|
|D|AH|1273|1192|50.50%|-1.98%|-23.57800000000001|49.20050000000001|8|
|D|OU|1273|1210|49.91%|-3.57%|-43.23700000000001|68.68300000000002|8|

A opportunities absent from B: 401 fixtures (coverage opportunity, not proof of profitable missed bets). Setup + decision pairs: 1066.

|Kickoff group|Population|18 receipt by 18:15|Both 15 and 18|New 18 scan by exact 18:00|
|---|---:|---:|---:|---:|
|00_03|578|390|342|0|
|21_00|741|501|461|0|
|18_21|426|274|244|0|
|BEFORE_18|72|0|0|0|
|03_06|20|20|19|0|

03–06 group crosses the 05:00 football-day boundary; actual fixture day controls receipt lookup. Risk metrics are descriptive and sort tied kickoff fixtures by ID; bankroll settlement timestamps are not available. Missing FT remains in coverage but not in ROI. 30-minute sensitivity, paired B-A results and full request ledger are in 05_schedules.json.

Planned round counts A/B/C = 30/14/21 per week. Equal-cost B saving = 53.33%, C = 30%; these are not measured billable savings. Recorded requests may be incomplete and quota skips distort observed costs. No provider requests were made by this study.
