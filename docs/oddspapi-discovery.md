# OddsPapi discovery policy

The Free OddsPapi account is treated as a scarce current-execution source (250 requests/month).

Current health discovery uses one filtered `/v4/fixtures` call for an exact rolling 24-hour UTC window with `sportId=10`, `statusId=0`, `hasOdds=true`, and `bookmakers=bet365`. It then requests `/v4/odds` only for the earliest filtered fixtures, capped at five per health run.

The provider remains fail-closed. A fixture is not an execution candidate unless canonical 1X2, two-sided Asian Handicap, and two-sided Over/Under markets are all present on exact quarter-grid lines and the oldest required `bookmakerChangedAt`/`changedAt` timestamp passes the production freshness gate.

No health result can alter the frozen pattern registry or promote exploratory research.
