# Report 3 — Odds movement impact


EXPLORATORY / NO PROVEN EDGE. Flat stake 1 unit, price 1.80–2.20; AH contemporaneous favorite, OU Over. This benchmark is not a validated betting strategy. WR uses winning/losing stake fractions; pushes excluded. CLV unavailable: last observed quote is not a verified closing quote. All times Asia/Bangkok; football-day cutoff 05:00.

|Market|Category|N|WR|ROI|95% CI|
|---|---|---:|---:|---:|---|
|AH|CONTINUOUS_UNCHANGED_LINE|134|52.72%|2.65%|[-12.23%, 17.71%]|
|AH|LINE_DOWN_025|196|46.22%|-6.82%|[-19.88%, 6.36%]|
|AH|LINE_DOWN_050_PLUS|9|37.50%|-21.67%|[-77.78%, 39.56%]|
|AH|LINE_UP_025|129|50.70%|-4.46%|[-18.73%, 9.50%]|
|AH|LINE_UP_050_PLUS|5|42.86%|-13.32%|[-80.00%, 53.36%]|
|AH|REVERSAL_UNCHANGED_LINE|200|52.84%|2.52%|[-9.54%, 14.36%]|
|AH|SAME_LINE_PRICE_DOWN|394|50.79%|-2.05%|[-10.39%, 6.27%]|
|AH|SAME_LINE_PRICE_UP|422|50.93%|-0.18%|[-8.79%, 8.42%]|
|AH|STABLE|278|47.72%|-7.42%|[-17.42%, 2.70%]|
|OU|CONTINUOUS_UNCHANGED_LINE|110|44.04%|-13.49%|[-29.57%, 1.89%]|
|OU|LINE_DOWN_025|126|52.91%|-0.40%|[-14.86%, 14.66%]|
|OU|LINE_DOWN_050_PLUS|3|66.67%|23.13%|[-100.00%, 84.70%]|
|OU|LINE_UP_025|177|58.13%|13.59%|[0.48%, 27.18%]|
|OU|LINE_UP_050_PLUS|5|40.00%|-19.80%|[-100.00%, 60.60%]|
|OU|REVERSAL_UNCHANGED_LINE|161|55.12%|5.48%|[-7.96%, 19.22%]|
|OU|SAME_LINE_PRICE_DOWN|356|49.84%|-4.40%|[-13.87%, 4.32%]|
|OU|SAME_LINE_PRICE_UP|368|50.23%|-1.84%|[-11.01%, 7.59%]|
|OU|STABLE|417|48.11%|-6.83%|[-15.01%, 1.75%]|

Categories use the first AH selected-side line, or OU total. A line move changes the contract, so its normalized share change is not a probability change for the same event. Reversal/continuous categories overlap main categories and require an unchanged line throughout. Raw goal difference, total goals and share movements are retained in movement_features.csv.

Controlled chronological ridge models condition on initial line, odds/share, league, kickoff hour and lead time; setup/decision models instead start with 18-scan prices. Full sample/split sizes and MSE lift are in predictive_validation.json. FT availability at every historical training date is not certified; these are retrospective diagnostics, not historically executable EV bets.

- FIRST_LAST_CONTROLLED / AH / B_PLUS_MOVEMENT_MSE_IMPROVEMENT: N=393, MSE improvement=-0.00241, CI=[-0.04023033794547625, 0.032934672387189515], q=0.9805097451274363, relative lift=-0.07%.

- FIRST_LAST_CONTROLLED / AH / C_PLUS_PAST_SCANS_MSE_IMPROVEMENT: N=393, MSE improvement=-0.10653, CI=[-0.18283593681142063, -0.033493350566441524], q=0.047976011994003, relative lift=-2.98%.

- FIRST_LAST_CONTROLLED / OU / B_PLUS_MOVEMENT_MSE_IMPROVEMENT: N=393, MSE improvement=0.02802, CI=[-0.01561549637521237, 0.06953272899506964], q=0.3094452773613193, relative lift=0.87%.

- FIRST_LAST_CONTROLLED / OU / C_PLUS_PAST_SCANS_MSE_IMPROVEMENT: N=393, MSE improvement=0.00066, CI=[-0.056952239146996285, 0.05541148104467396], q=0.9805097451274363, relative lift=0.02%.

- SETUP_DECISION / AH / B_PLUS_MOVEMENT_MSE_IMPROVEMENT: N=297, MSE improvement=-0.01416, CI=[-0.03157533574219999, 0.004136462127642446], q=0.2538730634682659, relative lift=-0.38%.

- SETUP_DECISION / AH / C_PLUS_PAST_SCANS_MSE_IMPROVEMENT: N=297, MSE improvement=-0.05515, CI=[-0.12209804452355219, 0.010150200069583238], q=0.2538730634682659, relative lift=-1.49%.

- SETUP_DECISION / OU / B_PLUS_MOVEMENT_MSE_IMPROVEMENT: N=297, MSE improvement=-0.00602, CI=[-0.031066088612719974, 0.018623245077781608], q=0.8582375478927203, relative lift=-0.22%.

- SETUP_DECISION / OU / C_PLUS_PAST_SCANS_MSE_IMPROVEMENT: N=297, MSE improvement=-0.04277, CI=[-0.08887765532643013, 0.003503869878093861], q=0.2538730634682659, relative lift=-1.54%.
