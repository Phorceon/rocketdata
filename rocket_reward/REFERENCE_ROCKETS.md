# Reference rockets the reward does not pass

For the people who own the training data. This list comes from the latest
calibration run: every one of the 594 reference rows (197 distinct designs,
`sft_v5_meta_c94ffa5.jsonl`) scored through the whole ladder with
`tools/calibrate.py`, on 2026-11-19, with the package as it is now.

| | rows | designs |
|---|---|---|
| reach the targets stage (stage 7) | 498 | 165 |
| stop at stage 4, limits | 24 | 8 |
| stop at stage 5, build | 30 | 10 |
| stop at stage 6, flight | 42 | 14 |
| **do not pass (stages 4-6)** | **96** | **32** |
| pass, but carry a defect (score 0.975-0.985 instead of up to 1.0) | 12 | 4 |

No reference stops at stages 1-3. Every design is used by three rows (the
original, casual and engineering prompt styles), and all three stop at the
same place.

The RL prompt file (`prompts/rl_prompts_v1.jsonl`, 482 rows) leaves out all
of these: the 96 rows that do not pass, the 12 rows with a defect (they
cannot reach the 0.99 the prompt builder asks of a reference) and 4 rows whose
prompt names a motor the design does not fly (see the end). That is 112 rows
in all, listed with their reasons in `prompts/excluded_references.jsonl`.

The rules and limits are in [DESIGN.md](DESIGN.md) and `limits.py`. Each
sentence below says what is wrong with the design as written; fixing the
design file (or dropping the row) is the data owners' call.

## Cannot be built (stages 1-5)

### Stage 4: limits (sizes, counts and materials)

| design | source file | stage | rule and measured value | what is wrong |
|---|---|---|---|---|
| V4-0021 | 75MDL3.ork | limits (0.311) | body tube wall 0 mm (at least 0.13 mm); wall areal density 0 kg/m2 (at least 0.045) | A body tube has no wall at all, so it weighs nothing. |
| V4-0075 | ESTES Alpha 3.ork | limits (0.324) | fin thickness 0.1 mm (at least 0.5 mm) | The fins are thinner than paper. |
| V4-0101 | OpenRocket Estes Super Shot Design.ork | limits (0.311) | fin thickness 0.0002667 mm (at least 0.5 mm); fin areal density 0.00035 kg/m2 (at least 0.12) | The fins are a film a quarter of a micrometre thick. |
| V4-0163 | estes_antar_7310.ork | limits (0.322) | fin thickness 0.07857 mm (at least 0.5 mm) | One fin set is thinner than paper. |
| V4-0165 | estes_black_brant_xii_9723.ork | limits (0.320) | body tube radius 0.0127 mm (at least 2.5 mm) | A body tube is a hair-thin stub, a modelling trick rather than a part. |
| V4-0167 | estes_boosted_bertha_1946.ork | limits (0.361) | 124 parts (at most 100) | The design has more parts than the cap; with the earlier cap of 150 it stopped at flight instead (rail exit 9.0 m/s, at least 11). |
| V4-0172 | estes_rubicon_2189.ork | limits (0.333) | material name 'Custom' (written 0 kg/m3) is not a known material; 134 parts (at most 100) | A transition uses a made-up material with no density, and the design has more parts than the cap. |
| V4-0232 | starfire_star_crusher.ork | limits (0.311) | body tube radius 0.0127 mm (at least 2.5 mm); tube fins 976 times the body radius (at most 1) | A body tube is a hair-thin stub carrying full-size tube fins. |

V4-0165, V4-0167, V4-0168 and V4-0172 are in the meta file but not in the
`sft_v5` training files, so the stage 1-4 check of the 582 training answers
never saw them.

### Stage 5: build (OpenRocket builds it and the parts fit)

| design | source file | stage | rule and measured value | what is wrong |
|---|---|---|---|---|
| V4-0002 | 02.Two-stage.ork | build (0.415) | fin root 5.0 chords past the back of its tube (at most 0.5); overrides move the balance point 3.41 cal (at most 1.5) | The fins hang off the back of their tube, and mass overrides fake the stability. |
| V4-0062 | Base drag hack (short-wide).ork | build (0.417) | outer radius step 100% (at most 10%); motor back end 0.24 m ahead of the tail (at most 0.15 m) | A deliberate base-drag trick: the body ends in a needle-thin transition and the motor fires into the airframe. |
| V4-0195 | rocket_11.ork | build (0.444) | motor hangs 88% of its length out of its mount (at most 50%) | The motor mount tube is far too short for the K motor. |
| V4-0210 | rocket_3_1.ork | build (0.445) | engine block 34 mm outside the airframe (at most 20 mm) | The engine block sits entirely outside the body tube. |
| V4-0213 | rocket_5.ork | build (0.440) | fin root 1.0 chord past the back of its tube (at most 0.5) | The fins start where the body tube ends, so they hang off the back. |
| V4-0215 | rocket_6.ork | build (0.440) | fin root 1.0 chord past the back of its tube (at most 0.5) | The same fault as V4-0213. |
| V4-0222 | rocketarium_trident.ork | build (0.441) | overrides move the balance point 2.94 cal towards the nose (at most 1.5) | The rocket is made stable by a mass override, not by its parts. |
| V4-0227 | siriusrocketry_eradicator_s-0017.ork | build (0.418) | outer radius step 26% (at most 10%); two pods start with an open body tube | The body steps down in width with no transition, and the pods have no nose cones. |
| V4-0229 | starfire73_steel_rain.ork | build (0.413) | outer radius step 100% (at most 10%); motor back end 0.60 m ahead of the tail (at most 0.15 m) | The same base-drag trick as V4-0062, with the motor deep inside the body. |
| V4-0230 | starfire73_talon.ork | build (0.431) | two centering rings pushed 10.5 mm into each other (at most 3.5 mm) | Two centering rings occupy the same place. |

