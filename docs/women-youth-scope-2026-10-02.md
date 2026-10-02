# Exclude women and youth from Research V2

User-authorized population change on 2026-10-02: women and youth (including U23) are outside active collection, AH/O-U statistics, movement, forward metrics and result recovery. Reserve teams without explicit youth labels remain in scope. Raw historical snapshots and verified result storage are not deleted.

Shared deterministic policy: `research_population.py`. Explicit competition/team labels drive exclusion, including underscore-separated provider sport keys and the existing Damallsvenskan label. Unknown/unlabelled populations are not guessed to be women or youth; classification coverage is limited by provider metadata. Out-of-scope rows are counted separately from integrity quarantine. This is a population decision, not a claim of inferior women's/youth data or a recovered result.

Local replay on main 3388017: raw 1,312 unchanged; integrity quarantine 86 unchanged; 217 verified observations out of scope (93 women, 124 youth); 1,009 remaining observations; 353 settled / 333 core settled; active matured recovery queue 25. Historical settled population previously 395 / 372. Ratios and denominators are rebuilt, never merely hidden in the UI. Raw and result records are retained for reversal and forensic review.

371 tests passed before publication, including source integrity, population boundaries, raw/result preservation, exclusion from settlement and recovery. Data-level operational assertions passed. Main-triggered free-result workflow rebuilds derived artifacts and then Pages deployment publishes them. No validation minimum is lowered.
