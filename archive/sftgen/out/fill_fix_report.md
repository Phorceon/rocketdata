# Fix-prompt fill

Filled 29 of 48. Left 19 unchanged.

| flaw | converted | synthesized | filled |
|---|---:|---:|---:|
| low_margin | 3 | 3 | 6 |
| landing_fast | 5 | 6 | 11 |
| apogee_low | 4 | 3 | 7 |
| apogee_high | 1 | 2 | 3 |
| rail_exit_slow | 0 | 2 | 2 |

## Per prompt

| prompt | flaw | base | observed | fix check | extra gates |
|---|---|---|---|---|---|
| `g_two_stage_02__p3` | apogee_low | converted | 1,200 m (1183.7) | s[0].c[4].x: len 2 -> len 1 |  |
| `g_54mdl2__p2` | landing_fast | converted | 23 ft/s (7.0) | s[0].c[3].x[2].diameter_m: 1.1188 -> 2.797 |  |
| `g_aeolus_updated_weights__p3` | landing_fast | synthesized | 26 ft/s (7.8) | s[0].c[1].x[0].diameter_m: 0.1276 -> 0.319 |  |
| `g_apex_20102020_longer_bt__p3` | landing_fast | converted | 24 ft/s (7.3) | s[0].c[1].x[0].diameter_m: 0.6677 -> 1.3354; s[0].c[1].x[1].strip_length_m: 0.1 -> 0.141; s[0].c[1].x[1].strip_width_m: 0.037 -> 0.074 |  |
| `g_apex_04_21__p2` | rail_exit_slow | synthesized | 12 m/s (12.0) | s[0].c[1].x[3].mass_kg: 3.0 -> 0.2 |  |
| `g_apex_4f8fe7__p2` | low_margin | converted | 0.9 cal (0.88) | s[0].c[3].x[1].root_chord_m: 0.07189 -> 0.1027; s[0].c[3].x[1].span_m: 0.0429 -> 0.06128; s[0].c[3].x[1].sweep_m: 0.0974 -> 0.13914 |  |
| `g_astra_bbbe1f__p3` | apogee_high | synthesized | 4,100 ft (1250.3) | s[0].c[1].x[1].motor.designation: 636I216-14A -> 381I224-15A |  |
| `g_borealisa8_10_final__p2` | low_margin | synthesized | 0.8 cal (0.75) | s[0].c[1].x[3].mass_kg: 0.2 -> 0.4 |  |
| `g_estes_boosted_bertha_1946__p3` | apogee_low | converted | 190 m (190.3) | s[0].c[1].x[4].mass_kg: 0.05 -> 0.02 | rail_exit_ms 13.8 < 15 (min rail-exit speed) |
| `g_fred_v_2_3__p2` | rail_exit_slow | synthesized | 10 m/s (9.8) | s[0].c[1].x: len 4 -> len 3 | thrust_to_weight 2.3 < 3 (min thrust-to-weight) |
| `g_nasa_rocket_v1__p2` | landing_fast | converted | 25 ft/s (7.7) | s[0].c[1].x[0].diameter_m: 1.7469 -> 5.8229; s[0].c[3].x[1].diameter_m: 1.7469 -> 5.8229 |  |
| `g_numericalrocketry_green_eggs_openrocket_design__p2` | landing_fast | converted | 23 ft/s (7.1) | s[0].c[3].x[2].diameter_m: 0.274 -> 0.548 |  |
| `g_olexam_twomotors__p4` | landing_fast | synthesized | 10 m/s (9.6) | s[0].c[1].x[0].diameter_m: 0.17 -> 0.425 | stability_rail_exit_cal 0.75 < 1 (min launch margin) |
| `g_openrocket_file_utils_centuriarrow300__p4` | low_margin | synthesized | 0.8 cal (0.78) | s[0].c[1].x[2].root_chord_m: 0.02032 -> 0.0508; s[0].c[1].x[2].tip_chord_m: 0.00916 -> 0.0229; s[0].c[1].x[2].span_m: 0.01572 -> 0.0393; s[0].c[1].x[2].sweep_m: 0.00608 -> 0.0152; s[1].c[0].x[2].root_chord_m: 0.02032 -> 0.0508; s[1].c[0].x[2].tip_chord_m: 0.00916 -> 0.0229 (+6 more) |  |
| `g_othertwostager__p1` | apogee_high | converted | 7,800 ft (2365.5) | s[0].c[1].x[6].mass_kg: 1.5 -> 3.0 |  |
| `g_pml_smallendeavour_38_8__p2` | apogee_low | converted | 3,700 ft (1131.2) | s[0].c[1].x: len 7 -> len 6 | Etage landing_ms 7.1 > 6 |
| `g_pods_powered_with_recovery_deployment__p4` | apogee_high | synthesized | 60 m (61.6) | s[0].c[1].x: len 4 -> len 5 |  |
| `g_rocket_3b8501__p2` | landing_fast | synthesized | 8 m/s (8.5) | s[0].c[1].x[0].diameter_m: 1.6161 -> 4.0403 |  |
| `g_rocket_504e63__p2` | landing_fast | synthesized | 7 m/s (7.3) | s[0].c[1].x[0].diameter_m: 1.4564 -> 3.641 |  |
| `g_rocket_7e1fd3__p2` | apogee_low | synthesized | 6,700 m (6717.6) | s[0].c[1].x: len 4 -> len 3 |  |
| `g_rocket_b87d11__p2` | apogee_low | synthesized | 6,600 m (6617.7) | s[0].c[1].x[3].mass_kg: 30.0 -> 18.0 |  |
| `g_rocket_c3d681__p2` | apogee_low | synthesized | 6,600 m (6555.2) | s[0].c[1].x: len 4 -> len 3 |  |
| `g_rocket_e9e655__p3` | low_margin | synthesized | 0.9 cal (0.89) | s[0].c[1].x[2].offset_from_aft_m: 0.07 -> 0.0 |  |
| `g_rocket_f4bcc9__p2` | landing_fast | synthesized | 24 ft/s (7.3) | s[0].c[1].x[0].diameter_m: 1.9474 -> 4.8685 |  |
| `g_rockets_bt_55__p3` | landing_fast | converted | 8 m/s (7.9) | s[0].c[1].x[1].diameter_m: 0.1829 -> 0.4572 |  |
| `g_simulation_extensions__p2` | low_margin | converted | 0.8 cal (0.85) | s[0].c[1].x[0].offset_from_aft_m: 0.22 -> 0.175; s[0].c[3].x[0].offset_from_aft_m: 0.22 -> 0.03 |  |
| `g_sirius__p3` | landing_fast | synthesized | 10 m/s (10.3) | s[0].c[1].x[0].diameter_m: 1.2075 -> 5.4886; s[1].c[0].x[0].diameter_m: 1.267 -> 5.759 |  |
| `g_testlaunch_fall2022__p3` | low_margin | converted | 0.4 cal (0.44) | s[0].c[2].x[0].root_chord_m: 0.01778 -> 0.04445; s[0].c[2].x[0].tip_chord_m: 0.00762 -> 0.01905; s[0].c[2].x[0].span_m: 0.01524 -> 0.0381; s[0].c[2].x[0].sweep_m: 0.01016 -> 0.0254 |  |
| `g_three_stage_low_power_rocket__p4` | apogee_low | converted | 400 m (423.5) | s[0].c[1].x[5].mass_kg: 0.1 -> 0.02 | rail_exit_ms 13.7 < 15 (min rail-exit speed); Sustainer landing_ms 6.7 > 6 |

