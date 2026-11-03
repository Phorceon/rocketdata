# SFT v4 — complete catalog assembly

- **317 rows, one per catalog rocket (317/317)**.
- Label modes: {'flight_grounded': 317}.
- Flight-label sources: {'saved_result': 244, 'new_simulation': 73}.
- Upstream flight simulation calls: 219 (assembler calls: 0).
- Saved-simulation status: {'uptodate': 223, 'outdated': 40, 'notsimulated': 54}.

## Splits (disjoint slices of the main file)

- train: 255 rows / 252 families -> sft_train_v4.jsonl
- val: 31 rows / 31 families -> sft_val_v4.jsonl
- test: 31 rows / 31 families -> sft_test_v4.jsonl

## Use

- sft_v4.jsonl is the complete 317-rocket corpus for curation and inspection; it CONTAINS the val and test slices, so it is NOT itself a held-out training split.
- For comparisons, train only on sft_train_v4.jsonl, tune on sft_val_v4.jsonl, and evaluate once on sft_test_v4.jsonl.
- Training on sft_v4.jsonl would leak every held-out rocket into training and invalidate test metrics.
- Duplicate hardware and original/motor-filled families never cross splits; group_id marks each family in every row.

## Honesty and limits

- The assembler itself runs no flights, training, CAD or installs. Upstream flight simulations are counted separately, and all flight numbers remain recorded reference data rather than safety guarantees.
- Fresh dataset-preparation simulations and reused saved results have distinct provenance and flags.
- Exactly one complete conversation per catalog id; duplicate designs are kept, not deduplicated away.
- Unsafe sources (hard landings, poor stability, fit problems) are kept with honest warnings in text and flags.
- Outdated saved simulations are marked as historical reference, never as current predictions.
- Rows over the token limit keep their complete design and carry context_over_limit with the exact token count.
- Oversized explanations are shortened to engineering summaries first; their complete design JSON is unchanged.
- v3 artifacts are preserved byte-for-byte; this assembler never writes them.
- Dataset-contract validation is not a claim that the full source-code unit-test suite passes.

## Tokens

- Full-conversation tokens: min 2516, median 8839, max 29995; 0 row(s) over the 32768 limit, kept complete with the context_over_limit flag.

Files: sft_v4.jsonl (main), sft_train_v4.jsonl, sft_val_v4.jsonl, sft_test_v4.jsonl, sft_v4_motor_lookup.json, sft_v4_assets.json, sft_v4_coverage.json, sft_v4_report.json.

Every catalog id maps to its row in sft_v4_coverage.json. v3 files are byte-for-byte unchanged.

## Owner-approved exclusions (13 of 330 catalog rockets)

These rockets have no usable flight result. The owner chose to leave them out on 2026-11-03.

- `original:Argonia_3p120OD_K160-P_SIM_9-22-24.ork`: OpenRocket aborted the main branch (SIM_ABORT at t=0.2750000000000001 s, no ground impact); main_branch_ground_hit; finite_nonnegative_landing_speed
- `original:Mojave Sphinx V1.2.ork`: OpenRocket aborted the main branch (SIM_ABORT at t=0.0 s, no ground impact); main_branch_ground_hit; finite_positive_apogee; finite_nonnegative_landing_speed; f
- `original:Raketa.ork`: OpenRocket aborted the main branch (SIM_ABORT at t=0.0 s, no ground impact); main_branch_ground_hit; finite_positive_apogee; finite_nonnegative_landing_speed; f
- `original:Siruis_O3800_ACTUALmass.ork`: OpenRocket aborted the main branch (SIM_ABORT at t=0.0 s, no ground impact); main_branch_ground_hit; finite_positive_apogee; finite_nonnegative_landing_speed; f
- `original:Siruis_O3800_CADmasses.ork`: OpenRocket aborted the main branch (SIM_ABORT at t=0.0025 s, no ground impact); main_branch_ground_hit; finite_positive_apogee; finite_nonnegative_landing_speed
- `original:c31a.ork`: OpenRocket aborted the main branch (SIM_ABORT at t=0.0 s, no ground impact); main_branch_ground_hit; finite_positive_apogee; finite_nonnegative_landing_speed; f
- `original:demo-boattail.ork`: flown configuration 00000000-0000-0000-ffff-ffffdc90bd01 does not match the selected configuration cfg-bt-h128: flown motors [none resolvable] vs design motors 
- `original:demo-dual-deploy.ork`: flown configuration 00000000-0000-0000-0000-000022e3974a does not match the selected configuration cfg-54-k550: flown motors [none resolvable] vs design motors 
- `original:demo-multi-config.ork`: flown configuration 00000000-0000-0000-ffff-ffffbfe916ce does not match the selected configuration cfg-38-h128: flown motors [none resolvable] vs design motors 
- `original:demo-single-deploy.ork`: flown configuration 00000000-0000-0000-ffff-ffffbfe916ce does not match the selected configuration cfg-38-h128: flown motors [none resolvable] vs design motors 
- `original:demo-stable.ork`: info.openrocket.core.file.RocketLoadException: info.openrocket.core.file.RocketLoadException: Unsupported or corrupt file.
- `original:template.ork`: info.openrocket.core.util.BugException: info.openrocket.core.util.BugException: BUG: Simulation resulted in not-a-number (NaN) value for structureMass.getLongit
- `original:teste.ork`: OpenRocket aborted the main branch (SIM_ABORT at t=0.0 s, no ground impact); main_branch_ground_hit; finite_positive_apogee; finite_nonnegative_landing_speed; f

