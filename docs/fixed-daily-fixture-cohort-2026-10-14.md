# Fixed 15:00 fixture cohort

The 18:00 recovery used an unseen-league priority and produced five new fixtures,
without repeating the 15:00 observation group. This correction freezes IDs from
the earliest successful 15:00 OddsPapi receipt and its retained schedule response.
It never uses fuzzy names, live later fixtures, or newly discovered tournaments
to replace a missing 15:00 population.

October 14's setup queried tournaments 7, 18, 22, 98 and 682. Their original
schedule contains 27 prematch fixtures; 26 first-round quotes satisfy the core
validation gates. The out-of-price-range row remains in raw history and in the
fixed setup population. The setup evidence covers these queried tournaments,
not all 36 discovered fixtures across 12 tournaments. Unqueried discovery rows
remain whole-scope coverage gaps and cannot be claimed as captured setup odds.

All 18:00/21:00/next-midnight followups request the original tournaments still
containing pre-kickoff setup fixtures and persist only the original fixture IDs.
Provider responses are retained unchanged; additional fixtures in those responses
are counted separately. Report every setup fixture with observed core odds,
observed outside-core odds, kickoff passed, provider no-fixture/no-market,
mapping/eligibility failures, API failure, or quota/unqueried status. Passing
kickoff never authorizes an in-play snapshot or retrospective price reconstruction.

A followup is deduplicated after all remaining setup fixtures' tournaments are
queried successfully, not after a handful of unrelated snapshots. The original
18:00 five-fixture receipt stays intact but cannot close the fixed-cohort task.
Real response timestamps and new late receipts remain append-only. No source
price, score, mapping, frozen validation gate or old observation is modified.

Limit the initial 15:00 odds collection to one provider batch (five tournaments),
even when schedule discovery is cached, so its whole population fits one call
per subsequent slot. Existing 8/day, 240/month and 10-account-reserve guards
remain enforced. Larger externally retained cohorts can have explicit quota gaps;
never silently rotate the affordable batch into new leagues. This fixes the
population selection; it cannot guarantee cron punctuality or available markets.

Validation includes all three followup clocks, midnight same-football-day identity,
extra provider fixture exclusion, frozen setup IDs, already-started fixtures,
missing setup fail-closed, account skip reasons, and old unrelated receipt dedupe.
