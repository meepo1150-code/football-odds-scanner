# Retired FT recovery: 13 October 2026

Five fixtures from 26 September were manually reviewed against SoccerAssociation's 2026 Ettan round 24 tables and the retained original FotMob response. Both independent hosts agree on home/away, date and regulation-time final score. These are tier B sources, not official federation evidence.

The original FotMob response was retrieved on 30 September; today's verification timestamp is distinct. The batch retains source event IDs, original fetch time, response path, SHA-256, raw status and source spellings. All five statuses are FT, period length 45, not cancelled or awarded. Exact UTC kickoff agrees with the historical snapshot. No odds requests or guessed canonical identities are used.

| Historical identity | FT | FotMob event |
|---|---|---|
| Jarfalla – Eskilstuna | 2–4 | 5127598 |
| Sollentuna – Stockholm Internazionale | 1–2 | 5127602 |
| Rosengaard – Hassleholms | 2–1 | 5127945 |
| Laholms – Aatvidabergs | 1–2 | 5127947 |
| Utsiktens – Jonkopings Sodra | 3–0 | 5127951 |

Stockholm Internazionale is FC Stockholm: the official club information at https://www.fcsthlm.com/foreningen identifies Football Club Stockholm Internazionale and the first team in Ettan Norra. Other source spellings are preserved alongside reviewed historical names; this batch does not add automatic fuzzy aliases.

Historical recovery does not reapprove these competitions for future odds collection. Original evidence and snapshots are untouched. The existing fail-closed importer and exact fixture identity validator apply. After merge, the free-result workflow must demonstrate five additions, statistics recomputation and deployed dashboard consistency; merge alone is not runtime verification.

Review also found a provenance loop bug: provider/canonical metadata came from the last validated snapshot when expanding duplicate fixture identities. The importer now resolves metadata per accepted fixture ID; a regression covers two namespaces plus an unrelated last snapshot. Scores and raw evidence are not rewritten.

Existing WEB_EVIDENCE rows with the same reverified score can have only known provider/canonical/team metadata corrected. Each complete previous row and actual correction timestamp is appended to web_result_provenance_corrections.jsonl before derived-cache changes. Unknown IDs are not filled, trusted other providers are not changed, and repeat imports add no duplicate corrections.
