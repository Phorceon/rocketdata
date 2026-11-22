# RL prompts v1

`rl_prompts_v1.jsonl` holds 474 prompts for reinforcement learning, one per line. Each is a reference prompt whose numbers were rewritten from the reward's own flight of the reference design, so the prompt text, its requirements record and the reward's physics agree, and the reference answer scores at least 0.99 on it. `excluded_references.jsonl` lists the 120 reference rows that were left out, with the stage and the reason.

## Fields

- `id`: the reference row and prompt style (`V4-0001:original`); also the record's id.
- `group_id`, `split` (train / val / test) and `prompt_style`: as in the reference row.
- `family`: the kit the rocket belongs to (see Families). Siblings of one kit share it.
- `system`: the exact system prompt the model was trained with (1 distinct text in the reference rows).
- `prompt`: the user prompt, rewritten.
- `requirements`: the record to score against (`Requirements.from_dict`). Every `max` and `min` target carries `"tol": 0.0`: the margin is already in the number. An `about` target keeps the prompt's own tolerance (none written means 5%).
- `reference_score`: what the reference answer scores on this record.
- `leaks_family`: true for a val or test row whose family also has a train row in the reference set (the model saw a sibling rocket during fine-tuning).

## How it was made

Source: `sft_v5_meta_c94ffa5.jsonl` (594 reference rows). For every row:

1. A stated wind that disagrees with the wind the reference flew in, while every sibling prompt of the same design agrees, is set to the reference wind (1 row(s): V4-0099-casual:casual 5.9 -> 4.5 m/s).
2. The reference answer is scored through the whole ladder with the record parsed from its prompt (the prompt's numbers only shape the targets stage's credit, so an old number cannot stop a sound rocket before it is measured). The measured values are the ones the targets stage reads from the 1x-wind flight: times from the first ignition, the main section's landing speed, the widest main-body tube, the liftoff mass.
3. Only references that pass stages 1-6 and fly the motors the prompt names are kept.
4. Every stated number is rewritten in place, keeping the unit, thousands separators and decimals as written: `about` gets the measured value; `max` the measured value plus a margin, rounded up (landing speed +10% and never above 9 m/s, flight time +5%, mass +5%, body diameter +2%); `min` the measured value minus the margin, rounded down. Wind and motor names are not changed. When the written precision is too coarse (an `about` number more than 2% (or half its tolerance) off the measured value, or a rounded-up limit with more than twice its margin), one more decimal is written. A spelled-out number stays spelled out when a word fits (`four minutes` -> `three minutes`), else it becomes digits (`a minute` -> `1.4 minutes`).
5. The new text is parsed again and must give the same fields and kinds with no unplaced number; the reference must score at least 0.99 on the new record.

Rebuild (from the folder that holds `rocket_reward`, with `ROCKET_REWARD_JAVA_HOME` and `ROCKET_REWARD_JAR` set):

```
python -m rocket_reward.tools.build_rl_prompts --meta sft_v5_meta_c94ffa5.jsonl --out-dir rocket_reward/prompts
```

The output is sorted by id and the same byte for byte on every run.

## Counts

Kept / all reference rows:

| style | train | val | test | all |
|---|---|---|---|---|
| casual | 128 / 159 | 12 / 16 | 18 / 23 | 158 / 198 |
| engineering | 128 / 159 | 12 / 16 | 17 / 23 | 157 / 198 |
| original | 129 / 159 | 12 / 16 | 18 / 23 | 159 / 198 |
| all | 385 / 477 | 36 / 48 | 53 / 69 | 474 / 594 |

Kept val and test rows whose family has a train row (`leaks_family`): val 18 of 36, test 32 of 53.

Excluded rows by reason:

| stage | reason | rows | by split | by style | designs |
|---|---|---|---|---|---|
| flight | stage_flight | 57 | train 45, val 9, test 3 | casual 19, engineering 19, original 19 | V4-0003, V4-0025, V4-0027, V4-0048, V4-0049, V4-0120, V4-0162, V4-0166, V4-0171, V4-0189, V4-0285, V4-0297, V4-0298, V4-0299, V4-0302, V4-0303, V4-0304, V4-0305, V4-0316 |
| limits | stage_limits | 36 | train 27, test 9 | casual 12, engineering 12, original 12 | V4-0021, V4-0062, V4-0075, V4-0101, V4-0163, V4-0165, V4-0167, V4-0172, V4-0222, V4-0225, V4-0229, V4-0232 |
| build | stage_build | 21 | train 15, val 3, test 3 | casual 7, engineering 7, original 7 | V4-0002, V4-0195, V4-0210, V4-0213, V4-0215, V4-0227, V4-0230 |
| targets | motor_not_flown | 3 | train 2, test 1 | casual 1, engineering 2 | V4-0076, V4-0193 |
| targets | proof_below_min | 3 | train 3 | casual 1, engineering 1, original 1 | V4-0045 |

## How far the numbers moved

Over the kept prompts, per field and kind: how many numbers were stated, how many now read differently, and the change of the value (new over old, minus 1).

