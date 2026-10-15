# Global Master Phase 2 — verified roster staging

Research date: **2026-10-15, Asia/Bangkok**. This dataset adds 20 new competitions, 337 new canonical identities (including one explicitly separate reserve squad), and 337 season memberships. It does not activate competitions or change production tables.

Thai League 1 and Thai League 2 already exist as `THA-0001` and `THA-0002`. They are not duplicated. Their current roster completion remains REVIEW; Peru Liga1 and Bolivia División Profesional replace them in the twenty-new-league target.

## Identity and evidence

`evidence/rosters.json` is the reviewed factual source extract with official URLs, season/stage, format, expected counts, retrieval receipts and source club labels. `identity_ledger.json` freezes permanent COUNTRY-AAA club IDs independently of source order and provider identifiers. `build.py` reads this ledger; it never allocates IDs again. CSV files preserve the existing master schema. `clubs_canonical.csv` contains only new identities; no existing code is renamed or removed.

Names are official published roster labels, including abbreviations and non-Latin names, not certification of corporate registered legal names. No unsupported transliteration or predecessor merger is inferred. Source-attested alternatives are scoped by competition in `aliases.json`; they are not fuzzy runtime joins.

DPMM uses the **BRN** club namespace with **MYS** host membership. Jeonbuk N/reserve has its own ID and a parent relationship to the existing K League first team in `special_identities.json`. The generic KFA label must never be globally bound to the first team. This follows the existing master convention for B/II squads.

Official sources certify current membership at the recorded research time. Promotion/relegation legal history and corporate succession are partially reviewed, not universally certified. Source format notes are descriptive; they do not alter scanner scheduling or settlement rules. `seasons.csv` limits Colombia to verified Liga II and Peru to verified Clausura; it does not silently extend stage coverage.

## Provider boundary

All 20 competitions have cached OddsPapi catalog candidates. Multiple catalog IDs for Chile, Colombia, Paraguay and Bolivia remain distinct alternatives requiring season/stage review. The cached snapshot was observed on 2026-10-11; it does not establish current availability. Exact normalized source labels produce candidate hits for 144 of 337 clubs. These remain REVIEW, with the rest UNRESOLVED. A name match or cached fixture appearance alone is not verified mapping. No PropLine ID or live fixture binding is guessed. Production mappings added: **0**. No bookmaker/provider API calls are made by this work.

The two CFL website JSON requests retrieve public official club directories. They are not OddsPapi/PropLine requests and do not consume their quotas. Those records explicitly carry `competition_code` and `tournament_calendar_name=2026`.

## Reproduction and admission

```sh
python data/research/global_master_phase2/build.py
python data/research/global_master_phase2/validate.py
python -m pytest -q
python data/master/validate_uefa_master.py
python -m unittest discover -s data/master -p test_uefa_registry.py -v
```

The builder writes only the specified research directory. The validator pins production master/catalog hashes and checks staging foreign keys, complete rosters, frozen IDs, aliases, cross-border/reserve handling, exclusions and provider namespaces. `baseline.json` also retains a full production isolation manifest for the pinned main commit. Continuous roster checks intentionally do not freeze operational reports: scheduled scans may legitimately advance them. PR diff and merge-parent comparisons establish isolation from concurrent production updates.

Full-suite production tests can write synthetic scan-health reports locally. Restore only their known generated outputs after testing, then verify hashes; do not commit those test outputs as observations.

Database merge grants **no production activation**. Future activation needs reviewed season/stage and participant mappings, ambiguity resolution, legal identity decisions where relevant, quota-approved live coverage/freshness checks, and a separate activation PR. No new scheduler, API quota, fixture, price, FT, snapshot or dashboard behavior is included here.
