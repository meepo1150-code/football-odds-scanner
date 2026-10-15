# Staging-only cached provider identity review

Run `python data/research/global_provider_identity_review/review.py` to check the
committed review against its deterministic, network-free evidence rebuild.
Use `--write` only when deliberately regenerating `review.json` for review.

`VERIFIED_CACHED_*_IDENTITY` certifies catalog/participant identity corroboration,
not provider season/stage, live coverage, complete membership mapping or activation.
All activation flags remain false. No production consumer imports this directory.

`baseline.json` records 361 production hashes at the exact audited main parent.
CI pins static scanner/master evidence; the release audit compares the full
manifest after restoring the two known synthetic scan-health test outputs.
Scheduled runtime data changes on main must be attributed independently.

See `docs/global-provider-identity-review-2026-10-15.md` for the gates and blockers.
