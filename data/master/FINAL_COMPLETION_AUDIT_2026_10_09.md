# Football Master Database — completion audit

Date: 2026-10-09. Branch: `feature/league-selection-v1-20261008`. PR #309. Issue #310.

**PARTIAL/BLOCKED — structural QA passes; official confirmation remains incomplete.**

| Metric | Result |
|---|---:|
| Associations covered | 54 |
| Divisions covered | 87 |
| Canonical clubs, including historical/reserved | 1,374 |
| Current memberships / distinct active clubs | 1,285 |
| VERIFIED_OFFICIAL | 81 |
| VERIFIED_SECONDARY | 6 |
| Membership status BLOCKED | 0 |
| Official-confirmation blockers (subset of secondary) | 6 |
| Baseline-secondary official reviews attempted | 66 |
| Baseline-secondary team-by-team official comparisons completed | 60 |
| Earlier official rosters retained | 21 |
| Cup / UEFA identities registered | 11 |
| Cup season-confirmation blockers | 1 |
| Cup entrant rows imported | 0 |
| Provider mapping rows | 0 |

## Corrections and identity safety

- Lithuania: LFF revoked Riteriai TOPLYGA licence on 14 June 2026 and excluded the club, annulling results. Remove its current scoped snapshot membership (1,286 -> 1,285); retain `LTU-RIT` in canonical/assignment ledgers. Earlier participation and historical fixtures are not deleted. This table is a current snapshot, not an opening-day participation ledger.
- Upgrade 60 of the 66 baseline secondary divisions only after complete official roster comparison. Original source names and assigned club IDs remain stable; official spellings are recorded separately per team.
- Three additional verification records (Finland, Northern Ireland and existing Portugal top tier) use complete retrieved official indexed text. The audit states direct-fetch failures separately; no successful HTML retrieval is fabricated.
- Cup identities reuse the eleven previously allocated competition IDs, including `INT-0004` for Conference League. No entrants are inferred from domestic league members.
- Builder uses independent expected team counts when available and carries official-confirmation reasons into coverage output. Validator rejects incomplete evidence, wrong club IDs, invalid provider foreign keys, duplicate cups, inferred cup entrants and stale membership projection rows.
- All 666 pre-existing club IDs/names and their history remain unchanged. Existing competition IDs and legacy numeric tables are preserved.

## Verification actually executed

- `python data/master/build_uefa_registry.py`: completed.
- `python data/master/validate_uefa_master.py --write-report`: PASS, zero errors.
- `python -m unittest discover -s data/master -p test_uefa_registry.py -v`: 21 tests PASS, including byte-identical rebuild test.
- `python -m pytest -q`: 470 tests PASS (full offline scanner/provider/dashboard/master suite).
- `git diff --check`: PASS.
- GitHub Actions: PENDING until the pushed commit is checked; local tests do not imply remote CI PASS.

## Scanner integration safety and limits

Four fixture tests cover England tier agreement, exact historical fixture-ID joins with canonical club metadata, separate cup classification and empty provider mappings. Existing real dashboard JavaScript tests and provider/scanner tests are included in the full offline suite. Valid mock mappings are accepted and nonexistent IDs rejected.

The master is not wired into production league admission. No verified external provider IDs are present in `provider_mappings.csv`, so live mapping coverage and expanded production league selection are NOT certified. Runtime/history/dashboard code is unchanged; the registry must not replace provider fixture IDs or admit leagues automatically. Resolve provider IDs from official provider documentation/catalog snapshots and add reviewed mapping fixtures before enabling production integration. No football API requests, key changes, schedule changes, deployment or merge were performed.

## Remaining official-source blockers

| Competition | Season | Reason / next action |
|---|---|---|
| AND-0001 | 2026-27 | FAF returns an application shell; the complete 2026/27 ten-club roster was not retrieved. Alternate official directory redirects to login; youth rules do not establish senior participants. Retrieve a readable full federation/league season roster or official PDF and compare all clubs before upgrading. |
| AZE-0001 | 2026-27 | PFL returns an application shell. The accessible AFFA table contains historical Inter, Simurg and AZAL and cannot certify 2026/27. The current 12/10 clubs remain unconfirmed. Official indexed selector establishes 2026-2027, but open supplies no roster text. Retrieve a readable full federation/league season roster or official PDF and compare all clubs before upgrading. |
| AZE-0002 | 2026-27 | PFL returns an application shell. The accessible AFFA table contains historical Inter, Simurg and AZAL and cannot certify 2026/27. The current 12/10 clubs remain unconfirmed. Official indexed selector establishes 2026-2027, but open supplies no second-tier roster text. Retrieve a readable full federation/league season roster or official PDF and compare all clubs before upgrading. |
| BLR-0001 | 2026 | ABFF championship endpoints return HTTP 502. An indexed season-54 table is not sufficient to establish the 2026 season. Fallback official page still returns 502; search index supplies only first three clubs, insufficient for all sixteen. Retrieve a readable full federation/league season roster or official PDF and compare all clubs before upgrading. |
| POL-0002 | 2026-27 | Official 1liga homepage/table return HTTP 403. A PZPN season calendar cannot establish all 18 participants. Alternate official season fixture PDF returns 403; indexed fragment is not a complete eighteen-club comparison. Retrieve a readable full federation/league season roster or official PDF and compare all clubs before upgrading. |
| RUS-0001 | 2026-27 | The official Premierliga table presents a robot challenge; search results do not establish all 16 clubs. Official indexed table labels 2025/26; cannot substitute it for 2026/27 roster confirmation. Retrieve a readable full federation/league season roster or official PDF and compare all clubs before upgrading. |

Portugal Taça de Portugal `PRT-0003`: official competition identity registered; 2026/27 season rules remain blocked by FPF 403 access. A readable official calendar/rules document is needed. Cup entrant import is deliberately outside this identity inventory and is not completed.

Promotion/relegation legal history is not independently certified for every club across all 87 divisions. Current complete official rosters confirm participation; they do not prove every historical licensing/promotion decision.

## Per-division evidence

See `research/official_roster_audit_2026_10_09.json`: all 66 baseline secondary divisions have URL/date, original roster, retrieval attempts, full official comparison or specific blocker. `QA_2026.json` records input hashes. No blocked country has been silently skipped.
