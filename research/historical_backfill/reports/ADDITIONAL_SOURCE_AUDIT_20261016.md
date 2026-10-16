# Additional source coverage audit — 2026-10-16

Read-only follow-up to PARTIAL_PRODUCTION_RECONCILIATION_20261016.md.

Checked `main:data/normalized/five_dollar_snapshots.jsonl`: 297 JSONL rows. None of the 129 historical selected candidates shared the exact provider fixture ID. This dataset identifies itself as `OPENING_AND_LATEST_OR_FINAL_PREMATCH_ONLY_NO_TICKS` and uses a different provider's fixture IDs, so the absence of an exact-ID match **is not evidence of a missed production scan**. It is not a valid slot-by-slot observed AH comparator.

Checked `main:data/normalized/europe_pinnacle_research_v2_snapshots.jsonl`: empty in the connected file response; zero rows available for reconciliation from this access path.

Previously checked `main:data/normalized/v2_mainline_snapshots.jsonl` and `main:data/normalized/research_v2_slot_ledger.jsonl`. These are incomplete as authoritative fixture+round proof.

**Conclusion:** The current checked sources do not prove which of the 129 research candidates are missing in actual production. Import approval remains **FALSE**. Do not treat 119, 82, or 129 as the number of recoverable missed production scans. Exact-ID mapping, observed AH tick history, source timestamp, and full collector scope remain blocking gates. No writes to production or API requests were performed.
