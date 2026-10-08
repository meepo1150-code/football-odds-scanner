# Football Master Registry — scope v1
This is our OWN registry. No provider/API IDs belong here.

## Scope
21 specifically named European domestic football countries in `country_scope.csv`. International (INT) is a competition scope, **not** a country. Other European countries remain optional expansion candidates. Non-European leagues are out of scope. Existing `countries.csv` contains other starter countries (ROU, ISR, EGY, THA, BRA, JPN, KOR) that are not yet in the explicitly named domestic selection and should not be claimed as selected.

## IDs
Country: three uppercase letters (ENG, ESP, ...).
Competition: COUNTRY-4-digit sequence (ENG-0001). Cups receive their own unique competition ID.
Team: COUNTRY-3 uppercase letters (ENG-LFC, ESP-RMA). Check uniqueness *within country*; reserve codes once issued. Team ID does not change with league or season. A team in a foreign league retains its home country code. Where all three-letter combinations are occupied, flag for manual resolution, never overwrite.
Membership: (season, competition_id, team_id), separate from permanent team identity.

## Integrity
`teams.csv` is an early **unverified** seed, NOT a completed roster for 2026-27. It currently contains legacy numeric team IDs, which require explicit migration/collision review before being replaced by three-letter IDs. Never infer active membership from this seed. Do not fabricate teams to reach a target count.

## Order
1. Collect real current clubs for selected leagues from public sources.
2. Assign and check permanent 3-letter team codes; preserve a migration crosswalk for legacy IDs.
3. Record seasonal league memberships and cups.
4. Only after the master is completed, create separate provider/API mapping tables.
No odds-scanner integration in this stage.

## October 2026 scope adjustment
Europe-only: add Finland (FIN), Russia (RUS), Ukraine (UKR); remove Brazil (BRA), Japan (JPN), South Korea (KOR) from active research scope. Preserve any existing historical rows and IDs; removal from scope is not data deletion. Russia/Ukraine coverage and match availability must be verified later, not assumed.
