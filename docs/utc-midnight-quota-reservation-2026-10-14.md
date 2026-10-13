# UTC research quota reservation

## Confirmed incident

Main inspected: eb23f842a557cd3038353d42d1ffd1fb408134b7. No AGENTS.md found.
The project instructions attachment predates the current collector; current main
and the user's 6/UTC-day and 180/UTC-month limits govern this change.

Watchdog run https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38439011217
completed successfully at 00:29 Bangkok on October 14. Its receipt reports
SKIPPED_RESEARCH_REQUEST_BUDGET: research usage was 6 on October 13 UTC (82
month-to-date). The 15:00, 18:00 and 21:00 collectors each used two requests.
There were 28 approved fixtures in saved schedule evidence and no new midnight
quotes. A future reservation cannot retrospectively restore these quotes.

## Policy and behavior

- Bangkok 15/18/21/00 are UTC 08/11/14/17 on ONE UTC quota date. The midnight
  observation still belongs to the preceding football day.
- Reserve one market request for every future UTC slot. Before preparation,
  also reserve one fixture discovery request. Manual/recovery use only surplus.
- Allow one odds batch per canonical slot (five provider tournament IDs). A
  cache miss permits one fixture discovery plus one odds batch, within all limits.
- Reserve five requests per future UTC day through month end. 31 * 6 exceeds
  180; optional breadth must yield to future discovery/observation capacity.
- The shared account guard remains authoritative. Account capacity required by
  future slots is protected; the current canonical slot can consume its share.
- In Actions, refresh current main ledgers and durably publish a conservative
  run grant BEFORE billable transport. The isolated-index fast-forward commit
  changes only the reservation file. A losing push refreshes and rechecks;
  persistence failure authorizes zero billable HTTP calls.
- Count grants once, including cancelled runs and failed requests; final slot
  receipts linked to a grant do not count again. Unused granted capacity is not
  refunded without provider evidence. Report actual transport attempts separately.
- Verify the UTC date and grant ceiling before each billable request. /account
  remains unmetered. No automatic odds retry, no historical price recreation.
- SKIPPED_QUOTA is a control warning with zero API errors. An HTTP/API failure
  remains separately reported. Account health unavailable is still an unavailable
  health probe, not evidence of exhausted quota.
- Preserve divergent raw observations and slot receipts, rather than replacing
  an earlier record with the same identity and timestamp.

## Fallback and limitations

All OddsPapi collector entry points share research-v2-collectors concurrency and
stage the grant ledger through the exact-record persistence union. Public result
recovery consumes zero OddsPapi research requests. Execution registry lazy gates
and frozen validation gates are unchanged.

Propline has no verified competition entries in the current master mapping and
no retained authoritative catalog-to-canonical mapping evidence was found. Do
not guess bindings from historical key names. Keep MASTER_PROVIDER_MAPPING_UNAVAILABLE
and zero provider HTTP calls until reviewed evidence exists. This change makes
no Propline mapping claims.

Reservations protect request capacity, not provider availability, fixture odds,
full 92-competition coverage, cron punctuality, or a successful quote on every
slot. When a day is already at six, the only permissible result is quota skip.
Unused grants can reduce breadth; this conservatism prevents overspend after a
cancelled runner. Validation covers reservation, durable persistence, UTC/month
boundaries, manual/recovery yielding, exhaustion, and non-overwriting history.
