# Scan compatibility and non-destructive scope adoption

Audit source: main commit `3189c622970cb9c8ace8c02998352f7176164eca`, football day 2026-10-11 (Asia/Bangkok). No provider requests made for this audit; saved scan records were inspected read-only.

Today's saved Pinnacle research archive contains 70 observations: 40 Oddspapi and 30 PropLine. Four Oddspapi observations belong to Poland 1. Liga, participant competition ID 229 / canonical excluded division POL-0002. These four are historical evidence, not deleted or rewritten. Future requests must exclude this tournament before budget rotation or odds batches. Three further Oddspapi observations belong to Germany 3. Liga, which is outside the current master roster scope but was NOT cancelled by the user; it is not silently removed. The other 33 Oddspapi observations have active canonical competition bindings.

The separate mainline archive contains 31 observations for today's Big-5 leagues; all have active canonical competition bindings. The 30 PropLine observations lack accepted provider-to-canonical competition IDs; they remain valid old-format records, not falsely certified canonical mappings. Provider IDs are never reused across namespaces. Today's local daily fixture records preserve their old fixture IDs even where canonical metadata is missing.

Adoption changes add canonical identity fields to new Oddspapi snapshots without changing fixture IDs, teams, prices, kickoff, source semantics, observed timestamps or validation flags. Six explicit user exclusions have reviewed Oddspapi tournament IDs and exact country/name evidence from the saved full provider catalog. Country-qualified equivalent labels can be rejected across providers; a generic Premier League/1. Liga label or unknown foreign provider ID is not guessed. Missing metadata remains unresolved, not falsely identified.

Oddspapi target batches are filtered before odds calls. FiveDollar per-fixture calls check available league/country metadata before requesting odds; PropLine sports discovery applies reviewed country/name exclusions before per-sport odds requests. Payload-side scope checks remain a second guard. Legacy archive files, results, joins and patterns are not replaced. Derived active-scope research views may exclude cancelled league observations without deleting their raw evidence.

The original 54-row Europe target document is preserved; effective requests exclude Poland 1. Liga, leaving 53 entries. Frozen ten-league research targets remain ten; the cancelled leagues are not part of those ten. Other outside-master competitions are not automatically treated as poor-quality leagues or cancelled. No API keys, schedules, odds-price gates or production patterns changed.

Compatibility tests and final CI for this adoption commit are recorded in PR #309. A successful identity migration does not establish a betting edge or live market availability. The old production pattern registry remains unchanged.


## 2026-10-12 follow-up: strict allowlist migration preflight (Issue #323)

**Decision: NO-GO for switching the production scanner to strict master-only mode yet.** This is a static, read-only preflight against the current repository and existing saved evidence; it is **not** a complete multi-day dry run, nor proof of live odds coverage. No metered requests were sent.

- **Authority:** The active roster is 50 associations / 81 UEFA domestic divisions, with 11 separately registered cup identities. The superseded 54/87 target is not the production allowlist. `config/league_selection_v1.json` is an older broader policy (including Brazil, Japan, South Korea, and other-world conditional selections); it must not silently override the revised 81-division master. Whether non-European competitions should be newly excluded from live collection is a production policy change, not a historical data purge.
- **Identity mapping:** The final master completion audit reports 92 reviewed Oddspapi competition bindings and 1,203 active club mappings. This proves catalog identity, **not** odds availability for each league, and does not authorize reusing Oddspapi IDs for PropLine or any other provider.
- **Actual saved sample, 2026-10-11:** 40 Oddspapi observations = 33 with active canonical bindings + 4 explicitly cancelled Poland 1. Liga + 3 Germany 3. Liga outside the current master. Another 30 PropLine observations lack accepted provider competition IDs. Separately 31 Big-5 mainline observations have active canonical bindings. These are **observations**, not unique fixtures; do not extrapolate percentages to all dates/providers.
- **Producer path concern:** `src/odds_scanner/master_scan_scope.py` implements six-division *denylist*, not an 81-division *allowlist*. `src/odds_scanner/propline_provider.py` includes `soccer_japan_j_league` and `soccer_usa_mls` in its fallback `SPORTS` list; `active_soccer_sports()` returns fallback `SPORTS` when the catalog is unavailable or fails with a non-auth error. This can still request out-of-master competitions even if downstream snapshots are filtered. PropLine must fail closed or use independently reviewed exact sport-key bindings **before** odds requests. A shared name such as Premier League is insufficient.
- **Other paths:** Oddspapi tournament discovery and odds batches, FiveDollar per-fixture requests, fallback collection, mainline discovery, and daily dashboard sync need individual pre-request assertions. The existing six-exclusion integration does not demonstrate an end-to-end allowlist guarantee.
- **Data invariants:** Keep historical raw and quarantined observations, fixture/provider IDs, FT joins and recovery, scan-round price flow, settled statistical evidence and frozen promotion gates. New-scope-only statistics must be explicitly labeled and must not silently rewrite the old WR/OU population. Quarter-line AH settlement and 1.80–2.20 odds constraints are unchanged.

### Required acceptance evidence before activation

1. Deterministic offline replay across multiple football days, with per-provider, country and competition counts: accepted active-master, reviewed cups, explicit exclusion, unmapped, and historical-only; preserve raw input checksums.
2. Tests for every provider's discovery and pre-metered odds-request filter, including catalog outage/fallback, country-qualified names, unknown IDs, and distinct provider namespaces; fail closed for unverified mappings.
3. Verify the treatment of 11 registered cups, international senior competitions, Brazil/Japan/USA and other non-master leagues; resolve scope explicitly, rather than accidentally dropping or retaining them.
4. Compare expected fixture count, number of paired price rounds, quota calls, FT backfill, dashboard daily cards, and active-scope WR/OU against the legacy behavior; avoid claiming live coverage from catalog mapping.
5. CI and deployed dashboard browser check; observe the first scheduled weekday/weekend scan slots with evidence. Roll back only the new future-target policy if coverage or integrity gates fail, without deleting archive.

**Until those checks pass, the system is still using mixed legacy discovery rules and cannot truthfully be called a master-only scanner.**