## Landing limit

The owner changed the Tier 3 touchdown limit from 6 m/s to 8 m/s on 2026-11-03. The `*_v4_land8.jsonl` files hold the 231 rockets at or below 8 m/s and with no low-stability flag; 13 rows under 1 caliber were removed on the owner's decision. 73 rows above 8 m/s stay flagged `landing_over_8ms` in the 317-row files.

## Outdated saved results re-flown (2026-11-03)

- The land8 file now holds **226 rockets** (was 231).
- 21 rows had saved results flagged `outdated_saved_results_reference_only`. Each was re-flown headlessly, unmodified, on the same saved simulation and configuration (seed 42, one discarded warm-up). Flight counts are in `flight_completion_report.json` (`flight_simulations_run` raised by 42).
- 19 flew to a real main-branch ground impact. 2 did not (see below).
- Removed from the file: 5 rockets. 3 landed above 8 m/s on the new flight; 2 failed to produce a ground impact.
- Removed rockets: `original:24mmRocket.ork` (10.62 m/s), `original:APEX 29.08.2021.ork` (8.39 m/s), `original:Sainath_L1.ork` (8.44 m/s), `original:rocket_19.ork` (OpenRocket aborted main branch, no ground impact), `original:rocket_6_1.ork` (OpenRocket aborted main branch, no ground impact).
- No previously excluded rocket newly passes the filter. None of the 86 excluded rows was re-flown, and their targets are unchanged.
- The 210 unaffected rows keep the same `targets` as before.
- Large apogee changes (for example MockUp ASCENSION 1364 to 5850 m, Big_Red 10335 to 11129 m, APEXJTentative 2864 to 3739 m) come from the fresh simulations. Review them before training.

| Rocket | Old apogee (m) | New apogee (m) | Old landing (m/s) | New landing (m/s) | Result |
|---|---|---|---|---|---|
| `original:24mmRocket.ork` | 744.2 | 652.5 | 7.57 | 10.62 | removed (landing > 8 m/s) |
| `original:APEX 29.08.2021.ork` | 2837.3 | 2837.9 | 6.67 | 8.39 | removed (landing > 8 m/s) |
| `original:APEX 30.08.2021.ork` | 2881.3 | 2862.3 | 6.53 | 7.72 | kept |
| `original:APEXJTentative.ork` | 2863.9 | 3739.0 | 5.68 | 7.00 | kept |
| `original:ASTRA.ork` | 1040.6 | 1001.2 | 0.00 | 4.56 | kept |
| `original:ASTRAwFairing.ork` | 1040.6 | 647.0 | 0.00 | 5.25 | kept |
| `original:Argonia_Cup.ork` | 4016.1 | 3972.1 | 7.75 | 7.88 | kept |
| `original:Big_Red.ork` | 10335.0 | 11128.9 | 4.92 | 4.92 | kept |
| `original:MockUpofASCENSION(StabilityIssue).ork` | 1364.4 | 5850.5 | 5.81 | 5.81 | kept |
| `original:NASA_Rocket_V1.ork` | 1676.3 | 1651.4 | 6.10 | 6.21 | kept |
| `original:RocketV1.2.ork` | 218.2 | 229.4 | 7.27 | 7.29 | kept |
| `original:Sainath_L1.ork` | 480.2 | 477.3 | 5.82 | 8.44 | removed (landing > 8 m/s) |
| `original:astron drifter.ork` | 115.0 | 115.4 | 2.17 | 2.93 | kept |
| `original:base_23.09.ork` | 50.4 | 54.3 | 3.95 | 4.50 | kept |
| `original:endurance.ork` | 1022.6 | 1382.2 | 7.21 | 5.73 | kept |
| `original:estes_boosted_bertha_1946.ork` | 228.7 | 227.4 | 3.75 | 5.16 | kept |
| `original:locprecision_ezi-65_pk-64.ork` | 491.6 | 494.5 | 7.13 | 7.86 | kept |
| `original:rocket_19.ork` | 3180.7 | - | 5.34 | - | removed (no ground impact) |
| `original:rocket_6_1.ork` | 2917.6 | - | 2.65 | - | removed (no ground impact) |
| `original:rockets__bt_55.ork` | 84.4 | 82.6 | 3.17 | 3.60 | kept |
| `original:starfire73_talon.ork` | 331.0 | 329.9 | 6.15 | 7.27 | kept |

