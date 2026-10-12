# Verified Master scope for future quotes

The old forward filter removed only six reviewed divisions. The saved discovery target file still admitted Germany 3. Liga and five cups without an accepted Master mapping. PropLine's catalog/error fallback could also call unreviewed sport keys. The forward filter now requires an accepted namespaced provider competition ID in the approved registry before odds requests.

The registry is **81 divisions + 8 domestic cups + 3 UEFA club competitions = 92 mappings**. The three UEFA rows are Champions League, Europa League and Conference League. This is the actual content of the previously approved 11-row cup registry, not 11 domestic cups. Nations League, other national-team events, additional cups and other countries are not implicitly included. Country conflicts and conflicting canonical IDs are rejected. Provider category aliases come only from the reviewed catalog snapshot.

Existing discovery replay: 54 original targets; 53 after the old six-division exclusion policy; 47 with verified active Master mappings. The additional rejected targets are Germany 3. Liga, Norway NM Cup, Denmark DBU Pokalen, Switzerland Schweizer Cup, Scotland Challenge Cup and Romania Cup. The current discovery file is a subset of the approved registry; this release does not promise a 92-competition full-market scan under a limited rotating-cohort quota.

## Producer enforcement

- Europe discovery, Pinnacle collection and the mainline observer share the strict filter before odds batch requests.
- PropLine has no accepted Master sport-key mapping. Its live catalog and static error/empty fallback therefore produce no HTTP requests until verified mappings exist. Accepted catalog keys and normalized rows are rechecked by ID. Catalog failure can never re-enable the old unreviewed sports tuple.
- PinnWire has no verified league mapping; live global prematch collection/probe is blocked before HTTP. Future mapped payloads must also pass their league ID check.
- 5Dollar live Research V2 has no verified competition mapping and stops before fixture discovery or per-fixture odds. Future mapped fixtures are checked before odds requests.
- Singapore Pools live Research V2 has no verified competition ID mapping and stops before fetching markets.
- Daily fixture/result sync is currently local-only metadata, not odds collection. Historical FT recovery and archives remain available for prior identities and do not inherit the new quote allowlist.

This trades fallback coverage for verified scope. Unsupported providers display `MASTER_PROVIDER_MAPPING_UNAVAILABLE`; they are not reported as successful empty-football-day receipts. Existing quotes, results, fixture IDs, historical scope and frozen validation data remain intact. No team-name or league-name similarity authorizes a mapping.

## Additional FT population correction

The existing derivative-market regex over-escaped parentheses, so `China (Corners)–Maldives (Corners)` (`pinnwire:1637244651`) appeared as a missing normal football FT. Corrected literal-parenthesis matching excludes corner/booking/card fixture derivatives from normal football settlement, discloses the excluded count in the report and dashboard, and retains the raw observation. It does not fill the derivative with a football score. The stored eligible-football rebuild is 783/1,030 = 76.02% FT, with 247 eligible groups without verified FT. This differs from the previous 783/1,031 solely because one openly reported non-football derivative was excluded; the settled match population is unchanged.

Offline evidence is in `reports/master_allowlist_preflight.json`, including per-day/provider replay, excluded IDs, producer gates, preserved artifact hashes and coverage limitations. The source/gate tests cover ID namespaces, wrong country, missing IDs, unknown providers, zero HTTP requests, failed-catalog fallback, quarter settlement and archives. The required live observation and independent browser inspection remain separate acceptance gates; this release does not close the full production audit or claim movement edge.
