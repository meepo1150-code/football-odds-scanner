# Football Master Registry — scope 2026-10-08

## Authority

`uefa_55_division_scope.csv` is the latest user-approved scope: **54 associations and 87 domestic divisions**. The historical filename contains 55; do not infer row count from it. Liechtenstein has no domestic league in this scope; retain its club identities for cross-border membership. Earlier 21/28-country selections and England tiers 5–6 are superseded for this task. Existing out-of-scope IDs/data remain reserved, not deleted.

This snapshot covers domestic league membership only. The `domestic_cup` flags in the scope remain future policy metadata; cup draws and international competitions are not part of the 87-division deliverable. Russia's domestic inclusion is not a statement about UEFA competition eligibility.

## Permanent IDs

- Country: three uppercase letters, following this registry (including ENG/SCO/WAL/NIR and KOS; not strictly ISO).
- Competition: COUNTRY-4-digit sequence. Existing IDs are reused; tiers 1–4 use the existing country sequences. IDs remain stable when league sponsors change.
- Club: COUNTRY-3 uppercase letters, unique within registry country. Existing codes are never reassigned. New codes are reserved in `research/club_assignments.csv`.
- Membership: season + competition_id + club_id. League changes never change club ID.
- INT is a competition grouping, not a country.

## Cross-border and legacy exceptions

Vaduz reuses **LIE-VAD** in the Swiss association. FC Andorra receives an **AND-** ID for Spanish league membership. Existing English-affiliated Welsh clubs retain their issued ENG- codes (Cardiff, Swansea, Wrexham, Newport), Monaco retains FRA-MON, Derry retains IRL-DER, and The New Saints retains WAL-TNS. Those inherited registry prefixes must not be interpreted as proof of physical location. This is an explicit compatibility exception to the home-country rule; silently changing them would break the user's ID-reuse requirement.

The `country_id` of a club means its historical registry namespace; the membership `country_id` means league association. They may differ. A future geographical field should be separate, not a renumbering migration.

GIB-BRU (Bruno's Magpies) is retained as a reserved duplicate identity redirect to GIB-FCB (FCB Magpies). Only GIB-FCB receives current membership. Both historical codes remain available. AFC Wimbledon is ENG-WIM, not the separate historical Wimbledon FC code ENG-WAA. Reserve sides admitted to senior divisions have separate IDs from their first teams.

## Integrity

No provider IDs are embedded in permanent IDs. Do not infer membership from the historical seed. Unknown future rosters must be marked BLOCKED after fallback attempts, with reason/source attempts recorded; never invent clubs to satisfy a target count. The present snapshot has a retrieved source roster for all 87 divisions, with evidence quality separated in coverage.
