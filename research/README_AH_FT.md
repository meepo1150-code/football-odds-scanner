# AH Movement × FT — isolated research prototype

This is **research-only**, not a production scan or validated edge. Run locally from repo root:

```sh
python -m unittest tests.test_ah_ft_join_research
python research/ah_ft_join.py
```

Reads existing normalized movement features and exact-ID verified FT results; writes only `reports/research_ah_ft_join_exploratory.json` when explicitly invoked. Never calls provider APIs or modifies raw history, scheduler, collector, dashboard or quota ledger.

**Known blocker:** current `research_v2_movement_features.jsonl` generator does not emit `favorite_side` or `last_favorite_side`. Rows without a verified side are intentionally excluded rather than guessed. Next step: safely enrich side and bookmaker from source snapshots under identical fixture, provider, bookmaker and prematch timestamp before trusting settlement. Pinnwire IDs require verified bridge and are not joined by fuzzy name. Missing FT is excluded. No CI or real full-data execution has been confirmed.