## Unsafe to fly (stage 6)

| design | source file | stage | rule and measured value | what is wrong |
|---|---|---|---|---|
| V4-0003 | 03.Three-stage.ork | flight (0.591) | stability leaving the rail -0.39 cal in 3 m/s wind (above 0) | The three-stage stack is unstable off the rail in the strongest wind. |
| V4-0048 | Argonia_1p79OD_trans_2p240OD_SkinnyK627LR-7_SIM_9-15-24_SPINNY.ork | flight (0.545) | stability during the burn -20.16 cal (above 0) | The rocket becomes badly unstable while the motor burns. |
| V4-0049 | Argonia_1p79OD_trans_2p240OD_SkinnyK627LR-7_SIM_9-15-24_SPINNY2.ork | flight (0.609) | stability during the burn -0.55 cal in 8 m/s wind (above 0) | The rocket goes unstable during the burn in the strongest wind. |
| V4-0120 | RocketProject.ork | flight (0.624) | recovery opens at 81.8 m/s (at most 60) | The parachute opens while the rocket is still moving fast, far from apogee; the ejection delay does not suit the motor. |
| V4-0171 | estes_patriot.ork | flight (0.673) | stability on the pad 0.973 cal (at least 1.0) | The rocket is just short of one calibre of stability on the pad (see the note below). |
| V4-0285 | PML_MiniBBXwithTerrierBooster.ork | flight (0.579) | booster with no recovery lands at 60.1 m/s (at most 25) | The spent booster has no streamer or parachute and falls hard. |
| V4-0297 | PML_QuantumLeapCPR3K_38mmConfigurationE.ork | flight (0.582) | booster with no recovery lands at 56.8 m/s (at most 25) | The same as V4-0285. |
| V4-0298 | PML_QuantumLeapCPR3K_54mmConfigurationE.ork | flight (0.576) | booster with no recovery lands at 64.3 m/s (at most 25) | The same as V4-0285. |
| V4-0299 | PML_QuantumLeapII_38mmConfigurationE.ork | flight (0.582) | booster with no recovery lands at 57.1 m/s (at most 25) | The same as V4-0285. |
| V4-0302 | PML_QuantumLeapII_54mmConfigurationD.ork | flight (0.580) | booster with no recovery lands at 59.7 m/s (at most 25) | The same as V4-0285. |
| V4-0303 | PML_QuantumLeapII_54mmConfigurationE.ork | flight (0.581) | booster with no recovery lands at 58.6 m/s (at most 25) | The same as V4-0285. |
| V4-0304 | PML_QuantumLeap_38mm.ork | flight (0.584) | booster with no recovery lands at 55.1 m/s (at most 25) | The same as V4-0285. |
| V4-0305 | PML_QuantumLeap_54mm.ork | flight (0.577) | booster with no recovery lands at 63.8 m/s (at most 25) | The same as V4-0285. |
| V4-0316 | PML_ThundLight.ork | flight (0.588) | booster with no recovery lands at 51.8 m/s (at most 25) | The same as V4-0285. |

**Note on V4-0171.** Its file stores its own material densities, and with
those it measured 1.023 cal on the pad, just above the limit. The reward
never flies the densities a design writes: every known material name gets its
density from the material table (DESIGN.md section 5). With the table's
densities the rocket measures 0.973 cal and fails by 2.7%. The design was
never called unsafe. The stage 6 limits were measured on the references with
their written densities, so the owner should either re-measure those limits
on the designs as the reward flies them or accept V4-0171 as a failure. For
the same reason V4-0173 and V4-0224, once predicted to fail stage 6, now pass.

## Pass, but carry a defect

A defect is a small problem that does not stop the ladder; each one costs 5%
of the final credit.

| design | source file | score | defect |
|---|---|---|---|
| V4-0045 | ASTRAwFairing.ork | 0.985 | A mass component is 64% wider than the tube around it (at most 30%). |
| V4-0162 | estes_alpha_vi_1958.ork | 0.976-0.985 | A centering ring is 15% wider than the tube around it (at most 8%). |
| V4-0168 | estes_boosted_bertha_1946_mod24.ork | 0.985 | Mass overrides move the balance point 1.64 cal (at most 1.5). |
| V4-0189 | quest_seeker.ork | 0.975-0.985 | A centering ring is 23% wider than the tube around it (at most 8%). |

## Prompts that name another motor

These designs pass, but one of their prompts names a motor the design does
not fly as the reward reads it, so the row would lose its motor credit.

| row | prompt names | design flies |
|---|---|---|
| V4-0025 engineering | I216-CL(I) | 636I216-14A |
| V4-0076 casual and engineering | E20W | E15W |
| V4-0193 engineering | M1520-BS | 7579M1520-P |

## How to make this list again

From the folder that holds `rocket_reward`, with Java set up (README.md):

```
python -X utf8 -m rocket_reward.tools.calibrate --meta sft_v5_meta_c94ffa5.jsonl \
    --prompts parsed_prompts.jsonl --out calib.md --json calib.json
```

The report's "Failures" sections give the same designs, rules and values.
