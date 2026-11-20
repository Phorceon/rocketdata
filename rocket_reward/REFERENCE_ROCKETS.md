# Reference rockets the reward does not pass

For the people who own the training data. This list comes from the latest
calibration run: every one of the 594 reference rows (197 distinct designs,
`sft_v5_meta_c94ffa5.jsonl`) scored through the whole ladder with
`tools/calibrate.py`, on 2026-11-19, with the package as it is now.

Since 2026-11-19 the reward removes every override setting (`overridemass`,
`overridecg`, `overridecd` and their `overridesubcomponents` switches) before
it judges a design, and flies the design on its parts alone. Many reference
files write such overrides, so their numbers moved, and some designs that
passed with their overrides no longer do (see "Sound only with their
overrides" below).

The second round of rules on 2026-11-19 (pods, parts of a lower stage, the
rocket's slenderness, late and low parachute openings; DESIGN.md section 7)
was checked by scoring the 197 designs again (one row each, the design's
first prompt): every design stops at the same stage as below, and only two
scores changed, V4-0189 and V4-0227, both already failing; their rows below
give the new values. The row counts were not re-run. The third pass (nested
pods, pod overhang as a share, the slenderness width, rings counted from the
coupler that holds them) was checked the same way: every design keeps the
stage and score it had after the second round.

| | rows | designs |
|---|---|---|
| reach the targets stage (stage 7) | 480 | 159 |
| stop at stage 4, limits | 36 | 12 |
| stop at stage 5, build | 21 | 7 |
| stop at stage 6, flight | 57 | 19 |
| **do not pass (stages 4-6)** | **114** | **38** |
| pass, but carry a defect | 3 | 1 |

No reference stops at stages 1-3. Every design is used by three rows (the
original, casual and engineering prompt styles), and all three stop at the
same place. Nine rows carry a defect in all: the 3 rows that pass and the 6
rows of V4-0162 and V4-0189, which now stop at stage 6.

The RL prompt file (`prompts/rl_prompts_v1.jsonl`, 474 rows: train 385, val
36, test 53) leaves out all of these: the 114 rows that do not pass, the 3
rows with a defect (they cannot reach the 0.99 the prompt builder asks of a
reference) and 3 rows whose prompt names a motor the design does not fly (see
the end). That is 120 rows in all, listed with their reasons in
`prompts/excluded_references.jsonl`. Every kept row's reference answer scores
exactly 1.0 on its own record.

The rules and limits are in [DESIGN.md](DESIGN.md) and `limits.py`. Each
sentence below says what is wrong with the design as written; fixing the
design file (or dropping the row) is the data owners' call.

## Cannot be built (stages 1-5)

### Stage 4: limits (sizes, counts and materials)

| design | source file | stage | rule and measured value | what is wrong |
|---|---|---|---|---|
| V4-0021 | 75MDL3.ork | limits (0.311) | body tube wall 0 mm (at least 0.13 mm); wall areal density 0 kg/m2 (at least 0.045) | A body tube has no wall at all, so it weighs nothing. |
| V4-0062 | Base drag hack (short-wide).ork | limits (0.320) | transition wall 0.0254 mm (at least 0.13 mm); wall areal density 0.03048 kg/m2 (at least 0.045) | A deliberate base-drag trick: the body ends in a needle-thin transition (radius 0.01514 mm) and the motor fires into the airframe (its back end 0.24 m ahead of the tail). The transition's paper-thin wall was covered by a mass override; with overrides removed it now stops at stage 4 before stage 5 finds the rest. |
| V4-0075 | ESTES Alpha 3.ork | limits (0.324) | fin thickness 0.1 mm (at least 0.5 mm) | The fins are thinner than paper. |
| V4-0101 | OpenRocket Estes Super Shot Design.ork | limits (0.311) | fin thickness 0.0002667 mm (at least 0.5 mm); fin areal density 0.00035 kg/m2 (at least 0.12) | The fins are a film a quarter of a micrometre thick. |
| V4-0163 | estes_antar_7310.ork | limits (0.307) | nose cone wall 0 mm (at least 0.13 mm); fin thickness 0.07857 mm (at least 0.5 mm) | The nose cone has no wall (a mass override used to stand in for it) and one fin set is thinner than paper. |
| V4-0165 | estes_black_brant_xii_9723.ork | limits (0.320) | body tube radius 0.0127 mm (at least 2.5 mm) | A body tube is a hair-thin stub, a modelling trick rather than a part. |
| V4-0167 | estes_boosted_bertha_1946.ork | limits (0.361) | 124 parts (at most 100) | The design has more parts than the cap. |
| V4-0172 | estes_rubicon_2189.ork | limits (0.301) | material name 'Custom' (written 0 kg/m3) is not a known material; body tubes of radius 0 and wall 0 mm (a written 0 is no longer read as "auto"); 134 parts (at most 100) | A transition uses a made-up material with no density, several pod tubes have no size, and the design has more parts than the cap. |
| V4-0222 | rocketarium_trident.ork | limits (0.306) | nose cone wall 0 mm and a body tube wall 0 mm (at least 0.13 mm) | The nose cone and a body tube have no walls. Before overrides were removed it stopped at stage 5 instead: its mass overrides moved the balance point 2.94 calibres towards the nose, so its stability came from the override, not from its parts. |
| V4-0229 | starfire73_steel_rain.ork | limits (0.311) | transition wall 0.00254 mm (at least 0.13 mm); wall areal density 0.0004318 kg/m2 (at least 0.045) | The same base-drag trick as V4-0062 (transition radius 0.00127 mm, motor back end 0.60 m ahead of the tail); the thin wall was covered by a mass override. |
| V4-0232 | starfire_star_crusher.ork | limits (0.306) | body tube radius 0.0127 mm (at least 2.5 mm) and wall 0.0127 mm (at least 0.13 mm); tube fins 976 times the body radius (at most 1) | A body tube is a hair-thin stub carrying full-size tube fins. |

V4-0225 also stops here; it is listed under "Sound only with their
overrides". V4-0165, V4-0167 and V4-0172 are in the meta file but not in the
`sft_v5` training files, so the stage 1-4 check of the training answers never
saw them.

### Stage 5: build (OpenRocket builds it and the parts fit)

| design | source file | stage | rule and measured value | what is wrong |
|---|---|---|---|---|
| V4-0002 | 02.Two-stage.ork | build (0.420) | fin root 5.0 chords past the back of its tube (at most 0.5) | The fins hang off the back of their tube. Its mass overrides also faked the stability (4.56 cal with them, 1.15 cal on its parts alone). |
| V4-0195 | rocket_11.ork | build (0.444) | motor hangs 88% of its length out of its mount (at most 50%) | The motor mount tube is far too short for the K motor. |
| V4-0210 | rocket_3_1.ork | build (0.442) | engine block lies 38 mm behind the back of the airframe (at most 20 mm) | The engine block sits entirely outside the body tube. |
| V4-0213 | rocket_5.ork | build (0.440) | fin root 1.0 chord past the back of its tube (at most 0.5) | The fins start where the body tube ends, so they hang off the back. |
| V4-0215 | rocket_6.ork | build (0.440) | fin root 1.0 chord past the back of its tube (at most 0.5) | The same fault as V4-0213. |
| V4-0227 | siriusrocketry_eradicator_s-0017.ork | build (0.410) | outer radius step 26% (at most 10%); both pods' axes 0 mm from the centre line, so 100% of each pod's 38.1 mm radius lies inside the 28.5 mm body that holds it (at most 50%); two pods start with an open body tube | The body steps down in width with no transition, and the pods sit on the centre line inside the body and have no nose cones. |
| V4-0230 | starfire73_talon.ork | build (0.431) | two centering rings pushed 10.49 mm into each other (at most 3.5 mm) | Two centering rings occupy the same place. |

## Unsafe to fly (stage 6)

| design | source file | stage | rule and measured value | what is wrong |
|---|---|---|---|---|
| V4-0003 | 03.Three-stage.ork | flight (0.597) | stability leaving the rail -0.33 cal in 3 m/s wind (above 0) | The three-stage stack is unstable off the rail in the strongest wind. |
| V4-0048 | Argonia_1p79OD_trans_2p240OD_SkinnyK627LR-7_SIM_9-15-24_SPINNY.ork | flight (0.545) | stability during the burn -20.42 cal (above 0) | The rocket becomes badly unstable while the motor burns. |
| V4-0049 | Argonia_1p79OD_trans_2p240OD_SkinnyK627LR-7_SIM_9-15-24_SPINNY2.ork | flight (0.594) | stability during the burn -0.82 cal in 8 m/s wind (above 0) | The rocket goes unstable during the burn in the strongest wind. |
| V4-0120 | RocketProject.ork | flight (0.624) | recovery opens at 82.3 m/s (at most 60) | The parachute opens while the rocket is still moving fast, far from apogee; the ejection delay does not suit the motor. |
| V4-0171 | estes_patriot.ork | flight (0.648) | stability on the pad 0.86 cal (at least 1.0) | The rocket is short of one calibre of stability on the pad (see the note below). |
| V4-0285 | PML_MiniBBXwithTerrierBooster.ork | flight (0.579) | booster with no recovery lands at 60.4 m/s (at most 25) | The spent booster has no streamer or parachute and falls hard. |
| V4-0297 | PML_QuantumLeapCPR3K_38mmConfigurationE.ork | flight (0.582) | booster with no recovery lands at 56.8 m/s (at most 25) | The same as V4-0285. |
| V4-0298 | PML_QuantumLeapCPR3K_54mmConfigurationE.ork | flight (0.576) | booster with no recovery lands at 64.3 m/s (at most 25) | The same as V4-0285. |
| V4-0299 | PML_QuantumLeapII_38mmConfigurationE.ork | flight (0.582) | booster with no recovery lands at 57.0 m/s (at most 25) | The same as V4-0285. |
| V4-0302 | PML_QuantumLeapII_54mmConfigurationD.ork | flight (0.580) | booster with no recovery lands at 59.7 m/s (at most 25) | The same as V4-0285. |
| V4-0303 | PML_QuantumLeapII_54mmConfigurationE.ork | flight (0.581) | booster with no recovery lands at 58.6 m/s (at most 25) | The same as V4-0285. |
| V4-0304 | PML_QuantumLeap_38mm.ork | flight (0.584) | booster with no recovery lands at 55.1 m/s (at most 25) | The same as V4-0285. |
| V4-0305 | PML_QuantumLeap_54mm.ork | flight (0.577) | booster with no recovery lands at 63.8 m/s (at most 25) | The same as V4-0285. |
| V4-0316 | PML_ThundLight.ork | flight (0.587) | booster with no recovery lands at 52.0 m/s (at most 25) | The same as V4-0285. |

Five more designs stop here; they are listed under "Sound only with their
overrides".

**Note on V4-0171.** Its file stores its own material densities, and with
those it measured 1.023 cal on the pad, just above the limit. The reward
never flies the densities a design writes: every known material name gets its
density from the material table (DESIGN.md section 5). With the table's
densities and the file's mass overrides the rocket measured 0.973 cal; now
that the overrides are removed it measures 0.86 cal on its parts alone. The
stage 6 limits were measured on the references with their written densities
and overrides, so the owner should either re-measure those limits on the
designs as the reward flies them or accept V4-0171 as a failure. For the same
reason V4-0173 and V4-0224, once predicted to fail stage 6, pass.

## Sound only with their overrides

These designs passed (stage 7) while the reward honoured the mass and balance
overrides their files write. The overrides hold the designer's measured mass
or balance point, so the rocket as built may well be sound, but the parts the
file describes do not add up to it, and the reward now flies the parts alone.
The fix is to describe the real mass as parts (a mass component for ballast,
real wall thicknesses) instead of an override.

| design | source file | stage now | rule and measured value now | with the overrides (earlier run) |
|---|---|---|---|---|
| V4-0025 | APEX 30.08.2021.ork | flight (0.649-0.650) | stability leaving the rail -0.00 cal in 6 m/s wind (above 0) | targets; liftoff mass 1.545 kg instead of 1.828 kg on its parts |
| V4-0027 | APEXJTentative.ork | flight (0.646) | recovery opens at 70.4 m/s (at most 60) | targets; recovery opened at 58.5 m/s |
| V4-0162 | estes_alpha_vi_1958.ork | flight (0.588) | stability on the pad 0.52 cal (at least 1.0) | targets with one defect; 1.31 cal on the pad |
| V4-0166 | estes_blu-97b_cluster_bomb_2055-1246.ork | flight (0.639) | stability on the pad 0.82 cal (at least 1.0) | targets; 1.29 cal on the pad |
| V4-0189 | quest_seeker.ork | flight (0.536) | in 3 m/s wind its last recovery device opens only 0.1 s before the section lands (at least 3 s), and it lands at 15.1 m/s (at most 9) | targets with one defect; liftoff mass 0.088 kg instead of 0.115 kg on its parts |
| V4-0225 | semroc_starfire_kv-20.ork | limits (0.311) | transition wall 0.000254 mm (at least 0.13 mm); wall areal density 0.0002848 kg/m2 (at least 0.045) | targets (1.0); the mass override stood in for the transition's weight |

V4-0162 and V4-0189 also still carry their fit defect (a centering ring 15%
and 23% wider than the tube around it, at most 8%).

V4-0168 (`estes_boosted_bertha_1946_mod24.ork`) went the other way: it used
to pass with a defect because its mass overrides moved the balance point 1.64
calibres; with the overrides removed it scores 1.0 with no defect.

## Pass, but carry a defect

A defect is a small problem that does not stop the ladder; each one costs 5%
of the final credit.

| design | source file | score | defect |
|---|---|---|---|
| V4-0045 | ASTRAwFairing.ork | 0.820-0.878 on its original prompts, 0.985 on its own rewritten prompt | A mass component is 64% wider than the tube around it (at most 30%). |

## Prompts that name another motor

These designs pass, but one of their prompts names a motor the design does
not fly as the reward reads it, so the row would lose half its motor credit
(it scores 0.85 on its own rewritten prompt).

| row | prompt names | design flies |
|---|---|---|
| V4-0076 casual and engineering | E20W | E15W |
| V4-0193 engineering | M1520-BS | 7579M1520-P |

V4-0025 engineering (prompt names I216-CL(I), the design flies 636I216-14A)
was in this list before; it now stops at stage 6 (see "Sound only with their
overrides").

## How to make this list again

From the folder that holds `rocket_reward`, with Java set up (README.md):

```
python -X utf8 -m rocket_reward.tools.calibrate --meta sft_v5_meta_c94ffa5.jsonl \
    --prompts parsed_prompts.jsonl --out calib.md --json calib.json
```

The report's "Failures" sections give the same designs, rules and values. The
prompt file and its list of left-out rows are re-made with

```
python -X utf8 -m rocket_reward.tools.build_rl_prompts --meta sft_v5_meta_c94ffa5.jsonl \
    --out-dir rocket_reward/prompts
```
