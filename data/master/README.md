# Football Master Database (v1)

Internal IDs are stable and independent of provider IDs. Never construct team identity by concatenating league and team IDs.

Tables:
- countries.csv: country_id, country_name, status
- competitions.csv: competition_id, country_id, competition_name, status
- teams.csv: team_id, country_id, canonical_name
- provider_mappings.csv: entity_type, internal_id, provider, provider_id, verification_status
- memberships.csv: season, competition_id, team_id

Provider mappings must be verified before using them for permanent deletion. Names are aliases, not unique keys. Unknowns remain REVIEW. Cross-border competitions use INT country grouping, while each club retains its home country. Historical membership is season-scoped.
