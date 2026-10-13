# Daily midnight collection

Effective football day October 13, 2026: canonical targets are 15:00, 18:00, 21:00 and next-day 00:00 Asia/Bangkok every day (28 per complete week). The first additional weekday target is October 14 00:00 Bangkok, equivalent to October 13 17:00 UTC, belonging to football day October 13. Legacy dates before October 13 retain their existing slot definitions. Existing stored receipts and prices are not rewritten.

Both canonical collector entry workflows wake at UTC 17:00 on weekdays as well as weekends. The primary heartbeats and independent watchdog now cover weekday midnight through the existing 150-minute recovery window. Shared concurrency and exact completed-slot evidence prevent duplicate collection. GitHub cron timing is best effort; snapshots retain actual observation time.

The existing allocator now applies its four-slot-day rule every day: normally one market batch per attempt, up to five approved competitions, with room for fixture-discovery overhead. The limits remain six research requests per UTC day / 180 per UTC month plus the fresh provider-account gate. More rounds trade off breadth per round. This is not an increase in API allowance.

October 13 already consumed six research requests before this change. The first midnight check may therefore report SKIPPED_RESEARCH_REQUEST_BUDGET rather than collect new odds; Bangkok midnight does not reset the UTC ledger (07:00 Bangkok does). The schedule will still check and persist honest health evidence. No historical or in-play price is substituted for a missing pre-match quote.

Validation covers every weekday midnight's date/football-day identity, UTC cron coverage, heartbeat coverage, completed-slot deduplication, expired-window no-fetch behavior, weekday/weekend four-slot budgeting, and legacy schedule retention. Dashboard and audit configuration display the new daily midnight schedule.
