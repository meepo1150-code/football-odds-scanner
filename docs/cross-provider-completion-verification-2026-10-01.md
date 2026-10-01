# Completion verification — cross-provider identity, 1 October 2026

PR235 merged as bc655560b9d41612752b54ace13ca41e3826b751. Full local suite341 passed. GitHub full-suite PR run36877609149 and main run36878001776 completed SUCCESS, as did independent confirmation. Derived stats run36878001678 completed SUCCESS.

Independent slot recovery run36878001763 executed at21:39 Bangkok: PinnWire persisted cooldown respected with ZERO requests; validated PropLine/Pinnacle produced7 pre-match observations. This run was push-triggered to validate the new workflow; future cron punctuality is not yet proven. Shared collector lock and attempt-gate regressions pass.

Actual deployed manifest run36878162875/source f9d9c4c35a8c9605de20a43c95508790c6d06b19. Downloaded public HTML, raw snapshots, stats, operational audit, canonical and dashboard verified results, and conflict ledger. Executed deployed pure JavaScript assertions:8 verified bridges;76 current-day match groups;90 observations;352 settled/330 core;86 quarantined; Finland source results collapse to one canonical ID; AH -1.5 FT1–0 remains FULL_LOSS. PASS.

Direct browser verification on the deployed site: Germany–Serbia exactly ONE card,3 scans09:40/17:49/21:39, prices1.952→1.885→1.862 at AH-2; providers labeled. September29 selection: Finland–Belarus exactly ONE card,FT0–0,AH-1 shows underdog price win;3 trusted pre-match observations; legacy @4.xx and post-kickoff quote absent. Stats panel visibly352 settled/330 core/1226 clean/86 quarantine/schema2.7. Browser coverage is scoped to these flows; generated audit browser_verified=false remains because no persistent automated browser job was added.

## Data accounting

|Metric|Before this change|Verified deployed after|
|---|---:|---:|
|Raw snapshots|1305|1312|
|Verified snapshots|1219|1226|
|Quarantined snapshots|86|86|
|Recovered legacy prices|0|0|
|Current-day observations|83|90|
|Current-day distinct observation timestamps|2|3|
|Current-day verified match groups|76 (83 separate source IDs)|76 (83 source IDs grouped)|
|Settled canonical statistical fixtures|353 provider-ID rows|352 unique verified matches|
|Core-price settled fixtures|331 provider-ID rows|330 unique verified matches|
|Movement fixtures|110|117|
|Numeric movement deltas|652|684|
|Raw unresolved provider IDs|591|591|
|Canonical unresolved matches|not deduplicated|584|
|Retired unresolved|439|439|
|Active matured unresolved at21:40|80|80|
|Future/recent canonical unresolved|72 source IDs|65 matches|

The seven missing-ID reduction is identity deduplication, NOT seven recovered results. One settled reduction removes duplicate Finland–Belarus. Raw evidence/results were not deleted. No source quota reset, odds, timestamp or score was invented.

## Final operational matrix

|Component|Status|Before → after|Evidence|Remaining blocker|Next automatic action|
|---|---|---|---|---|---|
|Cross-provider identity|GREEN for verified scope|Split/duplicate →8 verified bridges|Artifact+actual browser+regressions|Other league/name mappings remain deliberately unmerged|Rebuild bridge from each current raw set|
|AH/O-U statistics|GREEN for verified scope|Duplicate N →one canonical settled match|352/330, settlement+O/U denominator tests|Missing outcomes still excluded; sample bias remains visible|Rebuild after observations/results|
|Movement|GREEN for verified scope|110→117 match histories|684 deltas, live3-scan card|Unverified identities not joined|Rebuild after scans|
|Current collection/fallback|PARTIAL|PinnWire429 →PropLine7 usable quotes|Actual runner with0 PinnWire requests|Fallback covers only7 of76 observed matches|Collect bounded next slot|
|Schedule reliability|PARTIAL|Missing primary round →independent recovery path works on push|Run36878001763, shared-lock/gate tests|GitHub cron timing still external and future cron execution unverified|Offset scheduled checks; skip completed slots|
|PinnWire|WAITING_EXTERNAL_DATA|429→cooldown correctly honored|0 requests21:39|Provider rate limit|Eligible request after cooldown; not guaranteed reset|
|OddsPapi|QUOTA_AVAILABLE; current feed unqualified|Latest account247/250 remaining|13:02 UTC quota report|Current quote availability not proven by quota|Budget-aware existing calls|
|FT/daily sync|PARTIAL|Free paths operating, backlog persists|Latest scheduled free-result report+canonical store|80 active matured,API-Football account suspended|Free exact/verified-identity backfill; revalidate and rebuild|
|Legacy PropLine recovery|WAITING_EXTERNAL_DATA|84 legacy still quarantined,0 recovered|Quarantine preserved|Verified historical prices unavailable|Existing recovery review, never fabricate|
|Forward validation|COLLECTING|10/4/0 unchanged|min150 gates preserved|Future real outcomes|Paper collection/settlement;no promotion|
|Dashboard|GREEN for tested flows|Duplicate cards→canonical timelines,correctN|Live browser and deployed artifact assertions|Exhaustive interaction coverage not claimed|Deploy after successful data jobs|

No execution-ready provider or betting edge is asserted. PAPER_RESEARCH_ONLY remains.
