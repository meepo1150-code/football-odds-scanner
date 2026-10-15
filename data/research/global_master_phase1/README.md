# Global Master Phase 1 — isolated staging dataset

Research date: **2026-10-14, Asia/Bangkok**. These files do not extend the production registry yet.

The production allowlist reads `data/master/competitions.csv` and the existing provider ledger. Adding accepted competitions there risks automatic inclusion. This dataset is instead stored under an explicitly unused research directory. No production module, workflow, provider configuration, activation flag, quota, scanner, result, historical price or dashboard file is changed.

## Files and schema

- `countries.csv`, `competitions.csv`, `clubs_canonical.csv`, `memberships.csv`, `verified_memberships.csv`, and `club_assignments.csv` preserve the field conventions of the existing master tables. Existing country rows are reused unchanged. New country and competition records retain the existing `REVIEW` status. Verified membership evidence does **not** grant production admission.
- `seasons.csv` is separate evidence metadata, since production has no standalone season table. Argentina has annual 2026 membership across Apertura/Clausura; Mexico verifies Apertura 2026 only within the 2026-27 season. A-League 2026-27 is `NEXT_ANNOUNCED` on October 14 and starts October 16. No future Clausura 2027 roster is inferred.
- `evidence/rosters.json` contains factual official roster extracts, source URLs, independently sourced expected counts, date, season basis, and the proposed permanent-code ledger. It does not copy complete source articles.
- `evidence/aliases.json` contains only reviewed source-attested alternative labels. Korean native roster names are retained; unverified English transliterations are not generated.
- `evidence/change_review.json` records material current roster/admission/name changes and cross-border provenance. It does not claim exhaustive historical licensing or corporate identity certification.
- `evidence/provider_candidates.json` references exact rows in the existing hashed OddsPapi catalog. All candidates remain `REVIEW`, with activation explicitly prohibited. No participant mappings are guessed or promoted.
- `baseline.json` pins main SHA, counts and hashes of all 715 tracked baseline files. `qa.json` records the offline audit. `validate.py` only reads and reports; it does not rebuild or activate production.

Official name means the official league/federation's published roster label, including native text, abbreviations and Brazilian state-qualified labels. It is not a claim that every label is the legal corporate registered name. Série B's regulations provide legal and short names in paired columns; those pairs are preserved as aliases. Brazilian Botafogo RJ and Botafogo SP are distinct clubs. Short-name aliases always require club/country/membership context; they are not runtime fuzzy joins.

Country prefix is the registry namespace; membership `country_id` is the host league association. Auckland and Wellington use `NZL-` IDs under `AUS-0001`; Montréal, Toronto and Vancouver use `CAN-` IDs under `USA-0001`. This follows the existing cross-border convention without creating duplicate MLS or A-League competitions.

## Offline checks

```sh
PYTHONPATH=src python data/research/global_master_phase1/validate.py
PYTHONPATH=src python -m pytest -q tests/test_global_master_phase1.py
PYTHONPATH=src python data/master/validate_uefa_master.py
PYTHONPATH=src python -m unittest discover -s data/master -p test_uefa_registry.py -v
PYTHONPATH=src python -m pytest -q
```

Existing full-suite tests can write synthetic scan-health reports into the local worktree. Run that suite in a disposable checkout and inspect the diff afterwards. These are test side effects, not new production observations. They must never be committed. This expansion does not alter those production tests.

## Admission boundary

Draft PR only. No merge, deployment, automatic mapper rebuild, source refresh API, or activation is authorized by this dataset. Future admission requires a separately approved migration preserving permanent IDs, reviewed provider season/stage and team bindings, exclusion-ledger protection, and a bounded operational coverage check. The offline catalog does not prove live odds availability or quote quality.

Head commit deliberately uses `[skip ci]`: the existing unconditional Pages `workflow_run` listener can deploy main after an offline-evidence PR workflow completes. Automatic CI cannot be run safely until that existing workflow coupling is addressed separately. Local checks are complete; skipped GitHub CI must not be described as passing CI.

## Completion review — 2026-10-15

PR #373 isolates PR validation from Pages and production evidence writes. The historical manifest is retained; continuous staging QA pins master tables and provider catalog, while the PR diff verifies no scanner, scheduler, quota, raw history, production mapping, or dashboard modifications. Operational reports may advance independently. Safe merge is authorized as staging only; production admission remains prohibited. Original 2026-10-14 roster evidence is retained without claiming a new live re-fetch.
