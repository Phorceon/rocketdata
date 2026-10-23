# SFT_V2_REPORT

- Rows kept (train): 164 / 182
- Rows kept (test): 40 / 43
- Regenerated rows (with reasons): [('U-197', 'mismatch_known'), ('U-199', 'mismatch_known'), ('U-441', 'mismatch_known'), ('U-443', 'mismatch_known'), ('U-444', 'mismatch_known'), ('U-452', 'mismatch_known'), ('NEW-003', 'unmapped_no_spans'), ('NEW-006', 'unmapped_no_spans'), ('NEW-022', 'unmapped_no_spans'), ('NEW-023', 'unmapped_no_spans'), ('NEW-026', 'unmapped_no_spans'), ('NEW-033', 'unmapped_no_spans'), ('V1-042', 'unmapped'), ('U-052', 'unmapped_no_spans'), ('U-487', 'unmapped_no_spans')]

- Touchdown speed % change (train, after drops): median=8.59%, p90=39.24%
- Flight time % change (train, after drops): median=0.49%, p90=19.00%

## Top 10 changes (old → new)
- U-197 (ft): 28.490 → 256.325 (799.7% change)
- U-199 (ft): 28.490 → 256.292 (799.6% change)
- V1-042 (ft): 95.610 → 273.773 (186.3% change)
- U-054 (ft): 232.110 → 473.194 (103.9% change)
- V1-096 (gh): 3.766 → 6.880 (82.7% change)
- V1-042 (gh): 6.104 → 11.091 (81.7% change)
- V1-048 (ft): 67.707 → 117.174 (73.1% change)
- V1-086 (gh): 5.276 → 8.891 (68.5% change)
- V1-041 (gh): 5.840 → 9.427 (61.4% change)
- V1-039 (gh): 5.822 → 8.889 (52.7% change)

## All dropped rows with reasons
- train_drop U-023 ork/openrocketdoc__example_simple_1.ork [Simulation 1]: info.openrocket.core.util.BugException: BUG: Simulation resulted in not-a-number (NaN) value for structureMass.getLongitudinalInertia(), please report a bug.
- train_drop U-042 ork/openrocketdoc__example_simple_1.ork [Simulation 1]: info.openrocket.core.util.BugException: BUG: Simulation resulted in not-a-number (NaN) value for structureMass.getLongitudinalInertia(), please report a bug.
- train_drop U-061 ork/openrocketdoc__example_simple_1.ork [Simulation 1]: info.openrocket.core.util.BugException: BUG: Simulation resulted in not-a-number (NaN) value for structureMass.getLongitudinalInertia(), please report a bug.
- train_drop U-062 ork/openrocketdoc__example_simple_1.ork [Simulation 1]: info.openrocket.core.util.BugException: BUG: Simulation resulted in not-a-number (NaN) value for structureMass.getLongitudinalInertia(), please report a bug.
- train_drop U-063 ork/openrocketdoc__example_simple_1.ork [Simulation 1]: info.openrocket.core.util.BugException: BUG: Simulation resulted in not-a-number (NaN) value for structureMass.getLongitudinalInertia(), please report a bug.
- train_drop U-033 ork/czech-rocket-challenge-2025__Raketa.ork [Simulation 1]: recovery: no ground hit / NaN
- train_drop U-078 ork/czech-rocket-challenge-2025__Raketa.ork [Simulation 1]: recovery: no ground hit / NaN
- train_drop U-079 ork/czech-rocket-challenge-2025__Raketa.ork [Simulation 1]: recovery: no ground hit / NaN
- train_drop U-227 ork/czech-rocket-challenge-2025__Raketa.ork [Simulation 1]: recovery: no ground hit / NaN
- train_drop U-228 ork/czech-rocket-challenge-2025__Raketa.ork [Simulation 1]: recovery: no ground hit / NaN
- train_drop V1-016 ork/FRED_v_2.3.ork [Simulation 4]: recovery: no ground hit / NaN
- train_drop V1-099 ork/simulation_1.ork [Simulation 3]: recovery: no ground hit / NaN
- train_drop V1-100 ork/simulation_1.ork [Simulation 4]: recovery: no ground hit / NaN
- train_drop NEW-019 None [None]: touchdown_filter
- train_drop NEW-021 None [None]: touchdown_filter
- train_drop NEW-022 None [None]: touchdown_filter
- train_drop NEW-023 None [None]: touchdown_filter
- train_drop V1-084 None [None]: touchdown_filter
- test_drop U-002 ork/Mojave Sphinx V1.2.ork [Mojave Sphinx, Launch 9 Simulation using Static Test 10 Thrust Curve]: recovery: no ground hit / NaN
- test_drop U-159 ork/APEX_04:21.ork [Simulation 3]: recovery: no ground hit / NaN
- test_drop U-180 ork/aerotech_arreaux.ork [Simulation 1]: "simulation 'Simulation 1' not found; available: ['Simulation 2', 'Simulation 3', 'Simulation 5', 'Simulation 7', 'Simulation 8', 'Simulation 9', 'Simulation 10']"

## Verification
- eval_test.score style (types,motors from reference_vocab()): 204/204
- Deterministic (train): False
- Deterministic (test): False
- <design> blocks byte-identical to v1: verified by design copy
- Hashes train: 68fc45468055dd0405f3a8e2439cc0c58b24b349b0022388e3377f6404b8eae4 vs 3f1de23660f7c79bd5439e630f7d96b403a1f5784058e62752d462a447190951
- Hashes test: 21dd3019a1979ddefedeb429035d03fbfc31c1f824ac7cdaa97845dbd135d694 vs 99f1b22bd51f780919c8bee86a4803c6c2a324038af3a57e5621d8152542eb5a
