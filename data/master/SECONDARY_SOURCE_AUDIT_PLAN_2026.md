# Secondary roster evidence audit — 2026-10-09

## Confirmed from registry snapshot

66 of 87 scoped divisions have VERIFIED_SECONDARY status; 21 have VERIFIED_OFFICIAL. Of those 66, source domains break down as follows:

| Source domain | Divisions |
|---|---:|
| www.soccerassociation.com | 50 |
| www.sportsmole.co.uk | 4 |
| primatips.com | 3 |
| czechleague.com | 2 |
| footystats.org | 1 |
| greekleague.net | 1 |
| kosovascore.com | 1 |
| www.vi.nl | 1 |
| sportalic.com | 1 |
| www.eurofotbal.cz | 1 |
| www.footballwebpages.co.uk | 1 |

## Prioritized verification queue

1. Verify 50 soccerassociation.com-backed divisions using federation or league websites and season-specific participant tables; check whether the source displays the correct season rather than current/live tables without a season label.
2. Cross-check four SportsMole-backed divisions, particularly ENG tiers 2-4 and Portugal top tier, with official EFL/Liga Portugal fixtures or team lists.
3. Review the remaining 12 secondary divisions using season-specific official sources where available.
4. For each upgraded division, record source URL, retrieval date, evidence of season and all team names; compare roster count and IDs; only then change status.
5. Investigate mismatches explicitly; do not silently substitute guessed promoted/relegated clubs or reuse IDs for different clubs.

## Acceptance criteria

- 87 scoped divisions retain season-specific roster and stable IDs.
- Every official upgrade is supported by a checked federation/league source that explicitly identifies the season and roster.
- All mismatches are documented with before/after counts and corrected canonical links.
- Existing 1,286 memberships are a baseline, not proof of factual accuracy.
- No live scanner/API/deployment modifications; PR #309 remains unmerged.

This document is an audit queue derived from repository data. **It is not a claim that 66 divisions have been independently verified.**
