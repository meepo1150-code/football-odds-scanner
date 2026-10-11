# Scan compatibility and non-destructive scope adoption

Audit source: main commit `3189c622970cb9c8ace8c02998352f7176164eca`, football day 2026-10-11 (Asia/Bangkok). No provider requests made for this audit; saved scan records were inspected read-only.

Today's saved Pinnacle research archive contains 70 observations: 40 Oddspapi and 30 PropLine. Four Oddspapi observations belong to Poland 1. Liga, participant competition ID 229 / canonical excluded division POL-0002. These four are historical evidence, not deleted or rewritten. Future requests must exclude this tournament before budget rotation or odds batches. Three further Oddspapi observations belong to Germany 3. Liga, which is outside the current master roster scope but was NOT cancelled by the user; it is not silently removed. The other 33 Oddspapi observations have active canonical competition bindings.

The separate mainline archive contains 31 observations for today's Big-5 leagues; all have active canonical competition bindings. The 30 PropLine observations lack accepted provider-to-canonical competition IDs; they remain valid old-format records, not falsely certified canonical mappings. Provider IDs are never reused across namespaces. Today's local daily fixture records preserve their old fixture IDs even where canonical metadata is missing.

Adoption changes add canonical identity fields to new Oddspapi snapshots without changing fixture IDs, teams, prices, kickoff, source semantics, observed timestamps or validation flags. Six explicit user exclusions have reviewed Oddspapi tournament IDs and exact country/name evidence from the saved full provider catalog. Country-qualified equivalent labels can be rejected across providers; a generic Premier League/1. Liga label or unknown foreign provider ID is not guessed. Missing metadata remains unresolved, not falsely identified.

Oddspapi target batches are filtered before odds calls. FiveDollar per-fixture calls check available league/country metadata before requesting odds; PropLine sports discovery applies reviewed country/name exclusions before per-sport odds requests. Payload-side scope checks remain a second guard. Legacy archive files, results, joins and patterns are not replaced. Derived active-scope research views may exclude cancelled league observations without deleting their raw evidence.

The original 54-row Europe target document is preserved; effective requests exclude Poland 1. Liga, leaving 53 entries. Frozen ten-league research targets remain ten; the cancelled leagues are not part of those ten. Other outside-master competitions are not automatically treated as poor-quality leagues or cancelled. No API keys, schedules, odds-price gates or production patterns changed.

Compatibility tests and final CI for this adoption commit are recorded in PR #309. A successful identity migration does not establish a betting edge or live market availability. The old production pattern registry remains unchanged.
