# Thailand current-season membership completion — staging only

THA-0001 and THA-0002 already exist in production as REVIEW. They are not new
competitions and are not counted again toward Phase 2's 20-league expansion.

Official 2026/27 public roster and standings records agree on 16 + 18 teams.
`identity_ledger.json` freezes 34 independent canonical IDs. Official club IDs,
season tournament-team IDs and bookmaker participant IDs are separate namespaces.
`evidence.json` stores identity-field extracts, source URLs, raw-response hashes
and retrieval timestamps. Build pins require deliberate review for evidence edits.

Run `python data/research/thailand_membership_completion/build.py` to validate;
`--write` regenerates only this directory's derived artifacts. No network is used.
Previous/current roster differences do not certify promotion/relegation mechanisms.
No production memberships, mappings, scanner configuration or quota are changed.