## Not filled

- `g_three_stage_03__p3` (apogee_high, converted): safety repair did not converge (rail_exit_ms 13.9 < 15 (min rail-exit speed); Booster 1 landing_ms 12.3 > 6; Booster 2 landing_ms 11.6 > 6)
- `g_54subminl3__p2` (apogee_low, converted): no nose weight on this airframe passes every target and gate
- `g_bigheavy1_simulation__p2` (apogee_high, synthesized): no nose weight on this airframe passes every target and gate
- `g_czech_rocket_challenge_2025_raketa__p2` (landing_fast, none): motor 'GragasMAY24' is not in the pinned database
- `g_gabrielpresley_arrow__p2` (low_margin, synthesized): could not put apogee on the target (lightest design reaches 831.4 m)
- `g_locprecision_starburst_pk_28__p4` (apogee_low, converted): no nose weight on this airframe passes every target and gate
- `g_mojave_sphinx_v1_2__p2` (rail_exit_slow, none): motor 'L839' is not in the pinned database
- `g_parallel_booster_staging__p3` (low_margin, synthesized): could not put apogee on the target (lightest design reaches 771.1 m)
- `g_rocket__p2` (apogee_high, none): motor 'fenix' is not in the pinned database
- `g_rocket_1cd69d__p2` (apogee_low, synthesized): no nose weight on this airframe passes every target and gate
- `g_rocket_61cb00__p2` (apogee_low, converted): no nose weight on this airframe passes every target and gate
- `g_rocket_620f66__p2` (low_margin, synthesized): could not put apogee on the target (lightest design reaches 6824.6 m)
- `g_rocket_d5a7f2__p2` (landing_fast, none): motor 'Team01_Test_220626' is not in the pinned database
- `g_rocket_d77051__p2` (low_margin, none): motor 'KERON' is not in the pinned database
- `g_rocket_f39723__p2` (apogee_low, converted): no nose weight on this airframe passes every target and gate
- `g_rocket_fdc85b__p2` (low_margin, none): motor 'Amalia 6s5 EuRoC' is not in the pinned database
- `g_rocketproject__p3` (apogee_high, converted): rail exit or thrust-to-weight stays under the gate after removing ballast
- `g_simulation_1__p2` (landing_fast, none): motor 'E17' is not in the pinned database
- `g_siriusrocketry_eradicator_s_0017__p3` (apogee_high, synthesized): no nose weight on this airframe passes every target and gate