| field | kind | stated | text changed | median change | median size | largest size | range | one more decimal | words to digits |
|---|---|---|---|---|---|---|---|---|---|
| apogee_m | about | 474 | 442 | +0.0% | 1.5% | 103.1% | -39.5% .. +103.1% | 0 | 0 |
| body_diameter_m | about | 92 | 88 | -7.6% | 7.6% | 20.0% | -20.0% .. +0.0% | 10 | 0 |
| body_diameter_m | max | 174 | 166 | -9.3% | 9.3% | 18.3% | -18.3% .. +2.2% | 32 | 2 |
| flight_time_s | about | 152 | 145 | -5.1% | 6.2% | 87.7% | -51.0% .. +87.7% | 19 | 7 |
| flight_time_s | max | 264 | 248 | +3.1% | 5.0% | 116.7% | -48.0% .. +116.7% | 9 | 0 |
| landing_ms | max | 473 | 393 | +0.0% | 4.7% | 32.5% | -32.5% .. +31.3% | 47 | 0 |
| mass_kg | about | 74 | 74 | -14.3% | 14.3% | 36.8% | -36.8% .. +4.5% | 33 | 0 |
| mass_kg | max | 177 | 155 | -4.5% | 6.7% | 52.9% | -37.1% .. +52.9% | 36 | 0 |

## Families

A family groups the sibling rockets of one kit. It comes from the reference file name (`tools/build_rl_prompts.family_name`): lower case, no extension, text in brackets and dates removed, options glued to a word removed (`withCPR3000`, `CPR3K`, `wFairing`, `Tentative`), everything from the first size, version, motor or variant word on removed (`29mm`, `38mmConfigurationE`, `29-38ADPTR`, `1p79OD`, `V2`, `mod24`, `SIM`, `Subscale`, `FRR`, `L1420`, a hash), then trailing one- or two-digit numbers removed. Rows that share a group id or a design block are in one family too. Names that differ only in spelling are not merged.

129 families over 198 reference files. The largest:

| family | files | rows by split | files (first 6) |
|---|---|---|---|
| `rocket` | 10 | train 24, val 3, test 3 | rocket_10.ork, rocket_11.ork, rocket_18.ork, rocket_2.ork, rocket_21.ork, rocket_23.ork ... |
| `argonia` | 8 | train 21, test 3 | Argonia_1p79OD_trans_2p240OD_SkinnyK627LR-7_SIM_9-15-24_SPINNY.ork, Argonia_1p79OD_trans_2p240OD_SkinnyK627LR-7_SIM_9-15-24_SPINNY2.ork, Argonia_1p79OD_trans_2p240OD_SkinnyK627LR-7_SIM_9-22-24.ork, Argonia_2p242OD_K250W_SIM_9-25-24_NoDeploymentBags.ork, Argonia_2p242OD_longburnK160-P_SIM_9-25-24_NoDeploymentBags.ork, Argonia_2p242OD_trans_3p120OD_longburnK160-P_SIM_9-13-24.ork ... |
| `nasa rocket` | 5 | train 15 | NASA_Rocket_FRR_L1420_Nose_Shift.ork, NASA_Rocket_V1.ork, NASA_Rocket_V2_L1420.ork, NASA_Rocket_V3_L1420.ork, NASA_Rocket_V4_L1420.ork |
| `pml amraam4` | 5 | train 9, test 6 | PML_AMRAAM4-withCPR3000_29mm.ork, PML_AMRAAM4-withCPR3000_38mm.ork, PML_AMRAAM4-withCPR3000_54mm.ork, PML_AMRAAM4_29mmMAC.ork, PML_AMRAAM4_38mmMAC.ork |
| `pml quantumleapii` | 5 | train 6, val 9 | PML_QuantumLeapII_38mmConfigurationE.ork, PML_QuantumLeapII_54mmConfigurationB.ork, PML_QuantumLeapII_54mmConfigurationC.ork, PML_QuantumLeapII_54mmConfigurationD.ork, PML_QuantumLeapII_54mmConfigurationE.ork |
| `pml quantumleap` | 4 | train 12 | PML_QuantumLeapCPR3K_38mmConfigurationE.ork, PML_QuantumLeapCPR3K_54mmConfigurationE.ork, PML_QuantumLeap_38mm.ork, PML_QuantumLeap_54mm.ork |
| `pml blackbrantx` | 3 | train 9 | PML_BlackBrantX_29mm.ork, PML_BlackBrantX_38mm.ork, PML_BlackBrantX_54mm.ork |
| `pml cygnus` | 3 | train 9 | PML_Cygnus 29mm ADPTR.ork, PML_Cygnus 38mm ADPTR.ork, PML_Cygnus 54mm.ork |
| `pml eclipsea` | 3 | train 9 | PML_EclipseA_29mm.ork, PML_EclipseA_38mm.ork, PML_EclipseA_54mm.ork |
| `pml endeavour` | 3 | train 6, test 3 | PML_Endeavour_29mm.ork, PML_Endeavour_38mm.ork, PML_Endeavour_54mm.ork |
| `pml miranda` | 3 | train 6, test 3 | PML_Miranda_29mm.ork, PML_Miranda_38mm.ork, PML_Miranda_54mm.ork |
| `pml smallendeavour` | 3 | train 6, test 3 | PML_SmallEndeavour_29-38ADPTR.ork, PML_SmallEndeavour_38-8.ork, PML_SmallEndeavour_38mm.ork |
| `pml suddenrush` | 3 | train 9 | PML_SuddenRush_29mm.ork, PML_SuddenRush_38mm.ork, PML_SuddenRush_54mm.ork |
| `2024 irec` | 2 | train 3, val 3 | 2024_IREC.ork, 2024_IREC_Subscale.ork |
| `a simple model rocket` | 2 | train 6 | A simple model rocket.ork, cohete.ork |

## Recommended use

- Train RL on the rows with `split` train.
- Use the val rows to pick a checkpoint and keep the test rows for the final number.
- Report val and test results twice: on all rows and on the rows with `leaks_family` false, because a sibling of a leaking rocket was in the fine-tuning data.
- Score with `Requirements.from_dict(row["requirements"])`; the reward never reads the prompt text.