Refly files: `sftgen/out/scratch/sft_v4_final_refly/` (sources, flight results, summary). Backup of the prior state: `sftgen/out/scratch/sft_v4_refly_backup_20261103-092219/`.

The owner also removed `original:MockUpofASCENSION(StabilityIssue).ork` on 2026-11-03. `sft_v4_land8.jsonl` has 225 rows and is the only current training file.

`sft_v4_land8.jsonl` was renamed to `sft_v5.jsonl` on 2026-11-03. It is the only current training file.

The owner removed 7 rockets with fit overlap of 5 mm or more from `sft_v5.jsonl` on 2026-11-03: `original:Nemesis150_v4.3.ork`, `original:example.ork`, `original:rocket.ork`, `original:rocket_17.ork`, `original:rocket_3.ork`, `original:rocket_4.ork`, `original:rocket_7.ork`. The file has 218 rows.

`sft_v5.jsonl` now has 654 rows: 218 rockets with 3 prompts each (original, casual, engineering). All rows for one rocket have the same design and flight numbers. Touchdown limits in prompts stay at or below 8 m/s.

`sft_v5.jsonl` reasoning was replaced on 2026-11-03: a short engineering explanation per rocket plus a computed REQUEST CHECK per row. Designs, prompts and flight numbers did not change.

## Refresh in current OpenRocket (2026-11-03)

`sft_v5.jsonl` now has 594 rows: 198 rockets with 3 prompts each. Every design was rebuilt from its JSON and flown in OpenRocket 24.12. 148 rockets use a fresh flight; 50 use fill-pipeline results that match the rebuilt flight closely. Removed 20 rockets:

- `original:APEX.ork`: lands at 9.21 m/s in current OpenRocket, above the 8 m/s limit
- `original:ASTRA_V1.ork`: lands at 9.99 m/s in current OpenRocket, above the 8 m/s limit
- `original:FRED_V_2.0.ork`: no thrust curve for the motor, so it cannot leave the ground
- `original:FRED_v_2.3.ork`: no thrust curve for the motor, so it cannot leave the ground
- `original:PML_SmallEndeavour_29-38ADPTRv2.ork`: no thrust curve for the motor, so it cannot leave the ground
- `original:Scale_model_Nasa.ork`: lands at 9.90 m/s in current OpenRocket, above the 8 m/s limit
- `original:Scale_model_Nasa_Updated.ork`: lands at 9.38 m/s in current OpenRocket, above the 8 m/s limit
- `original:Seongyong_L1_July.ork`: lands at 9.19 m/s in current OpenRocket, above the 8 m/s limit
- `original:falconHeavey.ork`: lands at 8.38 m/s in current OpenRocket, above the 8 m/s limit
- `original:falconHeavey_SCAD.ork`: lands at 8.64 m/s in current OpenRocket, above the 8 m/s limit
- `original:locprecision_weasel-29_pk-3.ork`: lands at 8.75 m/s in current OpenRocket, above the 8 m/s limit
- `original:rocket_1.ork`: no thrust curve for the motor, so it cannot leave the ground
- `original:rocket_10_1.ork`: no thrust curve for the motor, so it cannot leave the ground
- `original:rocket_15.ork`: no thrust curve for the motor, so it cannot leave the ground
- `original:rocket_20.ork`: no thrust curve for the motor, so it cannot leave the ground
- `original:rocket_2_1.ork`: no thrust curve for the motor, so it cannot leave the ground
- `original:rocket_5_1.ork`: no thrust curve for the motor, so it cannot leave the ground
- `original:rocket_9_1.ork`: lands at 8.28 m/s in current OpenRocket, above the 8 m/s limit
- `original:rocketryworks_payloader_24-56.ork`: lands at 8.04 m/s in current OpenRocket, above the 8 m/s limit
- `original:simulation_1.ork`: no thrust curve for the motor, so it cannot leave the ground
