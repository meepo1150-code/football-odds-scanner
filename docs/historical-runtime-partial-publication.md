# Retained historical partial publication

Run 39094936689 stopped after its 1,200-second runtime budget with 122 of
1,157 planned missing historical requests attempted. Its saved artifact contains
27 BALANCED_LINE slots. The scan remains STOPPED and incomplete.

The separate, manual-only Publish Retained Historical Artifact workflow downloads
an existing Manual Historical Scan artifact. It never invokes a collector and
receives no provider credentials. A source run ID is required. Artifact report
provenance must match that exact run in this repository.

Partial publication requires explicit opt-in and exactly the runtime-budget stop
reason. Account, quota, transport, identity and other failures remain blocked.
Each processed fixture/bookmaker must still contain its complete requested target
set and pass all existing identity, price, line, activity and quote-time checks.
Unprocessed candidates produce no rows. The original report and raw cache are
not rewritten or relabeled COMPLETED.

The publication receipt records PARTIAL_PROMOTED, the unchanged source scan
status/error, processed/unprocessed candidate counts, and zero provider calls.
Snapshots remain append-only, replay is idempotent, and concurrent changes are
preserved by re-importing the same artifact on fresh main after a push conflict.
Manual Current-Day, Auto Scan and the original Historical Scan workflow are
unchanged. Research promotion gates remain frozen.
