# October 13 21:00 collection failure

Evidence: Independent Slot Watchdog run https://github.com/meepo1150-code/football-odds-scanner/actions/runs/38410241324 checked out 222d18dd65df98450ac15592c673fee114ecde76 and completed successfully. This certifies execution and persistence, not odds availability.

The primary receipt at 14:04:42 UTC is SKIPPED_QUOTA_HEALTH_UNAVAILABLE: HTTP 500 from the unmetered OddsPapi /account endpoint. The quota health observation at 14:03:44 UTC also records ACCOUNT_UNAVAILABLE / HTTP 500. No metered request was attempted. A provider-side internal error is established; its internal underlying cause is not available in these logs. Earlier 18:00 collection observed 88 requests remaining before two requests; that historical balance is not permission to bypass the current account check.

Propline at 14:04:44 UTC has MASTER_PROVIDER_MAPPING_UNAVAILABLE and http_requests_attempted=0. API_REQUEST_FAILED was a misleading generic wrapper for a configuration gate. There is no Propline provider HTTP response in this attempt. Approved mappings must be verified before this fallback can collect; this change does not invent mappings or enable unreviewed sport keys.

The October 13 research ledger before recovery contains two OddsPapi requests at 15:29 Bangkok and two at 19:21 Bangkok, plus the zero-request Propline failure. The daily cap remains six requests and the monthly research cap 180. Primary transport additionally gates requests against the fresh provider account and reserves before sending, including failed billable calls.

Fix: at most three unmetered account attempts, with 2/4-second backoff only for HTTP 500/502/503/504 or transport failure. Authentication, 429, unknown/malformed quota and persistent outage still fail closed; no cached balance bypass and no retries of billable odds. Sanitized HTTP status/attempt diagnostics are retained in new immutable health receipts. Logs retain both primary and fallback outcomes. Propline reports the actual configuration failure and unknown fixture count. Actions summaries and the dashboard expose health independently from workflow completion.

Regression coverage: transient recovery preserves the original market budget; persistent account failure cannot send odds even with a cached positive balance; 401/403/429 never retry; unmapped fallback makes zero HTTP requests and cannot claim a confirmed empty fixture set. Existing history remains untouched; delayed quotes use their actual fetch times.

Limit: bounded retries improve transient availability but cannot repair a persistent external provider outage. Full odds coverage remains constrained by the unchanged free-tier budget and identity validation. Runtime proof must come from a new real provider response after merge, never from these tests.
