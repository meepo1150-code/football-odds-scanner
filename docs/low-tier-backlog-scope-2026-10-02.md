# Low-tier unresolved backlog triage — 2026-10-02

User authorized excluding unrecoverable low-level leagues. This is reversible queue exclusion, not result recovery. Raw observations and canonical results are preserved. Only fixtures kicked off by 2026-10-02 07:21 UTC qualify for this scoped exception; future collection policy is unchanged.

Exact league labels and classification provenance are in `result_recovery_lifecycle.LOW_TIER_LEAGUES`: German Regionalliga North (regional tier 4), Slovenian 3. SNL and Israeli Liga Alef (regional tier 3), Bangalore Super Division and Mizoram Premier League (state/city competitions). No fuzzy league matching. National top divisions in smaller countries, youth, women's competitions and cups are not automatically excluded.

Each fixture still requires four distinct successful covered recovery rounds across two sources, a consistent identity, both team names, maturity of three hours, and no canonical result conflict. This explicit scope decision replaces the ordinary 72-hour age/24-hour attempt-span wait only for the selected existing backlog. Ordinary retirement rules remain unchanged. A subsequent verified result automatically restores eligibility for statistics.

Local replay at 07:30 UTC: active unresolved 82 → 70; archived 459 → 471; total unresolved remains 541. Twelve newly excluded: Slovenia 1, Mizoram 1, Bangalore 4, Israel 5, Germany 1. Twenty-nine archived rows have the scoped reason, including seventeen already archived by ordinary recovery rules. No new FT result is claimed. No raw or settled record deleted.

Validation: all 355 tests pass, including insufficient attempts, source diversity, result conflicts, future cutoff, small-country top division preservation, raw preservation, and reinstatement on verified result. Live workflow and deployment must separately confirm the generated counts.
