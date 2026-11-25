# Readable SFT v1

A human-readable view of `new_results/sft_v1.jsonl` (the balanced SFT v1 training split), one section per difficulty level. Difficulty is based ONLY on the number of requirements stated in the prompt: a requirement is counted when its value appears in the prompt and matches the rocket's target or simulated value (rounding, thousands separators and unit conversions allowed). A named motor counts as a requirement. More stated requirements = easier, because the task is more constrained.

| Level | Requirements | Count | What it means |
|---|---|---|---|
| Easy | 3 requirements | 60 | Prompt states 3 target values, so lots of freedom is allowed |
| Medium | 2 requirements | 109 | Prompt states 2 target values |
| Hard | 0–1 requirements | 13 | Prompt states 0 or 1 target value (very open-ended) |

**Total rows:** 182 · **Distinct rockets:** 85

## ⚠️ Prompt doesn't match its rocket

These rows have a prompt whose numbers do not describe the rocket they are paired with (or contain a broken value). They are listed here for visibility and left unchanged.

- **U-197** — prompt contains literal 'None m/s' for deployment (broken template)
  - Prompt: Design a rocket that goes to about 5,748 m apogee with deployment at about None m/s and a 28 s flight.
  - Targets: apogee 5747.8 m · max velocity 612.43 m/s · time to apogee 28.39 s · flight time 28.49 s · touchdown — m/s · wind 2 m/s
- **U-199** — prompt asks for 5,899 m apogee / 317 s flight; rocket actually flies 5,748 m and lands after 28.5 s
  - Prompt: Design a rocket that goes to about 5,899 m apogee with a total flight time of about 317 s.
  - Targets: apogee 5747.8 m · max velocity 612.43 m/s · time to apogee 28.39 s · flight time 28.49 s · touchdown — m/s · wind 2 m/s
- **U-441** — prompt asks for 244 m / 61 s; rocket actually flies 31.9 m over 10.3 s
  - Prompt: Make a rocket that hits 244 m and stays up about 61 s, weighs around 84 g and is about 44 cm long.
  - Targets: apogee 31.928 m · max velocity 24.753 m/s · time to apogee 2.807 s · flight time 10.323 s · touchdown 4.892 m/s · wind 2.2352 m/s
- **U-443** — prompt asks for 263 m / 73 s; rocket actually flies 31.8 m over 10.8 s
  - Prompt: Make a rocket that hits 263 m and stays up about 73 s, weighs around 88 g and is about 50 cm long.
  - Targets: apogee 31.783 m · max velocity 21.802 m/s · time to apogee 2.867 s · flight time 10.759 s · touchdown 4.398 m/s · wind 2 m/s
- **U-444** — prompt asks for 273 m / 70 s; rocket actually flies 38.7 m over 12.2 s
  - Prompt: Make a rocket that hits 273 m and stays up about 70 s, weighs around 81 g and is about 33 cm long.
  - Targets: apogee 38.733 m · max velocity 24.764 m/s · time to apogee 3.085 s · flight time 12.194 s · touchdown 4.691 m/s · wind 2 m/s
- **U-452** — prompt asks for 307 m / 59 s; rocket actually flies 57.9 m over 13.7 s
  - Prompt: Make a rocket that hits 307 m and stays up about 59 s, weighs around 262 g and is about 70 cm long.
  - Targets: apogee 57.857 m · max velocity 32.36 m/s · time to apogee 3.622 s · flight time 13.745 s · touchdown 6.27 m/s · wind 2 m/s

## Contents

- [🟢 Easy (60)](#easy-60)
- [🟡 Medium (109)](#medium-109)
- [🔴 Hard (13)](#hard-13)

<a id="easy-60"></a>

## 🟢 Easy (60)

### NEW-001 · EASY
**Prompt:** Design a rocket on a B6 motor that reaches about 170 m and stays up just over a minute.
**Rocket:** `ork/Comet Chaser.ork` · **Sim:** Simulation 5 · **Motor:** B6
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 171.41 m · max velocity 88.338 m/s · time to apogee 5.072 s · flight time 66.391 s · touchdown 3.003 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on a B6 motor that reaches about 170 m and stays up just over a minute.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 171 m (562 ft)
- Time to apogee: 5.1 s
- Peak velocity: 88 m/s (Mach 0.26)

3. RECOVERY & DESCENT:
- Parachute 0.33 m diameter, deploys at ejection
- Total flight time 66 s; descent from apogee takes 61 s
- Touchdown velocity: 3.00 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.03543,"material":"Balsa","name":"Nose cone"},{"type":"bodytube","length_m":0.0762,"wall_thickness_m":0.00038,"material":"Cardboard","name":"Body tube"},{"type":"transition","shape":"conical","length_m":0.0268,"fore_d_m":0.02504,"material":"Balsa","name":"Transition"},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.01854,"wall_thickness_m":0.00014,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3302,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (thin)","name":"Parachute"},{"type":"launchlug","length_m":0.0508,"name":"Launch lug"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.001,"kind":"recoveryhardware"}]},{"type":"bodytube","length_m":0.0762,"outer_d_m":0.01854,"wall_thickness_m":0.00014,"material":"Cardboard","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00152,"material":"Cardboard","name":"Freeform fin set"},{"type":"engineblock","name":"Engine block"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.0005,"kind":"masscomponent"},{"type":"innertube","length_m":0.007,"outer_d_m":0.0191,"wall_thickness_m":0.00955,"material":"Kraft phenolic","name":"Inner Tube"}],"motors":[{"manufacturer":"Estes","designation":"B6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"}]}]}
</design>
```
</details>

### NEW-004 · EASY
**Prompt:** Build a rocket on an A6 motor that reaches about 105 m and hangs in the air for about 30 seconds.
**Rocket:** `ork/ESTES Alpha 3.ork` · **Sim:** Simulation 1 · **Motor:** A6
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 105.318 m · max velocity 50.565 m/s · time to apogee 4.705 s · flight time 30.476 s · touchdown 4.455 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Build a rocket on an A6 motor that reaches about 105 m and hangs in the air for about 30 seconds.

2. PROPULSION & ASCENT:
- Motor: A6
- Simulated apogee: 105 m (346 ft)
- Time to apogee: 4.7 s
- Peak velocity: 51 m/s (Mach 0.15)

3. RECOVERY & DESCENT:
- Parachute 0.25 m diameter, deploys at ejection
- Total flight time 30 s; descent from apogee takes 26 s
- Touchdown velocity: 4.46 m/s
</thought>
<design>
{"flight":{"motor":"A6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Hauptstufe","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.065,"base_radius_m":0.0124,"wall_thickness_m":0.002,"material":"PVC","name":"Spitze"},{"type":"bodytube","length_m":0.139,"outer_d_m":0.0248,"wall_thickness_m":0.0004,"material":"Cardboard","name":"K\u00f6rperrohr","contains":[{"type":"parachute","diameter_m":0.25,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (thin)","name":"Fallschirm"}]},{"type":"bodytube","length_m":0.057,"outer_d_m":0.0248,"wall_thickness_m":0.002,"material":"PVC","name":"K\u00f6rperrohr","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.057,"tip_chord_m":0.03,"span_m":0.04,"sweep_m":0.07,"thickness_m":0.0001,"material":"PVC","name":"Trapezoide Leitwerke"},{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Innenrohr","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]}]}
</design>
```
</details>

### NEW-008 · EASY
**Prompt:** Make a rocket on a D12 motor that reaches about 150 m and flies for roughly 34 seconds.
**Rocket:** `ork/Estes Impulse.ork` · **Sim:** Simulation 1 · **Motor:** D12
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 153.22 m · max velocity 52.003 m/s · time to apogee 6.023 s · flight time 33.922 s · touchdown 5.541 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket on a D12 motor that reaches about 150 m and flies for roughly 34 seconds.

2. PROPULSION & ASCENT:
- Motor: D12
- Simulated apogee: 153 m (503 ft)
- Time to apogee: 6.0 s
- Peak velocity: 52 m/s (Mach 0.15)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at ejection
- Total flight time 34 s; descent from apogee takes 28 s
- Touchdown velocity: 5.54 m/s
</thought>
<design>
{"flight":{"motor":"D12","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.24765,"base_radius_m":0.03175,"wall_thickness_m":0.00635,"material":"Polystyrene","name":"Nose Cone"},{"type":"bodytube","length_m":0.22225,"outer_d_m":0.0635,"wall_thickness_m":0.00086,"material":"Paper","preset":"Estes 31390","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Nylon fabric","preset":"Estes 002261","name":"Parachute, 24 in., nylon, 6 lines, PN 002261"}]},{"type":"bodytube","length_m":0.3937,"outer_d_m":0.0635,"wall_thickness_m":0.00086,"material":"Paper","preset":"Estes 31390","name":"Body Tube","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.1016,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Freeform Fin Set"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]}]}
</design>
```
</details>

### NEW-011 · EASY
**Prompt:** Design a rocket on an E20W motor that gets up around 345 m and stays in the air about 64 seconds.
**Rocket:** `ork/Estes Impulse.ork` · **Sim:** Simulation 4 · **Motor:** E20W
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 344.113 m · max velocity 95.538 m/s · time to apogee 8.075 s · flight time 64.452 s · touchdown 6.098 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on an E20W motor that gets up around 345 m and stays in the air about 64 seconds.

2. PROPULSION & ASCENT:
- Motor: E20W
- Simulated apogee: 344 m (1,129 ft)
- Time to apogee: 8.1 s
- Peak velocity: 96 m/s (Mach 0.28)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at ejection
- Total flight time 64 s; descent from apogee takes 56 s
- Touchdown velocity: 6.10 m/s
</thought>
<design>
{"flight":{"motor":"E20W","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.24765,"base_radius_m":0.03175,"wall_thickness_m":0.00635,"material":"Polystyrene","name":"Nose Cone"},{"type":"bodytube","length_m":0.22225,"outer_d_m":0.0635,"wall_thickness_m":0.00086,"material":"Paper","preset":"Estes 31390","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Nylon fabric","preset":"Estes 002261","name":"Parachute, 24 in., nylon, 6 lines, PN 002261"}]},{"type":"bodytube","length_m":0.3937,"outer_d_m":0.0635,"wall_thickness_m":0.00086,"material":"Paper","preset":"Estes 31390","name":"Body Tube","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.1016,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Freeform Fin Set"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]}]}
</design>
```
</details>

### NEW-012 · EASY
**Prompt:** Build a streamer-recovery rocket on an A8 motor that reaches about 180 m in under 20 seconds.
**Rocket:** `ork/Estes_Mark2.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 179.58 m · max velocity 83.133 m/s · time to apogee 5.487 s · flight time 17.262 s · touchdown 17.5 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 streamer recovery
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Build a streamer-recovery rocket on an A8 motor that reaches about 180 m in under 20 seconds.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 180 m (589 ft)
- Time to apogee: 5.5 s
- Peak velocity: 83 m/s (Mach 0.24)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 17 s; descent from apogee takes 12 s
- Touchdown velocity: 17.50 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.05558,"base_radius_m":0.00972,"material":"Balsa","name":"BNC-30E"},{"type":"bodytube","length_m":0.0889,"wall_thickness_m":0.00053,"material":"Cardboard","name":"BT-30A","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.0254,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"}]},{"type":"bodytube","length_m":0.06985,"wall_thickness_m":0.00053,"material":"Cardboard","name":"BT-30J","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"launchlug","length_m":0.03175,"name":"LL-2A"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-014 · EASY
**Prompt:** Make a rocket on a C6 motor that goes close to 470 m and is back down in about 36 seconds.
**Rocket:** `ork/Estes_Mark2.ork` · **Sim:** Simulation 3 · **Motor:** C6
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 468.73 m · max velocity 173.88 m/s · time to apogee 7.493 s · flight time 36.303 s · touchdown 16.946 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 streamer recovery
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket on a C6 motor that goes close to 470 m and is back down in about 36 seconds.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 469 m (1,538 ft)
- Time to apogee: 7.5 s
- Peak velocity: 174 m/s (Mach 0.51)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 36 s; descent from apogee takes 29 s
- Touchdown velocity: 16.95 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.05558,"base_radius_m":0.00972,"material":"Balsa","name":"BNC-30E"},{"type":"bodytube","length_m":0.0889,"wall_thickness_m":0.00053,"material":"Cardboard","name":"BT-30A","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.0254,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"}]},{"type":"bodytube","length_m":0.06985,"wall_thickness_m":0.00053,"material":"Cardboard","name":"BT-30J","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"launchlug","length_m":0.03175,"name":"LL-2A"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-016 · EASY
**Prompt:** Make a rocket on an A8 motor that reaches about 175 m and is back down in about 14 seconds.
**Rocket:** `ork/Estes Wizard.ork` · **Sim:** Simulation 2 · **Motor:** A8
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 176.616 m · max velocity 77.908 m/s · time to apogee 5.548 s · flight time 14.144 s · touchdown 25.582 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 1 streamer recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket on an A8 motor that reaches about 175 m and is back down in about 14 seconds.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 177 m (579 ft)
- Time to apogee: 5.5 s
- Peak velocity: 78 m/s (Mach 0.23)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 14 s; descent from apogee takes 9 s
- Touchdown velocity: 25.58 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.07,"base_radius_m":0.00935,"wall_thickness_m":0.00159,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.221,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes EST 3085","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"streamer","strip_length_m":0.45,"strip_width_m":0.03,"deploy_event":"ejection","material":"Polyethylene (thin)","name":"Streamer"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00157,"material":"Balsa","name":"Freeform fin set"}],"motors":[{"manufacturer":"Estes","designation":"A8"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"}]}]}
</design>
```
</details>

### NEW-019 · EASY
**Prompt:** Make a rocket that reaches about 175 m on a C6 motor and is down in about 24 seconds.
**Rocket:** `ork/FlipFlyer.ork` · **Sim:** Simulation 3 · **Motor:** C6
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 175.56 m · max velocity 56.58 m/s · time to apogee 6.502 s · flight time 23.894 s · touchdown 14.539 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 3 fins, 2 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that reaches about 175 m on a C6 motor and is down in about 24 seconds.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 176 m (576 ft)
- Time to apogee: 6.5 s
- Peak velocity: 57 m/s (Mach 0.17)

3. RECOVERY & DESCENT:
- Parachute 0.23 m diameter, deploys at ejection
- Total flight time 24 s; descent from apogee takes 17 s
- Touchdown velocity: 14.54 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Nose","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06985,"base_radius_m":0.0124,"wall_thickness_m":0.00157,"material":"Polystyrene","preset":"Estes PNC-50KA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Nose Clay","mass_kg":0.01451,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.128,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50, 30352","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"parachute","diameter_m":0.2286,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes parachute_9in, 002268","name":"Parachute"}]}]},{"type":"stage_marker","name":"Sustainer","contains":[{"type":"bodytube","length_m":0.2,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50, 30352","name":"Body tube","contains":[{"type":"launchlug","length_m":0.055,"name":"Launch lug"}]},{"type":"bodytube","length_m":0.065,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"PVC","name":"Engine mount and fin box","contains":[{"type":"engineblock","name":"Engine block"},{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Motor Mount","motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.001,"material":"PVC","name":"Notched PVC Fins"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.23,"tip_chord_m":0.22,"span_m":0.001,"sweep_m":0.025,"thickness_m":0.025,"material":"PVC","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-021 · EASY
**Prompt:** Design a rocket on a C6 motor that reaches around 245 m and floats down for about a minute and a half.
**Rocket:** `ork/OpenRocket Estes Super Shot Design.ork` · **Sim:** Fight Path Recovery · **Motor:** C6
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 247.058 m · max velocity 81.115 m/s · time to apogee 6.965 s · flight time 91.752 s · touchdown 2.931 m/s · wind 6.7056 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 2 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on a C6 motor that reaches around 245 m and floats down for about a minute and a half.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 247 m (811 ft)
- Time to apogee: 7.0 s
- Peak velocity: 81 m/s (Mach 0.24)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 92 s; descent from apogee takes 85 s
- Touchdown velocity: 2.93 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":6.7056},"components":[{"type":"stage_marker","name":"Sustainer"},{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":0.11639,"base_radius_m":0.01231,"wall_thickness_m":0.001,"material":"Styrene Plastic","name":"Nose Cone"},{"type":"bodytube","length_m":0.229,"outer_d_m":0.0248,"wall_thickness_m":0.00045,"material":"Cardboard","name":"Estes Super Shot Body Tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes parachute_18in, 035823","name":"Parachute, plastic, preassembled, 18 in., Der Red Max, PN 035823"},{"type":"masscomponent","name":"Estes Altimeter","mass_kg":0.01177,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.229,"outer_d_m":0.0248,"wall_thickness_m":0.00045,"material":"Cardboard","name":"Estes Super Shot Body Tube","contains":[{"type":"launchlug","length_m":0.058,"name":"Launch Lug"}]},{"type":"bodytube","length_m":0.09289,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Styrene Plastic","name":"Fin Tube","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.0,"material":"Styrene Plastic","name":"Freeform Fin Set"},{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-024 · EASY
**Prompt:** Design a rocket on an E9 motor that reaches about 375 m and stays up close to 100 seconds.
**Rocket:** `ork/Renegade.ork` · **Sim:** Simulation 1 · **Motor:** E9
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 377.12 m · max velocity 97.433 m/s · time to apogee 8.687 s · flight time 99.608 s · touchdown 3.929 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on an E9 motor that reaches about 375 m and stays up close to 100 seconds.

2. PROPULSION & ASCENT:
- Motor: E9
- Simulated apogee: 377 m (1,237 ft)
- Time to apogee: 8.7 s
- Peak velocity: 97 m/s (Mach 0.29)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 100 s; descent from apogee takes 91 s
- Touchdown velocity: 3.93 m/s
</thought>
<design>
{"flight":{"motor":"E9","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.17145,"base_radius_m":0.02079,"wall_thickness_m":0.00317,"material":"Polystyrene PS","preset":"Estes PNC-60AH","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"wall_thickness_m":0.00056,"material":"Cardboard","name":"BT-60","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.2159,"wall_thickness_m":0.00056,"material":"Cardboard","name":"BT-60HE","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00317,"material":"Balsa","name":"Freeform fin set"},{"type":"innertube","length_m":0.381,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-50KE","motors":[{"manufacturer":"Estes","designation":"E9"}]},{"type":"centeringring","material":"Fiber","name":"Centering ring"},{"type":"centeringring","material":"Fiber","name":"Centering ring"},{"type":"centeringring","material":"Fiber","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"E9"}]}],"motors":[{"manufacturer":"Estes","designation":"E9"}]}]}
</design>
```
</details>

### NEW-030 · EASY
**Prompt:** Make a rocket on an A8 motor that reaches about 190 m in around 15 seconds.
**Rocket:** `ork/estes-007275–STERLING_SILVER.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 192.57 m · max velocity 70.532 m/s · time to apogee 6.466 s · flight time 15.549 s · touchdown 28.93 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 6 fins, 2 stages, 1 streamer recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket on an A8 motor that reaches about 190 m in around 15 seconds.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 193 m (632 ft)
- Time to apogee: 6.5 s
- Peak velocity: 71 m/s (Mach 0.21)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 16 s; descent from apogee takes 9 s
- Touchdown velocity: 28.93 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06731,"base_radius_m":0.00935,"wall_thickness_m":0.00159,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.3048,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes EST 3085","name":"Body tube","contains":[{"type":"streamer","strip_length_m":0.762,"strip_width_m":0.03175,"deploy_event":"ejection","material":"Polyethylene (thin)","name":"Streamer"}]},{"type":"bodytube","length_m":0.07,"wall_thickness_m":0.00035,"material":"Cardboard","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.043,"tip_chord_m":0.0255,"span_m":0.03188,"sweep_m":0.03188,"thickness_m":0.00234,"material":"Balsa","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.08916,"wall_thickness_m":0.00035,"material":"Cardboard","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.06186,"tip_chord_m":0.04116,"span_m":0.04743,"sweep_m":0.04743,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-032 · EASY
**Prompt:** I want a rocket on a C6 motor that goes about 640 m and is down in around 35 seconds.
**Rocket:** `ork/estes-007275–STERLING_SILVER.ork` · **Sim:** Simulation 3 · **Motor:** C6
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 642.5 m · max velocity 156.64 m/s · time to apogee 10.412 s · flight time 34.775 s · touchdown 28.755 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 6 fins, 2 stages, 1 streamer recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I want a rocket on a C6 motor that goes about 640 m and is down in around 35 seconds.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 642 m (2,108 ft)
- Time to apogee: 10.4 s
- Peak velocity: 157 m/s (Mach 0.46)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 35 s; descent from apogee takes 24 s
- Touchdown velocity: 28.75 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06731,"base_radius_m":0.00935,"wall_thickness_m":0.00159,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.3048,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes EST 3085","name":"Body tube","contains":[{"type":"streamer","strip_length_m":0.762,"strip_width_m":0.03175,"deploy_event":"ejection","material":"Polyethylene (thin)","name":"Streamer"}]},{"type":"bodytube","length_m":0.07,"wall_thickness_m":0.00035,"material":"Cardboard","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.043,"tip_chord_m":0.0255,"span_m":0.03188,"sweep_m":0.03188,"thickness_m":0.00234,"material":"Balsa","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.08916,"wall_thickness_m":0.00035,"material":"Cardboard","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.06186,"tip_chord_m":0.04116,"span_m":0.04743,"sweep_m":0.04743,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### U-062 · EASY
**Prompt:** Design a rocket that goes to about 102.5 m/s max velocity with a 24.4 s flight and touchdown at about 43.8 m/s.
**Rocket:** `ork/openrocketdoc__example_simple_1.ork` · **Sim:** Simulation 1 · **Motor:** F15
**Why easy: 3 requirements: max velocity, flight time, touchdown speed**
**Targets:** apogee 474.48 m · max velocity 102.54 m/s · time to apogee 10.217 s · flight time 24.417 s · touchdown 43.819 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 102.5 m/s max velocity with a 24.4 s flight and touchdown at about 43.8 m/s.

2. PROPULSION & ASCENT:
- Motor: F15
- Simulated apogee: 474 m (1,557 ft)
- Time to apogee: 10.2 s
- Peak velocity: 103 m/s (Mach 0.30)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 24 s; descent from apogee takes 14 s
- Touchdown velocity: 43.82 m/s
</thought>
<design>
{"flight":{"motor":"F15","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.15,"wall_thickness_m":0.001,"material":"Polystyrene","name":"Nose cone","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"},{"type":"masscomponent","name":"Mass component","mass_kg":0.05}]},{"type":"bodytube","length_m":0.3,"wall_thickness_m":0.002,"material":"Kraft phenolic","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.08,"tip_chord_m":0.03,"span_m":0.05,"sweep_m":0.045,"thickness_m":0.003,"material":"Fiberglass","name":"Trapezoidal fin set"},{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Maple","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}]}
</design>
```
</details>

### U-063 · EASY
**Prompt:** Design a rocket that goes to about 102.5 m/s on a F15 motor, reaching apogee in about 10.2 s.
**Rocket:** `ork/openrocketdoc__example_simple_1.ork` · **Sim:** Simulation 1 · **Motor:** F15
**Why easy: 3 requirements: max velocity, time to apogee, motor**
**Targets:** apogee 474.48 m · max velocity 102.54 m/s · time to apogee 10.217 s · flight time 24.417 s · touchdown 43.819 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 102.5 m/s on a F15 motor, reaching apogee in about 10.2 s.

2. PROPULSION & ASCENT:
- Motor: F15
- Simulated apogee: 474 m (1,557 ft)
- Time to apogee: 10.2 s
- Peak velocity: 103 m/s (Mach 0.30)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 24 s; descent from apogee takes 14 s
- Touchdown velocity: 43.82 m/s
</thought>
<design>
{"flight":{"motor":"F15","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.15,"wall_thickness_m":0.001,"material":"Polystyrene","name":"Nose cone","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"},{"type":"masscomponent","name":"Mass component","mass_kg":0.05}]},{"type":"bodytube","length_m":0.3,"wall_thickness_m":0.002,"material":"Kraft phenolic","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.08,"tip_chord_m":0.03,"span_m":0.05,"sweep_m":0.045,"thickness_m":0.003,"material":"Fiberglass","name":"Trapezoidal fin set"},{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Maple","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}]}
</design>
```
</details>

### U-227 · EASY
**Prompt:** Design a rocket that goes to about 618 m apogee on a GragasMAY24 motor, taking about 11.4 s to apogee.
**Rocket:** `ork/czech-rocket-challenge-2025__Raketa.ork` · **Sim:** Simulation 1 · **Motor:** GragasMAY24
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 617.783 m · max velocity 127.543 m/s · time to apogee 11.408 s · flight time 146.734 s · touchdown 4.495 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 3 fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 618 m apogee on a GragasMAY24 motor, taking about 11.4 s to apogee.

2. PROPULSION & ASCENT:
- Motor: GragasMAY24
- Simulated apogee: 618 m (2,027 ft)
- Time to apogee: 11.4 s
- Peak velocity: 128 m/s (Mach 0.38)

3. RECOVERY & DESCENT:
- Parachute 1.00 m diameter, deploys at apogee
- Total flight time 147 s; descent from apogee takes 135 s
- Touchdown velocity: 4.50 m/s
</thought>
<design>
{"flight":{"motor":"GragasMAY24","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.15,"base_radius_m":0.03,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"Nose Cone","contains":[{"type":"parachute","diameter_m":1.0,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":12.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.2,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"horn\u00e1 trubka","contains":[{"type":"masscomponent","name":"flight computer","mass_kg":0.034,"kind":"flightcomputer"},{"type":"masscomponent","name":"kaboom","mass_kg":0.03,"kind":"recoveryhardware"},{"type":"masscomponent","name":"altimaeter","mass_kg":0.02228,"kind":"altimeter"},{"type":"masscomponent","name":"GY-BM","mass_kg":0.003,"kind":"masscomponent"},{"type":"masscomponent","name":"MPU 6500","mass_kg":0.006,"kind":"masscomponent"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.02172,"kind":"battery"}]},{"type":"bodytube","length_m":0.15,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"naklad","contains":[{"type":"masscomponent","name":"vaj\u010disko","mass_kg":0.05,"kind":"masscomponent"},{"type":"masscomponent","name":"blublub","mass_kg":0.001,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.173,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"spodn\u00e1 trubka","contains":[{"type":"bulkhead","material":"PETG - 100% infill","name":"Bulkhead"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.093,"tip_chord_m":0.09,"span_m":0.1,"sweep_m":0.1,"thickness_m":0.003,"material":"PLA - 20% infill","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}]}
</design>
```
</details>

### V1-006 · EASY
**Prompt:** Make a rocket that reaches about 3,951 m on a 867J244-14A, 2833L805-P motor and is down in about 357 seconds.
**Rocket:** `ork/Argonia_3p120OD_K160-P_SIM_9-22-24.ork` · **Sim:** Simulation 14 · **Motor:** 867J244-14A, 2833L805-P
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 3950.8 m · max velocity 277.187 m/s · time to apogee 28.061 s · flight time 357.376 s · touchdown 5.236 m/s · wind 5.36448 m/s
**Parts:** nose cone, 4 body tubes, 6 fins, 2 stages, 4 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that reaches about 3,951 m on a 867J244-14A, 2833L805-P motor and is down in about 357 seconds.

2. PROPULSION & ASCENT:
- Motor: 867J244-14A, 2833L805-P
- Simulated apogee: 3,951 m (12,962 ft)
- Time to apogee: 28.1 s
- Peak velocity: 277 m/s (Mach 0.83)

3. RECOVERY & DESCENT:
- Parachute 1.07 m diameter, deploys at 305 m (1000 ft)
- Parachute 0.61 m diameter, deploys at apogee
- Parachute 0.46 m diameter, deploys at apogee
- Parachute 0.91 m diameter, deploys at 305 m (1000 ft)
- Total flight time 357 s; descent from apogee takes 329 s
- Touchdown velocity: 5.24 m/s
</thought>
<design>
{"flight":{"motor":"867J244-14A, 2833L805-P","wind_ms":5.36448},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.39624,"base_radius_m":0.03962,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Aluminum Tip","mass_kg":0.25515,"kind":"masscomponent"},{"type":"parachute","diameter_m":1.0668,"deploy_event":"altitude","deploy_altitude_m":304.8,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-042-SL","name":"Iris Ultra Light Parachute [Cd 2.2 (2.9 oz) 16.1 in^3]"}]},{"type":"bodytube","length_m":0.0635,"outer_d_m":0.07924,"wall_thickness_m":0.0,"material":"Cardboard","name":"Front Tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes CFC-024-S","name":"Compact Elliptical Parachute [Cd 1.55 (1.6 oz) 8.8 in^3)"}]},{"type":"bodytube","length_m":0.9652,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Sustainer Body Tube","contains":[{"type":"innertube","length_m":0.4064,"outer_d_m":0.054,"wall_thickness_m":0.0005,"material":"Aluminum","name":"Aerotech 5417SC Motor Case","motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]},{"type":"innertube","length_m":0.2286,"outer_d_m":0.05694,"wall_thickness_m":0.00114,"material":"Fiberglass","name":"Inner Tube","contains":[{"type":"masscomponent","name":"Batteries","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"AV Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"Camera Bay","mass_kg":0.54715,"kind":"masscomponent"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.17534,"kind":"masscomponent"}]},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"railbutton","name":"Rail Button"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1524,"tip_chord_m":0.0508,"span_m":0.0889,"sweep_m":0.12065,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal Fin Set"},{"type":"masscomponent","name":"Golf Balls","mass_kg":0.5508,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]},{"type":"stage_marker","name":"Stage","contains":[{"type":"bodytube","length_m":0.073,"outer_d_m":0.07924,"wall_thickness_m":0.002,"material":"Cardboard","name":"Interstage"},{"type":"bodytube","length_m":0.89408,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Booster Body Tube","contains":[{"type":"masscomponent","name":"Batteries","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"AV Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Maple","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"innertube","length_m":0.49784,"outer_d_m":0.0762,"wall_thickness_m":0.0005,"material":"Aluminum","name":"Aerotech 5417SC Motor Case","motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1778,"tip_chord_m":0.05715,"span_m":0.1016,"sweep_m":0.1143,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes CFC-018-S","name":"Compact Elliptical Parachute [Cd 1.55 (1.16 oz) 6.4 in^3)"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":304.8,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-036-N","name":"Iris Ultra Parachute [Cd 2.2 (5.0 oz) 27.6 in^3]"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]}]}
</design>
```
</details>

### V1-008 · EASY
**Prompt:** Design a rocket on a 1526K160-6, 2833L805-P motor that reaches about 4,976 m and stays up close to 420 seconds.
**Rocket:** `ork/Argonia_3p120OD_K160-P_SIM_9-22-24.ork` · **Sim:** Simulation 16 · **Motor:** 1526K160-6, 2833L805-P
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 4976.43 m · max velocity 264.404 m/s · time to apogee 33.694 s · flight time 420.373 s · touchdown 5.396 m/s · wind 5.36448 m/s
**Parts:** nose cone, 4 body tubes, 6 fins, 2 stages, 4 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on a 1526K160-6, 2833L805-P motor that reaches about 4,976 m and stays up close to 420 seconds.

2. PROPULSION & ASCENT:
- Motor: 1526K160-6, 2833L805-P
- Simulated apogee: 4,976 m (16,327 ft)
- Time to apogee: 33.7 s
- Peak velocity: 264 m/s (Mach 0.81)

3. RECOVERY & DESCENT:
- Parachute 1.07 m diameter, deploys at 305 m (1000 ft)
- Parachute 0.61 m diameter, deploys at apogee
- Parachute 0.46 m diameter, deploys at apogee
- Parachute 0.91 m diameter, deploys at 305 m (1000 ft)
- Total flight time 420 s; descent from apogee takes 387 s
- Touchdown velocity: 5.40 m/s
</thought>
<design>
{"flight":{"motor":"1526K160-6, 2833L805-P","wind_ms":5.36448},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.39624,"base_radius_m":0.03962,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Aluminum Tip","mass_kg":0.25515,"kind":"masscomponent"},{"type":"parachute","diameter_m":1.0668,"deploy_event":"altitude","deploy_altitude_m":304.8,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-042-SL","name":"Iris Ultra Light Parachute [Cd 2.2 (2.9 oz) 16.1 in^3]"}]},{"type":"bodytube","length_m":0.0635,"outer_d_m":0.07924,"wall_thickness_m":0.0,"material":"Cardboard","name":"Front Tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes CFC-024-S","name":"Compact Elliptical Parachute [Cd 1.55 (1.6 oz) 8.8 in^3)"}]},{"type":"bodytube","length_m":0.9652,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Sustainer Body Tube","contains":[{"type":"innertube","length_m":0.4064,"outer_d_m":0.054,"wall_thickness_m":0.0005,"material":"Aluminum","name":"Aerotech 5417SC Motor Case","motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]},{"type":"innertube","length_m":0.2286,"outer_d_m":0.05694,"wall_thickness_m":0.00114,"material":"Fiberglass","name":"Inner Tube","contains":[{"type":"masscomponent","name":"Batteries","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"AV Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"Camera Bay","mass_kg":0.54715,"kind":"masscomponent"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.17534,"kind":"masscomponent"}]},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"railbutton","name":"Rail Button"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1524,"tip_chord_m":0.0508,"span_m":0.0889,"sweep_m":0.12065,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal Fin Set"},{"type":"masscomponent","name":"Golf Balls","mass_kg":0.5508,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]},{"type":"stage_marker","name":"Stage","contains":[{"type":"bodytube","length_m":0.073,"outer_d_m":0.07924,"wall_thickness_m":0.002,"material":"Cardboard","name":"Interstage"},{"type":"bodytube","length_m":0.89408,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Booster Body Tube","contains":[{"type":"masscomponent","name":"Batteries","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"AV Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Maple","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"innertube","length_m":0.49784,"outer_d_m":0.0762,"wall_thickness_m":0.0005,"material":"Aluminum","name":"Aerotech 5417SC Motor Case","motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1778,"tip_chord_m":0.05715,"span_m":0.1016,"sweep_m":0.1143,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes CFC-018-S","name":"Compact Elliptical Parachute [Cd 1.55 (1.16 oz) 6.4 in^3)"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":304.8,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-036-N","name":"Iris Ultra Parachute [Cd 2.2 (5.0 oz) 27.6 in^3]"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]}]}
</design>
```
</details>

### V1-010 · EASY
**Prompt:** Design a rocket that goes to about 198 m apogee with deployment at about 4.7 m/s and a 52.5 s flight.
**Rocket:** `ork/Base drag hack (short-wide).ork` · **Sim:** Simulation 2 · **Motor:** D12
**Why easy: 3 requirements: apogee, flight time, touchdown speed**
**Targets:** apogee 198.192 m · max velocity 73.693 m/s · time to apogee 5.174 s · flight time 52.492 s · touchdown 4.667 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 198 m apogee with deployment at about 4.7 m/s and a 52.5 s flight.

2. PROPULSION & ASCENT:
- Motor: D12
- Simulated apogee: 198 m (650 ft)
- Time to apogee: 5.2 s
- Peak velocity: 74 m/s (Mach 0.22)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 52 s; descent from apogee takes 47 s
- Touchdown velocity: 4.67 m/s
</thought>
<design>
{"flight":{"motor":"D12","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.04543,"base_radius_m":0.03937,"wall_thickness_m":0.00168,"material":"Polycarbonate (Lexan)","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Tungsten .5 oz Nose Weight","mass_kg":0.01417,"kind":"masscomponent"},{"type":"masscomponent","name":"Tungsten .5 oz Nose Weight","mass_kg":0.01417,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.12114,"outer_d_m":0.07874,"wall_thickness_m":0.00061,"material":"Cardboard","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Mylar polyester film","name":"18\" Mylar Parachute"},{"type":"masscomponent","name":"9\" Nomex Blanket","mass_kg":0.01531,"kind":"masscomponent"},{"type":"launchlug","length_m":0.03175,"name":"Launch Lug"},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00305,"material":"Basswood","name":"Freeform Fiin Set (4)"},{"type":"centeringring","material":"Paper (office)","name":"Centering Ring"},{"type":"centeringring","material":"Paper (office)","name":"Centering Ring"},{"type":"innertube","length_m":0.09525,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"24mm Motor Mount Tube","contains":[{"type":"engineblock","name":"Engine Block"},{"type":"engineblock","name":"Engine Adapter [Remove for \"E\" Engine]"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"}]}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"}]},{"type":"transition","shape":"conical","length_m":0.24746,"fore_d_m":4e-05,"aft_d_m":0.07874,"material":"Polycarbonate (Lexan)","name":"Base-Drag Hack Transition"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"}]}]}
</design>
```
</details>

### V1-012 · EASY
**Prompt:** Design a rocket that goes to about 1,683 m apogee in about 18.1 s to apogee on a 2014K1200-16A motor.
**Rocket:** `ork/BorealisA8-10_FINAL.ork` · **Sim:** Simulation 1 · **Motor:** 2014K1200-16A
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 1682.63 m · max velocity 213.511 m/s · time to apogee 18.05 s · flight time 67.577 s · touchdown 34.471 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, transition, 3 fins, 5 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 1,683 m apogee in about 18.1 s to apogee on a 2014K1200-16A motor.

2. PROPULSION & ASCENT:
- Motor: 2014K1200-16A
- Simulated apogee: 1,683 m (5,520 ft)
- Time to apogee: 18.1 s
- Peak velocity: 214 m/s (Mach 0.63)

3. RECOVERY & DESCENT:
- Parachute 0.90 m diameter, deploys at ejection
- Total flight time 68 s; descent from apogee takes 50 s
- Touchdown velocity: 34.47 m/s
</thought>
<design>
{"flight":{"motor":"2014K1200-16A","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer"},{"type":"stage_marker","name":"NoseCone","contains":[{"type":"nosecone","shape":"power","shape_param":0.7,"length_m":0.05,"base_radius_m":0.00933,"material":"Aluminum","name":"NoseCone_Tip_Aluminum","contains":[{"type":"innertube","length_m":0.035,"outer_d_m":0.005,"wall_thickness_m":0.0,"material":"Aluminum","name":"Vite?"}]},{"type":"transition","shape":"power","length_m":0.5,"fore_d_m":0.01866,"aft_d_m":0.1,"material":"Carbon fiber","name":"NoseCone_Bottom_CarbonFiber"},{"type":"transition","shape":"conical","length_m":0.01,"fore_d_m":0.1,"aft_d_m":0.1,"material":"Aluminum","name":"NoseCone_Flange","contains":[{"type":"innertube","length_m":0.001,"outer_d_m":0.001,"wall_thickness_m":0.0005,"material":"Nylon","name":"Nylon_Screws"}]}]},{"type":"stage_marker","name":"RecoverySystem","contains":[{"type":"bodytube","length_m":0.65,"outer_d_m":0.1,"wall_thickness_m":0.002,"material":"Aluminum","name":"Body Tube","contains":[{"type":"innertube","length_m":0.001,"outer_d_m":0.001,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Shear Pins"},{"type":"innertube","length_m":0.001,"outer_d_m":0.001,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Screws (correggere peso x tutte)"},{"type":"innertube","length_m":0.001,"outer_d_m":0.001,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Screws"},{"type":"innertube","length_m":0.317,"outer_d_m":0.096,"wall_thickness_m":0.003,"material":"Acrylic","name":"Plexiglass cavo","contains":[{"type":"parachute","diameter_m":0.9,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute (drouge+main+swivel+ropes)"},{"type":"innertube","length_m":0.003,"outer_d_m":0.096,"wall_thickness_m":0.048,"material":"Cardboard","name":"Fondo plexiglass"}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.096,"wall_thickness_m":0.048,"material":"Aluminum","name":"Peregrine base","contains":[{"type":"innertube","length_m":0.0045,"outer_d_m":0.0445,"wall_thickness_m":0.02225,"material":"Aluminum","name":"Peregrine base 1","contains":[{"type":"innertube","length_m":0.012,"outer_d_m":0.0286,"wall_thickness_m":0.0025,"material":"Cardboard","name":"Peregrine base 2"},{"type":"innertube","length_m":0.109,"outer_d_m":0.0235,"wall_thickness_m":0.01175,"material":"Cardboard","name":"Peregrine + CO2 canister"}]}]}]}]},{"type":"stage_marker","name":"ElectronicsBay","contains":[{"type":"transition","shape":"conical","length_m":0.01,"fore_d_m":0.1,"aft_d_m":0.1,"material":"Aluminum","name":"Transizione","contains":[{"type":"innertube","length_m":0.004,"outer_d_m":0.003,"wall_thickness_m":0.0015,"material":"Steel","name":"Tubo interno"},{"type":"innertube","length_m":0.004,"outer_d_m":0.003,"wall_thickness_m":0.0015,"material":"Steel","name":"Tubo interno"}]},{"type":"bodytube","length_m":0.21,"outer_d_m":0.1,"wall_thickness_m":0.002,"material":"Acrylic","name":"Corpo","contains":[{"type":"centeringring","material":"pcb","name":"scheda madre"},{"type":"innertube","length_m":0.24,"outer_d_m":0.008,"wall_thickness_m":0.004,"material":"Steel","name":"Tubo interno"},{"type":"innertube","length_m":0.1,"outer_d_m":0.0055,"wall_thickness_m":0.00275,"material":"pcb","name":"antenna"},{"type":"masscomponent","name":"Zavorra","mass_kg":0.00924,"kind":"flightcomputer"},{"type":"masscomponent","name":"Batteria","mass_kg":0.049,"kind":"battery"},{"type":"masscomponent","name":"Batteria","mass_kg":0.049,"kind":"battery"}]},{"type":"transition","shape":"conical","length_m":0.01,"fore_d_m":0.1,"aft_d_m":0.1,"material":"lega 6061","name":"flangia inferiore","contains":[{"type":"innertube","length_m":0.004,"outer_d_m":0.005,"wall_thickness_m":0.0025,"material":"Steel","name":"Tubo interno"},{"type":"innertube","length_m":0.004,"outer_d_m":0.004,"wall_thickness_m":0.002,"material":"Steel","name":"Tubo interno"}]}]},{"type":"stage_marker","name":"MotorAssembly","contains":[{"type":"bodytube","length_m":0.52,"outer_d_m":0.1,"wall_thickness_m":0.002,"material":"Aluminum","name":"MotorAssembly_Tube","contains":[{"type":"innertube","length_m":0.45,"outer_d_m":0.058,"wall_thickness_m":0.002,"material":"Cardboard","name":"CartoneFenolico","contains":[{"type":"innertube","length_m":0.0241,"outer_d_m":0.061,"wall_thickness_m":0.00145,"material":"Aluminum","name":"MotorRetainerBase","contains":[{"type":"innertube","length_m":0.0153,"outer_d_m":0.0664,"wall_thickness_m":0.0016,"material":"Cardboard","name":"MotorRetainerTesta"}]},{"type":"innertube","length_m":0.007,"outer_d_m":0.0574,"wall_thickness_m":0.0022,"material":"Aluminum","name":"EngineMount1"},{"type":"innertube","length_m":0.0025,"outer_d_m":0.0574,"wall_thickness_m":0.01285,"material":"Aluminum","name":"EngineMount2"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2014K1200-16A"}]},{"type":"centeringring","material":"Aluminum","name":"FinalRing_75mm"},{"type":"centeringring","material":"Aluminum","name":"CenteringRing_1"},{"type":"centeringring","material":"Aluminum","name":"CenteringRing_2"},{"type":"centeringring","material":"Aluminum","name":"CenteringRing_3"},{"type":"centeringring","material":"Aluminum","name":"CenteringRing_4"},{"type":"bulkhead","material":"Aluminum","name":"Bulkhead_Top"},{"type":"innertube","length_m":0.006,"outer_d_m":0.008,"wall_thickness_m":0.004,"material":"Steel","name":"Bulkhead_Top_Screws1"},{"type":"innertube","length_m":0.006,"outer_d_m":0.008,"wall_thickness_m":0.004,"material":"Steel","name":"Bulkhead_Top_Screws2"},{"type":"innertube","length_m":0.02,"outer_d_m":0.062,"wall_thickness_m":0.004,"material":"Cardboard","name":"Bulkhead_Bottom"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.24,"tip_chord_m":0.12,"span_m":0.11,"sweep_m":0.05997,"thickness_m":0.003,"material":"Carbon fiber","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2014K1200-16A"}]},{"type":"transition","shape":"conical","length_m":0.1,"fore_d_m":0.1,"aft_d_m":0.072,"material":"Aluminum","name":"Transition"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2014K1200-16A"}]}]}
</design>
```
</details>

### V1-013 · EASY
**Prompt:** Make a rocket that reaches about 2,928 m on a M1340W motor and is down in about 158 seconds.
**Rocket:** `ork/DarkMatter2.ork` · **Sim:** Indiana Rocketry · **Motor:** M1340W
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 2927.75 m · max velocity 273.656 m/s · time to apogee 24.143 s · flight time 157.827 s · touchdown 9.183 m/s · wind 8.9408 m/s
**Parts:** nose cone, 2 body tubes, transition, freeform fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that reaches about 2,928 m on a M1340W motor and is down in about 158 seconds.

2. PROPULSION & ASCENT:
- Motor: M1340W
- Simulated apogee: 2,928 m (9,605 ft)
- Time to apogee: 24.1 s
- Peak velocity: 274 m/s (Mach 0.82)

3. RECOVERY & DESCENT:
- Parachute 2.13 m diameter, deploys at 244 m (800 ft)
- Parachute 0.91 m diameter, deploys at apogee
- Total flight time 158 s; descent from apogee takes 134 s
- Touchdown velocity: 9.18 m/s
</thought>
<design>
{"flight":{"motor":"M1340W","wind_ms":8.9408},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.533,"base_radius_m":0.025,"wall_thickness_m":0.00635,"material":"Fiberglass","name":"Nose cone (Random ass profile lol)","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":2.26796,"kind":"masscomponent"}]},{"type":"bodytube","length_m":1.143,"outer_d_m":0.05,"wall_thickness_m":0.0,"material":"Carbon fiber","name":"Upper Body Tube (CF)","contains":[{"type":"masscomponent","name":"AVI Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"bulkhead","material":"Maple","name":"Bulkhead"},{"type":"masscomponent","name":"Separation Mechanism","mass_kg":1.36078,"kind":"recoveryhardware"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Camera Bay","mass_kg":1.0,"kind":"masscomponent"}]},{"type":"bodytube","length_m":1.17792,"outer_d_m":0.1429,"wall_thickness_m":0.0016,"material":"Carbon fiber","name":"Lower Body Tube (CF)","contains":[{"type":"parachute","diameter_m":2.1336,"deploy_event":"altitude","deploy_altitude_m":243.84,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Drogue Parachute"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00635,"material":"Carbon fiber","name":"Freeform fin set"},{"type":"innertube","length_m":0.8636,"outer_d_m":0.1021,"wall_thickness_m":0.00152,"material":"Cardboard","name":"Motor Mount Tube","motors":[{"manufacturer":"AeroTech","designation":"M1340W"}]},{"type":"centeringring","material":"Carbon fiber","name":"Centering ring"},{"type":"centeringring","material":"Carbon fiber","name":"Centering ring"},{"type":"centeringring","material":"Carbon fiber","name":"Centering ring"},{"type":"centeringring","material":"Carbon fiber","name":"Centering ring"}],"motors":[{"manufacturer":"AeroTech","designation":"M1340W"}]},{"type":"transition","shape":"conical","length_m":0.04127,"fore_d_m":0.05,"aft_d_m":0.1,"material":"Aluminum","name":"Transition"}],"motors":[{"manufacturer":"AeroTech","designation":"M1340W"}]}]}
</design>
```
</details>

### V1-014 · EASY
**Prompt:** Make a rocket that reaches about 3,025 m on a M1340W motor and is down in about 161 seconds.
**Rocket:** `ork/DarkMatter2.ork` · **Sim:** Indiana Rocketry, Weather Data · **Motor:** M1340W
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 3024.84 m · max velocity 274.329 m/s · time to apogee 24.564 s · flight time 161.383 s · touchdown 9.194 m/s · wind 6.25856 m/s
**Parts:** nose cone, 2 body tubes, transition, freeform fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that reaches about 3,025 m on a M1340W motor and is down in about 161 seconds.

2. PROPULSION & ASCENT:
- Motor: M1340W
- Simulated apogee: 3,025 m (9,924 ft)
- Time to apogee: 24.6 s
- Peak velocity: 274 m/s (Mach 0.82)

3. RECOVERY & DESCENT:
- Parachute 2.13 m diameter, deploys at 244 m (800 ft)
- Parachute 0.91 m diameter, deploys at apogee
- Total flight time 161 s; descent from apogee takes 137 s
- Touchdown velocity: 9.19 m/s
</thought>
<design>
{"flight":{"motor":"M1340W","wind_ms":6.25856},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.533,"base_radius_m":0.025,"wall_thickness_m":0.00635,"material":"Fiberglass","name":"Nose cone (Random ass profile lol)","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":2.26796,"kind":"masscomponent"}]},{"type":"bodytube","length_m":1.143,"outer_d_m":0.05,"wall_thickness_m":0.0,"material":"Carbon fiber","name":"Upper Body Tube (CF)","contains":[{"type":"masscomponent","name":"AVI Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"bulkhead","material":"Maple","name":"Bulkhead"},{"type":"masscomponent","name":"Separation Mechanism","mass_kg":1.36078,"kind":"recoveryhardware"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Camera Bay","mass_kg":1.0,"kind":"masscomponent"}]},{"type":"bodytube","length_m":1.17792,"outer_d_m":0.1429,"wall_thickness_m":0.0016,"material":"Carbon fiber","name":"Lower Body Tube (CF)","contains":[{"type":"parachute","diameter_m":2.1336,"deploy_event":"altitude","deploy_altitude_m":243.84,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Drogue Parachute"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00635,"material":"Carbon fiber","name":"Freeform fin set"},{"type":"innertube","length_m":0.8636,"outer_d_m":0.1021,"wall_thickness_m":0.00152,"material":"Cardboard","name":"Motor Mount Tube","motors":[{"manufacturer":"AeroTech","designation":"M1340W"}]},{"type":"centeringring","material":"Carbon fiber","name":"Centering ring"},{"type":"centeringring","material":"Carbon fiber","name":"Centering ring"},{"type":"centeringring","material":"Carbon fiber","name":"Centering ring"},{"type":"centeringring","material":"Carbon fiber","name":"Centering ring"}],"motors":[{"manufacturer":"AeroTech","designation":"M1340W"}]},{"type":"transition","shape":"conical","length_m":0.04127,"fore_d_m":0.05,"aft_d_m":0.1,"material":"Aluminum","name":"Transition"}],"motors":[{"manufacturer":"AeroTech","designation":"M1340W"}]}]}
</design>
```
</details>

### V1-016 · EASY
**Prompt:** Make a rocket that hits 176 m and stays up about 33 s on a H248 motor.
**Rocket:** `ork/FRED_v_2.3.ork` · **Sim:** Simulation 4 · **Motor:** H248
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 176.41 m · max velocity 60.836 m/s · time to apogee 6.416 s · flight time 32.755 s · touchdown 7.14 m/s · wind 2 m/s
**Parts:** nose cone, 4 body tubes, transition, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 176 m and stays up about 33 s on a H248 motor.

2. PROPULSION & ASCENT:
- Motor: H248
- Simulated apogee: 176 m (579 ft)
- Time to apogee: 6.4 s
- Peak velocity: 61 m/s (Mach 0.18)

3. RECOVERY & DESCENT:
- Parachute 1.22 m diameter, deploys at apogee
- Total flight time 33 s; descent from apogee takes 26 s
- Touchdown velocity: 7.14 m/s
</thought>
<design>
{"flight":{"motor":"H248","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Principale","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.14,"base_radius_m":0.0425,"wall_thickness_m":0.02,"material":"PETG-CF","name":"Naso","contains":[{"type":"masscomponent","name":"Occhiello+vite","mass_kg":0.063,"kind":"masscomponent"},{"type":"innertube","length_m":0.04,"outer_d_m":0.0079,"wall_thickness_m":0.00095,"material":"Aluminum","name":"Pistoni 4cm"}]},{"type":"bodytube","length_m":0.055,"outer_d_m":0.085,"wall_thickness_m":0.0155,"material":"PETG-CF","name":"TUbo par","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.01,"wall_thickness_m":0.001,"material":"Aluminum","name":"charge cups"},{"type":"innertube","length_m":0.04,"outer_d_m":0.015,"wall_thickness_m":0.0075,"material":"Steel","name":"Tubo interno"}]},{"type":"bodytube","length_m":0.234,"outer_d_m":0.085,"wall_thickness_m":0.002,"material":"PETG-CF","name":"Recovery Bay","contains":[{"type":"parachute","diameter_m":1.22,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","name":"Paracadute"},{"type":"innertube","length_m":0.185,"outer_d_m":0.058,"wall_thickness_m":0.0,"material":"Cardboard","name":"TUbo Par","contains":[{"type":"masscomponent","name":"Correzioni massa real","mass_kg":0.1,"kind":"masscomponent"}]},{"type":"innertube","length_m":0.25,"outer_d_m":0.01,"wall_thickness_m":0.005,"material":"Steel","name":"Barre \"basse\" no presenti"},{"type":"innertube","length_m":0.25,"outer_d_m":0.01,"wall_thickness_m":0.005,"material":"Steel","name":"Barre alte 1-2 no presenti"},{"type":"innertube","length_m":0.25,"outer_d_m":0.01,"wall_thickness_m":0.005,"material":"Steel","name":"Barre alte 3-4"},{"type":"masscomponent","name":"Occhiello e vite","mass_kg":0.063,"kind":"masscomponent"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]},{"type":"transition","shape":"conical","length_m":0.005,"fore_d_m":0.085,"aft_d_m":0.085,"material":"Cardboard","name":"Transizione"},{"type":"bodytube","length_m":0.1925,"outer_d_m":0.085,"wall_thickness_m":0.002,"material":"PETG-CF","name":"E-bay","contains":[{"type":"innertube","length_m":0.15,"outer_d_m":0.013,"wall_thickness_m":0.0065,"material":"PETG-CF","name":"Sostegno Manny"},{"type":"innertube","length_m":0.08,"outer_d_m":0.0175,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Manny"},{"type":"innertube","length_m":0.05,"outer_d_m":0.0175,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Batteria"},{"type":"masscomponent","name":"Modulo Lora+cavi+altro","mass_kg":0.092,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button"}]},{"type":"transition","shape":"conical","length_m":0.01,"fore_d_m":0.085,"aft_d_m":0.085,"material":"PETG-CF","name":"Transizione"},{"type":"bodytube","length_m":0.195,"outer_d_m":0.085,"wall_thickness_m":0.0025,"material":"PETG-CF","name":"Corpo","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.12,"tip_chord_m":0.03,"span_m":0.12,"sweep_m":0.07,"thickness_m":0.004,"material":"PETG-CF","name":"Pinne trapezoidali"},{"type":"innertube","length_m":0.5,"outer_d_m":0.003,"wall_thickness_m":0.0015,"material":"Steel","name":"Barre m3"}],"motors":[{"manufacturer":"AuroraRocketry","designation":"H248"}]},{"type":"transition","shape":"conical","length_m":0.043,"fore_d_m":0.085,"aft_d_m":0.06,"material":"PETG-CF","name":"Transizione","contains":[{"type":"masscomponent","name":"Nozzle massa 0","mass_kg":0.0,"kind":"masscomponent"}]}],"motors":[{"manufacturer":"AuroraRocketry","designation":"H248"}]}]}
</design>
```
</details>

### V1-021 · EASY
**Prompt:** Design a rocket that goes to about 146.2 m/s max velocity with a 81.7 s flight and touchdown at about 5.6 m/s.
**Rocket:** `ork/Myles_L1.ork` · **Sim:** Simulation 1 · **Motor:** H143SS
**Why easy: 3 requirements: max velocity, flight time, touchdown speed**
**Targets:** apogee 786.43 m · max velocity 146.24 m/s · time to apogee 12.388 s · flight time 81.65 s · touchdown 5.5763 m/s · wind 4.4704 m/s
**Parts:** nose cone, 2 body tubes, transition, 3 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 146.2 m/s max velocity with a 81.7 s flight and touchdown at about 5.6 m/s.

2. PROPULSION & ASCENT:
- Motor: H143SS
- Simulated apogee: 786 m (2,580 ft)
- Time to apogee: 12.4 s
- Peak velocity: 146 m/s (Mach 0.43)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at 61 m (200 ft)
- Parachute 0.47 m diameter, deploys at ejection
- Total flight time 82 s; descent from apogee takes 69 s
- Touchdown velocity: 5.58 m/s
</thought>
<design>
{"flight":{"motor":"H143SS","wind_ms":4.4704},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.2667,"base_radius_m":0.0334,"wall_thickness_m":0.002,"material":"PVC","name":"Nose cone","contains":[{"type":"masscomponent","name":"AV","mass_kg":0.1134,"kind":"masscomponent"},{"type":"masscomponent","name":"Ballast 1","mass_kg":0.0,"kind":"masscomponent"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.254,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Blue tube","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":60.96,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"launchlug","length_m":0.03,"name":"Launch lug"}]},{"type":"bodytube","length_m":0.4318,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Blue tube","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4699,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"launchlug","length_m":0.03,"name":"Launch lug"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"innertube","length_m":0.18593,"outer_d_m":0.04064,"wall_thickness_m":0.00127,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.127,"tip_chord_m":0.0508,"span_m":0.0508,"sweep_m":0.09069,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]},{"type":"transition","shape":"conical","length_m":0.0381,"aft_d_m":0.04444,"material":"Blue tube","name":"Transition"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]}]}
</design>
```
</details>

### V1-022 · EASY
**Prompt:** Design a rocket that goes to about 1,676 m apogee in about 18.1 s to apogee on a L1390G motor.
**Rocket:** `ork/NASA_Rocket_V1.ork` · **Sim:** Simulation to 5766 · **Motor:** L1390G
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 1676.3 m · max velocity 213.19 m/s · time to apogee 18.131 s · flight time 95.61 s · touchdown 6.1038 m/s · wind 0 m/s
**Parts:** nose cone, 3 body tubes, 4 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 1,676 m apogee in about 18.1 s to apogee on a L1390G motor.

2. PROPULSION & ASCENT:
- Motor: L1390G
- Simulated apogee: 1,676 m (5,500 ft)
- Time to apogee: 18.1 s
- Peak velocity: 213 m/s (Mach 0.63)

3. RECOVERY & DESCENT:
- Parachute 3.05 m diameter, deploys at 213 m (700 ft)
- Parachute 0.61 m diameter, deploys at apogee
- Total flight time 96 s; descent from apogee takes 77 s
- Touchdown velocity: 6.10 m/s
</thought>
<design>
{"flight":{"motor":"L1390G","wind_ms":0.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.381,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Nose cone","contains":[{"type":"masscomponent","name":"Payload","mass_kg":1.36078,"kind":"masscomponent"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.9144,"outer_d_m":0.15672,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Body tube","contains":[{"type":"parachute","diameter_m":3.048,"deploy_event":"altitude","deploy_altitude_m":213.36,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.0762,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Body tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Avionics","mass_kg":1.36078,"kind":"masscomponent"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}]},{"type":"bodytube","length_m":1.2192,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering Ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering Ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering Ring"},{"type":"innertube","length_m":0.6858,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"L1170FJ"},{"manufacturer":"AeroTech","designation":"L900DM"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"L1040DM"}]},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.381,"tip_chord_m":0.0762,"span_m":0.1524,"sweep_m":0.32682,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"L1170FJ"},{"manufacturer":"AeroTech","designation":"L900DM"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"L1040DM"}]}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"L1170FJ"},{"manufacturer":"AeroTech","designation":"L900DM"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"L1040DM"}]}]}
</design>
```
</details>

### V1-024 · EASY
**Prompt:** Design a rocket that goes to about 181.6 m/s on a H143SS motor, reaching apogee in about 9.2 s.
**Rocket:** `ork/Navya_L1.ork` · **Sim:** Simulation 3 · **Motor:** H143SS
**Why easy: 3 requirements: max velocity, time to apogee, motor**
**Targets:** apogee 580.04 m · max velocity 181.58 m/s · time to apogee 9.2455 s · flight time 80.798 s · touchdown 8.1287 m/s · wind 4.4704 m/s
**Parts:** nose cone, 1 body tube, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 181.6 m/s on a H143SS motor, reaching apogee in about 9.2 s.

2. PROPULSION & ASCENT:
- Motor: H143SS
- Simulated apogee: 580 m (1,903 ft)
- Time to apogee: 9.2 s
- Peak velocity: 182 m/s (Mach 0.54)

3. RECOVERY & DESCENT:
- Parachute 1.22 m diameter, deploys at apogee
- Total flight time 81 s; descent from apogee takes 72 s
- Touchdown velocity: 8.13 m/s
</thought>
<design>
{"flight":{"motor":"H143SS","wind_ms":4.4704},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"conical","length_m":0.15748,"wall_thickness_m":0.002,"material":"PLA Plastic","name":"Nose cone w hole in it","contains":[{"type":"masscomponent","name":"altimeter","mass_kg":0.02,"kind":"altimeter"},{"type":"bulkhead","material":"Plywood (birch)","name":"bulkhead (nose cone lid)"},{"type":"masscomponent","name":"weights (dump washers in epoxy and pour??)","mass_kg":0.3,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.8636,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Kraft phenolic","name":"Booster tube","contains":[{"type":"innertube","length_m":0.21844,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Kraft phenolic","name":"Inner Tube"},{"type":"innertube","length_m":0.0127,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Masking Tape","name":"diy thrust ring (tape)","motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Birch","name":"Centering ring"},{"type":"parachute","diameter_m":1.2192,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.14732,"tip_chord_m":0.0889,"span_m":0.1016,"sweep_m":0.07566,"thickness_m":0.00635,"material":"Plywood (birch)","name":"Trapezoidal fin set"},{"type":"masscomponent","name":"motor retainer ring","mass_kg":0.0227,"kind":"masscomponent"},{"type":"masscomponent","name":"rail button #1","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"rail button #2","mass_kg":0.0019,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]}]}
</design>
```
</details>

### V1-025 · EASY
**Prompt:** Design a rocket that goes to about 130.9 m/s on a H143SS motor, reaching apogee in about 8.6 s.
**Rocket:** `ork/Navya_L1.ork` · **Sim:** Simulation 6 · **Motor:** H143SS
**Why easy: 3 requirements: max velocity, time to apogee, motor**
**Targets:** apogee 426.97 m · max velocity 130.92 m/s · time to apogee 8.5579 s · flight time 98.954 s · touchdown 4.8101 m/s · wind 4.4704 m/s
**Parts:** nose cone, 1 body tube, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 130.9 m/s on a H143SS motor, reaching apogee in about 8.6 s.

2. PROPULSION & ASCENT:
- Motor: H143SS
- Simulated apogee: 427 m (1,401 ft)
- Time to apogee: 8.6 s
- Peak velocity: 131 m/s (Mach 0.39)

3. RECOVERY & DESCENT:
- Parachute 1.22 m diameter, deploys at apogee
- Total flight time 99 s; descent from apogee takes 90 s
- Touchdown velocity: 4.81 m/s
</thought>
<design>
{"flight":{"motor":"H143SS","wind_ms":4.4704},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"conical","length_m":0.15748,"wall_thickness_m":0.002,"material":"PLA Plastic","name":"Nose cone w hole in it","contains":[{"type":"masscomponent","name":"altimeter","mass_kg":0.02,"kind":"altimeter"},{"type":"bulkhead","material":"Plywood (birch)","name":"bulkhead (nose cone lid)"},{"type":"masscomponent","name":"weights (dump washers in epoxy and pour??)","mass_kg":0.3,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.8636,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Kraft phenolic","name":"Booster tube","contains":[{"type":"innertube","length_m":0.21844,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Kraft phenolic","name":"Inner Tube"},{"type":"innertube","length_m":0.0127,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Masking Tape","name":"diy thrust ring (tape)","motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Birch","name":"Centering ring"},{"type":"parachute","diameter_m":1.2192,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.14732,"tip_chord_m":0.0889,"span_m":0.1016,"sweep_m":0.07566,"thickness_m":0.00635,"material":"Plywood (birch)","name":"Trapezoidal fin set"},{"type":"masscomponent","name":"motor retainer ring","mass_kg":0.0227,"kind":"masscomponent"},{"type":"masscomponent","name":"rail button #1","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"rail button #2","mass_kg":0.0019,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]}]}
</design>
```
</details>

### V1-027 · EASY
**Prompt:** Make a rocket that hits 2,818 m and stays up about 193 s on a 8187M1545-P motor.
**Rocket:** `ork/Nemesis150_v4.3.ork` · **Sim:** Simulation 1 · **Motor:** 8187M1545-P
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 2817.53 m · max velocity 246.875 m/s · time to apogee 24.93 s · flight time 192.78 s · touchdown 6.176 m/s · wind 2 m/s
**Parts:** nose cone, 4 body tubes, transition, 3 fins, 5 stages, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 2,818 m and stays up about 193 s on a 8187M1545-P motor.

2. PROPULSION & ASCENT:
- Motor: 8187M1545-P
- Simulated apogee: 2,818 m (9,244 ft)
- Time to apogee: 24.9 s
- Peak velocity: 247 m/s (Mach 0.73)

3. RECOVERY & DESCENT:
- Parachute 3.66 m diameter, deploys at 450 m (1476 ft)
- Parachute 0.91 m diameter, deploys at apogee
- Total flight time 193 s; descent from apogee takes 168 s
- Touchdown velocity: 6.18 m/s
</thought>
<design>
{"flight":{"motor":"8187M1545-P","wind_ms":2.0},"components":[{"type":"stage_marker","name":"NoseCone","contains":[{"type":"nosecone","shape":"conical","length_m":0.02,"base_radius_m":0.0094,"material":"PVC","name":"NoseCone_Tip_Aluminum"},{"type":"transition","shape":"haack","length_m":0.43,"fore_d_m":0.0188,"aft_d_m":0.15,"material":"Fiberglass","name":"NoseCone_Bottom_GlassFiber"},{"type":"bodytube","length_m":0.2,"outer_d_m":0.15,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Fiber_Body","contains":[{"type":"masscomponent","name":"Payload","mass_kg":1.0115,"kind":"masscomponent"},{"type":"masscomponent","name":"Zavorra","mass_kg":0.0,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.01,"fore_d_m":0.15,"aft_d_m":0.15,"material":"Aluminum","name":"NoseCone_Flange","contains":[{"type":"innertube","length_m":0.005,"outer_d_m":0.005,"wall_thickness_m":0.0025,"material":"Aluminum","name":"Screw"},{"type":"innertube","length_m":0.0025,"outer_d_m":0.0025,"wall_thickness_m":0.00125,"material":"Nylon","name":"Shear_Pins"},{"type":"innertube","length_m":0.07,"outer_d_m":0.008,"wall_thickness_m":0.004,"material":"Aluminum","name":"Occhiello"}]}]},{"type":"stage_marker","name":"RecoverySystem","contains":[{"type":"bodytube","length_m":0.71,"outer_d_m":0.15,"wall_thickness_m":0.003,"material":"Aluminum","name":"Body Tube","contains":[{"type":"innertube","length_m":0.476,"outer_d_m":0.14,"wall_thickness_m":0.002,"material":"Acrylic","name":"Recovery_Bay","contains":[{"type":"innertube","length_m":0.015,"outer_d_m":0.144,"wall_thickness_m":0.002,"material":"Aluminum","name":"Centering_Ring_Chute_1"},{"type":"innertube","length_m":0.015,"outer_d_m":0.144,"wall_thickness_m":0.002,"material":"Aluminum","name":"Centering_Ring_Chute_2"},{"type":"innertube","length_m":0.015,"outer_d_m":0.144,"wall_thickness_m":0.072,"material":"Acrylic","name":"Tube_Bottom_out","contains":[{"type":"innertube","length_m":0.01,"outer_d_m":0.144,"wall_thickness_m":0.072,"material":"Aluminum","name":"Peregrine_Base","contains":[{"type":"innertube","length_m":0.0033,"outer_d_m":0.0033,"wall_thickness_m":0.00165,"material":"Cardboard","name":"Screws"},{"type":"innertube","length_m":0.0044,"outer_d_m":0.044,"wall_thickness_m":0.014,"material":"Aluminum","name":"Peregrine_Top","contains":[{"type":"innertube","length_m":0.013,"outer_d_m":0.0286,"wall_thickness_m":0.0033,"material":"Aluminum","name":"Peregrine_Ring"},{"type":"innertube","length_m":0.109,"outer_d_m":0.0235,"wall_thickness_m":0.01175,"material":"Cardboard","name":"Peregrine + CO2_canister"}]}]},{"type":"innertube","length_m":0.002,"outer_d_m":0.144,"wall_thickness_m":0.072,"material":"Cardboard","name":"Silicon_pad_1"},{"type":"innertube","length_m":0.002,"outer_d_m":0.144,"wall_thickness_m":0.072,"material":"Cardboard","name":"Silicon_pad_1"}]},{"type":"parachute","diameter_m":3.6576,"deploy_event":"altitude","deploy_altitude_m":450.0,"deploy_delay_s":0.0,"line_count":4.0,"material":"Ripstop nylon","name":"Std Parabolic Parachute [Cd .97 (17 oz)]"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":4.0,"material":"Ripstop nylon","name":"Std Parabolic Parachute [Cd .97 (2.4 oz)]"},{"type":"masscomponent","name":"Cavi_Paracadute","mass_kg":0.8212,"kind":"masscomponent"},{"type":"innertube","length_m":0.01,"outer_d_m":0.135,"wall_thickness_m":0.0675,"material":"Cardboard","name":"Tube_bottom_in"}]},{"type":"innertube","length_m":0.025,"outer_d_m":0.134,"wall_thickness_m":0.005,"material":"Cardboard","name":"Anello centra-dadi (bi-fila)"},{"type":"masscomponent","name":"Correzione peso Recovery FINALE","mass_kg":0.4507,"kind":"masscomponent"}]}]},{"type":"stage_marker","name":"ElectronicsBay","contains":[{"type":"transition","shape":"conical","length_m":0.01,"fore_d_m":0.15,"aft_d_m":0.15,"material":"Aluminum","name":"Flange_2","contains":[{"type":"innertube","length_m":0.003,"outer_d_m":0.003,"wall_thickness_m":0.0015,"material":"Aluminum","name":"Screw_Bottom_1"},{"type":"innertube","length_m":0.003,"outer_d_m":0.003,"wall_thickness_m":0.0015,"material":"Aluminum","name":"Screw_Bottom_2"},{"type":"innertube","length_m":0.003,"outer_d_m":0.003,"wall_thickness_m":0.0015,"material":"Aluminum","name":"Screw_Top"},{"type":"innertube","length_m":0.07,"outer_d_m":0.008,"wall_thickness_m":0.004,"material":"Aluminum","name":"Occhiello"}]},{"type":"bodytube","length_m":0.35,"outer_d_m":0.15,"wall_thickness_m":0.003,"material":"Acrylic","name":"BodyTube","contains":[{"type":"innertube","length_m":0.4,"outer_d_m":0.01,"wall_thickness_m":0.005,"material":"Steel","name":"Steel_Bars","contains":[{"type":"innertube","length_m":0.0145,"outer_d_m":0.016,"wall_thickness_m":0.0035,"material":"Steel","name":"Dado_Bottom_Out"},{"type":"innertube","length_m":0.0145,"outer_d_m":0.016,"wall_thickness_m":0.0035,"material":"Steel","name":"Dado_Bottom_In"},{"type":"innertube","length_m":0.0145,"outer_d_m":0.016,"wall_thickness_m":0.0035,"material":"Steel","name":"Dado_Top_Out"},{"type":"innertube","length_m":0.0145,"outer_d_m":0.016,"wall_thickness_m":0.0035,"material":"Steel","name":"Dado_Top_In"}]},{"type":"innertube","length_m":0.0065,"outer_d_m":0.144,"wall_thickness_m":0.067,"material":"Aluminum","name":"Scheda_1","contains":[{"type":"innertube","length_m":0.0065,"outer_d_m":0.144,"wall_thickness_m":0.067,"material":"Aluminum","name":"Scheda_2","contains":[{"type":"innertube","length_m":0.11,"outer_d_m":0.009,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube"}]},{"type":"innertube","length_m":0.01025,"outer_d_m":0.016,"wall_thickness_m":0.0035,"material":"Steel","name":"Retainer_Schede_Lower"},{"type":"innertube","length_m":0.01025,"outer_d_m":0.016,"wall_thickness_m":0.0035,"material":"Steel","name":"Retainer_Schede_Upper"},{"type":"innertube","length_m":0.011,"outer_d_m":0.016,"wall_thickness_m":0.0035,"material":"Steel","name":"Retainer_Schede_Middle"},{"type":"innertube","length_m":0.0051,"outer_d_m":0.016,"wall_thickness_m":0.0035,"material":"Steel","name":"CATS_Vega_Retainer_1"},{"type":"innertube","length_m":0.0051,"outer_d_m":0.016,"wall_thickness_m":0.0035,"material":"Steel","name":"CATS_Vega_Retainer_2"}]},{"type":"masscomponent","name":"Batteries","mass_kg":0.327,"kind":"battery"},{"type":"innertube","length_m":0.1,"outer_d_m":0.025,"wall_thickness_m":0.0125,"material":"Cardboard","name":"CATS_Vega","contains":[{"type":"masscomponent","name":"CATS_Vega_Support","mass_kg":0.0196,"kind":"masscomponent"}]},{"type":"masscomponent","name":"Batteries_Support","mass_kg":0.0885,"kind":"masscomponent"},{"type":"innertube","length_m":0.01,"outer_d_m":0.134,"wall_thickness_m":0.005,"material":"Cardboard","name":"Anello centra-dadi (mono-fila)"},{"type":"innertube","length_m":0.01,"outer_d_m":0.134,"wall_thickness_m":0.005,"material":"Cardboard","name":"Anello centra-dadi (mono-fila)"},{"type":"innertube","length_m":0.1,"outer_d_m":0.025,"wall_thickness_m":0.0125,"material":"Cardboard","name":"Scheda_wifi","contains":[{"type":"masscomponent","name":"Scheda_wifi_support","mass_kg":0.061,"kind":"masscomponent"}]},{"type":"masscomponent","name":"Supplemento massa FINALE","mass_kg":0.241,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.01,"fore_d_m":0.15,"aft_d_m":0.15,"material":"Aluminum","name":"Flange_1","contains":[{"type":"innertube","length_m":0.003,"outer_d_m":0.003,"wall_thickness_m":0.0015,"material":"Aluminum","name":"Screw_Bottom_1"},{"type":"innertube","length_m":0.003,"outer_d_m":0.003,"wall_thickness_m":0.0015,"material":"Aluminum","name":"Screw_Bottom_2"},{"type":"innertube","length_m":0.003,"outer_d_m":0.003,"wall_thickness_m":0.0015,"material":"Aluminum","name":"Screw_Top"}]}]},{"type":"stage_marker","name":"MotorAssembly","contains":[{"type":"bodytube","length_m":1.05,"outer_d_m":0.15,"wall_thickness_m":0.003,"material":"Aluminum","name":"Body Tube","contains":[{"type":"innertube","length_m":0.025,"outer_d_m":0.134,"wall_thickness_m":0.005,"material":"Cardboard","name":"Anello centra-dadi (bi-fila)"},{"type":"innertube","length_m":0.998,"outer_d_m":0.079,"wall_thickness_m":0.002,"material":"Kraft phenolic","name":"CartoneFenolico","contains":[{"type":"innertube","length_m":0.025,"outer_d_m":0.144,"wall_thickness_m":0.048,"material":"Aluminum","name":"Bulkhead_Body","contains":[{"type":"innertube","length_m":0.03,"outer_d_m":0.083,"wall_thickness_m":0.004,"material":"Aluminum","name":"Bulkhead_Bottom"},{"type":"innertube","length_m":0.009,"outer_d_m":0.06,"wall_thickness_m":0.006,"material":"Aluminum","name":"Bulkhead_Top1","contains":[{"type":"innertube","length_m":0.008,"outer_d_m":0.05,"wall_thickness_m":0.006,"material":"Aluminum","name":"Bulkhead_Top2","contains":[{"type":"innertube","length_m":0.008,"outer_d_m":0.04,"wall_thickness_m":0.006,"material":"Aluminum","name":"Bulkhead_Top3","contains":[{"type":"innertube","length_m":0.007,"outer_d_m":0.0305,"wall_thickness_m":0.01,"material":"Aluminum","name":"Bulkhead_Top4","contains":[{"type":"innertube","length_m":0.036,"outer_d_m":0.009,"wall_thickness_m":0.0,"material":"Aluminum","name":"Motor Screw"},{"type":"innertube","length_m":0.0026,"outer_d_m":0.0296,"wall_thickness_m":0.00875,"material":"Cardboard","name":"Motor Ring"}]}]}]}]},{"type":"innertube","length_m":0.009,"outer_d_m":0.009,"wall_thickness_m":0.0,"material":"Aluminum","name":"Screw_1"},{"type":"innertube","length_m":0.009,"outer_d_m":0.009,"wall_thickness_m":0.0,"material":"Aluminum","name":"Screw_2"}]},{"type":"innertube","length_m":0.003,"outer_d_m":0.075,"wall_thickness_m":0.0028,"material":"Aluminum","name":"ExtraTube"},{"type":"innertube","length_m":0.0126,"outer_d_m":0.0792,"wall_thickness_m":0.01065,"material":"Aluminum","name":"ThrustRing-1_RIFERIMENTO","contains":[{"type":"innertube","length_m":0.0127,"outer_d_m":0.0706,"wall_thickness_m":0.00635,"material":"Aluminum","name":"ThrustRing-2-Filetto","contains":[{"type":"innertube","length_m":0.0029,"outer_d_m":0.0695,"wall_thickness_m":0.00592,"material":"Aluminum","name":"BackwardRetainer-1","contains":[{"type":"innertube","length_m":0.00476,"outer_d_m":0.0695,"wall_thickness_m":0.00275,"material":"Aluminum","name":"BackwardRetainer-2","contains":[{"type":"innertube","length_m":0.00248,"outer_d_m":0.0695,"wall_thickness_m":0.00592,"material":"Aluminum","name":"BackwardRetainer-3","contains":[{"type":"innertube","length_m":0.0048,"outer_d_m":0.064,"wall_thickness_m":0.00317,"material":"Aluminum","name":"BackwardRetainer-4","contains":[{"type":"innertube","length_m":0.0029,"outer_d_m":0.0695,"wall_thickness_m":0.00592,"material":"Aluminum","name":"BackwardRetainer-5"}]}]}]}]}]},{"type":"innertube","length_m":0.0126,"outer_d_m":0.088,"wall_thickness_m":0.00235,"material":"Aluminum","name":"MotorRetainer_Front-1","contains":[{"type":"innertube","length_m":0.0028,"outer_d_m":0.088,"wall_thickness_m":0.0077,"material":"Aluminum","name":"MotorRetainer_Front-2","contains":[{"type":"innertube","length_m":0.0188,"outer_d_m":0.08286,"wall_thickness_m":0.0017,"material":"Aluminum","name":"MotorRetainer_Front-3"}]}]},{"type":"innertube","length_m":0.0021,"outer_d_m":0.093,"wall_thickness_m":0.0105,"material":"Aluminum","name":"MotorRetainer_Rear-1","contains":[{"type":"innertube","length_m":0.0226,"outer_d_m":0.093,"wall_thickness_m":0.0021,"material":"Aluminum","name":"MotorRetainer_Rear-2"}]}]},{"type":"innertube","length_m":0.0258,"outer_d_m":0.0476,"wall_thickness_m":0.00468,"material":"Cardboard","name":"SmokeTrackingModule-2_RIFERIMENTO","contains":[{"type":"innertube","length_m":0.0046,"outer_d_m":0.0695,"wall_thickness_m":0.01563,"material":"Aluminum","name":"SmokeTrackingModule-3","contains":[{"type":"innertube","length_m":0.0126,"outer_d_m":0.0721,"wall_thickness_m":0.0071,"material":"Cardboard","name":"ForwardRetainer"},{"type":"innertube","length_m":0.00492,"outer_d_m":0.064,"wall_thickness_m":0.01288,"material":"Cardboard","name":"SMT-4-ORing","contains":[{"type":"innertube","length_m":0.00311,"outer_d_m":0.0695,"wall_thickness_m":0.01563,"material":"Cardboard","name":"SMT-5"}]}]},{"type":"innertube","length_m":0.005,"outer_d_m":0.0476,"wall_thickness_m":0.0238,"material":"Cardboard","name":"SMT-1.5"},{"type":"innertube","length_m":0.0278,"outer_d_m":0.0222,"wall_thickness_m":0.00615,"material":"Cardboard","name":"SMT-1"}]},{"type":"innertube","length_m":0.008,"outer_d_m":0.144,"wall_thickness_m":0.012,"material":"ABS - 100% infill","name":"CenteringRing_1-OUT","contains":[{"type":"innertube","length_m":0.003,"outer_d_m":0.12,"wall_thickness_m":0.0205,"material":"Cardboard","name":"CenteringRing_1-IN","contains":[{"type":"innertube","length_m":0.005,"outer_d_m":0.083,"wall_thickness_m":0.002,"material":"Cardboard","name":"CenteringRing_1-CENTRE"}]},{"type":"innertube","length_m":0.0045,"outer_d_m":0.0045,"wall_thickness_m":0.0,"material":"Aluminum","name":"Screw_CR_1"},{"type":"innertube","length_m":0.008,"outer_d_m":0.144,"wall_thickness_m":0.012,"material":"ABS - 100% infill","name":"CenteringRing_2-OUT","contains":[{"type":"innertube","length_m":0.003,"outer_d_m":0.12,"wall_thickness_m":0.0205,"material":"Cardboard","name":"CenteringRing_2-IN","contains":[{"type":"innertube","length_m":0.005,"outer_d_m":0.083,"wall_thickness_m":0.002,"material":"Cardboard","name":"CenteringRing_2-CENTRE"}]},{"type":"innertube","length_m":0.0045,"outer_d_m":0.0045,"wall_thickness_m":0.0,"material":"Aluminum","name":"Screw_CR_2"},{"type":"innertube","length_m":0.008,"outer_d_m":0.144,"wall_thickness_m":0.012,"material":"ABS - 100% infill","name":"CenteringRing_FinHolder_1-OUT","contains":[{"type":"innertube","length_m":0.003,"outer_d_m":0.12,"wall_thickness_m":0.0205,"material":"Cardboard","name":"CenteringRing_FinHolder_1-IN","contains":[{"type":"innertube","length_m":0.005,"outer_d_m":0.083,"wall_thickness_m":0.002,"material":"Cardboard","name":"CenteringRing_FinHolder_1-CENTRE"}]},{"type":"innertube","length_m":0.0045,"outer_d_m":0.0045,"wall_thickness_m":0.0,"material":"Aluminum","name":"Screw_CR_FN_1"},{"type":"innertube","length_m":0.008,"outer_d_m":0.144,"wall_thickness_m":0.012,"material":"ABS - 100% infill","name":"CenteringRing_FinHolder_2-OUT","contains":[{"type":"innertube","length_m":0.003,"outer_d_m":0.12,"wall_thickness_m":0.0205,"material":"Cardboard","name":"CenteringRing_FinHolder_2-IN","contains":[{"type":"innertube","length_m":0.005,"outer_d_m":0.083,"wall_thickness_m":0.002,"material":"Cardboard","name":"CenteringRing_FinHolder_2-CENTRE"}]},{"type":"innertube","length_m":0.0045,"outer_d_m":0.0045,"wall_thickness_m":0.0,"material":"Aluminum","name":"Screw_CR_FN_2"}]}]}]}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"8187M1545-P"}]},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.3,"tip_chord_m":0.091,"span_m":0.16,"sweep_m":0.24768,"thickness_m":0.0076,"material":"Fins sandwich","name":"Pinne trapezoidali"},{"type":"innertube","length_m":0.02,"outer_d_m":0.144,"wall_thickness_m":0.0035,"material":"Cardboard","name":"BoatTail_Coupler_1","contains":[{"type":"innertube","length_m":0.006,"outer_d_m":0.143,"wall_thickness_m":0.003,"material":"Cardboard","name":"BoatTail_Coupler_2.1","contains":[{"type":"innertube","length_m":0.006,"outer_d_m":0.139,"wall_thickness_m":0.003,"material":"Cardboard","name":"BoatTail_Coupler_2.2","contains":[{"type":"innertube","length_m":0.006,"outer_d_m":0.136,"wall_thickness_m":0.003,"material":"Cardboard","name":"BoatTail_Coupler_2.3"}]}]}]},{"type":"railbutton","name":"RailButton_Bulkhead"},{"type":"railbutton","name":"RailButton_NC_Flange"},{"type":"railbutton","name":"RailButton_EBfwd_Flange"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"8187M1545-P"}]},{"type":"transition","shape":"conical","length_m":0.116,"fore_d_m":0.15,"aft_d_m":0.092,"material":"Fiberglass","name":"BoatTail"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"8187M1545-P"}]},{"type":"stage_marker","name":"Stadio"}]}
</design>
```
</details>

### V1-028 · EASY
**Prompt:** Make a rocket that hits 2,471 m and stays up about 297 s on a J1000-LW motor.
**Rocket:** `ork/PML_SmallEndeavour_38-8.ork` · **Sim:** Simulation 1 · **Motor:** J1000-LW
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 2471.3 m · max velocity 561.79 m/s · time to apogee 17.033 s · flight time 296.66 s · touchdown 8.36 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 6 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 2,471 m and stays up about 297 s on a J1000-LW motor.

2. PROPULSION & ASCENT:
- Motor: J1000-LW
- Simulated apogee: 2,471 m (8,108 ft)
- Time to apogee: 17.0 s
- Peak velocity: 562 m/s (Mach 1.66)

3. RECOVERY & DESCENT:
- Parachute 0.76 m diameter, deploys at ejection
- Total flight time 297 s; descent from apogee takes 280 s
- Touchdown velocity: 8.36 m/s
</thought>
<design>
{"flight":{"motor":"J1000-LW","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Etage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.28575,"base_radius_m":0.03429,"wall_thickness_m":0.00317,"material":"RS: Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.9144,"outer_d_m":0.06818,"wall_thickness_m":0.00158,"material":"RS: Kraft phenolic","name":"QT Airframe","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.0762,"tip_chord_m":0.04445,"span_m":0.0635,"sweep_m":0.03176,"thickness_m":0.0016,"material":"RS: G10 fiberglass","name":"Lower Fin set"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1143,"tip_chord_m":0.0254,"span_m":0.0635,"sweep_m":0.12064,"thickness_m":0.0016,"material":"RS: G10 fiberglass","name":"Upper Fin set"},{"type":"innertube","length_m":0.254,"outer_d_m":0.04188,"wall_thickness_m":0.00158,"material":"RS: Kraft phenolic","name":"38mm MMT","motors":[{"manufacturer":"Loki Research","designation":"J1000-LW"},{"manufacturer":"AeroTech","designation":"J350W-L"}]},{"type":"innertube","length_m":0.0508,"outer_d_m":0.06502,"wall_thickness_m":0.00157,"material":"RS: Kraft phenolic","name":"Piston","contains":[{"type":"centeringring","material":"RS: Birch","name":"Bulkhead"},{"type":"masscomponent","name":"D-ring","mass_kg":0.00283}]},{"type":"parachute","diameter_m":0.762,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"RS: Rip stop nylon","name":"Parachute"},{"type":"masscomponent","name":"8 oz. epoxy/paint/misc.","mass_kg":0.2268},{"type":"launchlug","length_m":0.1016,"name":"Launch lug"},{"type":"centeringring","material":"RS: Aircraft plywood (Birch)","name":"Ring"},{"type":"centeringring","material":"RS: Aircraft plywood (Birch)","name":"Ring"}],"motors":[{"manufacturer":"Loki Research","designation":"J1000-LW"},{"manufacturer":"AeroTech","designation":"J350W-L"}]}],"motors":[{"manufacturer":"Loki Research","designation":"J1000-LW"},{"manufacturer":"AeroTech","designation":"J350W-L"}]}]}
</design>
```
</details>

### V1-029 · EASY
**Prompt:** Design a rocket on a J350W-L motor that reaches about 1,650 m and stays up close to 226 seconds.
**Rocket:** `ork/PML_SmallEndeavour_38-8.ork` · **Sim:** Simulation 2 · **Motor:** J350W-L
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 1649.9 m · max velocity 356.53 m/s · time to apogee 14.877 s · flight time 226.36 s · touchdown 7.5334 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 6 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on a J350W-L motor that reaches about 1,650 m and stays up close to 226 seconds.

2. PROPULSION & ASCENT:
- Motor: J350W-L
- Simulated apogee: 1,650 m (5,413 ft)
- Time to apogee: 14.9 s
- Peak velocity: 357 m/s (Mach 1.05)

3. RECOVERY & DESCENT:
- Parachute 0.76 m diameter, deploys at ejection
- Total flight time 226 s; descent from apogee takes 211 s
- Touchdown velocity: 7.53 m/s
</thought>
<design>
{"flight":{"motor":"J350W-L","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Etage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.28575,"base_radius_m":0.03429,"wall_thickness_m":0.00317,"material":"RS: Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.9144,"outer_d_m":0.06818,"wall_thickness_m":0.00158,"material":"RS: Kraft phenolic","name":"QT Airframe","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.0762,"tip_chord_m":0.04445,"span_m":0.0635,"sweep_m":0.03176,"thickness_m":0.0016,"material":"RS: G10 fiberglass","name":"Lower Fin set"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1143,"tip_chord_m":0.0254,"span_m":0.0635,"sweep_m":0.12064,"thickness_m":0.0016,"material":"RS: G10 fiberglass","name":"Upper Fin set"},{"type":"innertube","length_m":0.254,"outer_d_m":0.04188,"wall_thickness_m":0.00158,"material":"RS: Kraft phenolic","name":"38mm MMT","motors":[{"manufacturer":"Loki Research","designation":"J1000-LW"},{"manufacturer":"AeroTech","designation":"J350W-L"}]},{"type":"innertube","length_m":0.0508,"outer_d_m":0.06502,"wall_thickness_m":0.00157,"material":"RS: Kraft phenolic","name":"Piston","contains":[{"type":"centeringring","material":"RS: Birch","name":"Bulkhead"},{"type":"masscomponent","name":"D-ring","mass_kg":0.00283}]},{"type":"parachute","diameter_m":0.762,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"RS: Rip stop nylon","name":"Parachute"},{"type":"masscomponent","name":"8 oz. epoxy/paint/misc.","mass_kg":0.2268},{"type":"launchlug","length_m":0.1016,"name":"Launch lug"},{"type":"centeringring","material":"RS: Aircraft plywood (Birch)","name":"Ring"},{"type":"centeringring","material":"RS: Aircraft plywood (Birch)","name":"Ring"}],"motors":[{"manufacturer":"Loki Research","designation":"J1000-LW"},{"manufacturer":"AeroTech","designation":"J350W-L"}]}],"motors":[{"manufacturer":"Loki Research","designation":"J1000-LW"},{"manufacturer":"AeroTech","designation":"J350W-L"}]}]}
</design>
```
</details>

### V1-034 · EASY
**Prompt:** Make a rocket that hits 119 m and stays up about 19 s on a E16 motor.
**Rocket:** `ork/RocketProject.ork` · **Sim:** Simulation 1 · **Motor:** E16
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 119.013 m · max velocity 99.714 m/s · time to apogee 3.202 s · flight time 19.263 s · touchdown 7.877 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 119 m and stays up about 19 s on a E16 motor.

2. PROPULSION & ASCENT:
- Motor: E16
- Simulated apogee: 119 m (390 ft)
- Time to apogee: 3.2 s
- Peak velocity: 100 m/s (Mach 0.29)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 19 s; descent from apogee takes 16 s
- Touchdown velocity: 7.88 m/s
</thought>
<design>
{"flight":{"motor":"E16","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"conical","length_m":0.1524,"base_radius_m":0.0254,"wall_thickness_m":0.0254,"material":"Polyethylene","name":"Nose Cone"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.0508,"wall_thickness_m":0.00127,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.003,"material":"Balsa","name":"Freeform Fin Set"},{"type":"innertube","length_m":0.1524,"outer_d_m":0.03074,"wall_thickness_m":0.00089,"material":"Paper","name":"Inner Tube","motors":[{"manufacturer":"Estes","designation":"E16"}]},{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":4.0,"material":"Rip stop nylon","preset":"Public Missiles Xform","name":"Parachute, nylon, 12\", X-form"}],"motors":[{"manufacturer":"Estes","designation":"E16"}]}],"motors":[{"manufacturer":"Estes","designation":"E16"}]}]}
</design>
```
</details>

### V1-035 · EASY
**Prompt:** Design a rocket that goes to about 218 m apogee on a F27 motor, taking about 7.0 s to apogee.
**Rocket:** `ork/RocketV1.1.ork` · **Sim:** Simulation 1 · **Motor:** F27
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 218.16 m · max velocity 60.311 m/s · time to apogee 7.0344 s · flight time 33.292 s · touchdown 7.2713 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 3 parachutes recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 218 m apogee on a F27 motor, taking about 7.0 s to apogee.

2. PROPULSION & ASCENT:
- Motor: F27
- Simulated apogee: 218 m (716 ft)
- Time to apogee: 7.0 s
- Peak velocity: 60 m/s (Mach 0.18)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 33 s; descent from apogee takes 26 s
- Touchdown velocity: 7.27 m/s
</thought>
<design>
{"flight":{"motor":"F27","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"conical","length_m":0.13,"base_radius_m":0.03,"wall_thickness_m":0.002,"material":"PLA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.1,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.52,"wall_thickness_m":0.002,"material":"PLA","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.003,"material":"PLA","name":"Freeform fin set"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 1"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 2"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 3"},{"type":"masscomponent","name":"Egg 1","mass_kg":0.06,"kind":"payload"},{"type":"masscomponent","name":"Egg 2","mass_kg":0.06,"kind":"payload"},{"type":"masscomponent","name":"Egg 3","mass_kg":0.06,"kind":"payload"}],"motors":[{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"AeroTech","designation":"F23FJ"},{"manufacturer":"AeroTech","designation":"F39"},{"manufacturer":"Apogee","designation":"F10"},{"manufacturer":"AeroTech","designation":"F42T"},{"manufacturer":"AeroTech","designation":"F40"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F35W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"AeroTech","designation":"F23FJ"},{"manufacturer":"AeroTech","designation":"F39"},{"manufacturer":"Apogee","designation":"F10"},{"manufacturer":"AeroTech","designation":"F42T"},{"manufacturer":"AeroTech","designation":"F40"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F35W"}]}]}
</design>
```
</details>

### V1-036 · EASY
**Prompt:** Design a rocket that goes to about 56.9 m/s on a F27 motor, reaching apogee in about 6.8 s.
**Rocket:** `ork/RocketV1.1.ork` · **Sim:** Simulation 2 · **Motor:** F27
**Why easy: 3 requirements: max velocity, time to apogee, motor**
**Targets:** apogee 195.54 m · max velocity 56.928 m/s · time to apogee 6.815 s · flight time 29.813 s · touchdown 7.3873 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 3 parachutes recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 56.9 m/s on a F27 motor, reaching apogee in about 6.8 s.

2. PROPULSION & ASCENT:
- Motor: F27
- Simulated apogee: 196 m (642 ft)
- Time to apogee: 6.8 s
- Peak velocity: 57 m/s (Mach 0.17)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 30 s; descent from apogee takes 23 s
- Touchdown velocity: 7.39 m/s
</thought>
<design>
{"flight":{"motor":"F27","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"conical","length_m":0.13,"base_radius_m":0.03,"wall_thickness_m":0.002,"material":"PLA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.1,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.52,"wall_thickness_m":0.002,"material":"PLA","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.003,"material":"PLA","name":"Freeform fin set"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 1"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 2"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 3"},{"type":"masscomponent","name":"Egg 1","mass_kg":0.06,"kind":"payload"},{"type":"masscomponent","name":"Egg 2","mass_kg":0.06,"kind":"payload"},{"type":"masscomponent","name":"Egg 3","mass_kg":0.06,"kind":"payload"}],"motors":[{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"AeroTech","designation":"F23FJ"},{"manufacturer":"AeroTech","designation":"F39"},{"manufacturer":"Apogee","designation":"F10"},{"manufacturer":"AeroTech","designation":"F42T"},{"manufacturer":"AeroTech","designation":"F40"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F35W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"AeroTech","designation":"F23FJ"},{"manufacturer":"AeroTech","designation":"F39"},{"manufacturer":"Apogee","designation":"F10"},{"manufacturer":"AeroTech","designation":"F42T"},{"manufacturer":"AeroTech","designation":"F40"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F35W"}]}]}
</design>
```
</details>

### V1-041 · EASY
**Prompt:** Design a rocket that goes to about 531 m apogee on a H400-Vmax motor, taking about 9.1 s to apogee.
**Rocket:** `ork/Sainath_L1.ork` · **Sim:** Simulation 11 · **Motor:** H400-Vmax
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 530.99 m · max velocity 165.17 m/s · time to apogee 9.0735 s · flight time 55.189 s · touchdown 5.8396 m/s · wind 6.7056 m/s
**Parts:** nose cone, 2 body tubes, 4 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 531 m apogee on a H400-Vmax motor, taking about 9.1 s to apogee.

2. PROPULSION & ASCENT:
- Motor: H400-Vmax
- Simulated apogee: 531 m (1,742 ft)
- Time to apogee: 9.1 s
- Peak velocity: 165 m/s (Mach 0.49)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at 91 m (300 ft)
- Parachute 0.41 m diameter, deploys at ejection
- Total flight time 55 s; descent from apogee takes 46 s
- Touchdown velocity: 5.84 m/s
</thought>
<design>
{"flight":{"motor":"H400-Vmax","wind_ms":6.7056},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.254,"base_radius_m":0.0508,"wall_thickness_m":0.002,"material":"PLA","name":"3D Printed Nose cone"},{"type":"bodytube","length_m":0.381,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Upper Body tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead 1"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead 2"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead 3 (epoxyed)"},{"type":"masscomponent","name":"1/4'' Threaded Rod","mass_kg":0.032,"kind":"masscomponent"},{"type":"masscomponent","name":"1/4'' Threaded Rod","mass_kg":0.032,"kind":"masscomponent"},{"type":"masscomponent","name":"Altimeter","mass_kg":0.161,"kind":"altimeter"},{"type":"masscomponent","name":"Eye Hook and bolt for altimeter","mass_kg":0.005,"kind":"recoveryhardware"},{"type":"masscomponent","name":"Camera","mass_kg":0.02835,"kind":"masscomponent"},{"type":"masscomponent","name":"Eye Hook and bolt for the shock chord end 1","mass_kg":0.005,"kind":"recoveryhardware"}]},{"type":"bodytube","length_m":0.4826,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Booster Section tube","contains":[{"type":"innertube","length_m":0.2032,"outer_d_m":0.042,"wall_thickness_m":0.00127,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"masscomponent","name":"Motor retainer","mass_kg":0.025,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"},{"manufacturer":"Cesaroni Technology","designation":"H143SS"},{"manufacturer":"Cesaroni Technology","designation":"H400-Vmax"},{"manufacturer":"Cesaroni Technology","designation":"244H153"},{"manufacturer":"Cesaroni Technology","designation":"H120-14A"},{"manufacturer":"Cesaroni Technology","designation":"H125-Classic"},{"manufacturer":"Cesaroni Technology","designation":"H225-14A"},{"manufacturer":"Cesaroni Technology","designation":"269-H110-WH-14A"},{"manufacturer":"Cesaroni Technology","designation":"H152BS"},{"manufacturer":"Cesaroni Technology","designation":"H565"},{"manufacturer":"Cesaroni Technology","designation":"H100-IM"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.178,"tip_chord_m":0.0508,"span_m":0.127,"sweep_m":0.127,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Trapezoidal fin set"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":91.44,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"parachute","diameter_m":0.4064,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Drogue Chute"},{"type":"launchlug","length_m":0.03,"name":"Rail Buttons"},{"type":"launchlug","length_m":0.03,"name":"Rail Buttons"},{"type":"masscomponent","name":"Eye Hook and bolt for the shock chord end 2","mass_kg":0.005,"kind":"recoveryhardware"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"},{"manufacturer":"Cesaroni Technology","designation":"H143SS"},{"manufacturer":"Cesaroni Technology","designation":"H400-Vmax"},{"manufacturer":"Cesaroni Technology","designation":"244H153"},{"manufacturer":"Cesaroni Technology","designation":"H120-14A"},{"manufacturer":"Cesaroni Technology","designation":"H125-Classic"},{"manufacturer":"Cesaroni Technology","designation":"H225-14A"},{"manufacturer":"Cesaroni Technology","designation":"269-H110-WH-14A"},{"manufacturer":"Cesaroni Technology","designation":"H152BS"},{"manufacturer":"Cesaroni Technology","designation":"H565"},{"manufacturer":"Cesaroni Technology","designation":"H100-IM"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"},{"manufacturer":"Cesaroni Technology","designation":"H143SS"},{"manufacturer":"Cesaroni Technology","designation":"H400-Vmax"},{"manufacturer":"Cesaroni Technology","designation":"244H153"},{"manufacturer":"Cesaroni Technology","designation":"H120-14A"},{"manufacturer":"Cesaroni Technology","designation":"H125-Classic"},{"manufacturer":"Cesaroni Technology","designation":"H225-14A"},{"manufacturer":"Cesaroni Technology","designation":"269-H110-WH-14A"},{"manufacturer":"Cesaroni Technology","designation":"H152BS"},{"manufacturer":"Cesaroni Technology","designation":"H565"},{"manufacturer":"Cesaroni Technology","designation":"H100-IM"}]}]}
</design>
```
</details>

### V1-042 · EASY
**Prompt:** Design a rocket on a L1390G motor that reaches about 1,676 m and stays up close to 96 seconds.
**Rocket:** `ork/Scale_model_Nasa.ork` · **Sim:** Simulation to 5766 · **Motor:** L1390G
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 1676.3 m · max velocity 213.19 m/s · time to apogee 18.131 s · flight time 95.61 s · touchdown 6.1038 m/s · wind 0 m/s
**Parts:** nose cone, 3 body tubes, 4 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on a L1390G motor that reaches about 1,676 m and stays up close to 96 seconds.

2. PROPULSION & ASCENT:
- Motor: L1390G
- Simulated apogee: 1,676 m (5,500 ft)
- Time to apogee: 18.1 s
- Peak velocity: 213 m/s (Mach 0.63)

3. RECOVERY & DESCENT:
- Parachute 0.71 m diameter, deploys at 213 m (700 ft)
- Parachute 0.41 m diameter, deploys at apogee
- Total flight time 96 s; descent from apogee takes 77 s
- Touchdown velocity: 6.10 m/s
</thought>
<design>
{"flight":{"motor":"L1390G","wind_ms":0.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1905,"wall_thickness_m":0.00097,"material":"Fiberglass","name":"Nose cone","contains":[{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.15642,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.4446,"outer_d_m":0.0762,"wall_thickness_m":0.00105,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.7112,"deploy_event":"altitude","deploy_altitude_m":213.36,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.03705,"wall_thickness_m":0.00105,"material":"Cardboard","name":"Body tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.5928,"wall_thickness_m":0.00105,"material":"Cardboard","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.1905,"tip_chord_m":0.03705,"span_m":0.0635,"sweep_m":0.15891,"thickness_m":0.00146,"material":"Plywood (birch)","name":"Trapezoidal fin set"},{"type":"innertube","length_m":0.2032,"outer_d_m":0.03132,"wall_thickness_m":0.00104,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"H55W"},{"manufacturer":"AeroTech","designation":"G80NBT"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"parachute","diameter_m":0.4064,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"H55W"},{"manufacturer":"AeroTech","designation":"G80NBT"}]}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"H55W"},{"manufacturer":"AeroTech","designation":"G80NBT"}]}]}
</design>
```
</details>

### V1-048 · EASY
**Prompt:** Make a rocket that hits 450 m and stays up about 68 s on a F50T motor.
**Rocket:** `ork/TARC Payloader.ork` · **Sim:** Simulation 1 · **Motor:** F50T
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 450.34 m · max velocity 148.55 m/s · time to apogee 8.2147 s · flight time 67.707 s · touchdown 7.4426 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 2 stages, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 450 m and stays up about 68 s on a F50T motor.

2. PROPULSION & ASCENT:
- Motor: F50T
- Simulated apogee: 450 m (1,477 ft)
- Time to apogee: 8.2 s
- Peak velocity: 149 m/s (Mach 0.44)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at lowerstageseparation
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 68 s; descent from apogee takes 59 s
- Touchdown velocity: 7.44 m/s
</thought>
<design>
{"flight":{"motor":"F50T","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Payload","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1778,"material":"Balsa","name":"Nose cone"},{"type":"bodytube","length_m":0.127,"outer_d_m":0.05632,"wall_thickness_m":0.00053,"material":"Paper","name":"Body tube","contains":[{"type":"masscomponent","name":"Mass component","mass_kg":0.05},{"type":"parachute","diameter_m":0.4572,"deploy_event":"lowerstageseparation","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.762,"outer_d_m":0.05632,"wall_thickness_m":0.00053,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"innertube","length_m":0.2286,"outer_d_m":0.03214,"wall_thickness_m":0.00152,"material":"Kraft phenolic","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"F50T"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0754,"tip_chord_m":0.0246,"span_m":0.0554,"sweep_m":0.025,"thickness_m":0.003,"material":"Basswood","name":"Trapezoidal fin set #1"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0754,"tip_chord_m":0.0246,"span_m":0.0554,"sweep_m":0.025,"thickness_m":0.003,"material":"Basswood","name":"Trapezoidal fin set #2"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0754,"tip_chord_m":0.0246,"span_m":0.0554,"sweep_m":0.025,"thickness_m":0.003,"material":"Basswood","name":"Trapezoidal fin set #3"}],"motors":[{"manufacturer":"AeroTech","designation":"F50T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F50T"}]}]}
</design>
```
</details>

### V1-052 · EASY
**Prompt:** Design a rocket that goes to about 118.5 m/s max velocity with a 122.0 s flight and touchdown at about 4.4 m/s.
**Rocket:** `ork/Three-stage rocket.ork` · **Sim:** Simulation 2 · **Motor:** C6, B6
**Why easy: 3 requirements: max velocity, flight time, touchdown speed**
**Targets:** apogee 469.82 m · max velocity 118.52 m/s · time to apogee 8.9791 s · flight time 122.01 s · touchdown 4.3966 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 2 fins, 3 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 118.5 m/s max velocity with a 122.0 s flight and touchdown at about 4.4 m/s.

2. PROPULSION & ASCENT:
- Motor: C6, B6
- Simulated apogee: 470 m (1,541 ft)
- Time to apogee: 9.0 s
- Peak velocity: 119 m/s (Mach 0.35)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 122 s; descent from apogee takes 113 s
- Touchdown velocity: 4.40 m/s
</thought>
<design>
{"flight":{"motor":"C6, B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1,"base_radius_m":0.0125,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose cone"},{"type":"bodytube","length_m":0.3,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube","contains":[{"type":"trapezoidfin","root_chord_m":0.05,"tip_chord_m":0.05,"span_m":0.03,"sweep_m":0.025,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal fin set"},{"type":"innertube","length_m":0.075,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"masscomponent","name":"Wadding","mass_kg":0.002,"kind":"masscomponent"},{"type":"launchlug","length_m":0.035,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.08,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"freeformfinset","thickness_m":0.002,"material":"Cardboard","name":"Freeform fin set"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.08,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"trapezoidfin","root_chord_m":0.08,"tip_chord_m":0.03,"span_m":0.04,"sweep_m":0.025,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.035,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-054 · EASY
**Prompt:** Make a rocket that reaches about 995 m on a HP-I65W motor and is down in about 50 seconds.
**Rocket:** `ork/TrinetraOne.ork` · **Sim:** Simulation 2 · **Motor:** HP-I65W
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 995.009 m · max velocity 104.095 m/s · time to apogee 16.651 s · flight time 49.776 s · touchdown 31.333 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, transition, 3 fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that reaches about 995 m on a HP-I65W motor and is down in about 50 seconds.

2. PROPULSION & ASCENT:
- Motor: HP-I65W
- Simulated apogee: 995 m (3,264 ft)
- Time to apogee: 16.7 s
- Peak velocity: 104 m/s (Mach 0.31)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 50 s; descent from apogee takes 33 s
- Touchdown velocity: 31.33 m/s
</thought>
<design>
{"flight":{"motor":"HP-I65W","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.3048,"base_radius_m":0.0381,"wall_thickness_m":0.00127,"material":"Fiberglass","name":"Nose Cone"},{"type":"bodytube","length_m":0.2032,"outer_d_m":0.0762,"wall_thickness_m":0.00127,"material":"Blue tube","name":"Payload Tube","contains":[{"type":"masscomponent","name":"Payload","mass_kg":2.26796,"kind":"payload"}]},{"type":"transition","shape":"conical","length_m":0.075,"fore_d_m":0.0762,"aft_d_m":0.0574,"material":"Fiberglass","name":"Transition","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.254,"outer_d_m":0.0574,"wall_thickness_m":0.00127,"material":"Blue tube","name":"Parachute Tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.381,"outer_d_m":0.0574,"wall_thickness_m":0.00127,"material":"Blue tube","name":"Booster Tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.0574,"tip_chord_m":0.032,"span_m":0.03048,"sweep_m":0.0254,"thickness_m":0.003,"material":"Fiberglass","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"AeroTech","designation":"HP-I65W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"HP-I65W"}]}]}
</design>
```
</details>

### V1-057 · EASY
**Prompt:** Design a rocket that goes to about 1,378 m apogee in about 16.3 s to apogee on a I59WN, I357T motor.
**Rocket:** `ork/Two stage high power rocket.ork` · **Sim:** Simulation 2 · **Motor:** I59WN, I357T
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 1378.36 m · max velocity 175.735 m/s · time to apogee 16.275 s · flight time 103.389 s · touchdown 6.451 m/s · wind 1.99827 m/s
**Parts:** nose cone, 8 body tubes, 6 fins, 2 stages, 3 parachutes recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 1,378 m apogee in about 16.3 s to apogee on a I59WN, I357T motor.

2. PROPULSION & ASCENT:
- Motor: I59WN, I357T
- Simulated apogee: 1,378 m (4,522 ft)
- Time to apogee: 16.3 s
- Peak velocity: 176 m/s (Mach 0.52)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.61 m diameter, deploys at ejection
- Total flight time 103 s; descent from apogee takes 87 s
- Touchdown velocity: 6.45 m/s
</thought>
<design>
{"flight":{"motor":"I59WN, I357T","wind_ms":1.9982688},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.32385,"base_radius_m":0.0508,"wall_thickness_m":0.00152,"material":"Polypropylene","name":"Nose Cone"},{"type":"bodytube","length_m":0.0762,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Payload Bay"},{"type":"bodytube","length_m":0.4318,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Sustainer Forward Airframe","contains":[{"type":"parachute","diameter_m":0.9144,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":10.0,"material":"Nylon fabric","name":"Sustainer Main"}]},{"type":"bodytube","length_m":0.0254,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Sustainer Switch Band","contains":[{"type":"railbutton","name":"Rail Button"}]},{"type":"bodytube","length_m":0.381,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Sustainer Aft Airframe","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Nylon fabric","name":"Sustainer Drogue"}]},{"type":"bodytube","length_m":0.1778,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Sustainer Fin Section","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.14605,"tip_chord_m":0.0762,"span_m":0.1524,"sweep_m":0.0381,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"innertube","length_m":0.15875,"outer_d_m":0.07874,"wall_thickness_m":0.00127,"material":"Paper","name":"Inner Tube","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.15875,"outer_d_m":0.04128,"wall_thickness_m":0.00133,"material":"Paper","name":"Sustainer Motor Mount","motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I59WN"}]}]},{"type":"centeringring","material":"Plywood","name":"Centering Ring"}],"motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I59WN"}]}],"motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I59WN"}]},{"type":"stage_marker","name":"Booster","contains":[{"type":"bodytube","length_m":0.0762,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Interstage","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.0508,"outer_d_m":0.07874,"wall_thickness_m":0.00127,"material":"Paper","name":"Inner Tube"},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"railbutton","name":"Rail Button"}]},{"type":"bodytube","length_m":0.381,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Booster airframe","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","name":"Booster Chute"}]},{"type":"bodytube","length_m":0.1778,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Booster fin section","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.15875,"outer_d_m":0.04128,"wall_thickness_m":0.00133,"material":"Paper","name":"Booster motor mount","motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I357T"}]},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.14605,"tip_chord_m":0.0762,"span_m":0.1651,"sweep_m":0.0381,"thickness_m":0.003,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I357T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I357T"}]}]}
</design>
```
</details>

### V1-060 · EASY
**Prompt:** Design a rocket that goes to about 350 m apogee in about 8.4 s to apogee on a F50T motor.
**Rocket:** `ork/demo-payload-separation.ork` · **Sim:** Simulation 1 · **Motor:** F50T
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 350 m · max velocity 93 m/s · time to apogee 8.4 s · flight time 98 s · touchdown 4.5 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 2 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 350 m apogee in about 8.4 s to apogee on a F50T motor.

2. PROPULSION & ASCENT:
- Motor: F50T
- Simulated apogee: 350 m (1,148 ft)
- Time to apogee: 8.4 s
- Peak velocity: 93 m/s (Mach 0.27)

3. RECOVERY & DESCENT:
- Parachute 0.71 m diameter, deploys at lowerstageseparation
- Total flight time 98 s; descent from apogee takes 90 s
- Touchdown velocity: 4.50 m/s
</thought>
<design>
{"flight":{"motor":"F50T","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Payload","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.22,"base_radius_m":0.019,"wall_thickness_m":0.003,"material":"Fiberglass","name":"Nose cone"},{"type":"bodytube","length_m":0.32,"outer_d_m":0.038,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Payload bay","contains":[{"type":"masscomponent","name":"Payload + altimeter","mass_kg":0.09,"kind":"payload"},{"type":"parachute","diameter_m":0.71,"deploy_event":"lowerstageseparation","deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Payload parachute"}]}]},{"type":"stage_marker","name":"Booster","contains":[{"type":"bodytube","length_m":0.34,"outer_d_m":0.038,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Booster / motor bay","contains":[{"type":"innertube","length_m":0.2,"outer_d_m":0.029,"wall_thickness_m":0.0005,"material":"Kraft phenolic","name":"Motor mount tube","motors":[{"manufacturer":"AeroTech","designation":"F50T"}]},{"type":"centeringring","material":"Aircraft plywood","name":"Centering ring fore"},{"type":"centeringring","material":"Aircraft plywood","name":"Centering ring aft"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.11,"tip_chord_m":0.05,"span_m":0.055,"sweep_m":0.06,"thickness_m":0.004,"material":"G10 fiberglass","name":"Fins"}],"motors":[{"manufacturer":"AeroTech","designation":"F50T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F50T"}]}]}
</design>
```
</details>

### V1-061 · EASY
**Prompt:** Design a rocket that goes to about 142.7 m/s max velocity with a 90.9 s flight and touchdown at about 7.2 m/s.
**Rocket:** `ork/endurance.ork` · **Sim:** Simulation 10 · **Motor:** L2200G
**Why easy: 3 requirements: max velocity, flight time, touchdown speed**
**Targets:** apogee 1022.6 m · max velocity 142.74 m/s · time to apogee 14.871 s · flight time 90.896 s · touchdown 7.2069 m/s · wind 0.1 m/s
**Parts:** nose cone, 3 body tubes, 3 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 142.7 m/s max velocity with a 90.9 s flight and touchdown at about 7.2 m/s.

2. PROPULSION & ASCENT:
- Motor: L2200G
- Simulated apogee: 1,023 m (3,355 ft)
- Time to apogee: 14.9 s
- Peak velocity: 143 m/s (Mach 0.42)

3. RECOVERY & DESCENT:
- Parachute 1.27 m diameter, deploys at apogee
- Parachute 2.44 m diameter, deploys at 213 m (700 ft)
- Total flight time 91 s; descent from apogee takes 76 s
- Touchdown velocity: 7.21 m/s
</thought>
<design>
{"flight":{"motor":"L2200G","wind_ms":0.1},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.9144,"base_radius_m":0.07836,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Nose cone","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Lower Bulkhead"},{"type":"bulkhead","material":"PLA","name":"Upper Bulkhead"},{"type":"masscomponent","name":"Metal Tip","mass_kg":0.03317,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Ballast","mass_kg":4.53592,"kind":"masscomponent"}]},{"type":"bodytube","length_m":1.016,"wall_thickness_m":0.0023,"material":"Fiberglass","name":"Mid-airframe 5'","contains":[{"type":"parachute","diameter_m":1.27,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":3.0,"material":"Ripstop nylon","name":"Drogue"},{"type":"parachute","diameter_m":2.4384,"deploy_event":"altitude","deploy_altitude_m":213.36,"deploy_delay_s":0.0,"line_count":14.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Quick Links + TD + Misc.","mass_kg":0.90718,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.0508,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Switchband"},{"type":"bodytube","length_m":0.9144,"wall_thickness_m":0.00254,"material":"Fiberglass","name":"Booster Tube","contains":[{"type":"centeringring","material":"Aluminum","name":"Bottom Centering ring"},{"type":"masscomponent","name":"Fin Can?","mass_kg":1.36078,"kind":"masscomponent"},{"type":"masscomponent","name":"N Casing + Motor Adapter","mass_kg":2.26796,"kind":"masscomponent"},{"type":"masscomponent","name":"Thrust Plate and Retainer","mass_kg":0.492,"kind":"masscomponent"},{"type":"innertube","length_m":0.7493,"outer_d_m":0.0983,"wall_thickness_m":0.00015,"material":"Aluminum","name":"Inner Tube"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.2794,"tip_chord_m":0.127,"span_m":0.15875,"sweep_m":0.127,"thickness_m":0.00635,"material":"Fiberglass","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"N2000W"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"M6000ST"}]}],"motors":[{"manufacturer":"AeroTech","designation":"N2000W"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"M6000ST"}]}]}
</design>
```
</details>

### V1-063 · EASY
**Prompt:** Build a rocket on a N2000W motor that reaches about 3,066 m and is back down in about 203 seconds.
**Rocket:** `ork/endurance.ork` · **Sim:** Simulation 12 · **Motor:** N2000W
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 3066 m · max velocity 254.61 m/s · time to apogee 25.451 s · flight time 202.99 s · touchdown 7.674 m/s · wind 4.5704 m/s
**Parts:** nose cone, 3 body tubes, 3 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Build a rocket on a N2000W motor that reaches about 3,066 m and is back down in about 203 seconds.

2. PROPULSION & ASCENT:
- Motor: N2000W
- Simulated apogee: 3,066 m (10,059 ft)
- Time to apogee: 25.5 s
- Peak velocity: 255 m/s (Mach 0.76)

3. RECOVERY & DESCENT:
- Parachute 1.27 m diameter, deploys at apogee
- Parachute 2.44 m diameter, deploys at 213 m (700 ft)
- Total flight time 203 s; descent from apogee takes 178 s
- Touchdown velocity: 7.67 m/s
</thought>
<design>
{"flight":{"motor":"N2000W","wind_ms":4.5704},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.9144,"base_radius_m":0.07836,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Nose cone","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Lower Bulkhead"},{"type":"bulkhead","material":"PLA","name":"Upper Bulkhead"},{"type":"masscomponent","name":"Metal Tip","mass_kg":0.03317,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Ballast","mass_kg":4.53592,"kind":"masscomponent"}]},{"type":"bodytube","length_m":1.016,"wall_thickness_m":0.0023,"material":"Fiberglass","name":"Mid-airframe 5'","contains":[{"type":"parachute","diameter_m":1.27,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":3.0,"material":"Ripstop nylon","name":"Drogue"},{"type":"parachute","diameter_m":2.4384,"deploy_event":"altitude","deploy_altitude_m":213.36,"deploy_delay_s":0.0,"line_count":14.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Quick Links + TD + Misc.","mass_kg":0.90718,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.0508,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Switchband"},{"type":"bodytube","length_m":0.9144,"wall_thickness_m":0.00254,"material":"Fiberglass","name":"Booster Tube","contains":[{"type":"centeringring","material":"Aluminum","name":"Bottom Centering ring"},{"type":"masscomponent","name":"Fin Can?","mass_kg":1.36078,"kind":"masscomponent"},{"type":"masscomponent","name":"N Casing + Motor Adapter","mass_kg":2.26796,"kind":"masscomponent"},{"type":"masscomponent","name":"Thrust Plate and Retainer","mass_kg":0.492,"kind":"masscomponent"},{"type":"innertube","length_m":0.7493,"outer_d_m":0.0983,"wall_thickness_m":0.00015,"material":"Aluminum","name":"Inner Tube"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.2794,"tip_chord_m":0.127,"span_m":0.15875,"sweep_m":0.127,"thickness_m":0.00635,"material":"Fiberglass","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"N2000W"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"M6000ST"}]}],"motors":[{"manufacturer":"AeroTech","designation":"N2000W"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"M6000ST"}]}]}
</design>
```
</details>

### V1-069 · EASY
**Prompt:** Make a rocket that reaches about 286 m on a D13W motor and is down in about 64 seconds.
**Rocket:** `ork/estes_antar_7310.ork` · **Sim:** Simulation 2 · **Motor:** D13W
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 286.229 m · max velocity 102.49 m/s · time to apogee 6.86 s · flight time 63.852 s · touchdown 4.932 m/s · wind 3.57632 m/s
**Parts:** nose cone, 4 body tubes, transition, freeform fins, 2 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that reaches about 286 m on a D13W motor and is down in about 64 seconds.

2. PROPULSION & ASCENT:
- Motor: D13W
- Simulated apogee: 286 m (939 ft)
- Time to apogee: 6.9 s
- Peak velocity: 102 m/s (Mach 0.30)

3. RECOVERY & DESCENT:
- Parachute 0.38 m diameter, deploys at ejection
- Total flight time 64 s; descent from apogee takes 57 s
- Touchdown velocity: 4.93 m/s
</thought>
<design>
{"flight":{"motor":"D13W","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.30000000000000004,"length_m":0.005,"base_radius_m":0.0035,"wall_thickness_m":0.0,"material":"Polystyrene PS","name":"Nose cone","contains":[{"type":"masscomponent","name":"Clay","mass_kg":0.01417,"kind":"masscomponent"}]},{"type":"transition","shape":"ogive","length_m":0.21,"fore_d_m":0.007,"aft_d_m":0.04166,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.3302,"outer_d_m":0.04166,"wall_thickness_m":0.00071,"material":"Cellulose Acetate Propionate","name":"Main Body tube","contains":[{"type":"parachute","diameter_m":0.381,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute - 15'"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Fin #1 (Dorsal)"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Dorsal fin"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Fin #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Fin #3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Wing - L"},{"type":"pod_set","count":1.0,"name":"Pod Set for Winglets - L","contains":[{"type":"bodytube","length_m":0.0,"wall_thickness_m":0.0,"material":"Cardboard","name":"(Phantom BT)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.05715,"tip_chord_m":0.0,"span_m":0.00965,"sweep_m":0.043,"thickness_m":0.00317,"material":"Cardboard","name":"Trapezoidal Wing Fin Set"}]}]},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Wing - R"},{"type":"pod_set","count":1.0,"name":"Pod Set for Winglets - R","contains":[{"type":"bodytube","length_m":0.0,"wall_thickness_m":0.0,"material":"Cardboard","name":"(Phantom BT)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.05715,"tip_chord_m":0.0,"span_m":0.00965,"sweep_m":0.043,"thickness_m":0.00317,"material":"Cardboard","name":"Trapezoidal Wing Fin Set"}]}]},{"type":"launchlug","length_m":0.01905,"name":"Launch Lug - F"},{"type":"launchlug","length_m":0.01905,"name":"Launch Lug - R"},{"type":"innertube","length_m":0.059,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Paper","name":"Motor tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Quest","designation":"D20W"}]},{"type":"centeringring","material":"Cardboard","name":"Centering Ring - F"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring - R"},{"type":"pod_set","count":1.0,"name":"Pod Set - Vanes","contains":[{"type":"bodytube","length_m":0.011,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Paper","name":"Body Tube (for MMT Vanes)","contains":[{"type":"freeformfinset","fin_count":8.0,"thickness_m":8e-05,"material":"Cardboard","name":"Vanes Fin Set MMT"}]}]},{"type":"innertube","length_m":0.0082,"outer_d_m":0.01956,"wall_thickness_m":0.00038,"material":"Cardboard","name":"Retainer Ring"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Quest","designation":"D20W"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Quest","designation":"D20W"}]}]}
</design>
```
</details>

### V1-075 · EASY
**Prompt:** Design a rocket on a E12 motor that reaches about 122 m and stays up close to 30 seconds.
**Rocket:** `ork/estes_explorer_aquarius_2016-7253.ork` · **Sim:** Simulation 3 · **Motor:** E12
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 121.822 m · max velocity 43.488 m/s · time to apogee 4.723 s · flight time 29.543 s · touchdown 4.691 m/s · wind 3.57632 m/s
**Parts:** nose cone, 24 body tubes, transition, 3 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on a E12 motor that reaches about 122 m and stays up close to 30 seconds.

2. PROPULSION & ASCENT:
- Motor: E12
- Simulated apogee: 122 m (400 ft)
- Time to apogee: 4.7 s
- Peak velocity: 43 m/s (Mach 0.13)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 30 s; descent from apogee takes 25 s
- Touchdown velocity: 4.69 m/s
</thought>
<design>
{"flight":{"motor":"E12","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.07303,"base_radius_m":0.03397,"wall_thickness_m":0.0003,"material":"Polystyrene PS","name":"Nose Cone - Upper"},{"type":"transition","shape":"power","length_m":0.0127,"fore_d_m":0.06794,"aft_d_m":0.03352,"material":"Polystyrene PS","name":"Nose Cone - Middle"},{"type":"bodytube","length_m":0.00476,"outer_d_m":0.03352,"wall_thickness_m":0.00053,"material":"Polystyrene","name":"Nose Cone - Lower"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.03352,"wall_thickness_m":0.00051,"material":"Spiral/Glassine","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute"},{"type":"innertube","length_m":0.0889,"outer_d_m":0.0249,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring - F"},{"type":"centeringring","material":"Cardboard","name":"Centering ring - R"},{"type":"centeringring","material":"Cardboard","name":"Sleeve"},{"type":"engineblock","name":"Engine block"},{"type":"masscomponent","name":"Engine Hook E","mass_kg":0.00185,"kind":"masscomponent"}],"motors":[{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Estes Industries, Inc.","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.06667,"tip_chord_m":0.06667,"span_m":0.08572,"sweep_m":0.0,"thickness_m":0.00238,"material":"Balsa","name":"Fin set #1"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.06667,"tip_chord_m":0.06667,"span_m":0.08572,"sweep_m":0.0,"thickness_m":0.00238,"material":"Balsa","name":"Fin set #2"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.06667,"tip_chord_m":0.06667,"span_m":0.08572,"sweep_m":0.0,"thickness_m":0.00238,"material":"Balsa","name":"Fin set #3"},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 1","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U1","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 2","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U2","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 3","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U3","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 4","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U4","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 5","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U5","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 6","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U6","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M1","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M2","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M3","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M4","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M5","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M6","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L1","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L2","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L3","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L4","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L5","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L6","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Nozzle Assembly","contains":[{"type":"bodytube","length_m":0.02222,"outer_d_m":0.03252,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle Shoulder - W1"},{"type":"transition","shape":"conical","length_m":0.0019,"fore_d_m":0.05,"aft_d_m":0.02032,"material":"Cardboard","name":"Nozzle Transition - W2"},{"type":"bodytube","length_m":0.00444,"outer_d_m":0.02032,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle - W3"},{"type":"bodytube","length_m":0.00165,"outer_d_m":0.02236,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle Collar - W4"},{"type":"bodytube","length_m":0.00698,"outer_d_m":0.02032,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle - S1"},{"type":"transition","shape":"conical","length_m":0.00521,"fore_d_m":0.05,"aft_d_m":0.0169,"material":"Cardboard","name":"Nozzle Bell Top - S2"},{"type":"transition","shape":"conical","length_m":0.00521,"fore_d_m":0.0169,"aft_d_m":0.02032,"material":"Cardboard","name":"Nozzle Bell Top - S3"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.0169,"aft_d_m":0.02032,"material":"Cardboard","name":"Nozzle Bell Ridge - B1"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0208,"aft_d_m":0.02174,"material":"Cardboard","name":"Nozzle Bell Band - B1"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.0241,"aft_d_m":0.0241,"material":"Cardboard","name":"Nozzle Bell Ridge - B2"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0241,"aft_d_m":0.02664,"material":"Cardboard","name":"Nozzle Bell Band - B2"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.02802,"aft_d_m":0.02802,"material":"Cardboard","name":"Nozzle Bell Ridge - B3"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.02768,"aft_d_m":0.0296,"material":"Cardboard","name":"Nozzle Bell Band - B3"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.0301,"aft_d_m":0.0301,"material":"Cardboard","name":"Nozzle Bell Ridge - B4"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0301,"aft_d_m":0.03148,"material":"Cardboard","name":"Nozzle Bell Band - B4"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03252,"aft_d_m":0.03252,"material":"Cardboard","name":"Nozzle Bell Ridge - B5"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.03226,"aft_d_m":0.0331,"material":"Cardboard","name":"Nozzle Bell Band - B5"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03442,"aft_d_m":0.03442,"material":"Cardboard","name":"Nozzle Bell Ridge - B6"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.03384,"aft_d_m":0.03432,"material":"Cardboard","name":"Nozzle Bell Band - B6"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03508,"aft_d_m":0.03508,"material":"Cardboard","name":"Nozzle Bell Ridge - B7"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.03442,"aft_d_m":0.03456,"material":"Cardboard","name":"Nozzle Bell Band - B7"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03586,"aft_d_m":0.03586,"material":"Cardboard","name":"Nozzle Bell Ridge - B8"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0349,"aft_d_m":0.03528,"material":"Cardboard","name":"Nozzle Bell Band - B8"}]}],"motors":[{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Estes Industries, Inc.","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}],"motors":[{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Estes Industries, Inc.","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}]}
</design>
```
</details>

### V1-077 · EASY
**Prompt:** Build a rocket on a B4 motor that reaches about 87 m and is back down in about 24 seconds.
**Rocket:** `ork/estes_patriot.ork` · **Sim:** Simulation 1 · **Motor:** B4
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 87.476 m · max velocity 43.091 m/s · time to apogee 4.3048 s · flight time 24.151 s · touchdown 4.2452 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Build a rocket on a B4 motor that reaches about 87 m and is back down in about 24 seconds.

2. PROPULSION & ASCENT:
- Motor: B4
- Simulated apogee: 87 m (287 ft)
- Time to apogee: 4.3 s
- Peak velocity: 43 m/s (Mach 0.13)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 24 s; descent from apogee takes 20 s
- Touchdown velocity: 4.25 m/s
</thought>
<design>
{"flight":{"motor":"B4","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.12,"wall_thickness_m":0.00118,"material":"Cardboard","name":"Nose cone"},{"type":"bodytube","length_m":0.078,"outer_d_m":0.04158,"wall_thickness_m":0.0006,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"}]},{"type":"bodytube","length_m":0.169,"outer_d_m":0.04158,"wall_thickness_m":0.0007,"material":"Cardboard","name":"Body tube"},{"type":"bodytube","length_m":0.169,"outer_d_m":0.04158,"wall_thickness_m":0.0007,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"Body tube","contains":[{"type":"centeringring","material":"Paper","name":"Ring"},{"type":"centeringring","material":"Paper","name":"Mylar Ring"},{"type":"centeringring","material":"Paper","name":"Ring"},{"type":"masscomponent","name":"Engine hook","mass_kg":0.0014},{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.075,"tip_chord_m":0.0325,"span_m":0.0345,"sweep_m":0.043,"thickness_m":0.0033,"material":"Balsa","name":"Fin set"},{"type":"launchlug","length_m":0.061,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-078 · EASY
**Prompt:** Design a rocket that goes to about 91 m apogee in about 4.3 s to apogee on a B6 motor.
**Rocket:** `ork/estes_patriot.ork` · **Sim:** Simulation 2 · **Motor:** B6
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 90.806 m · max velocity 47.862 m/s · time to apogee 4.3086 s · flight time 25.441 s · touchdown 4.5866 m/s · wind 4 m/s
**Parts:** nose cone, 3 body tubes, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 91 m apogee in about 4.3 s to apogee on a B6 motor.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 91 m (298 ft)
- Time to apogee: 4.3 s
- Peak velocity: 48 m/s (Mach 0.14)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 25 s; descent from apogee takes 21 s
- Touchdown velocity: 4.59 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":4.0},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.12,"wall_thickness_m":0.00118,"material":"Cardboard","name":"Nose cone"},{"type":"bodytube","length_m":0.078,"outer_d_m":0.04158,"wall_thickness_m":0.0006,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"}]},{"type":"bodytube","length_m":0.169,"outer_d_m":0.04158,"wall_thickness_m":0.0007,"material":"Cardboard","name":"Body tube"},{"type":"bodytube","length_m":0.169,"outer_d_m":0.04158,"wall_thickness_m":0.0007,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"Body tube","contains":[{"type":"centeringring","material":"Paper","name":"Ring"},{"type":"centeringring","material":"Paper","name":"Mylar Ring"},{"type":"centeringring","material":"Paper","name":"Ring"},{"type":"masscomponent","name":"Engine hook","mass_kg":0.0014},{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.075,"tip_chord_m":0.0325,"span_m":0.0345,"sweep_m":0.043,"thickness_m":0.0033,"material":"Balsa","name":"Fin set"},{"type":"launchlug","length_m":0.061,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-079 · EASY
**Prompt:** Design a rocket that goes to about 106 m apogee with deployment at about 5.8 m/s and a 23.6 s flight.
**Rocket:** `ork/estes_rubicon_2189.ork` · **Sim:** Simulation 1 · **Motor:** D12
**Why easy: 3 requirements: apogee, flight time, touchdown speed**
**Targets:** apogee 106.118 m · max velocity 41.562 m/s · time to apogee 5.035 s · flight time 23.6 s · touchdown 5.839 m/s · wind 3.57632 m/s
**Parts:** nose cone, 10 body tubes, transition, freeform fins, 12 fins, pods, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 106 m apogee with deployment at about 5.8 m/s and a 23.6 s flight.

2. PROPULSION & ASCENT:
- Motor: D12
- Simulated apogee: 106 m (348 ft)
- Time to apogee: 5.0 s
- Peak velocity: 42 m/s (Mach 0.12)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 24 s; descent from apogee takes 19 s
- Touchdown velocity: 5.84 m/s
</thought>
<design>
{"flight":{"motor":"D12","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":3e-05,"base_radius_m":0.00635,"wall_thickness_m":0.00508,"material":"Polystyrene","name":"Nose Cone"},{"type":"transition","shape":"conical","length_m":0.1524,"fore_d_m":0.015,"aft_d_m":0.082,"material":"Custom","name":"Transition"},{"type":"bodytube","length_m":0.154,"outer_d_m":0.082,"wall_thickness_m":0.0005,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"pod_set","count":1.0,"name":"Pod Set - Front Launch Lug","contains":[{"type":"bodytube","length_m":0.007,"outer_d_m":0.008,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body Tube (Launch Lug - R)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - L"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.007,"tip_chord_m":0.007,"span_m":0.01524,"sweep_m":0.0,"thickness_m":0.001,"material":"Cardboard","name":"Trapezoidal Fin Set - M"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - R"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Rear Launch Lug","contains":[{"type":"bodytube","length_m":0.007,"outer_d_m":0.008,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body Tube (Launch Lug - R)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - L"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.007,"tip_chord_m":0.007,"span_m":0.01524,"sweep_m":0.0,"thickness_m":0.001,"material":"Cardboard","name":"Trapezoidal Fin Set - M"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - R"}]}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"bulkhead","material":"Polycarbonate","name":"Bulkhead"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"innertube","length_m":0.3175,"outer_d_m":0.025,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Engine Mount Tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"C11"}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Engine Hook","contains":[{"type":"bodytube","length_m":0.0762,"wall_thickness_m":0.0,"material":"Cardboard","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Steel","name":"Freeform fin set #2"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set","contains":[{"type":"transition","shape":"conical","length_m":0.23564,"aft_d_m":0.082,"material":"Cardboard","name":"Base Vortex"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"C11"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"C11"}]}]}
</design>
```
</details>

### V1-080 · EASY
**Prompt:** Design a rocket that goes to about 174 m apogee in about 6.4 s to apogee on a E12 motor.
**Rocket:** `ork/estes_rubicon_2189.ork` · **Sim:** Simulation 2 · **Motor:** E12
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 174.408 m · max velocity 54.656 m/s · time to apogee 6.393 s · flight time 36.544 s · touchdown 5.896 m/s · wind 3.57632 m/s
**Parts:** nose cone, 10 body tubes, transition, freeform fins, 12 fins, pods, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 174 m apogee in about 6.4 s to apogee on a E12 motor.

2. PROPULSION & ASCENT:
- Motor: E12
- Simulated apogee: 174 m (572 ft)
- Time to apogee: 6.4 s
- Peak velocity: 55 m/s (Mach 0.16)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 37 s; descent from apogee takes 30 s
- Touchdown velocity: 5.90 m/s
</thought>
<design>
{"flight":{"motor":"E12","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":3e-05,"base_radius_m":0.00635,"wall_thickness_m":0.00508,"material":"Polystyrene","name":"Nose Cone"},{"type":"transition","shape":"conical","length_m":0.1524,"fore_d_m":0.015,"aft_d_m":0.082,"material":"Custom","name":"Transition"},{"type":"bodytube","length_m":0.154,"outer_d_m":0.082,"wall_thickness_m":0.0005,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"pod_set","count":1.0,"name":"Pod Set - Front Launch Lug","contains":[{"type":"bodytube","length_m":0.007,"outer_d_m":0.008,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body Tube (Launch Lug - R)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - L"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.007,"tip_chord_m":0.007,"span_m":0.01524,"sweep_m":0.0,"thickness_m":0.001,"material":"Cardboard","name":"Trapezoidal Fin Set - M"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - R"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Rear Launch Lug","contains":[{"type":"bodytube","length_m":0.007,"outer_d_m":0.008,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body Tube (Launch Lug - R)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - L"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.007,"tip_chord_m":0.007,"span_m":0.01524,"sweep_m":0.0,"thickness_m":0.001,"material":"Cardboard","name":"Trapezoidal Fin Set - M"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - R"}]}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"bulkhead","material":"Polycarbonate","name":"Bulkhead"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"innertube","length_m":0.3175,"outer_d_m":0.025,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Engine Mount Tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"C11"}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Engine Hook","contains":[{"type":"bodytube","length_m":0.0762,"wall_thickness_m":0.0,"material":"Cardboard","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Steel","name":"Freeform fin set #2"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set","contains":[{"type":"transition","shape":"conical","length_m":0.23564,"aft_d_m":0.082,"material":"Cardboard","name":"Base Vortex"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"C11"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"C11"}]}]}
</design>
```
</details>

### V1-083 · EASY
**Prompt:** Design a rocket on a E12 motor that reaches about 487 m and stays up close to 92 seconds.
**Rocket:** `ork/estes_sky_raider.ork` · **Sim:** Simulation 2 · **Motor:** E12
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 486.98 m · max velocity 139.99 m/s · time to apogee 8.3442 s · flight time 91.506 s · touchdown 3.3693 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on a E12 motor that reaches about 487 m and stays up close to 92 seconds.

2. PROPULSION & ASCENT:
- Motor: E12
- Simulated apogee: 487 m (1,598 ft)
- Time to apogee: 8.3 s
- Peak velocity: 140 m/s (Mach 0.41)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at 100 m (328 ft)
- Total flight time 92 s; descent from apogee takes 83 s
- Touchdown velocity: 3.37 m/s
</thought>
<design>
{"flight":{"motor":"E12","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.13724,"base_radius_m":0.01683,"wall_thickness_m":0.00317,"material":"Polystyrene PS","preset":"Estes PNC-55AC","name":"Nose cone"},{"type":"bodytube","length_m":0.2286,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-55IJ","contains":[{"type":"bulkhead","material":"Balsa","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.4572,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-55","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"altitude","deploy_altitude_m":100.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00239,"material":"Balsa","name":"Freeform fin set"},{"type":"innertube","length_m":0.127,"outer_d_m":0.02514,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]},{"type":"centeringring","material":"lite ply","name":"Centering ring"},{"type":"centeringring","material":"lite ply","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}],"motors":[{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}]}
</design>
```
</details>

### V1-086 · EASY
**Prompt:** Design a rocket that goes to about 84.1 m/s max velocity with a 65.8 s flight and touchdown at about 5.3 m/s.
**Rocket:** `ork/falconHeavey.ork` · **Sim:** Simulation 5 · **Motor:** F27
**Why easy: 3 requirements: max velocity, flight time, touchdown speed**
**Targets:** apogee 310.01 m · max velocity 84.107 m/s · time to apogee 6.988 s · flight time 65.831 s · touchdown 5.2758 m/s · wind 6 m/s
**Parts:** nose cone, 3 body tubes, transition, freeform fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 84.1 m/s max velocity with a 65.8 s flight and touchdown at about 5.3 m/s.

2. PROPULSION & ASCENT:
- Motor: F27
- Simulated apogee: 310 m (1,017 ft)
- Time to apogee: 7.0 s
- Peak velocity: 84 m/s (Mach 0.25)

3. RECOVERY & DESCENT:
- Parachute 0.40 m diameter, deploys at 152 m (500 ft)
- Total flight time 66 s; descent from apogee takes 59 s
- Touchdown velocity: 5.28 m/s
</thought>
<design>
{"flight":{"motor":"F27","wind_ms":6.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.04,"base_radius_m":0.0375,"wall_thickness_m":0.0012,"material":"PLA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.037,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.094,"outer_d_m":0.075,"wall_thickness_m":0.0012,"material":"PLA","name":"Body tube","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.06,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.03,"aft_d_m":0.05,"material":"PLA","name":"Transition"},{"type":"bodytube","length_m":0.331,"outer_d_m":0.05,"wall_thickness_m":0.0008,"material":"PLA","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":2.0,"thickness_m":0.004,"material":"PLA","name":"Freeform fin set"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.12,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.15,"outer_d_m":0.05,"wall_thickness_m":0.0012,"material":"PLA","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4037,"deploy_event":"altitude","deploy_altitude_m":152.4,"deploy_delay_s":0.0,"line_count":4.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.004,"material":"PLA","name":"Freeform fin set"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.013,"kind":"masscomponent"}],"motors":[{"manufacturer":"Estes","designation":"E16"},{"manufacturer":"AeroTech","designation":"E20"},{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"Estes","designation":"E30"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F23FJ"}]}],"motors":[{"manufacturer":"Estes","designation":"E16"},{"manufacturer":"AeroTech","designation":"E20"},{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"Estes","designation":"E30"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F23FJ"}]}]}
</design>
```
</details>

### V1-087 · EASY
**Prompt:** Make a rocket that hits 391 m and stays up about 52 s on a E28T motor.
**Rocket:** `ork/locprecision_starburst_pk-28.ork` · **Sim:** Simulation 1 · **Motor:** E28T
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 391.179 m · max velocity 101.961 m/s · time to apogee 8.616 s · flight time 51.565 s · touchdown 9.157 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 391 m and stays up about 52 s on a E28T motor.

2. PROPULSION & ASCENT:
- Motor: E28T
- Simulated apogee: 391 m (1,283 ft)
- Time to apogee: 8.6 s
- Peak velocity: 102 m/s (Mach 0.30)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 52 s; descent from apogee takes 43 s
- Touchdown velocity: 9.16 m/s
</thought>
<design>
{"flight":{"motor":"E28T","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.2286,"base_radius_m":0.03302,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.254,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Paper","name":"Body tube","contains":[{"type":"bulkhead","material":"Birch","name":"Bulkhead"},{"type":"masscomponent","name":"Large Screw Eye","mass_kg":0.00621,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.762,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute"},{"type":"innertube","length_m":0.3048,"outer_d_m":0.0254,"wall_thickness_m":0.00064,"material":"Paper","name":"Engine Tube x2 (24mm)","motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]},{"type":"centeringring","material":"Birch","name":"Centering Ring - F"},{"type":"centeringring","material":"Birch","name":"Centering Ring - R"},{"type":"launchlug","length_m":0.1524,"name":"Launch lug"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.20066,"tip_chord_m":0.0,"span_m":0.08052,"sweep_m":0.16149,"thickness_m":0.00317,"material":"Birch","name":"Fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]}]}
</design>
```
</details>

### V1-090 · EASY
**Prompt:** Make a rocket that reaches about 567 m on a F35W motor and is down in about 70 seconds.
**Rocket:** `ork/locprecision_starburst_pk-28.ork` · **Sim:** Simulation 4 · **Motor:** F35W
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 567.451 m · max velocity 133.97 m/s · time to apogee 9.967 s · flight time 70.009 s · touchdown 9.432 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that reaches about 567 m on a F35W motor and is down in about 70 seconds.

2. PROPULSION & ASCENT:
- Motor: F35W
- Simulated apogee: 567 m (1,862 ft)
- Time to apogee: 10.0 s
- Peak velocity: 134 m/s (Mach 0.40)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 70 s; descent from apogee takes 60 s
- Touchdown velocity: 9.43 m/s
</thought>
<design>
{"flight":{"motor":"F35W","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.2286,"base_radius_m":0.03302,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.254,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Paper","name":"Body tube","contains":[{"type":"bulkhead","material":"Birch","name":"Bulkhead"},{"type":"masscomponent","name":"Large Screw Eye","mass_kg":0.00621,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.762,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute"},{"type":"innertube","length_m":0.3048,"outer_d_m":0.0254,"wall_thickness_m":0.00064,"material":"Paper","name":"Engine Tube x2 (24mm)","motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]},{"type":"centeringring","material":"Birch","name":"Centering Ring - F"},{"type":"centeringring","material":"Birch","name":"Centering Ring - R"},{"type":"launchlug","length_m":0.1524,"name":"Launch lug"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.20066,"tip_chord_m":0.0,"span_m":0.08052,"sweep_m":0.16149,"thickness_m":0.00317,"material":"Birch","name":"Fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]}]}
</design>
```
</details>

### V1-092 · EASY
**Prompt:** Design a rocket that goes to about 68 m apogee with deployment at about 3.8 m/s and a 22.2 s flight.
**Rocket:** `ork/quest_astra_1004.ork` · **Sim:** Simulation 3 · **Motor:** A8
**Why easy: 3 requirements: apogee, flight time, touchdown speed**
**Targets:** apogee 67.917 m · max velocity 37.798 m/s · time to apogee 3.777 s · flight time 22.228 s · touchdown 3.767 m/s · wind 3.57632 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 68 m apogee with deployment at about 3.8 m/s and a 22.2 s flight.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 68 m (223 ft)
- Time to apogee: 3.8 s
- Peak velocity: 38 m/s (Mach 0.11)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 22 s; descent from apogee takes 18 s
- Touchdown velocity: 3.77 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":0.9,"length_m":0.08,"base_radius_m":0.01257,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.2286,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50AE, 30354","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute 12\""},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"},{"type":"innertube","length_m":0.0762,"outer_d_m":0.01998,"wall_thickness_m":0.00051,"material":"Paper","name":"Engine Mount tube","contains":[{"type":"centeringring","material":"Paper","name":"Engine Block Ring"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Paper","name":"Centering Ring - F"},{"type":"centeringring","material":"Paper","name":"Centering Ring - R"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Fin #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Fin #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Fin #3"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-093 · EASY
**Prompt:** Design a rocket that goes to about 385 m apogee in about 7.3 s to apogee on a C6 motor.
**Rocket:** `ork/quest_astra_1004.ork` · **Sim:** Simulation 4 · **Motor:** C6
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 384.669 m · max velocity 115.034 m/s · time to apogee 7.308 s · flight time 107.309 s · touchdown 3.836 m/s · wind 3.57632 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 385 m apogee in about 7.3 s to apogee on a C6 motor.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 385 m (1,262 ft)
- Time to apogee: 7.3 s
- Peak velocity: 115 m/s (Mach 0.34)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 107 s; descent from apogee takes 100 s
- Touchdown velocity: 3.84 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":0.9,"length_m":0.08,"base_radius_m":0.01257,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.2286,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50AE, 30354","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute 12\""},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"},{"type":"innertube","length_m":0.0762,"outer_d_m":0.01998,"wall_thickness_m":0.00051,"material":"Paper","name":"Engine Mount tube","contains":[{"type":"centeringring","material":"Paper","name":"Engine Block Ring"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Paper","name":"Centering Ring - F"},{"type":"centeringring","material":"Paper","name":"Centering Ring - R"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Fin #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Fin #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Fin #3"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-099 · EASY
**Prompt:** Make a rocket that hits 32 m and stays up about 9 s on a E17 motor.
**Rocket:** `ork/simulation_1.ork` · **Sim:** Simulation 3 · **Motor:** E17
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 31.797 m · max velocity 18.027 m/s · time to apogee 3.3912 s · flight time 9.0869 s · touchdown 6.1816 m/s · wind 4.16667 m/s
**Parts:** nose cone, 4 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 32 m and stays up about 9 s on a E17 motor.

2. PROPULSION & ASCENT:
- Motor: E17
- Simulated apogee: 32 m (104 ft)
- Time to apogee: 3.4 s
- Peak velocity: 18 m/s (Mach 0.06)

3. RECOVERY & DESCENT:
- Parachute 1.00 m diameter, deploys at apogee
- Total flight time 9 s; descent from apogee takes 6 s
- Touchdown velocity: 6.18 m/s
</thought>
<design>
{"flight":{"motor":"E17","wind_ms":4.166666666666667},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.25,"wall_thickness_m":0.0018,"material":"PLA","name":"Nose cone","contains":[{"type":"parachute","diameter_m":1.0,"deploy_event":"apogee","deploy_altitude_m":50.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Polyethylene (heavy)","name":"Parachute"}]},{"type":"bodytube","length_m":0.18,"outer_d_m":0.0536,"wall_thickness_m":0.0018,"material":"PLA","name":"Body tube","contains":[{"type":"masscomponent","name":"Altimeter","mass_kg":0.2,"kind":"flightcomputer"},{"type":"innertube","length_m":0.12,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"PLA","name":"Electronics bay"},{"type":"engineblock","name":"Altimeter block"}]},{"type":"bodytube","length_m":0.15,"wall_thickness_m":0.0018,"material":"PLA","name":"Extra trube","contains":[{"type":"masscomponent","name":"Tolerance","mass_kg":0.1,"kind":"masscomponent"},{"type":"launchlug","length_m":0.03,"name":"Launch lug"}]},{"type":"bodytube","length_m":0.15,"wall_thickness_m":0.0018,"material":"PLA","name":"Extra trube"},{"type":"bodytube","length_m":0.25,"wall_thickness_m":0.0018,"material":"PLA","name":"Tail","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.07,"tip_chord_m":0.05,"span_m":0.06,"sweep_m":0.0358,"thickness_m":0.0036,"material":"PLA","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.03,"name":"Launch lug"},{"type":"innertube","length_m":0.19,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"PLA","name":"Motor bracket","motors":[{"manufacturer":"NKJ","designation":"E17"},{"manufacturer":"Nakuja","designation":"G146"},{"manufacturer":"Nakuja","designation":"G106"},{"manufacturer":"Nakuja","designation":"G108"}]},{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"PLA","name":"Centering ring"}],"motors":[{"manufacturer":"NKJ","designation":"E17"},{"manufacturer":"Nakuja","designation":"G146"},{"manufacturer":"Nakuja","designation":"G106"},{"manufacturer":"Nakuja","designation":"G108"}]}],"motors":[{"manufacturer":"NKJ","designation":"E17"},{"manufacturer":"Nakuja","designation":"G146"},{"manufacturer":"Nakuja","designation":"G106"},{"manufacturer":"Nakuja","designation":"G108"}]}]}
</design>
```
</details>

### V1-100 · EASY
**Prompt:** Design a rocket that goes to about 80.8 m/s on a G146 motor, reaching apogee in about 7.8 s.
**Rocket:** `ork/simulation_1.ork` · **Sim:** Simulation 4 · **Motor:** G146
**Why easy: 3 requirements: max velocity, time to apogee, motor**
**Targets:** apogee 285.11 m · max velocity 80.84 m/s · time to apogee 7.7641 s · flight time 52.026 s · touchdown 6.5039 m/s · wind 4.16667 m/s
**Parts:** nose cone, 4 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 80.8 m/s on a G146 motor, reaching apogee in about 7.8 s.

2. PROPULSION & ASCENT:
- Motor: G146
- Simulated apogee: 285 m (935 ft)
- Time to apogee: 7.8 s
- Peak velocity: 81 m/s (Mach 0.24)

3. RECOVERY & DESCENT:
- Parachute 1.00 m diameter, deploys at apogee
- Total flight time 52 s; descent from apogee takes 44 s
- Touchdown velocity: 6.50 m/s
</thought>
<design>
{"flight":{"motor":"G146","wind_ms":4.166666666666667},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.25,"wall_thickness_m":0.0018,"material":"PLA","name":"Nose cone","contains":[{"type":"parachute","diameter_m":1.0,"deploy_event":"apogee","deploy_altitude_m":50.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Polyethylene (heavy)","name":"Parachute"}]},{"type":"bodytube","length_m":0.18,"outer_d_m":0.0536,"wall_thickness_m":0.0018,"material":"PLA","name":"Body tube","contains":[{"type":"masscomponent","name":"Altimeter","mass_kg":0.2,"kind":"flightcomputer"},{"type":"innertube","length_m":0.12,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"PLA","name":"Electronics bay"},{"type":"engineblock","name":"Altimeter block"}]},{"type":"bodytube","length_m":0.15,"wall_thickness_m":0.0018,"material":"PLA","name":"Extra trube","contains":[{"type":"masscomponent","name":"Tolerance","mass_kg":0.1,"kind":"masscomponent"},{"type":"launchlug","length_m":0.03,"name":"Launch lug"}]},{"type":"bodytube","length_m":0.15,"wall_thickness_m":0.0018,"material":"PLA","name":"Extra trube"},{"type":"bodytube","length_m":0.25,"wall_thickness_m":0.0018,"material":"PLA","name":"Tail","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.07,"tip_chord_m":0.05,"span_m":0.06,"sweep_m":0.0358,"thickness_m":0.0036,"material":"PLA","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.03,"name":"Launch lug"},{"type":"innertube","length_m":0.19,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"PLA","name":"Motor bracket","motors":[{"manufacturer":"NKJ","designation":"E17"},{"manufacturer":"Nakuja","designation":"G146"},{"manufacturer":"Nakuja","designation":"G106"},{"manufacturer":"Nakuja","designation":"G108"}]},{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"PLA","name":"Centering ring"}],"motors":[{"manufacturer":"NKJ","designation":"E17"},{"manufacturer":"Nakuja","designation":"G146"},{"manufacturer":"Nakuja","designation":"G106"},{"manufacturer":"Nakuja","designation":"G108"}]}],"motors":[{"manufacturer":"NKJ","designation":"E17"},{"manufacturer":"Nakuja","designation":"G146"},{"manufacturer":"Nakuja","designation":"G106"},{"manufacturer":"Nakuja","designation":"G108"}]}]}
</design>
```
</details>

### V1-101 · EASY
**Prompt:** Design a rocket that goes to about 380 m apogee with deployment at about 5.2 m/s and a 81.2 s flight.
**Rocket:** `ork/siriusrocketry_eradicator_s-0017.ork` · **Sim:** Simulation 5 · **Motor:** G40W
**Why easy: 3 requirements: apogee, flight time, touchdown speed**
**Targets:** apogee 380.476 m · max velocity 106.886 m/s · time to apogee 8.083 s · flight time 81.227 s · touchdown 5.197 m/s · wind 3.57632 m/s
**Parts:** nose cone, 4 body tubes, transition, freeform fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 380 m apogee with deployment at about 5.2 m/s and a 81.2 s flight.

2. PROPULSION & ASCENT:
- Motor: G40W
- Simulated apogee: 380 m (1,248 ft)
- Time to apogee: 8.1 s
- Peak velocity: 107 m/s (Mach 0.32)

3. RECOVERY & DESCENT:
- Parachute 0.76 m diameter, deploys at ejection
- Total flight time 81 s; descent from apogee takes 73 s
- Touchdown velocity: 5.20 m/s
</thought>
<design>
{"flight":{"motor":"G40W","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.00239,"base_radius_m":0.00237,"wall_thickness_m":0.00201,"material":"Polystyrene","name":"Nose cone"},{"type":"transition","shape":"ogive","length_m":0.27701,"fore_d_m":0.05,"aft_d_m":0.0762,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.4318,"outer_d_m":0.07672,"wall_thickness_m":0.00057,"material":"Paper","name":"Body tube, Upper, 3\"","contains":[{"type":"parachute","diameter_m":0.762,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute - 30\""},{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - F"},{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - R"},{"type":"masscomponent","name":"Mass - (1/8\" Quick Connect)","mass_kg":0.02268,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button - F"}]},{"type":"bodytube","length_m":0.4318,"outer_d_m":0.057,"wall_thickness_m":0.0005,"material":"Paper","name":"Body tube, Lower, 2 1/4\"","contains":[{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - F"},{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - R"},{"type":"freeformfinset","fin_count":8.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set - 8 Strakes"},{"type":"innertube","length_m":0.5588,"outer_d_m":0.031,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube, 29mm MMT","contains":[{"type":"innertube","length_m":0.0,"wall_thickness_m":0.0,"material":"PVC","name":"Estes Pro Series II 29mm Motor Retainer (PN 072412)(inner Ring)","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"innertube","length_m":0.00422,"outer_d_m":0.03698,"wall_thickness_m":0.00282,"material":"PVC","name":"Inner Ring Base","contains":[{"type":"innertube","length_m":0.0127,"outer_d_m":0.03134,"wall_thickness_m":0.0,"material":"Cardboard","name":"\"Smooth Inner tube"}]},{"type":"innertube","length_m":0.01137,"outer_d_m":0.03554,"wall_thickness_m":0.0021,"material":"PVC","name":"Threaded Section","contains":[{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"}]},{"type":"innertube","length_m":0.0045,"outer_d_m":0.03502,"wall_thickness_m":0.00291,"material":"PVC","name":"Inner Ring Peak"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.04232,"wall_thickness_m":0.00251,"material":"PVC","name":"Estes Pro Series II 29mm Motor Retainer (072412)(Outer Ring)","contains":[{"type":"innertube","length_m":0.01577,"outer_d_m":0.04232,"wall_thickness_m":0.00254,"material":"PVC","name":"Outer Ring Base and grips","contains":[{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04206,"wall_thickness_m":0.00228,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.0418,"wall_thickness_m":0.00228,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04128,"wall_thickness_m":0.00202,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04076,"wall_thickness_m":0.00176,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04024,"wall_thickness_m":0.0015,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03972,"wall_thickness_m":0.00124,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.0392,"wall_thickness_m":0.00098,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03868,"wall_thickness_m":0.00072,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03816,"wall_thickness_m":0.00046,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03764,"wall_thickness_m":0.0002,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.0371,"wall_thickness_m":0.00458,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03658,"wall_thickness_m":0.00547,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00013,"outer_d_m":0.03632,"wall_thickness_m":0.00547,"material":"PVC","name":"Slope"},{"type":"engineblock","name":"Engine block"}]}]}],"motors":[{"manufacturer":"AeroTech","designation":"H180W"},{"manufacturer":"AeroTech","designation":"G40W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"G80T"},{"manufacturer":"AeroTech","designation":"HP-H135W"},{"manufacturer":"AeroTech","designation":"HP-I205W"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"G64W"},{"manufacturer":"AeroTech","designation":"F40W"},{"manufacturer":"AeroTech","designation":"HP-G138T"},{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"H128W"}]},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #4"},{"type":"pod_set","count":1.0,"name":"Pod Set - F Ring Fin","contains":[{"type":"bodytube","length_m":0.0254,"outer_d_m":0.0762,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube - F, Ring Fin"}]},{"type":"pod_set","count":1.0,"name":"Pod Set - R Ring Fin","contains":[{"type":"bodytube","length_m":0.0254,"outer_d_m":0.0762,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube - R, Ring Fin","contains":[{"type":"railbutton","name":"Rail Button - R"}]}]}],"motors":[{"manufacturer":"AeroTech","designation":"H180W"},{"manufacturer":"AeroTech","designation":"G40W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"G80T"},{"manufacturer":"AeroTech","designation":"HP-H135W"},{"manufacturer":"AeroTech","designation":"HP-I205W"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"G64W"},{"manufacturer":"AeroTech","designation":"F40W"},{"manufacturer":"AeroTech","designation":"HP-G138T"},{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"H128W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"H180W"},{"manufacturer":"AeroTech","designation":"G40W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"G80T"},{"manufacturer":"AeroTech","designation":"HP-H135W"},{"manufacturer":"AeroTech","designation":"HP-I205W"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"G64W"},{"manufacturer":"AeroTech","designation":"F40W"},{"manufacturer":"AeroTech","designation":"HP-G138T"},{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"H128W"}]}]}
</design>
```
</details>

### V1-103 · EASY
**Prompt:** Make a rocket that hits 473 m and stays up about 100 s on a G80T motor.
**Rocket:** `ork/siriusrocketry_eradicator_s-0017.ork` · **Sim:** Simulation 6 · **Motor:** G80T
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 473.14 m · max velocity 153.066 m/s · time to apogee 8.341 s · flight time 99.644 s · touchdown 5.153 m/s · wind 3.57632 m/s
**Parts:** nose cone, 4 body tubes, transition, freeform fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 473 m and stays up about 100 s on a G80T motor.

2. PROPULSION & ASCENT:
- Motor: G80T
- Simulated apogee: 473 m (1,552 ft)
- Time to apogee: 8.3 s
- Peak velocity: 153 m/s (Mach 0.45)

3. RECOVERY & DESCENT:
- Parachute 0.76 m diameter, deploys at ejection
- Total flight time 100 s; descent from apogee takes 91 s
- Touchdown velocity: 5.15 m/s
</thought>
<design>
{"flight":{"motor":"G80T","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.00239,"base_radius_m":0.00237,"wall_thickness_m":0.00201,"material":"Polystyrene","name":"Nose cone"},{"type":"transition","shape":"ogive","length_m":0.27701,"fore_d_m":0.05,"aft_d_m":0.0762,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.4318,"outer_d_m":0.07672,"wall_thickness_m":0.00057,"material":"Paper","name":"Body tube, Upper, 3\"","contains":[{"type":"parachute","diameter_m":0.762,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute - 30\""},{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - F"},{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - R"},{"type":"masscomponent","name":"Mass - (1/8\" Quick Connect)","mass_kg":0.02268,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button - F"}]},{"type":"bodytube","length_m":0.4318,"outer_d_m":0.057,"wall_thickness_m":0.0005,"material":"Paper","name":"Body tube, Lower, 2 1/4\"","contains":[{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - F"},{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - R"},{"type":"freeformfinset","fin_count":8.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set - 8 Strakes"},{"type":"innertube","length_m":0.5588,"outer_d_m":0.031,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube, 29mm MMT","contains":[{"type":"innertube","length_m":0.0,"wall_thickness_m":0.0,"material":"PVC","name":"Estes Pro Series II 29mm Motor Retainer (PN 072412)(inner Ring)","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"innertube","length_m":0.00422,"outer_d_m":0.03698,"wall_thickness_m":0.00282,"material":"PVC","name":"Inner Ring Base","contains":[{"type":"innertube","length_m":0.0127,"outer_d_m":0.03134,"wall_thickness_m":0.0,"material":"Cardboard","name":"\"Smooth Inner tube"}]},{"type":"innertube","length_m":0.01137,"outer_d_m":0.03554,"wall_thickness_m":0.0021,"material":"PVC","name":"Threaded Section","contains":[{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"}]},{"type":"innertube","length_m":0.0045,"outer_d_m":0.03502,"wall_thickness_m":0.00291,"material":"PVC","name":"Inner Ring Peak"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.04232,"wall_thickness_m":0.00251,"material":"PVC","name":"Estes Pro Series II 29mm Motor Retainer (072412)(Outer Ring)","contains":[{"type":"innertube","length_m":0.01577,"outer_d_m":0.04232,"wall_thickness_m":0.00254,"material":"PVC","name":"Outer Ring Base and grips","contains":[{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04206,"wall_thickness_m":0.00228,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.0418,"wall_thickness_m":0.00228,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04128,"wall_thickness_m":0.00202,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04076,"wall_thickness_m":0.00176,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04024,"wall_thickness_m":0.0015,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03972,"wall_thickness_m":0.00124,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.0392,"wall_thickness_m":0.00098,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03868,"wall_thickness_m":0.00072,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03816,"wall_thickness_m":0.00046,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03764,"wall_thickness_m":0.0002,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.0371,"wall_thickness_m":0.00458,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03658,"wall_thickness_m":0.00547,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00013,"outer_d_m":0.03632,"wall_thickness_m":0.00547,"material":"PVC","name":"Slope"},{"type":"engineblock","name":"Engine block"}]}]}],"motors":[{"manufacturer":"AeroTech","designation":"H180W"},{"manufacturer":"AeroTech","designation":"G40W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"G80T"},{"manufacturer":"AeroTech","designation":"HP-H135W"},{"manufacturer":"AeroTech","designation":"HP-I205W"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"G64W"},{"manufacturer":"AeroTech","designation":"F40W"},{"manufacturer":"AeroTech","designation":"HP-G138T"},{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"H128W"}]},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #4"},{"type":"pod_set","count":1.0,"name":"Pod Set - F Ring Fin","contains":[{"type":"bodytube","length_m":0.0254,"outer_d_m":0.0762,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube - F, Ring Fin"}]},{"type":"pod_set","count":1.0,"name":"Pod Set - R Ring Fin","contains":[{"type":"bodytube","length_m":0.0254,"outer_d_m":0.0762,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube - R, Ring Fin","contains":[{"type":"railbutton","name":"Rail Button - R"}]}]}],"motors":[{"manufacturer":"AeroTech","designation":"H180W"},{"manufacturer":"AeroTech","designation":"G40W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"G80T"},{"manufacturer":"AeroTech","designation":"HP-H135W"},{"manufacturer":"AeroTech","designation":"HP-I205W"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"G64W"},{"manufacturer":"AeroTech","designation":"F40W"},{"manufacturer":"AeroTech","designation":"HP-G138T"},{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"H128W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"H180W"},{"manufacturer":"AeroTech","designation":"G40W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"G80T"},{"manufacturer":"AeroTech","designation":"HP-H135W"},{"manufacturer":"AeroTech","designation":"HP-I205W"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"G64W"},{"manufacturer":"AeroTech","designation":"F40W"},{"manufacturer":"AeroTech","designation":"HP-G138T"},{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"H128W"}]}]}
</design>
```
</details>

### V1-111 · EASY
**Prompt:** Design a rocket that goes to about 76 m apogee on a B6 motor, taking about 3.3 s to apogee.
**Rocket:** `ork/starfire_star_crusher.ork` · **Sim:** Simulation 3 · **Motor:** B6
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 75.817 m · max velocity 45.011 m/s · time to apogee 3.329 s · flight time 20.869 s · touchdown 4.396 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 76 m apogee on a B6 motor, taking about 3.3 s to apogee.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 76 m (249 ft)
- Time to apogee: 3.3 s
- Peak velocity: 45 m/s (Mach 0.13)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 21 s; descent from apogee takes 18 s
- Touchdown velocity: 4.40 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.1016,"base_radius_m":0.0124,"wall_thickness_m":0.00157,"material":"Polystyrene","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass - Nose Weight","mass_kg":0.00921,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.3302,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"SEMROC CP-12RW","name":"Parachute kit, plastic, 12 in, red/white"},{"type":"freeformfinset","fin_count":2.0,"thickness_m":0.003,"material":"Cardboard","name":"Fins  - Canard"},{"type":"innertube","length_m":0.0762,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"AeroTech","designation":"D13W"}]},{"type":"centeringring","material":"Fiber","name":"Centering Ring - F"},{"type":"centeringring","material":"Fiber","name":"Centering Ring - R"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin - Rudder"},{"type":"freeformfinset","fin_count":2.0,"thickness_m":0.003,"material":"Cardboard","name":"Fins - Wings"},{"type":"launchlug","length_m":0.05652,"name":"Launch Lug"},{"type":"pod_set","count":2.0,"name":"Pod Set","contains":[{"type":"bodytube","length_m":0.07112,"outer_d_m":2e-05,"wall_thickness_m":1e-05,"material":"Cardboard","name":"Body Tube","contains":[{"type":"tubefin","fin_count":1.0,"thickness_m":0.00033,"material":"Cardboard","name":"Tube Fin Set"}]}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"AeroTech","designation":"D13W"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"AeroTech","designation":"D13W"}]}]}
</design>
```
</details>

### V1-112 · EASY
**Prompt:** Build a rocket on a F63R motor that reaches about 214 m and is back down in about 35 seconds.
**Rocket:** `ork/test_1.ork` · **Sim:** Simulation 1 · **Motor:** F63R
**Why easy: 3 requirements: apogee, flight time, motor**
**Targets:** apogee 214.214 m · max velocity 73.065 m/s · time to apogee 6.524 s · flight time 34.659 s · touchdown 7.962 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Build a rocket on a F63R motor that reaches about 214 m and is back down in about 35 seconds.

2. PROPULSION & ASCENT:
- Motor: F63R
- Simulated apogee: 214 m (703 ft)
- Time to apogee: 6.5 s
- Peak velocity: 73 m/s (Mach 0.21)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 35 s; descent from apogee takes 28 s
- Touchdown velocity: 7.96 m/s
</thought>
<design>
{"flight":{"motor":"F63R","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.12,"base_radius_m":0.033,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose Cone"},{"type":"bodytube","length_m":0.2296,"outer_d_m":0.066,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.1,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button"}]},{"type":"bodytube","length_m":0.3302,"outer_d_m":0.066,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"innertube","length_m":0.079,"outer_d_m":0.024,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"F63R"}]},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","name":"Parachute, 24 in., Mylar, 0.25 mil, 8 lines"},{"type":"railbutton","name":"Rail Button"},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.006,"material":"Balsa","name":"Freeform Fin Set"}],"motors":[{"manufacturer":"AeroTech","designation":"F63R"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F63R"}]}]}
</design>
```
</details>

### V1-113 · EASY
**Prompt:** Design a rocket that goes to about 93 m apogee on a C11 motor, taking about 4.3 s to apogee.
**Rocket:** `ork/tlp_phoenix_k-017.ork` · **Sim:** Simulation 1 · **Motor:** C11
**Why easy: 3 requirements: apogee, time to apogee, motor**
**Targets:** apogee 93.152 m · max velocity 43.471 m/s · time to apogee 4.2546 s · flight time 25.611 s · touchdown 4.3499 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 93 m apogee on a C11 motor, taking about 4.3 s to apogee.

2. PROPULSION & ASCENT:
- Motor: C11
- Simulated apogee: 93 m (306 ft)
- Time to apogee: 4.3 s
- Peak velocity: 43 m/s (Mach 0.13)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 26 s; descent from apogee takes 21 s
- Touchdown velocity: 4.35 m/s
</thought>
<design>
{"flight":{"motor":"C11","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.11747,"base_radius_m":0.02079,"wall_thickness_m":0.00159,"material":"Polystyrene","name":"Nose cone","contains":[{"type":"masscomponent","name":"Mass component","mass_kg":0.05245}]},{"type":"bodytube","length_m":0.3048,"wall_thickness_m":0.0006,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.09525,"outer_d_m":0.02514,"wall_thickness_m":0.00051,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.0381,"tip_chord_m":0.0381,"span_m":0.03175,"sweep_m":0.0,"thickness_m":0.00238,"material":"Basswood","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.0635,"name":"Launch lug"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Mylar","name":"Parachute"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]}]}
</design>
```
</details>

<a id="medium-109"></a>

## 🟡 Medium (109)

### NEW-002 · MEDIUM
**Prompt:** I want a small rocket that comes down gently, around 3 m/s, after a long floaty flight of over a minute.
**Rocket:** `ork/Comet Chaser.ork` · **Sim:** Simulation 5 · **Motor:** B6
**Why medium: 2 requirements: flight time, touchdown speed**
**Targets:** apogee 171.41 m · max velocity 88.338 m/s · time to apogee 5.072 s · flight time 66.391 s · touchdown 3.003 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I want a small rocket that comes down gently, around 3 m/s, after a long floaty flight of over a minute.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 171 m (562 ft)
- Time to apogee: 5.1 s
- Peak velocity: 88 m/s (Mach 0.26)

3. RECOVERY & DESCENT:
- Parachute 0.33 m diameter, deploys at ejection
- Total flight time 66 s; descent from apogee takes 61 s
- Touchdown velocity: 3.00 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.03543,"material":"Balsa","name":"Nose cone"},{"type":"bodytube","length_m":0.0762,"wall_thickness_m":0.00038,"material":"Cardboard","name":"Body tube"},{"type":"transition","shape":"conical","length_m":0.0268,"fore_d_m":0.02504,"material":"Balsa","name":"Transition"},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.01854,"wall_thickness_m":0.00014,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3302,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (thin)","name":"Parachute"},{"type":"launchlug","length_m":0.0508,"name":"Launch lug"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.001,"kind":"recoveryhardware"}]},{"type":"bodytube","length_m":0.0762,"outer_d_m":0.01854,"wall_thickness_m":0.00014,"material":"Cardboard","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00152,"material":"Cardboard","name":"Freeform fin set"},{"type":"engineblock","name":"Engine block"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.0005,"kind":"masscomponent"},{"type":"innertube","length_m":0.007,"outer_d_m":0.0191,"wall_thickness_m":0.00955,"material":"Kraft phenolic","name":"Inner Tube"}],"motors":[{"manufacturer":"Estes","designation":"B6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"}]}]}
</design>
```
</details>

### NEW-003 · MEDIUM
**Prompt:** Make a rocket that goes up a few hundred feet and drifts back down slowly.
**Rocket:** `ork/Comet Chaser.ork` · **Sim:** Simulation 5 · **Motor:** B6
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 171.41 m · max velocity 88.338 m/s · time to apogee 5.072 s · flight time 66.391 s · touchdown 3.003 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that goes up a few hundred feet and drifts back down slowly.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 171 m (562 ft)
- Time to apogee: 5.1 s
- Peak velocity: 88 m/s (Mach 0.26)

3. RECOVERY & DESCENT:
- Parachute 0.33 m diameter, deploys at ejection
- Total flight time 66 s; descent from apogee takes 61 s
- Touchdown velocity: 3.00 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.03543,"material":"Balsa","name":"Nose cone"},{"type":"bodytube","length_m":0.0762,"wall_thickness_m":0.00038,"material":"Cardboard","name":"Body tube"},{"type":"transition","shape":"conical","length_m":0.0268,"fore_d_m":0.02504,"material":"Balsa","name":"Transition"},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.01854,"wall_thickness_m":0.00014,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3302,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (thin)","name":"Parachute"},{"type":"launchlug","length_m":0.0508,"name":"Launch lug"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.001,"kind":"recoveryhardware"}]},{"type":"bodytube","length_m":0.0762,"outer_d_m":0.01854,"wall_thickness_m":0.00014,"material":"Cardboard","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00152,"material":"Cardboard","name":"Freeform fin set"},{"type":"engineblock","name":"Engine block"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.0005,"kind":"masscomponent"},{"type":"innertube","length_m":0.007,"outer_d_m":0.0191,"wall_thickness_m":0.00955,"material":"Kraft phenolic","name":"Inner Tube"}],"motors":[{"manufacturer":"Estes","designation":"B6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"}]}]}
</design>
```
</details>

### NEW-005 · MEDIUM
**Prompt:** Give me something that climbs to around 240 m and lands softly, under 4 m/s.
**Rocket:** `ork/ESTES Alpha 3.ork` · **Sim:** Simulation 2 · **Motor:** B4
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 237.68 m · max velocity 85.849 m/s · time to apogee 5.88 s · flight time 63.704 s · touchdown 3.872 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Give me something that climbs to around 240 m and lands softly, under 4 m/s.

2. PROPULSION & ASCENT:
- Motor: B4
- Simulated apogee: 238 m (780 ft)
- Time to apogee: 5.9 s
- Peak velocity: 86 m/s (Mach 0.25)

3. RECOVERY & DESCENT:
- Parachute 0.25 m diameter, deploys at ejection
- Total flight time 64 s; descent from apogee takes 58 s
- Touchdown velocity: 3.87 m/s
</thought>
<design>
{"flight":{"motor":"B4","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Hauptstufe","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.065,"base_radius_m":0.0124,"wall_thickness_m":0.002,"material":"PVC","name":"Spitze"},{"type":"bodytube","length_m":0.139,"outer_d_m":0.0248,"wall_thickness_m":0.0004,"material":"Cardboard","name":"K\u00f6rperrohr","contains":[{"type":"parachute","diameter_m":0.25,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (thin)","name":"Fallschirm"}]},{"type":"bodytube","length_m":0.057,"outer_d_m":0.0248,"wall_thickness_m":0.002,"material":"PVC","name":"K\u00f6rperrohr","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.057,"tip_chord_m":0.03,"span_m":0.04,"sweep_m":0.07,"thickness_m":0.0001,"material":"PVC","name":"Trapezoide Leitwerke"},{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Innenrohr","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]}]}
</design>
```
</details>

### NEW-007 · MEDIUM
**Prompt:** I need a rocket on a C6 motor that gets up close to 450 m.
**Rocket:** `ork/ESTES Alpha 3.ork` · **Sim:** Simulation 3 · **Motor:** C6
**Why medium: 2 requirements: apogee, motor**
**Targets:** apogee 451.1 m · max velocity 145.03 m/s · time to apogee 8.241 s · flight time 20.468 s · touchdown 52.126 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I need a rocket on a C6 motor that gets up close to 450 m.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 451 m (1,480 ft)
- Time to apogee: 8.2 s
- Peak velocity: 145 m/s (Mach 0.43)

3. RECOVERY & DESCENT:
- Parachute 0.25 m diameter, deploys at ejection
- Total flight time 20 s; descent from apogee takes 12 s
- Touchdown velocity: 52.13 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Hauptstufe","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.065,"base_radius_m":0.0124,"wall_thickness_m":0.002,"material":"PVC","name":"Spitze"},{"type":"bodytube","length_m":0.139,"outer_d_m":0.0248,"wall_thickness_m":0.0004,"material":"Cardboard","name":"K\u00f6rperrohr","contains":[{"type":"parachute","diameter_m":0.25,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (thin)","name":"Fallschirm"}]},{"type":"bodytube","length_m":0.057,"outer_d_m":0.0248,"wall_thickness_m":0.002,"material":"PVC","name":"K\u00f6rperrohr","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.057,"tip_chord_m":0.03,"span_m":0.04,"sweep_m":0.07,"thickness_m":0.0001,"material":"PVC","name":"Trapezoide Leitwerke"},{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Innenrohr","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]}]}
</design>
```
</details>

### NEW-009 · MEDIUM
**Prompt:** Design a rocket with a half-minute flight that touches down at around 5.5 m/s.
**Rocket:** `ork/Estes Impulse.ork` · **Sim:** Simulation 1 · **Motor:** D12
**Why medium: 2 requirements: flight time, touchdown speed**
**Targets:** apogee 153.22 m · max velocity 52.003 m/s · time to apogee 6.023 s · flight time 33.922 s · touchdown 5.541 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket with a half-minute flight that touches down at around 5.5 m/s.

2. PROPULSION & ASCENT:
- Motor: D12
- Simulated apogee: 153 m (503 ft)
- Time to apogee: 6.0 s
- Peak velocity: 52 m/s (Mach 0.15)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at ejection
- Total flight time 34 s; descent from apogee takes 28 s
- Touchdown velocity: 5.54 m/s
</thought>
<design>
{"flight":{"motor":"D12","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.24765,"base_radius_m":0.03175,"wall_thickness_m":0.00635,"material":"Polystyrene","name":"Nose Cone"},{"type":"bodytube","length_m":0.22225,"outer_d_m":0.0635,"wall_thickness_m":0.00086,"material":"Paper","preset":"Estes 31390","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Nylon fabric","preset":"Estes 002261","name":"Parachute, 24 in., nylon, 6 lines, PN 002261"}]},{"type":"bodytube","length_m":0.3937,"outer_d_m":0.0635,"wall_thickness_m":0.00086,"material":"Paper","preset":"Estes 31390","name":"Body Tube","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.1016,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Freeform Fin Set"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]}]}
</design>
```
</details>

### NEW-010 · MEDIUM
**Prompt:** Build me a rocket for an E26W motor that tops out near 295 m.
**Rocket:** `ork/Estes Impulse.ork` · **Sim:** Simulation 3 · **Motor:** E26W
**Why medium: 2 requirements: apogee, motor**
**Targets:** apogee 295.036 m · max velocity 96.658 m/s · time to apogee 7.468 s · flight time 60.088 s · touchdown 5.6 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Build me a rocket for an E26W motor that tops out near 295 m.

2. PROPULSION & ASCENT:
- Motor: E26W
- Simulated apogee: 295 m (968 ft)
- Time to apogee: 7.5 s
- Peak velocity: 97 m/s (Mach 0.28)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at ejection
- Total flight time 60 s; descent from apogee takes 53 s
- Touchdown velocity: 5.60 m/s
</thought>
<design>
{"flight":{"motor":"E26W","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.24765,"base_radius_m":0.03175,"wall_thickness_m":0.00635,"material":"Polystyrene","name":"Nose Cone"},{"type":"bodytube","length_m":0.22225,"outer_d_m":0.0635,"wall_thickness_m":0.00086,"material":"Paper","preset":"Estes 31390","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Nylon fabric","preset":"Estes 002261","name":"Parachute, 24 in., nylon, 6 lines, PN 002261"}]},{"type":"bodytube","length_m":0.3937,"outer_d_m":0.0635,"wall_thickness_m":0.00086,"material":"Paper","preset":"Estes 31390","name":"Body Tube","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.1016,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Freeform Fin Set"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"}]}]}
</design>
```
</details>

### NEW-013 · MEDIUM
**Prompt:** I want a quick flight, about 25 seconds total, that goes up around 285 m.
**Rocket:** `ork/Estes_Mark2.ork` · **Sim:** Simulation 2 · **Motor:** B6
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 285.19 m · max velocity 137.65 m/s · time to apogee 6.26 s · flight time 24.477 s · touchdown 17.076 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 streamer recovery
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I want a quick flight, about 25 seconds total, that goes up around 285 m.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 285 m (936 ft)
- Time to apogee: 6.3 s
- Peak velocity: 138 m/s (Mach 0.41)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 24 s; descent from apogee takes 18 s
- Touchdown velocity: 17.08 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.05558,"base_radius_m":0.00972,"material":"Balsa","name":"BNC-30E"},{"type":"bodytube","length_m":0.0889,"wall_thickness_m":0.00053,"material":"Cardboard","name":"BT-30A","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.0254,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"}]},{"type":"bodytube","length_m":0.06985,"wall_thickness_m":0.00053,"material":"Cardboard","name":"BT-30J","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"launchlug","length_m":0.03175,"name":"LL-2A"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-018 · MEDIUM
**Prompt:** Design a rocket on a B6 motor that only goes up about 60 m.
**Rocket:** `ork/FlipFlyer.ork` · **Sim:** Simulation 1 · **Motor:** B6
**Why medium: 2 requirements: apogee, motor**
**Targets:** apogee 59.117 m · max velocity 31.33 m/s · time to apogee 3.82 s · flight time 8.668 s · touchdown 19.815 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 3 fins, 2 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on a B6 motor that only goes up about 60 m.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 59 m (194 ft)
- Time to apogee: 3.8 s
- Peak velocity: 31 m/s (Mach 0.09)

3. RECOVERY & DESCENT:
- Parachute 0.23 m diameter, deploys at ejection
- Total flight time 9 s; descent from apogee takes 5 s
- Touchdown velocity: 19.82 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Nose","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06985,"base_radius_m":0.0124,"wall_thickness_m":0.00157,"material":"Polystyrene","preset":"Estes PNC-50KA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Nose Clay","mass_kg":0.01451,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.128,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50, 30352","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"parachute","diameter_m":0.2286,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes parachute_9in, 002268","name":"Parachute"}]}]},{"type":"stage_marker","name":"Sustainer","contains":[{"type":"bodytube","length_m":0.2,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50, 30352","name":"Body tube","contains":[{"type":"launchlug","length_m":0.055,"name":"Launch lug"}]},{"type":"bodytube","length_m":0.065,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"PVC","name":"Engine mount and fin box","contains":[{"type":"engineblock","name":"Engine block"},{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Motor Mount","motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.001,"material":"PVC","name":"Notched PVC Fins"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.23,"tip_chord_m":0.22,"span_m":0.001,"sweep_m":0.025,"thickness_m":0.025,"material":"PVC","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-022 · MEDIUM
**Prompt:** I need a really soft landing, about 3 m/s, from a couple hundred meters up.
**Rocket:** `ork/OpenRocket Estes Super Shot Design.ork` · **Sim:** Fight Path Recovery · **Motor:** C6
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 247.058 m · max velocity 81.115 m/s · time to apogee 6.965 s · flight time 91.752 s · touchdown 2.931 m/s · wind 6.7056 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 2 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I need a really soft landing, about 3 m/s, from a couple hundred meters up.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 247 m (811 ft)
- Time to apogee: 7.0 s
- Peak velocity: 81 m/s (Mach 0.24)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 92 s; descent from apogee takes 85 s
- Touchdown velocity: 2.93 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":6.7056},"components":[{"type":"stage_marker","name":"Sustainer"},{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":0.11639,"base_radius_m":0.01231,"wall_thickness_m":0.001,"material":"Styrene Plastic","name":"Nose Cone"},{"type":"bodytube","length_m":0.229,"outer_d_m":0.0248,"wall_thickness_m":0.00045,"material":"Cardboard","name":"Estes Super Shot Body Tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes parachute_18in, 035823","name":"Parachute, plastic, preassembled, 18 in., Der Red Max, PN 035823"},{"type":"masscomponent","name":"Estes Altimeter","mass_kg":0.01177,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.229,"outer_d_m":0.0248,"wall_thickness_m":0.00045,"material":"Cardboard","name":"Estes Super Shot Body Tube","contains":[{"type":"launchlug","length_m":0.058,"name":"Launch Lug"}]},{"type":"bodytube","length_m":0.09289,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Styrene Plastic","name":"Fin Tube","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.0,"material":"Styrene Plastic","name":"Freeform Fin Set"},{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-025 · MEDIUM
**Prompt:** I want a rocket that climbs a few hundred meters and comes down gently, under 4 m/s.
**Rocket:** `ork/Renegade.ork` · **Sim:** Simulation 1 · **Motor:** E9
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 377.12 m · max velocity 97.433 m/s · time to apogee 8.687 s · flight time 99.608 s · touchdown 3.929 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I want a rocket that climbs a few hundred meters and comes down gently, under 4 m/s.

2. PROPULSION & ASCENT:
- Motor: E9
- Simulated apogee: 377 m (1,237 ft)
- Time to apogee: 8.7 s
- Peak velocity: 97 m/s (Mach 0.29)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 100 s; descent from apogee takes 91 s
- Touchdown velocity: 3.93 m/s
</thought>
<design>
{"flight":{"motor":"E9","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.17145,"base_radius_m":0.02079,"wall_thickness_m":0.00317,"material":"Polystyrene PS","preset":"Estes PNC-60AH","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"wall_thickness_m":0.00056,"material":"Cardboard","name":"BT-60","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.2159,"wall_thickness_m":0.00056,"material":"Cardboard","name":"BT-60HE","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00317,"material":"Balsa","name":"Freeform fin set"},{"type":"innertube","length_m":0.381,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-50KE","motors":[{"manufacturer":"Estes","designation":"E9"}]},{"type":"centeringring","material":"Fiber","name":"Centering ring"},{"type":"centeringring","material":"Fiber","name":"Centering ring"},{"type":"centeringring","material":"Fiber","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"E9"}]}],"motors":[{"manufacturer":"Estes","designation":"E9"}]}]}
</design>
```
</details>

### NEW-027 · MEDIUM
**Prompt:** Build a rocket on an A8 motor that reaches about 115 m and floats for close to a minute.
**Rocket:** `ork/astron drifter.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why medium: 2 requirements: apogee, motor**
**Targets:** apogee 115.03 m · max velocity 56.237 m/s · time to apogee 4.042 s · flight time 52.071 s · touchdown 2.168 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Build a rocket on an A8 motor that reaches about 115 m and floats for close to a minute.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 115 m (377 ft)
- Time to apogee: 4.0 s
- Peak velocity: 56 m/s (Mach 0.17)

3. RECOVERY & DESCENT:
- Parachute 0.38 m diameter, deploys at ejection
- Total flight time 52 s; descent from apogee takes 48 s
- Touchdown velocity: 2.17 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06985,"base_radius_m":0.0124,"material":"Balsa","preset":"Estes BNC-50K","name":"Nose cone","contains":[{"type":"masscomponent","name":"eye screw","mass_kg":0.0023}]},{"type":"bodytube","length_m":0.19685,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-50 7.75-inches","contains":[{"type":"centeringring","material":"Paper","name":"Centering ring"},{"type":"centeringring","material":"Paper","name":"Centering ring"},{"type":"parachute","diameter_m":0.381,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Polyethylene (heavy)","name":"Parachute"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"},{"type":"innertube","length_m":0.0508,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-20 #1 (part of BT-20 #2)"}]},{"type":"transition","shape":"conical","length_m":0.0254,"aft_d_m":0.0187,"material":"Paper (office)","name":"Transition"},{"type":"bodytube","length_m":0.0127,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-20 #2 (part of BT-20 #1)","motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"}]}]}
</design>
```
</details>

### NEW-028 · MEDIUM
**Prompt:** Design a rocket that goes up about 230 m and stays in the air about 105 seconds.
**Rocket:** `ork/astron drifter.ork` · **Sim:** Simulation 2 · **Motor:** B6
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 231.58 m · max velocity 105.06 m/s · time to apogee 6.008 s · flight time 105.86 s · touchdown 2.561 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes up about 230 m and stays in the air about 105 seconds.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 232 m (760 ft)
- Time to apogee: 6.0 s
- Peak velocity: 105 m/s (Mach 0.31)

3. RECOVERY & DESCENT:
- Parachute 0.38 m diameter, deploys at ejection
- Total flight time 106 s; descent from apogee takes 100 s
- Touchdown velocity: 2.56 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06985,"base_radius_m":0.0124,"material":"Balsa","preset":"Estes BNC-50K","name":"Nose cone","contains":[{"type":"masscomponent","name":"eye screw","mass_kg":0.0023}]},{"type":"bodytube","length_m":0.19685,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-50 7.75-inches","contains":[{"type":"centeringring","material":"Paper","name":"Centering ring"},{"type":"centeringring","material":"Paper","name":"Centering ring"},{"type":"parachute","diameter_m":0.381,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Polyethylene (heavy)","name":"Parachute"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"},{"type":"innertube","length_m":0.0508,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-20 #1 (part of BT-20 #2)"}]},{"type":"transition","shape":"conical","length_m":0.0254,"aft_d_m":0.0187,"material":"Paper (office)","name":"Transition"},{"type":"bodytube","length_m":0.0127,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-20 #2 (part of BT-20 #1)","motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"}]}]}
</design>
```
</details>

### NEW-029 · MEDIUM
**Prompt:** Design a rocket on a B6 motor that touches down under 3 m/s.
**Rocket:** `ork/astron drifter.ork` · **Sim:** Simulation 2 · **Motor:** B6
**Why medium: 2 requirements: touchdown speed, motor**
**Targets:** apogee 231.58 m · max velocity 105.06 m/s · time to apogee 6.008 s · flight time 105.86 s · touchdown 2.561 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket on a B6 motor that touches down under 3 m/s.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 232 m (760 ft)
- Time to apogee: 6.0 s
- Peak velocity: 105 m/s (Mach 0.31)

3. RECOVERY & DESCENT:
- Parachute 0.38 m diameter, deploys at ejection
- Total flight time 106 s; descent from apogee takes 100 s
- Touchdown velocity: 2.56 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06985,"base_radius_m":0.0124,"material":"Balsa","preset":"Estes BNC-50K","name":"Nose cone","contains":[{"type":"masscomponent","name":"eye screw","mass_kg":0.0023}]},{"type":"bodytube","length_m":0.19685,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-50 7.75-inches","contains":[{"type":"centeringring","material":"Paper","name":"Centering ring"},{"type":"centeringring","material":"Paper","name":"Centering ring"},{"type":"parachute","diameter_m":0.381,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Polyethylene (heavy)","name":"Parachute"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"},{"type":"innertube","length_m":0.0508,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-20 #1 (part of BT-20 #2)"}]},{"type":"transition","shape":"conical","length_m":0.0254,"aft_d_m":0.0187,"material":"Paper (office)","name":"Transition"},{"type":"bodytube","length_m":0.0127,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-20 #2 (part of BT-20 #1)","motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"}]}]}
</design>
```
</details>

### NEW-031 · MEDIUM
**Prompt:** Design a rocket that goes about 360 m and is back down in under 25 seconds.
**Rocket:** `ork/estes-007275–STERLING_SILVER.ork` · **Sim:** Simulation 2 · **Motor:** B6
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 361.02 m · max velocity 122.23 m/s · time to apogee 7.962 s · flight time 22.822 s · touchdown 28.869 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 6 fins, 2 stages, 1 streamer recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes about 360 m and is back down in under 25 seconds.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 361 m (1,184 ft)
- Time to apogee: 8.0 s
- Peak velocity: 122 m/s (Mach 0.36)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 23 s; descent from apogee takes 15 s
- Touchdown velocity: 28.87 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06731,"base_radius_m":0.00935,"wall_thickness_m":0.00159,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.3048,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes EST 3085","name":"Body tube","contains":[{"type":"streamer","strip_length_m":0.762,"strip_width_m":0.03175,"deploy_event":"ejection","material":"Polyethylene (thin)","name":"Streamer"}]},{"type":"bodytube","length_m":0.07,"wall_thickness_m":0.00035,"material":"Cardboard","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.043,"tip_chord_m":0.0255,"span_m":0.03188,"sweep_m":0.03188,"thickness_m":0.00234,"material":"Balsa","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.08916,"wall_thickness_m":0.00035,"material":"Cardboard","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.06186,"tip_chord_m":0.04116,"span_m":0.04743,"sweep_m":0.04743,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### U-023 · MEDIUM
**Prompt:** Design a rocket that goes on a F15 motor to apogee in about 10.2 s.
**Rocket:** `ork/openrocketdoc__example_simple_1.ork` · **Sim:** Simulation 1 · **Motor:** F15
**Why medium: 2 requirements: time to apogee, motor**
**Targets:** apogee 474.48 m · max velocity 102.54 m/s · time to apogee 10.217 s · flight time 24.417 s · touchdown 43.819 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes on a F15 motor to apogee in about 10.2 s.

2. PROPULSION & ASCENT:
- Motor: F15
- Simulated apogee: 474 m (1,557 ft)
- Time to apogee: 10.2 s
- Peak velocity: 103 m/s (Mach 0.30)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 24 s; descent from apogee takes 14 s
- Touchdown velocity: 43.82 m/s
</thought>
<design>
{"flight":{"motor":"F15","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.15,"wall_thickness_m":0.001,"material":"Polystyrene","name":"Nose cone","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"},{"type":"masscomponent","name":"Mass component","mass_kg":0.05}]},{"type":"bodytube","length_m":0.3,"wall_thickness_m":0.002,"material":"Kraft phenolic","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.08,"tip_chord_m":0.03,"span_m":0.05,"sweep_m":0.045,"thickness_m":0.003,"material":"Fiberglass","name":"Trapezoidal fin set"},{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Maple","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}]}
</design>
```
</details>

### U-033 · MEDIUM
**Prompt:** Design a rocket that goes on a GragasMAY24 motor to apogee in about 11.4 s.
**Rocket:** `ork/czech-rocket-challenge-2025__Raketa.ork` · **Sim:** Simulation 1 · **Motor:** GragasMAY24
**Why medium: 2 requirements: time to apogee, motor**
**Targets:** apogee 617.783 m · max velocity 127.543 m/s · time to apogee 11.408 s · flight time 146.734 s · touchdown 4.495 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 3 fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes on a GragasMAY24 motor to apogee in about 11.4 s.

2. PROPULSION & ASCENT:
- Motor: GragasMAY24
- Simulated apogee: 618 m (2,027 ft)
- Time to apogee: 11.4 s
- Peak velocity: 128 m/s (Mach 0.38)

3. RECOVERY & DESCENT:
- Parachute 1.00 m diameter, deploys at apogee
- Total flight time 147 s; descent from apogee takes 135 s
- Touchdown velocity: 4.50 m/s
</thought>
<design>
{"flight":{"motor":"GragasMAY24","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.15,"base_radius_m":0.03,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"Nose Cone","contains":[{"type":"parachute","diameter_m":1.0,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":12.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.2,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"horn\u00e1 trubka","contains":[{"type":"masscomponent","name":"flight computer","mass_kg":0.034,"kind":"flightcomputer"},{"type":"masscomponent","name":"kaboom","mass_kg":0.03,"kind":"recoveryhardware"},{"type":"masscomponent","name":"altimaeter","mass_kg":0.02228,"kind":"altimeter"},{"type":"masscomponent","name":"GY-BM","mass_kg":0.003,"kind":"masscomponent"},{"type":"masscomponent","name":"MPU 6500","mass_kg":0.006,"kind":"masscomponent"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.02172,"kind":"battery"}]},{"type":"bodytube","length_m":0.15,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"naklad","contains":[{"type":"masscomponent","name":"vaj\u010disko","mass_kg":0.05,"kind":"masscomponent"},{"type":"masscomponent","name":"blublub","mass_kg":0.001,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.173,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"spodn\u00e1 trubka","contains":[{"type":"bulkhead","material":"PETG - 100% infill","name":"Bulkhead"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.093,"tip_chord_m":0.09,"span_m":0.1,"sweep_m":0.1,"thickness_m":0.003,"material":"PLA - 20% infill","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}]}
</design>
```
</details>

### U-042 · MEDIUM
**Prompt:** Design a rocket that goes through about 67.9 m/s² max acceleration over a 24.4 s flight.
**Rocket:** `ork/openrocketdoc__example_simple_1.ork` · **Sim:** Simulation 1 · **Motor:** F15
**Why medium: 2 requirements: flight time, max acceleration**
**Targets:** apogee 474.48 m · max velocity 102.54 m/s · time to apogee 10.217 s · flight time 24.417 s · touchdown 43.819 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes through about 67.9 m/s² max acceleration over a 24.4 s flight.

2. PROPULSION & ASCENT:
- Motor: F15
- Simulated apogee: 474 m (1,557 ft)
- Time to apogee: 10.2 s
- Peak velocity: 103 m/s (Mach 0.30)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 24 s; descent from apogee takes 14 s
- Touchdown velocity: 43.82 m/s
</thought>
<design>
{"flight":{"motor":"F15","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.15,"wall_thickness_m":0.001,"material":"Polystyrene","name":"Nose cone","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"},{"type":"masscomponent","name":"Mass component","mass_kg":0.05}]},{"type":"bodytube","length_m":0.3,"wall_thickness_m":0.002,"material":"Kraft phenolic","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.08,"tip_chord_m":0.03,"span_m":0.05,"sweep_m":0.045,"thickness_m":0.003,"material":"Fiberglass","name":"Trapezoidal fin set"},{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Maple","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}]}
</design>
```
</details>

### U-054 · MEDIUM
**Prompt:** Design a rocket that goes to about 1,364 m apogee, hitting about Mach 2.05 and 320 m/s² max acceleration.
**Rocket:** `ork/MockUpofASCENSION(StabilityIssue).ork` · **Sim:** Simulation 1 · **Motor:** L1685-SS
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 1364.4 m · max velocity 687.34 m/s · time to apogee 4.304 s · flight time 232.11 s · touchdown 5.809 m/s · wind 0 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 1,364 m apogee, hitting about Mach 2.05 and 320 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: L1685-SS
- Simulated apogee: 1,364 m (4,476 ft)
- Time to apogee: 4.3 s
- Peak velocity: 687 m/s (Mach 2.05)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at 300 m (984 ft)
- Parachute 0.60 m diameter, deploys at apogee
- Total flight time 232 s; descent from apogee takes 228 s
- Touchdown velocity: 5.81 m/s
</thought>
<design>
{"flight":{"motor":"L1685-SS","wind_ms":0.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.32,"wall_thickness_m":0.002,"material":"Titanium","name":"Nose cone","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.02,"kind":"altimeter"}]},{"type":"bodytube","length_m":0.22,"wall_thickness_m":0.002,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.91,"deploy_event":"altitude","deploy_altitude_m":300.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Main"},{"type":"parachute","diameter_m":0.6,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Drogue"}]},{"type":"bodytube","length_m":0.8,"outer_d_m":0.085,"wall_thickness_m":0.002,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"innertube","length_m":0.757,"outer_d_m":0.076,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"L1685-SS"}]},{"type":"bodytube","length_m":0.0195,"wall_thickness_m":0.002,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.003,"material":"Cardboard","name":"Freeform fin set"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"L1685-SS"}]}]}
</design>
```
</details>

### U-061 · MEDIUM
**Prompt:** Design a rocket that goes to about 102.5 m/s max velocity at about 67.9 m/s² max acceleration.
**Rocket:** `ork/openrocketdoc__example_simple_1.ork` · **Sim:** Simulation 1 · **Motor:** F15
**Why medium: 2 requirements: max velocity, max acceleration**
**Targets:** apogee 474.48 m · max velocity 102.54 m/s · time to apogee 10.217 s · flight time 24.417 s · touchdown 43.819 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 102.5 m/s max velocity at about 67.9 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: F15
- Simulated apogee: 474 m (1,557 ft)
- Time to apogee: 10.2 s
- Peak velocity: 103 m/s (Mach 0.30)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 24 s; descent from apogee takes 14 s
- Touchdown velocity: 43.82 m/s
</thought>
<design>
{"flight":{"motor":"F15","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.15,"wall_thickness_m":0.001,"material":"Polystyrene","name":"Nose cone","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"},{"type":"masscomponent","name":"Mass component","mass_kg":0.05}]},{"type":"bodytube","length_m":0.3,"wall_thickness_m":0.002,"material":"Kraft phenolic","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.08,"tip_chord_m":0.03,"span_m":0.05,"sweep_m":0.045,"thickness_m":0.003,"material":"Fiberglass","name":"Trapezoidal fin set"},{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Maple","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}],"motors":[{"manufacturer":"Estes","designation":"F15"}]}]}
</design>
```
</details>

### U-078 · MEDIUM
**Prompt:** Design a rocket that goes to about 127.5 m/s max velocity at about 71.1 m/s² max acceleration.
**Rocket:** `ork/czech-rocket-challenge-2025__Raketa.ork` · **Sim:** Simulation 1 · **Motor:** GragasMAY24
**Why medium: 2 requirements: max velocity, max acceleration**
**Targets:** apogee 617.783 m · max velocity 127.543 m/s · time to apogee 11.408 s · flight time 146.734 s · touchdown 4.495 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 3 fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 127.5 m/s max velocity at about 71.1 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: GragasMAY24
- Simulated apogee: 618 m (2,027 ft)
- Time to apogee: 11.4 s
- Peak velocity: 128 m/s (Mach 0.38)

3. RECOVERY & DESCENT:
- Parachute 1.00 m diameter, deploys at apogee
- Total flight time 147 s; descent from apogee takes 135 s
- Touchdown velocity: 4.50 m/s
</thought>
<design>
{"flight":{"motor":"GragasMAY24","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.15,"base_radius_m":0.03,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"Nose Cone","contains":[{"type":"parachute","diameter_m":1.0,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":12.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.2,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"horn\u00e1 trubka","contains":[{"type":"masscomponent","name":"flight computer","mass_kg":0.034,"kind":"flightcomputer"},{"type":"masscomponent","name":"kaboom","mass_kg":0.03,"kind":"recoveryhardware"},{"type":"masscomponent","name":"altimaeter","mass_kg":0.02228,"kind":"altimeter"},{"type":"masscomponent","name":"GY-BM","mass_kg":0.003,"kind":"masscomponent"},{"type":"masscomponent","name":"MPU 6500","mass_kg":0.006,"kind":"masscomponent"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.02172,"kind":"battery"}]},{"type":"bodytube","length_m":0.15,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"naklad","contains":[{"type":"masscomponent","name":"vaj\u010disko","mass_kg":0.05,"kind":"masscomponent"},{"type":"masscomponent","name":"blublub","mass_kg":0.001,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.173,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"spodn\u00e1 trubka","contains":[{"type":"bulkhead","material":"PETG - 100% infill","name":"Bulkhead"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.093,"tip_chord_m":0.09,"span_m":0.1,"sweep_m":0.1,"thickness_m":0.003,"material":"PLA - 20% infill","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}]}
</design>
```
</details>

### U-079 · MEDIUM
**Prompt:** Design a rocket that goes to about 127.5 m/s max velocity at about 71.1 m/s² peak acceleration.
**Rocket:** `ork/czech-rocket-challenge-2025__Raketa.ork` · **Sim:** Simulation 1 · **Motor:** GragasMAY24
**Why medium: 2 requirements: max velocity, max acceleration**
**Targets:** apogee 617.783 m · max velocity 127.543 m/s · time to apogee 11.408 s · flight time 146.734 s · touchdown 4.495 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 3 fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 127.5 m/s max velocity at about 71.1 m/s² peak acceleration.

2. PROPULSION & ASCENT:
- Motor: GragasMAY24
- Simulated apogee: 618 m (2,027 ft)
- Time to apogee: 11.4 s
- Peak velocity: 128 m/s (Mach 0.38)

3. RECOVERY & DESCENT:
- Parachute 1.00 m diameter, deploys at apogee
- Total flight time 147 s; descent from apogee takes 135 s
- Touchdown velocity: 4.50 m/s
</thought>
<design>
{"flight":{"motor":"GragasMAY24","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.15,"base_radius_m":0.03,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"Nose Cone","contains":[{"type":"parachute","diameter_m":1.0,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":12.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.2,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"horn\u00e1 trubka","contains":[{"type":"masscomponent","name":"flight computer","mass_kg":0.034,"kind":"flightcomputer"},{"type":"masscomponent","name":"kaboom","mass_kg":0.03,"kind":"recoveryhardware"},{"type":"masscomponent","name":"altimaeter","mass_kg":0.02228,"kind":"altimeter"},{"type":"masscomponent","name":"GY-BM","mass_kg":0.003,"kind":"masscomponent"},{"type":"masscomponent","name":"MPU 6500","mass_kg":0.006,"kind":"masscomponent"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.02172,"kind":"battery"}]},{"type":"bodytube","length_m":0.15,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"naklad","contains":[{"type":"masscomponent","name":"vaj\u010disko","mass_kg":0.05,"kind":"masscomponent"},{"type":"masscomponent","name":"blublub","mass_kg":0.001,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.173,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"spodn\u00e1 trubka","contains":[{"type":"bulkhead","material":"PETG - 100% infill","name":"Bulkhead"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.093,"tip_chord_m":0.09,"span_m":0.1,"sweep_m":0.1,"thickness_m":0.003,"material":"PLA - 20% infill","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}]}
</design>
```
</details>

### U-099 · MEDIUM
**Prompt:** Design a rocket that goes to about 14,180 m apogee with deployment at about 30 m/s and a 547 s flight.
**Rocket:** `ork/54SubminL3.ork` · **Sim:** Simulation 1 · **Motor:** M1378LR
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 14180 m · max velocity 1069.04 m/s · time to apogee 44.063 s · flight time 546.996 s · touchdown 9.334 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, transition, 4 fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 14,180 m apogee with deployment at about 30 m/s and a 547 s flight.

2. PROPULSION & ASCENT:
- Motor: M1378LR
- Simulated apogee: 14,180 m (46,522 ft)
- Time to apogee: 44.1 s
- Peak velocity: 1069 m/s (Mach 3.23)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at 200 m (656 ft)
- Total flight time 547 s; descent from apogee takes 503 s
- Touchdown velocity: 9.33 m/s
</thought>
<design>
{"flight":{"motor":"M1378LR","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.3785,"base_radius_m":0.027,"wall_thickness_m":0.00203,"material":"G10 fiberglass","name":"Nose cone"},{"type":"bodytube","length_m":0.1143,"outer_d_m":0.054,"wall_thickness_m":0.0008,"material":"Fiberglass","name":"Extension"},{"type":"bodytube","length_m":0.93,"outer_d_m":0.054,"wall_thickness_m":0.0,"material":"Fiberglass","name":"Motor Casing","contains":[{"type":"masscomponent","name":"Avionics","mass_kg":0.3,"kind":"masscomponent"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","name":"Parachute, 45 in., nylon, thin mill, 8 lines"}]},{"type":"transition","shape":"conical","length_m":0.04,"fore_d_m":0.054,"aft_d_m":0.05694,"material":"Carbon fiber","name":"Transition"},{"type":"bodytube","length_m":0.14,"outer_d_m":0.05694,"wall_thickness_m":0.00114,"material":"Carbon fiber","name":"Body Tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.14,"tip_chord_m":0.02,"span_m":0.06,"sweep_m":0.12,"thickness_m":0.003,"material":"Carbon fiber","name":"Fin set"}],"motors":[{"manufacturer":"Loki Research","designation":"M1378LR"},{"manufacturer":"Loki Research","designation":"L2050LW"}]},{"type":"transition","shape":"conical","length_m":0.0337,"fore_d_m":0.05694,"aft_d_m":0.0514,"material":"Cardboard","name":"Transition"}],"motors":[{"manufacturer":"Loki Research","designation":"M1378LR"},{"manufacturer":"Loki Research","designation":"L2050LW"}]}]}
</design>
```
</details>

### U-118 · MEDIUM
**Prompt:** Design a rocket that goes to about 2,396 m apogee with deployment at about 28 m/s and a 123 s flight.
**Rocket:** `ork/OtherTwoStager.ork` · **Sim:** Simulation 1 · **Motor:** HP-I280DM, J474-CT
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 2396.04 m · max velocity 380.127 m/s · time to apogee 18.721 s · flight time 123.33 s · touchdown 7.316 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, transition, 8 fins, 2 stages, 3 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 2,396 m apogee with deployment at about 28 m/s and a 123 s flight.

2. PROPULSION & ASCENT:
- Motor: HP-I280DM, J474-CT
- Simulated apogee: 2,396 m (7,861 ft)
- Time to apogee: 18.7 s
- Peak velocity: 380 m/s (Mach 1.13)

3. RECOVERY & DESCENT:
- Parachute 0.76 m diameter, deploys at 200 m (656 ft)
- Parachute 0.20 m diameter, deploys at apogee
- Parachute 0.76 m diameter, deploys at apogee
- Total flight time 123 s; descent from apogee takes 105 s
- Touchdown velocity: 7.32 m/s
</thought>
<design>
{"flight":{"motor":["HP-I280DM","J474-CT"],"wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.3429,"base_radius_m":0.03353,"wall_thickness_m":0.00148,"material":"Fiberglass","preset":"Madcow FWNC26T-YY","name":"Nose Cone"},{"type":"bodytube","length_m":0.6604,"outer_d_m":0.06706,"wall_thickness_m":0.00102,"material":"Fiberglass","preset":"Madcow FT26-THIN-300-NAT","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.762,"deploy_event":"altitude","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","preset":"Top Flight Recovery PAR-30TM","name":"Parachute, 30 in., nylon, thin mill, 8 lines"},{"type":"masscomponent","name":"Avbay","mass_kg":0.2,"kind":"masscomponent"},{"type":"innertube","length_m":0.3048,"outer_d_m":0.05664,"wall_thickness_m":0.00099,"material":"Fiberglass","name":"Sustainer MMT","motors":[{"manufacturer":"AeroTech","designation":"HP-I280DM"}]},{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.1,"tip_chord_m":0.03,"span_m":0.066,"sweep_m":0.055,"thickness_m":0.002,"material":"Carbon fiber","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.2032,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes PK-8, 2260","name":"Drogueless Sim"}],"motors":[{"manufacturer":"AeroTech","designation":"HP-I280DM"}]}],"motors":[{"manufacturer":"AeroTech","designation":"HP-I280DM"}]},{"type":"stage_marker","name":"Booster","contains":[{"type":"transition","shape":"conical","length_m":0.07925,"fore_d_m":0.06706,"aft_d_m":0.07938,"material":"Aluminum","name":"Transition"},{"type":"bodytube","length_m":0.6604,"outer_d_m":0.07938,"wall_thickness_m":0.00159,"material":"Fiberglass","preset":"Madcow FT30-STD-300-NAT","name":"Body Tube","contains":[{"type":"innertube","length_m":0.4572,"outer_d_m":0.05784,"wall_thickness_m":0.00159,"material":"Fiberglass","name":"Booster MMT","motors":[{"manufacturer":"Loki Research","designation":"J474-CT"}]},{"type":"centeringring","material":"Fiberglass","name":"Centering Ring"},{"type":"centeringring","material":"Fiberglass","name":"Centering Ring"},{"type":"masscomponent","name":"Booster Avbay","mass_kg":0.1,"kind":"masscomponent"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.12,"tip_chord_m":0.04,"span_m":0.08,"sweep_m":0.065,"thickness_m":0.002,"material":"Carbon fiber","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.762,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","preset":"Top Flight Recovery PAR-30TM","name":"Parachute, 30 in., nylon, thin mill, 8 lines"}],"motors":[{"manufacturer":"Loki Research","designation":"J474-CT"}]}],"motors":[{"manufacturer":"Loki Research","designation":"J474-CT"}]}]}
</design>
```
</details>

### U-123 · MEDIUM
**Prompt:** Design a rocket that goes to about 2,718 m apogee with deployment at about 25 m/s and a 145 s flight.
**Rocket:** `ork/TwoStager.ork` · **Sim:** Simulation 1 · **Motor:** HP-I280DM, J474-CT
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 2718.29 m · max velocity 437.585 m/s · time to apogee 19.366 s · flight time 144.655 s · touchdown 6.703 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, transition, 8 fins, 2 stages, 3 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 2,718 m apogee with deployment at about 25 m/s and a 145 s flight.

2. PROPULSION & ASCENT:
- Motor: HP-I280DM, J474-CT
- Simulated apogee: 2,718 m (8,918 ft)
- Time to apogee: 19.4 s
- Peak velocity: 438 m/s (Mach 1.30)

3. RECOVERY & DESCENT:
- Parachute 0.76 m diameter, deploys at 200 m (656 ft)
- Parachute 0.20 m diameter, deploys at apogee
- Parachute 0.76 m diameter, deploys at apogee
- Total flight time 145 s; descent from apogee takes 125 s
- Touchdown velocity: 6.70 m/s
</thought>
<design>
{"flight":{"motor":["HP-I280DM","J474-CT"],"wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.30734,"base_radius_m":0.02832,"wall_thickness_m":0.0016,"material":"Fiberglass","name":"Nose Cone"},{"type":"bodytube","length_m":0.762,"outer_d_m":0.05664,"wall_thickness_m":0.00099,"material":"Fiberglass","preset":"Madcow FT22-THIN-300-NAT","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.762,"deploy_event":"altitude","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","preset":"Top Flight Recovery PAR-30TM","name":"Parachute, 30 in., nylon, thin mill, 8 lines"},{"type":"masscomponent","name":"Avbay","mass_kg":0.2,"kind":"masscomponent"},{"type":"innertube","length_m":0.3048,"outer_d_m":0.04064,"wall_thickness_m":0.00102,"material":"Fiberglass","name":"Sustainer MMT","motors":[{"manufacturer":"AeroTech","designation":"HP-I280DM"}]},{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.12,"tip_chord_m":0.04,"span_m":0.06,"sweep_m":0.065,"thickness_m":0.002,"material":"Carbon fiber","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.2032,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes PK-8, 2260","name":"Drogueless Sim"}],"motors":[{"manufacturer":"AeroTech","designation":"HP-I280DM"}]}],"motors":[{"manufacturer":"AeroTech","designation":"HP-I280DM"}]},{"type":"stage_marker","name":"Booster","contains":[{"type":"transition","shape":"conical","length_m":0.07925,"fore_d_m":0.05664,"aft_d_m":0.06706,"material":"Aluminum","name":"Transition"},{"type":"bodytube","length_m":0.762,"outer_d_m":0.06706,"wall_thickness_m":0.00102,"material":"Fiberglass","preset":"Madcow FT26-THIN-300-NAT","name":"Body Tube","contains":[{"type":"innertube","length_m":0.4572,"outer_d_m":0.05784,"wall_thickness_m":0.00159,"material":"Fiberglass","name":"Booster MMT","motors":[{"manufacturer":"Loki Research","designation":"J474-CT"}]},{"type":"centeringring","material":"Fiberglass","name":"Centering Ring"},{"type":"centeringring","material":"Fiberglass","name":"Centering Ring"},{"type":"masscomponent","name":"Booster Avbay","mass_kg":0.1,"kind":"masscomponent"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.12,"tip_chord_m":0.04,"span_m":0.08,"sweep_m":0.065,"thickness_m":0.002,"material":"Carbon fiber","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.762,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","preset":"Top Flight Recovery PAR-30TM","name":"Parachute, 30 in., nylon, thin mill, 8 lines"}],"motors":[{"manufacturer":"Loki Research","designation":"J474-CT"}]}],"motors":[{"manufacturer":"Loki Research","designation":"J474-CT"}]}]}
</design>
```
</details>

### U-162 · MEDIUM
**Prompt:** Design a rocket that goes to about 3,380 m apogee in about 22 s to apogee.
**Rocket:** `ork/3. Linear.ork` · **Sim:** Simulation 1 · **Motor:** I216-CL(I)
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 3379.6 m · max velocity 435.36 m/s · time to apogee 22.466 s · flight time 400.54 s · touchdown 8.051 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 1 stage, 1 parachute + 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 3,380 m apogee in about 22 s to apogee.

2. PROPULSION & ASCENT:
- Motor: I216-CL(I)
- Simulated apogee: 3,380 m (11,088 ft)
- Time to apogee: 22.5 s
- Peak velocity: 435 m/s (Mach 1.29)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at apogee
- Streamer recovery
- Total flight time 401 s; descent from apogee takes 378 s
- Touchdown velocity: 8.05 m/s
</thought>
<design>
{"flight":{"motor":"I216-CL(I)","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.215,"wall_thickness_m":0.002,"material":"ABS","name":"Nose cone4","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.00027,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.245,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"masscomponent","name":"Electronics Bay","mass_kg":0.0075,"kind":"payload"},{"type":"bulkhead","material":"Aluminum","name":"Bulkhead"},{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":5.0,"line_count":8.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"apogee","material":"Ripstop nylon","name":"Streamer"}]},{"type":"bodytube","length_m":0.244,"outer_d_m":0.046,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube Middle"},{"type":"bodytube","length_m":0.17,"wall_thickness_m":0.0015,"material":"PLA","name":"Fin Can","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00025,"material":"Aluminum","name":"Freeform fin set"},{"type":"innertube","length_m":0.33,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Cardboard","name":"Inner Tube"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"engineblock","name":"Retaining Ring"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}]}
</design>
```
</details>

### U-163 · MEDIUM
**Prompt:** Design a rocket that goes to about 3,380 m apogee with a total flight time of about 401 s.
**Rocket:** `ork/1. Rounded Spline.ork` · **Sim:** Simulation 1 · **Motor:** I216-CL(I)
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 3379.6 m · max velocity 435.36 m/s · time to apogee 22.466 s · flight time 400.54 s · touchdown 8.051 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 1 stage, 1 parachute + 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 3,380 m apogee with a total flight time of about 401 s.

2. PROPULSION & ASCENT:
- Motor: I216-CL(I)
- Simulated apogee: 3,380 m (11,088 ft)
- Time to apogee: 22.5 s
- Peak velocity: 435 m/s (Mach 1.29)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at apogee
- Streamer recovery
- Total flight time 401 s; descent from apogee takes 378 s
- Touchdown velocity: 8.05 m/s
</thought>
<design>
{"flight":{"motor":"I216-CL(I)","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.215,"wall_thickness_m":0.002,"material":"ABS","name":"Nose cone4","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.00027,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.245,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"masscomponent","name":"Electronics Bay","mass_kg":0.0075,"kind":"payload"},{"type":"bulkhead","material":"Aluminum","name":"Bulkhead"},{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":5.0,"line_count":8.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"apogee","material":"Ripstop nylon","name":"Streamer"}]},{"type":"bodytube","length_m":0.244,"outer_d_m":0.046,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube Middle"},{"type":"bodytube","length_m":0.17,"wall_thickness_m":0.0015,"material":"PLA","name":"Fin Can","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00026,"material":"Aluminum","name":"Freeform fin set"},{"type":"innertube","length_m":0.33,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Cardboard","name":"Inner Tube"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"engineblock","name":"Retaining Ring"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}]}
</design>
```
</details>

### U-164 · MEDIUM
**Prompt:** Design a rocket that goes to about 3,380 m apogee, reaching about 435 m/s max velocity.
**Rocket:** `ork/2. Rounded.ork` · **Sim:** Simulation 1 · **Motor:** I216-CL(I)
**Why medium: 2 requirements: apogee, max velocity**
**Targets:** apogee 3379.6 m · max velocity 435.36 m/s · time to apogee 22.466 s · flight time 400.54 s · touchdown 8.051 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 1 stage, 1 parachute + 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 3,380 m apogee, reaching about 435 m/s max velocity.

2. PROPULSION & ASCENT:
- Motor: I216-CL(I)
- Simulated apogee: 3,380 m (11,088 ft)
- Time to apogee: 22.5 s
- Peak velocity: 435 m/s (Mach 1.29)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at apogee
- Streamer recovery
- Total flight time 401 s; descent from apogee takes 378 s
- Touchdown velocity: 8.05 m/s
</thought>
<design>
{"flight":{"motor":"I216-CL(I)","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.215,"wall_thickness_m":0.002,"material":"ABS","name":"Nose cone4","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.00027,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.245,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"masscomponent","name":"Electronics Bay","mass_kg":0.0075,"kind":"payload"},{"type":"bulkhead","material":"Aluminum","name":"Bulkhead"},{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":5.0,"line_count":8.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"apogee","material":"Ripstop nylon","name":"Streamer"}]},{"type":"bodytube","length_m":0.244,"outer_d_m":0.046,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube Middle"},{"type":"bodytube","length_m":0.17,"wall_thickness_m":0.0015,"material":"PLA","name":"Fin Can","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00025,"material":"Aluminum","name":"Freeform fin set"},{"type":"innertube","length_m":0.33,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Cardboard","name":"Inner Tube"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"engineblock","name":"Retaining Ring"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}]}
</design>
```
</details>

### U-181 · MEDIUM
**Prompt:** Design a rocket that goes to about 399 m apogee, reaching about 131 m/s max velocity.
**Rocket:** `ork/RATO.ork` · **Sim:** Simulation 1 · **Motor:** F67W
**Why medium: 2 requirements: apogee, max velocity**
**Targets:** apogee 398.988 m · max velocity 131.065 m/s · time to apogee 7.486 s · flight time 84.46 s · touchdown 5.524 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 399 m apogee, reaching about 131 m/s max velocity.

2. PROPULSION & ASCENT:
- Motor: F67W
- Simulated apogee: 399 m (1,309 ft)
- Time to apogee: 7.5 s
- Peak velocity: 131 m/s (Mach 0.39)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at ejection
- Total flight time 84 s; descent from apogee takes 77 s
- Touchdown velocity: 5.52 m/s
</thought>
<design>
{"flight":{"motor":"F67W","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.15,"base_radius_m":0.03302,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Avionics","mass_kg":0.055,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.06604,"wall_thickness_m":0.00051,"material":"Paper","preset":"Estes BT-80, 30458","name":"Body Tube"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.06604,"wall_thickness_m":0.00051,"material":"Paper","preset":"Estes BT-80, 30458","name":"Body Tube","contains":[{"type":"innertube","length_m":0.127,"outer_d_m":0.03074,"wall_thickness_m":0.00089,"material":"Paper","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"F67W"}]},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.0795,"tip_chord_m":0.02,"span_m":0.05,"sweep_m":0.05,"thickness_m":0.0025,"material":"Birch","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.6096,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","name":"Parachute, 30 in., nylon, thin mill, 8 lines"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}],"motors":[{"manufacturer":"AeroTech","designation":"F67W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F67W"}]}]}
</design>
```
</details>

### U-197 · MEDIUM
**Prompt:** Design a rocket that goes to about 5,748 m apogee with deployment at about None m/s and a 28 s flight.
**Rocket:** `ork/ASCENSION.ork` · **Sim:** Simulation 1 (Florida baseline) · **Motor:** L1115
**Why medium: 2 requirements: apogee, flight time**
**⚠️ prompt/target mismatch:** prompt contains literal 'None m/s' for deployment (broken template)
**Targets:** apogee 5747.8 m · max velocity 612.43 m/s · time to apogee 28.39 s · flight time 28.49 s · touchdown — m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 1 fins, 1 stage, 1 parachute + 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 5,748 m apogee with deployment at about None m/s and a 28 s flight.

2. PROPULSION & ASCENT:
- Motor: L1115
- Simulated apogee: 5,748 m (18,858 ft)
- Time to apogee: 28.4 s
- Peak velocity: 612 m/s (Mach 1.83)

3. RECOVERY & DESCENT:
- Streamer recovery
- Parachute 1.47 m diameter, deploys at 600 m (1969 ft)
- Total flight time 28 s; descent from apogee takes 0 s
</thought>
<design>
{"flight":{"motor":"L1115","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.18,"base_radius_m":0.0525,"wall_thickness_m":0.003,"material":"PVC","name":"Nose cone","contains":[{"type":"masscomponent","name":"Avionics","mass_kg":0.2,"kind":"altimeter"}]},{"type":"bodytube","length_m":0.32,"outer_d_m":0.105,"wall_thickness_m":0.003,"material":"Carbon fiber","name":"Body tube 1","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.06,"deploy_event":"altitude","material":"Ripstop nylon","name":"Streamer"},{"type":"parachute","diameter_m":1.47,"deploy_event":"altitude","deploy_altitude_m":600.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.655,"outer_d_m":0.105,"wall_thickness_m":0.003,"material":"Carbon fiber","name":"Body tube 2","contains":[{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"innertube","length_m":0.618,"outer_d_m":0.08,"wall_thickness_m":0.00025,"material":"Cardboard","name":"Inner Tube"},{"type":"engineblock","name":"Motor Retainer"},{"type":"trapezoidfin","root_chord_m":0.17,"tip_chord_m":0.05,"span_m":0.088,"sweep_m":0.2,"thickness_m":0.003,"material":"Aluminum","name":"Fins"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"L1115"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"L1115"}]}]}
</design>
```
</details>

### U-228 · MEDIUM
**Prompt:** Design a rocket that goes to about 618 m apogee with a total flight time of about 146.7 s.
**Rocket:** `ork/czech-rocket-challenge-2025__Raketa.ork` · **Sim:** Simulation 1 · **Motor:** GragasMAY24
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 617.783 m · max velocity 127.543 m/s · time to apogee 11.408 s · flight time 146.734 s · touchdown 4.495 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 3 fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 618 m apogee with a total flight time of about 146.7 s.

2. PROPULSION & ASCENT:
- Motor: GragasMAY24
- Simulated apogee: 618 m (2,027 ft)
- Time to apogee: 11.4 s
- Peak velocity: 128 m/s (Mach 0.38)

3. RECOVERY & DESCENT:
- Parachute 1.00 m diameter, deploys at apogee
- Total flight time 147 s; descent from apogee takes 135 s
- Touchdown velocity: 4.50 m/s
</thought>
<design>
{"flight":{"motor":"GragasMAY24","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.15,"base_radius_m":0.03,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"Nose Cone","contains":[{"type":"parachute","diameter_m":1.0,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":12.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.2,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"horn\u00e1 trubka","contains":[{"type":"masscomponent","name":"flight computer","mass_kg":0.034,"kind":"flightcomputer"},{"type":"masscomponent","name":"kaboom","mass_kg":0.03,"kind":"recoveryhardware"},{"type":"masscomponent","name":"altimaeter","mass_kg":0.02228,"kind":"altimeter"},{"type":"masscomponent","name":"GY-BM","mass_kg":0.003,"kind":"masscomponent"},{"type":"masscomponent","name":"MPU 6500","mass_kg":0.006,"kind":"masscomponent"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.02172,"kind":"battery"}]},{"type":"bodytube","length_m":0.15,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"naklad","contains":[{"type":"masscomponent","name":"vaj\u010disko","mass_kg":0.05,"kind":"masscomponent"},{"type":"masscomponent","name":"blublub","mass_kg":0.001,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.173,"outer_d_m":0.06,"wall_thickness_m":0.0025,"material":"PLA - 20% infill","name":"spodn\u00e1 trubka","contains":[{"type":"bulkhead","material":"PETG - 100% infill","name":"Bulkhead"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.093,"tip_chord_m":0.09,"span_m":0.1,"sweep_m":0.1,"thickness_m":0.003,"material":"PLA - 20% infill","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}],"motors":[{"manufacturer":"CRS","designation":"GragasMAY24"}]}]}
</design>
```
</details>

### U-254 · MEDIUM
**Prompt:** Design a rocket that goes to about 67.8 m/s max velocity at about 156.6 m/s² max acceleration.
**Rocket:** `ork/rockets__bt_55.ork` · **Sim:** Simulation 1 · **Motor:** C6
**Why medium: 2 requirements: max velocity, max acceleration**
**Targets:** apogee 84.351 m · max velocity 67.805 m/s · time to apogee 2.357 s · flight time 30.891 s · touchdown 3.169 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 67.8 m/s max velocity at about 156.6 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 84 m (277 ft)
- Time to apogee: 2.4 s
- Peak velocity: 68 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 31 s; descent from apogee takes 29 s
- Touchdown velocity: 3.17 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1016,"base_radius_m":0.01683,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","preset":"Estes EST 3087","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","preset":"Estes 302267","name":"Parachute"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.09,"tip_chord_m":0.035,"span_m":0.05,"sweep_m":0.025,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}]}
</design>
```
</details>

### U-255 · MEDIUM
**Prompt:** Design a rocket that goes to about 67.8 m/s max velocity at about 156.6 m/s² peak acceleration.
**Rocket:** `ork/rockets__bt_55.ork` · **Sim:** Simulation 1 · **Motor:** C6
**Why medium: 2 requirements: max velocity, max acceleration**
**Targets:** apogee 84.351 m · max velocity 67.805 m/s · time to apogee 2.357 s · flight time 30.891 s · touchdown 3.169 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 67.8 m/s max velocity at about 156.6 m/s² peak acceleration.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 84 m (277 ft)
- Time to apogee: 2.4 s
- Peak velocity: 68 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 31 s; descent from apogee takes 29 s
- Touchdown velocity: 3.17 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1016,"base_radius_m":0.01683,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","preset":"Estes EST 3087","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","preset":"Estes 302267","name":"Parachute"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.09,"tip_chord_m":0.035,"span_m":0.05,"sweep_m":0.025,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}]}
</design>
```
</details>

### U-256 · MEDIUM
**Prompt:** Design a rocket that goes to about 673 m apogee with a total flight time of about 139 s.
**Rocket:** `ork/PK37-Athena.ork` · **Sim:** Simulation 1 · **Motor:** HP-H195NT
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 673.067 m · max velocity 204.82 m/s · time to apogee 9.747 s · flight time 139.409 s · touchdown 5.495 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 6 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 673 m apogee with a total flight time of about 139 s.

2. PROPULSION & ASCENT:
- Motor: HP-H195NT
- Simulated apogee: 673 m (2,208 ft)
- Time to apogee: 9.7 s
- Peak velocity: 205 m/s (Mach 0.60)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at ejection
- Total flight time 139 s; descent from apogee takes 130 s
- Touchdown velocity: 5.50 m/s
</thought>
<design>
{"flight":{"motor":"HP-H195NT","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.28448,"base_radius_m":0.03937,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.254,"outer_d_m":0.07874,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube"},{"type":"bodytube","length_m":0.8636,"outer_d_m":0.07874,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube","contains":[{"type":"bulkhead","material":"Aircraft plywood (LOC)","name":"Bulkhead"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.12383,"tip_chord_m":0.0889,"span_m":0.0889,"sweep_m":0.0,"thickness_m":0.003,"material":"Aircraft plywood (LOC)","name":"Fin set"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.14922,"tip_chord_m":0.0254,"span_m":0.0889,"sweep_m":0.12383,"thickness_m":0.003,"material":"Aircraft plywood (LOC)","name":"Fin set"},{"type":"innertube","length_m":0.3048,"outer_d_m":0.03074,"wall_thickness_m":0.00087,"material":"Paper","name":"Body tube","contains":[{"type":"centeringring","material":"Aircraft plywood (LOC)","name":"Centering ring"}],"motors":[{"manufacturer":"AeroTech","designation":"HP-H195NT"},{"manufacturer":"AeroTech","designation":"G79W/L"}]},{"type":"centeringring","material":"Aircraft plywood (LOC)","name":"Centering ring"},{"type":"centeringring","material":"Aircraft plywood (LOC)","name":"Centering ring"},{"type":"centeringring","material":"Aircraft plywood (LOC)","name":"Centering ring"},{"type":"masscomponent","name":"Mass","mass_kg":0.015,"kind":"masscomponent"},{"type":"masscomponent","name":"Shock cord mount","mass_kg":0.00709,"kind":"masscomponent"},{"type":"masscomponent","name":"Shock cord mount","mass_kg":0.00709,"kind":"masscomponent"},{"type":"parachute","diameter_m":0.914,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute"}],"motors":[{"manufacturer":"AeroTech","designation":"HP-H195NT"},{"manufacturer":"AeroTech","designation":"G79W/L"}]}],"motors":[{"manufacturer":"AeroTech","designation":"HP-H195NT"},{"manufacturer":"AeroTech","designation":"G79W/L"}]}]}
</design>
```
</details>

### U-268 · MEDIUM
**Prompt:** Design a rocket that goes to about 84 m apogee in about 2.4 s to apogee on a C11 motor.
**Rocket:** `ork/rockets__bt_55.ork` · **Sim:** Simulation 1 · **Motor:** C6
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 84.351 m · max velocity 67.805 m/s · time to apogee 2.357 s · flight time 30.891 s · touchdown 3.169 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 84 m apogee in about 2.4 s to apogee on a C11 motor.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 84 m (277 ft)
- Time to apogee: 2.4 s
- Peak velocity: 68 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 31 s; descent from apogee takes 29 s
- Touchdown velocity: 3.17 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1016,"base_radius_m":0.01683,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","preset":"Estes EST 3087","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","preset":"Estes 302267","name":"Parachute"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.09,"tip_chord_m":0.035,"span_m":0.05,"sweep_m":0.025,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}]}
</design>
```
</details>

### U-269 · MEDIUM
**Prompt:** Design a rocket that goes to about 84 m apogee on a C11 motor, taking about 2.4 s to apogee.
**Rocket:** `ork/rockets__bt_55.ork` · **Sim:** Simulation 1 · **Motor:** C6
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 84.351 m · max velocity 67.805 m/s · time to apogee 2.357 s · flight time 30.891 s · touchdown 3.169 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 84 m apogee on a C11 motor, taking about 2.4 s to apogee.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 84 m (277 ft)
- Time to apogee: 2.4 s
- Peak velocity: 68 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 31 s; descent from apogee takes 29 s
- Touchdown velocity: 3.17 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1016,"base_radius_m":0.01683,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","preset":"Estes EST 3087","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","preset":"Estes 302267","name":"Parachute"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.09,"tip_chord_m":0.035,"span_m":0.05,"sweep_m":0.025,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}]}
</design>
```
</details>

### U-297 · MEDIUM
**Prompt:** Design a rocket that goes to about 965 m apogee with deployment at about 18 m/s and a 116 s flight.
**Rocket:** `ork/DarkStar_Mini[1].ork` · **Sim:** Simulation 2 · **Motor:** G77R/L
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 965.325 m · max velocity 187.762 m/s · time to apogee 12.239 s · flight time 115.986 s · touchdown 9.362 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 965 m apogee with deployment at about 18 m/s and a 116 s flight.

2. PROPULSION & ASCENT:
- Motor: G77R/L
- Simulated apogee: 965 m (3,167 ft)
- Time to apogee: 12.2 s
- Peak velocity: 188 m/s (Mach 0.55)

3. RECOVERY & DESCENT:
- Parachute 0.38 m diameter, deploys at ejection
- Total flight time 116 s; descent from apogee takes 104 s
- Touchdown velocity: 9.36 m/s
</thought>
<design>
{"flight":{"motor":"G77R/L","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.20663,"base_radius_m":0.02057,"wall_thickness_m":0.00159,"material":"Fiberglass","name":"Nose cone with Foam and Kevlar Loop"},{"type":"bodytube","length_m":0.6096,"outer_d_m":0.04114,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Body tube","contains":[{"type":"innertube","length_m":0.20574,"outer_d_m":0.03136,"wall_thickness_m":0.00114,"material":"Fiberglass","name":"29 MMT","motors":[{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"G77R/L"},{"manufacturer":"AeroTech","designation":"F27R/L"}]},{"type":"centeringring","material":"Fiberglass","name":"Centering ring - forward"},{"type":"centeringring","material":"Fiberglass","name":"Centering ring - aft"},{"type":"masscomponent","name":"1/8 Tubular Kevlar recovery harness","mass_kg":0.0205,"kind":"masscomponent"},{"type":"parachute","diameter_m":0.3814,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Rip stop nylon","name":"Parachute"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.08484,"tip_chord_m":0.01968,"span_m":0.0494,"sweep_m":0.09955,"thickness_m":0.00159,"material":"Fiberglass","name":"Fin set - forward"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00159,"material":"G10 (PML 0.062\")","name":"Fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"G77R/L"},{"manufacturer":"AeroTech","designation":"F27R/L"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"G77R/L"},{"manufacturer":"AeroTech","designation":"F27R/L"}]}]}
</design>
```
</details>

### U-449 · MEDIUM
**Prompt:** Make a rocket that hits 282 m and stays up about 76 s, weighs around 76 g and is about 58 cm long.
**Rocket:** `ork/Tube fin rocket.ork` · **Sim:** Simulation 1 · **Motor:** D12
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 282.234 m · max velocity 119.326 m/s · time to apogee 5.933 s · flight time 75.614 s · touchdown 4.406 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 6 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 282 m and stays up about 76 s, weighs around 76 g and is about 58 cm long.

2. PROPULSION & ASCENT:
- Motor: D12
- Simulated apogee: 282 m (926 ft)
- Time to apogee: 5.9 s
- Peak velocity: 119 m/s (Mach 0.35)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 76 s; descent from apogee takes 70 s
- Touchdown velocity: 4.41 m/s
</thought>
<design>
{"flight":{"motor":"D12","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.11989,"base_radius_m":0.0124,"wall_thickness_m":0.00116,"material":"Polystyrene","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","name":"Parachute kit, plastic, 12 in., PN 85564"},{"type":"engineblock","name":"Engine Block"},{"type":"tubefin","fin_count":6.0,"thickness_m":0.00033,"material":"Paper","name":"Tube fin set"},{"type":"launchlug","length_m":0.06032,"name":"Launch Lug"}],"motors":[{"manufacturer":"Estes","designation":"D12"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"}]}]}
</design>
```
</details>

### U-459 · MEDIUM
**Prompt:** Make a rocket that hits 451 m and stays up about 110 s, weighs around 357 g and is about 107 cm long.
**Rocket:** `ork/ARC payload rocket.ork` · **Sim:** Simulation 1 · **Motor:** F50T
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 451.359 m · max velocity 150.261 m/s · time to apogee 8.172 s · flight time 109.981 s · touchdown 4.642 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 2 stages, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 451 m and stays up about 110 s, weighs around 357 g and is about 107 cm long.

2. PROPULSION & ASCENT:
- Motor: F50T
- Simulated apogee: 451 m (1,481 ft)
- Time to apogee: 8.2 s
- Peak velocity: 150 m/s (Mach 0.44)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at lowerstageseparation
- Parachute 0.38 m diameter, deploys at ejection
- Total flight time 110 s; descent from apogee takes 102 s
- Touchdown velocity: 4.64 m/s
</thought>
<design>
{"flight":{"motor":"F50T","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Payload","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1778,"base_radius_m":0.02816,"material":"Balsa","name":"Nose cone"},{"type":"bodytube","length_m":0.127,"outer_d_m":0.05632,"wall_thickness_m":0.00053,"material":"Paper","name":"Body tube","contains":[{"type":"masscomponent","name":"Mass component","mass_kg":0.05,"kind":"masscomponent"},{"type":"parachute","diameter_m":0.3048,"deploy_event":"lowerstageseparation","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":12.0,"material":"Ripstop nylon","name":"Elliptical 12-Gore 12\" Parachute"}]}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.762,"outer_d_m":0.05632,"wall_thickness_m":0.00053,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.381,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":12.0,"material":"Ripstop nylon","name":"Elliptical 12-Gore 15\" Parachute"},{"type":"innertube","length_m":0.2286,"outer_d_m":0.03214,"wall_thickness_m":0.00152,"material":"Kraft phenolic","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"F50T"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0754,"tip_chord_m":0.0246,"span_m":0.0554,"sweep_m":0.025,"thickness_m":0.003,"material":"Basswood","name":"Trapezoidal fin set #1"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0754,"tip_chord_m":0.0246,"span_m":0.0554,"sweep_m":0.025,"thickness_m":0.003,"material":"Basswood","name":"Trapezoidal fin set #2"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0754,"tip_chord_m":0.0246,"span_m":0.0554,"sweep_m":0.025,"thickness_m":0.003,"material":"Basswood","name":"Trapezoidal fin set #3"}],"motors":[{"manufacturer":"AeroTech","designation":"F50T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F50T"}]}]}
</design>
```
</details>

### V1-001 · MEDIUM
**Prompt:** Design a rocket that goes to about 1,408 m apogee in about 17.0 s to apogee.
**Rocket:** `ork/02.Two-stage.ork` · **Sim:** Simulation 1 · **Motor:** G80T, I300T
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 1408.16 m · max velocity 172.598 m/s · time to apogee 17.014 s · flight time 287.301 s · touchdown 5.048 m/s · wind 2 m/s
**Parts:** nose cone, 7 body tubes, transition, 12 fins, 2 stages, 2 parachutes recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 1,408 m apogee in about 17.0 s to apogee.

2. PROPULSION & ASCENT:
- Motor: G80T, I300T
- Simulated apogee: 1,408 m (4,620 ft)
- Time to apogee: 17.0 s
- Peak velocity: 173 m/s (Mach 0.51)

3. RECOVERY & DESCENT:
- Parachute 0.76 m diameter, deploys at apogee
- Parachute 0.91 m diameter, deploys at 200 m (656 ft)
- Total flight time 287 s; descent from apogee takes 270 s
- Touchdown velocity: 5.05 m/s
</thought>
<design>
{"flight":{"motor":"G80T, I300T","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Dart","contains":[{"type":"nosecone","shape":"conical","length_m":0.225,"base_radius_m":0.025,"material":"Balsa","name":"Nose cone"},{"type":"bodytube","length_m":0.0075,"outer_d_m":0.05,"wall_thickness_m":0.003,"material":"Cardboard","name":"Body tube"},{"type":"bodytube","length_m":0.1275,"outer_d_m":0.03976,"wall_thickness_m":0.003,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.762,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","name":"Iris Ultra Compact 30\" Parachute"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.003,"tip_chord_m":0.0015,"span_m":0.045,"sweep_m":0.0375,"thickness_m":0.001,"material":"Cardboard","name":"Trapezoidal fin set"}]},{"type":"transition","shape":"conical","length_m":0.03,"fore_d_m":0.05,"aft_d_m":0.05,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.33,"outer_d_m":0.03824,"wall_thickness_m":0.00112,"material":"Cardboard","name":"Body tube"},{"type":"transition","shape":"conical","length_m":0.015,"fore_d_m":0.05,"aft_d_m":0.05,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.135,"outer_d_m":0.0465,"wall_thickness_m":0.0015,"material":"Polycarbonate","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.126,"tip_chord_m":0.054,"span_m":0.045,"sweep_m":0.07275,"thickness_m":0.0045,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"G80T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"G80T"}]},{"type":"stage_marker","name":"Booster","contains":[{"type":"transition","shape":"conical","length_m":0.14176,"fore_d_m":0.1125,"aft_d_m":0.05,"material":"Balsa","name":"Transition"},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":12.0,"material":"Ripstop nylon","name":"Elliptical 12-Gore 36\" Parachute"},{"type":"railbutton","name":"Rail Button"}]},{"type":"bodytube","length_m":0.0254,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube"},{"type":"bodytube","length_m":0.6096,"outer_d_m":0.1005,"wall_thickness_m":0.003,"material":"Cardboard","name":"Body tube","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"innertube","length_m":0.2193,"outer_d_m":0.04,"wall_thickness_m":0.0,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"I300T"}]},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.1425,"tip_chord_m":0.0675,"span_m":0.129,"sweep_m":0.0375,"thickness_m":0.0045,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"I300T"}]},{"type":"transition","shape":"conical","length_m":0.0127,"fore_d_m":0.1125,"aft_d_m":0.05,"material":"Balsa","name":"Transition"}],"motors":[{"manufacturer":"AeroTech","designation":"I300T"}]}]}
</design>
```
</details>

### V1-002 · MEDIUM
**Prompt:** Design a rocket that goes to about 1,603 m apogee in about 21.4 s to apogee.
**Rocket:** `ork/03.Three-stage.ork` · **Sim:** Simulation 1 · **Motor:** J315R, J90W
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 1603.05 m · max velocity 227.786 m/s · time to apogee 21.435 s · flight time 247.479 s · touchdown 5.225 m/s · wind 2 m/s
**Parts:** nose cone, 9 body tubes, transition, 20 fins, 3 stages, 2 parachutes recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 1,603 m apogee in about 21.4 s to apogee.

2. PROPULSION & ASCENT:
- Motor: J315R, J90W
- Simulated apogee: 1,603 m (5,259 ft)
- Time to apogee: 21.4 s
- Peak velocity: 228 m/s (Mach 0.68)

3. RECOVERY & DESCENT:
- Parachute 1.07 m diameter, deploys at 200 m (656 ft)
- Parachute 1.14 m diameter, deploys at apogee
- Total flight time 247 s; descent from apogee takes 226 s
- Touchdown velocity: 5.22 m/s
</thought>
<design>
{"flight":{"motor":"J315R, J90W","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.42545,"base_radius_m":0.0508,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.8636,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":1.06731,"deploy_event":"altitude","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop Nylon","preset":"Spherachutes HS-066-UL","name":"UltraLight 66\" Hemispherical Spherachute [Cd .75 (2.6 oz)  19.69 in^3]"}]},{"type":"bodytube","length_m":0.4445,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":1.143,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.06985,"tip_chord_m":0.0254,"span_m":0.01905,"sweep_m":0.05398,"thickness_m":0.00478,"material":"Birch","name":"Fin set"},{"type":"bulkhead","material":"Birch","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.26035,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.19685,"tip_chord_m":0.0508,"span_m":0.10795,"sweep_m":0.22687,"thickness_m":0.00478,"material":"Birch","name":"Fin set"},{"type":"centeringring","material":"Aircraft plywood (Birch)","name":"Ring"},{"type":"centeringring","material":"Aircraft plywood (Birch)","name":"Ring"}]},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.13162,"tip_chord_m":0.06985,"span_m":0.0635,"sweep_m":0.04445,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal Fin Set"},{"type":"centeringring","material":"Aircraft plywood (Birch)","name":"Ring"},{"type":"centeringring","material":"Aircraft plywood (Birch)","name":"Ring"},{"type":"innertube","length_m":0.4318,"outer_d_m":0.05486,"wall_thickness_m":0.00025,"material":"Paper","name":"Body tube","motors":[{"manufacturer":"AeroTech","designation":"J315R"}]}],"motors":[{"manufacturer":"AeroTech","designation":"J315R"}]},{"type":"transition","shape":"conical","length_m":0.0127,"fore_d_m":0.05,"aft_d_m":0.0508,"material":"Cardboard","name":"Transition"}],"motors":[{"manufacturer":"AeroTech","designation":"J315R"}]},{"type":"stage_marker","name":"Booster 1","contains":[{"type":"transition","shape":"conical","length_m":0.0127,"fore_d_m":0.05,"aft_d_m":0.0381,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.0254,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube"},{"type":"bodytube","length_m":0.2159,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.19685,"tip_chord_m":0.0508,"span_m":0.10795,"sweep_m":0.22687,"thickness_m":0.00478,"material":"Birch","name":"Fin set"},{"type":"centeringring","material":"Aircraft plywood (Birch)","name":"Ring"},{"type":"centeringring","material":"Aircraft plywood (Birch)","name":"Ring"},{"type":"innertube","length_m":0.4318,"outer_d_m":0.05486,"wall_thickness_m":0.00025,"material":"Paper","name":"Body tube","motors":[{"manufacturer":"AeroTech","designation":"J90W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"J90W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"J90W"}]},{"type":"stage_marker","name":"Booster 2","contains":[{"type":"transition","shape":"conical","length_m":0.0127,"fore_d_m":0.05,"aft_d_m":0.0381,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.1778,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.13162,"tip_chord_m":0.06985,"span_m":0.0635,"sweep_m":0.04445,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal Fin Set"},{"type":"centeringring","material":"Aircraft plywood (Birch)","name":"Ring"},{"type":"centeringring","material":"Aircraft plywood (Birch)","name":"Ring"},{"type":"innertube","length_m":0.4318,"outer_d_m":0.05486,"wall_thickness_m":0.00025,"material":"Paper","name":"Body tube","motors":[{"manufacturer":"AeroTech","designation":"J315R"}]}],"motors":[{"manufacturer":"AeroTech","designation":"J315R"}]},{"type":"bodytube","length_m":0.0254,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube"},{"type":"bodytube","length_m":0.0254,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Body tube"},{"type":"transition","shape":"conical","length_m":0.0127,"fore_d_m":0.05,"aft_d_m":0.0508,"material":"Cardboard","name":"Transition"}],"motors":[{"manufacturer":"AeroTech","designation":"J315R"}]}]}
</design>
```
</details>

### V1-003 · MEDIUM
**Prompt:** Design a rocket that goes to about 3,380 m apogee and touches down at about 8.1 m/s.
**Rocket:** `ork/4. Spline.ork` · **Sim:** Simulation 1 · **Motor:** I216-CL(I)
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 3379.6 m · max velocity 435.36 m/s · time to apogee 22.466 s · flight time 400.54 s · touchdown 8.0507 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 1 stage, 1 parachute + 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 3,380 m apogee and touches down at about 8.1 m/s.

2. PROPULSION & ASCENT:
- Motor: I216-CL(I)
- Simulated apogee: 3,380 m (11,088 ft)
- Time to apogee: 22.5 s
- Peak velocity: 435 m/s (Mach 1.29)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at apogee
- Streamer recovery
- Total flight time 401 s; descent from apogee takes 378 s
- Touchdown velocity: 8.05 m/s
</thought>
<design>
{"flight":{"motor":"I216-CL(I)","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.215,"wall_thickness_m":0.002,"material":"ABS","name":"Nose cone4","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.00027,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.245,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"masscomponent","name":"Electronics Bay","mass_kg":0.0075,"kind":"payload"},{"type":"bulkhead","material":"Aluminum","name":"Bulkhead"},{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":5.0,"line_count":8.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"apogee","material":"Ripstop nylon","name":"Streamer"}]},{"type":"bodytube","length_m":0.244,"outer_d_m":0.046,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube Middle"},{"type":"bodytube","length_m":0.17,"wall_thickness_m":0.0015,"material":"PLA","name":"Fin Can","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00022,"material":"Aluminum","name":"Freeform fin set"},{"type":"innertube","length_m":0.33,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Cardboard","name":"Inner Tube"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"engineblock","name":"Retaining Ring"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}]}
</design>
```
</details>

### V1-004 · MEDIUM
**Prompt:** Design a rocket that goes to about 2,751 m apogee on a I216-CL(I) motor, taking about 19.7 s to apogee.
**Rocket:** `ork/4. Spline.ork` · **Sim:** Simulation 2 · **Motor:** I216-CL(I)
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 2751.4 m · max velocity 416.07 m/s · time to apogee 19.736 s · flight time 335.42 s · touchdown 7.932 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 1 stage, 1 parachute + 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 2,751 m apogee on a I216-CL(I) motor, taking about 19.7 s to apogee.

2. PROPULSION & ASCENT:
- Motor: I216-CL(I)
- Simulated apogee: 2,751 m (9,027 ft)
- Time to apogee: 19.7 s
- Peak velocity: 416 m/s (Mach 1.23)

3. RECOVERY & DESCENT:
- Parachute 0.61 m diameter, deploys at apogee
- Streamer recovery
- Total flight time 335 s; descent from apogee takes 316 s
- Touchdown velocity: 7.93 m/s
</thought>
<design>
{"flight":{"motor":"I216-CL(I)","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.215,"wall_thickness_m":0.002,"material":"ABS","name":"Nose cone4","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.00027,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.245,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"masscomponent","name":"Electronics Bay","mass_kg":0.0075,"kind":"payload"},{"type":"bulkhead","material":"Aluminum","name":"Bulkhead"},{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":5.0,"line_count":8.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"apogee","material":"Ripstop nylon","name":"Streamer"}]},{"type":"bodytube","length_m":0.244,"outer_d_m":0.046,"wall_thickness_m":0.0015,"material":"Carbon fiber","name":"Body tube Middle"},{"type":"bodytube","length_m":0.17,"wall_thickness_m":0.0015,"material":"PLA","name":"Fin Can","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00022,"material":"Aluminum","name":"Freeform fin set"},{"type":"innertube","length_m":0.33,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Cardboard","name":"Inner Tube"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"engineblock","name":"Retaining Ring"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"I216-CL(I)"}]}]}
</design>
```
</details>

### V1-005 · MEDIUM
**Prompt:** I need a rocket on a 1526K160-6, 2833L805-P motor that gets up close to 4,992 m.
**Rocket:** `ork/Argonia_3p120OD_K160-P_SIM_9-22-24.ork` · **Sim:** Simulation 12 · **Motor:** 1526K160-6, 2833L805-P
**Why medium: 2 requirements: apogee, motor**
**Targets:** apogee 4992.26 m · max velocity 264.633 m/s · time to apogee 33.668 s · flight time 421.209 s · touchdown 5.369 m/s · wind 5.36448 m/s
**Parts:** nose cone, 4 body tubes, 6 fins, 2 stages, 4 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I need a rocket on a 1526K160-6, 2833L805-P motor that gets up close to 4,992 m.

2. PROPULSION & ASCENT:
- Motor: 1526K160-6, 2833L805-P
- Simulated apogee: 4,992 m (16,379 ft)
- Time to apogee: 33.7 s
- Peak velocity: 265 m/s (Mach 0.81)

3. RECOVERY & DESCENT:
- Parachute 1.07 m diameter, deploys at 305 m (1000 ft)
- Parachute 0.61 m diameter, deploys at apogee
- Parachute 0.46 m diameter, deploys at apogee
- Parachute 0.91 m diameter, deploys at 305 m (1000 ft)
- Total flight time 421 s; descent from apogee takes 388 s
- Touchdown velocity: 5.37 m/s
</thought>
<design>
{"flight":{"motor":"1526K160-6, 2833L805-P","wind_ms":5.36448},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.39624,"base_radius_m":0.03962,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Aluminum Tip","mass_kg":0.25515,"kind":"masscomponent"},{"type":"parachute","diameter_m":1.0668,"deploy_event":"altitude","deploy_altitude_m":304.8,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-042-SL","name":"Iris Ultra Light Parachute [Cd 2.2 (2.9 oz) 16.1 in^3]"}]},{"type":"bodytube","length_m":0.0635,"outer_d_m":0.07924,"wall_thickness_m":0.0,"material":"Cardboard","name":"Front Tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes CFC-024-S","name":"Compact Elliptical Parachute [Cd 1.55 (1.6 oz) 8.8 in^3)"}]},{"type":"bodytube","length_m":0.9652,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Sustainer Body Tube","contains":[{"type":"innertube","length_m":0.4064,"outer_d_m":0.054,"wall_thickness_m":0.0005,"material":"Aluminum","name":"Aerotech 5417SC Motor Case","motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]},{"type":"innertube","length_m":0.2286,"outer_d_m":0.05694,"wall_thickness_m":0.00114,"material":"Fiberglass","name":"Inner Tube","contains":[{"type":"masscomponent","name":"Batteries","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"AV Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"Camera Bay","mass_kg":0.54715,"kind":"masscomponent"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.17534,"kind":"masscomponent"}]},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"railbutton","name":"Rail Button"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1524,"tip_chord_m":0.0508,"span_m":0.0889,"sweep_m":0.12065,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal Fin Set"},{"type":"masscomponent","name":"Golf Balls","mass_kg":0.5508,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]},{"type":"stage_marker","name":"Stage","contains":[{"type":"bodytube","length_m":0.073,"outer_d_m":0.07924,"wall_thickness_m":0.002,"material":"Cardboard","name":"Interstage"},{"type":"bodytube","length_m":0.89408,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Booster Body Tube","contains":[{"type":"masscomponent","name":"Batteries","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"AV Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Maple","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"innertube","length_m":0.49784,"outer_d_m":0.0762,"wall_thickness_m":0.0005,"material":"Aluminum","name":"Aerotech 5417SC Motor Case","motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1778,"tip_chord_m":0.05715,"span_m":0.1016,"sweep_m":0.1143,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes CFC-018-S","name":"Compact Elliptical Parachute [Cd 1.55 (1.16 oz) 6.4 in^3)"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":304.8,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-036-N","name":"Iris Ultra Parachute [Cd 2.2 (5.0 oz) 27.6 in^3]"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]}]}
</design>
```
</details>

### V1-007 · MEDIUM
**Prompt:** Design a rocket that goes to apogee in about 30.0 s with a total flight of about 306.1 s.
**Rocket:** `ork/Argonia_3p120OD_K160-P_SIM_9-22-24.ork` · **Sim:** Simulation 15 · **Motor:** 1526K160-6, 1654K515-16A
**Why medium: 2 requirements: time to apogee, flight time**
**Targets:** apogee 3285.5 m · max velocity 233.728 m/s · time to apogee 29.952 s · flight time 306.087 s · touchdown 5.376 m/s · wind 5.36448 m/s
**Parts:** nose cone, 4 body tubes, 6 fins, 2 stages, 4 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to apogee in about 30.0 s with a total flight of about 306.1 s.

2. PROPULSION & ASCENT:
- Motor: 1526K160-6, 1654K515-16A
- Simulated apogee: 3,285 m (10,779 ft)
- Time to apogee: 30.0 s
- Peak velocity: 234 m/s (Mach 0.71)

3. RECOVERY & DESCENT:
- Parachute 1.07 m diameter, deploys at 305 m (1000 ft)
- Parachute 0.61 m diameter, deploys at apogee
- Parachute 0.46 m diameter, deploys at apogee
- Parachute 0.91 m diameter, deploys at 305 m (1000 ft)
- Total flight time 306 s; descent from apogee takes 276 s
- Touchdown velocity: 5.38 m/s
</thought>
<design>
{"flight":{"motor":"1526K160-6, 1654K515-16A","wind_ms":5.36448},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.39624,"base_radius_m":0.03962,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Aluminum Tip","mass_kg":0.25515,"kind":"masscomponent"},{"type":"parachute","diameter_m":1.0668,"deploy_event":"altitude","deploy_altitude_m":304.8,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-042-SL","name":"Iris Ultra Light Parachute [Cd 2.2 (2.9 oz) 16.1 in^3]"}]},{"type":"bodytube","length_m":0.0635,"outer_d_m":0.07924,"wall_thickness_m":0.0,"material":"Cardboard","name":"Front Tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes CFC-024-S","name":"Compact Elliptical Parachute [Cd 1.55 (1.6 oz) 8.8 in^3)"}]},{"type":"bodytube","length_m":0.9652,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Sustainer Body Tube","contains":[{"type":"innertube","length_m":0.4064,"outer_d_m":0.054,"wall_thickness_m":0.0005,"material":"Aluminum","name":"Aerotech 5417SC Motor Case","motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]},{"type":"innertube","length_m":0.2286,"outer_d_m":0.05694,"wall_thickness_m":0.00114,"material":"Fiberglass","name":"Inner Tube","contains":[{"type":"masscomponent","name":"Batteries","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"AV Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"Camera Bay","mass_kg":0.54715,"kind":"masscomponent"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.17534,"kind":"masscomponent"}]},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"railbutton","name":"Rail Button"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1524,"tip_chord_m":0.0508,"span_m":0.0889,"sweep_m":0.12065,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal Fin Set"},{"type":"masscomponent","name":"Golf Balls","mass_kg":0.5508,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"1526K160-6"},{"manufacturer":"Cesaroni Technology","designation":"867J244-14A"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"K250-LW"}]},{"type":"stage_marker","name":"Stage","contains":[{"type":"bodytube","length_m":0.073,"outer_d_m":0.07924,"wall_thickness_m":0.002,"material":"Cardboard","name":"Interstage"},{"type":"bodytube","length_m":0.89408,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Booster Body Tube","contains":[{"type":"masscomponent","name":"Batteries","mass_kg":0.2268,"kind":"masscomponent"},{"type":"masscomponent","name":"AV Components","mass_kg":0.2268,"kind":"masscomponent"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"bulkhead","material":"Maple","name":"Bulkhead"},{"type":"bulkhead","material":"Fiberglass","name":"Bulkhead"},{"type":"innertube","length_m":0.49784,"outer_d_m":0.0762,"wall_thickness_m":0.0005,"material":"Aluminum","name":"Aerotech 5417SC Motor Case","motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.1778,"tip_chord_m":0.05715,"span_m":0.1016,"sweep_m":0.1143,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes CFC-018-S","name":"Compact Elliptical Parachute [Cd 1.55 (1.16 oz) 6.4 in^3)"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":304.8,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-036-N","name":"Iris Ultra Parachute [Cd 2.2 (5.0 oz) 27.6 in^3]"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"2833L805-P"},{"manufacturer":"Cesaroni Technology","designation":"1654K515-16A"},{"manufacturer":"AeroTech","designation":"K1000T"},{"manufacturer":"AeroTech","designation":"K560W"},{"manufacturer":"Cesaroni Technology","designation":"2856L910-P"},{"manufacturer":"AeroTech","designation":"K1800ST-P"},{"manufacturer":"Loki Research","designation":"L780-SF"},{"manufacturer":"Loki Research","designation":"L930-LW"},{"manufacturer":"AeroTech","designation":"L1150R"}]}]}
</design>
```
</details>

### V1-009 · MEDIUM
**Prompt:** Design a rocket that goes to about 98 m apogee with a total flight time of about 27.2 s.
**Rocket:** `ork/Base drag hack (short-wide).ork` · **Sim:** Simulation 1 · **Motor:** C11
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 98.286 m · max velocity 47.147 m/s · time to apogee 4.594 s · flight time 27.246 s · touchdown 4.718 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 98 m apogee with a total flight time of about 27.2 s.

2. PROPULSION & ASCENT:
- Motor: C11
- Simulated apogee: 98 m (322 ft)
- Time to apogee: 4.6 s
- Peak velocity: 47 m/s (Mach 0.14)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 27 s; descent from apogee takes 23 s
- Touchdown velocity: 4.72 m/s
</thought>
<design>
{"flight":{"motor":"C11","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.04543,"base_radius_m":0.03937,"wall_thickness_m":0.00168,"material":"Polycarbonate (Lexan)","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Tungsten .5 oz Nose Weight","mass_kg":0.01417,"kind":"masscomponent"},{"type":"masscomponent","name":"Tungsten .5 oz Nose Weight","mass_kg":0.01417,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.12114,"outer_d_m":0.07874,"wall_thickness_m":0.00061,"material":"Cardboard","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Mylar polyester film","name":"18\" Mylar Parachute"},{"type":"masscomponent","name":"9\" Nomex Blanket","mass_kg":0.01531,"kind":"masscomponent"},{"type":"launchlug","length_m":0.03175,"name":"Launch Lug"},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00305,"material":"Basswood","name":"Freeform Fiin Set (4)"},{"type":"centeringring","material":"Paper (office)","name":"Centering Ring"},{"type":"centeringring","material":"Paper (office)","name":"Centering Ring"},{"type":"innertube","length_m":0.09525,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"24mm Motor Mount Tube","contains":[{"type":"engineblock","name":"Engine Block"},{"type":"engineblock","name":"Engine Adapter [Remove for \"E\" Engine]"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"}]}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"}]},{"type":"transition","shape":"conical","length_m":0.24746,"fore_d_m":4e-05,"aft_d_m":0.07874,"material":"Polycarbonate (Lexan)","name":"Base-Drag Hack Transition"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"}]}]}
</design>
```
</details>

### V1-011 · MEDIUM
**Prompt:** Design a rocket that goes to about 315 m apogee, reaching about 91.4 m/s max velocity.
**Rocket:** `ork/Base drag hack (short-wide).ork` · **Sim:** Simulation 3 · **Motor:** E12
**Why medium: 2 requirements: apogee, max velocity**
**Targets:** apogee 314.744 m · max velocity 91.399 m/s · time to apogee 6.919 s · flight time 81.073 s · touchdown 4.757 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 315 m apogee, reaching about 91.4 m/s max velocity.

2. PROPULSION & ASCENT:
- Motor: E12
- Simulated apogee: 315 m (1,033 ft)
- Time to apogee: 6.9 s
- Peak velocity: 91 m/s (Mach 0.27)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 81 s; descent from apogee takes 74 s
- Touchdown velocity: 4.76 m/s
</thought>
<design>
{"flight":{"motor":"E12","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.04543,"base_radius_m":0.03937,"wall_thickness_m":0.00168,"material":"Polycarbonate (Lexan)","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Tungsten .5 oz Nose Weight","mass_kg":0.01417,"kind":"masscomponent"},{"type":"masscomponent","name":"Tungsten .5 oz Nose Weight","mass_kg":0.01417,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.12114,"outer_d_m":0.07874,"wall_thickness_m":0.00061,"material":"Cardboard","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Mylar polyester film","name":"18\" Mylar Parachute"},{"type":"masscomponent","name":"9\" Nomex Blanket","mass_kg":0.01531,"kind":"masscomponent"},{"type":"launchlug","length_m":0.03175,"name":"Launch Lug"},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00305,"material":"Basswood","name":"Freeform Fiin Set (4)"},{"type":"centeringring","material":"Paper (office)","name":"Centering Ring"},{"type":"centeringring","material":"Paper (office)","name":"Centering Ring"},{"type":"innertube","length_m":0.09525,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"24mm Motor Mount Tube","contains":[{"type":"engineblock","name":"Engine Block"},{"type":"engineblock","name":"Engine Adapter [Remove for \"E\" Engine]"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"}]}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"}]},{"type":"transition","shape":"conical","length_m":0.24746,"fore_d_m":4e-05,"aft_d_m":0.07874,"material":"Polycarbonate (Lexan)","name":"Base-Drag Hack Transition"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"}]}]}
</design>
```
</details>

### V1-015 · MEDIUM
**Prompt:** Design a rocket that goes to about 1,935 m apogee, reaching about 312.3 m/s max velocity.
**Rocket:** `ork/Example Rocket.ork` · **Sim:** Simulation 1 · **Motor:** K400C
**Why medium: 2 requirements: apogee, max velocity**
**Targets:** apogee 1935.42 m · max velocity 312.341 m/s · time to apogee 16.95 s · flight time 126.995 s · touchdown 7.813 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, transition, freeform fins, 7 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 1,935 m apogee, reaching about 312.3 m/s max velocity.

2. PROPULSION & ASCENT:
- Motor: K400C
- Simulated apogee: 1,935 m (6,350 ft)
- Time to apogee: 16.9 s
- Peak velocity: 312 m/s (Mach 0.92)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at 183 m (600 ft)
- Parachute 0.41 m diameter, deploys at apogee
- Total flight time 127 s; descent from apogee takes 110 s
- Touchdown velocity: 7.81 m/s
</thought>
<design>
{"flight":{"motor":"K400C","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.09029,"base_radius_m":0.04127,"wall_thickness_m":0.002,"material":"PLA - 100% infill","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.0,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.2032,"outer_d_m":0.08254,"wall_thickness_m":0.002,"material":"Cardboard","name":"Avionics Bay","contains":[{"type":"masscomponent","name":"Electronics","mass_kg":0.56699,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.6731,"outer_d_m":0.08254,"wall_thickness_m":0.00318,"material":"Cardboard","name":"Body Tube","contains":[{"type":"innertube","length_m":0.3556,"outer_d_m":0.06096,"wall_thickness_m":0.00325,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"K400C"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering Ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering Ring"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":182.88,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Main"},{"type":"parachute","diameter_m":0.4064,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Drouge"},{"type":"masscomponent","name":"Fin Can Weight","mass_kg":0.341,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button"},{"type":"ellipticalfin","fin_count":3.0,"root_chord_m":0.05,"span_m":0.05,"thickness_m":0.003,"material":"Cardboard","name":"Elliptical Fin Set"},{"type":"freeformfinset","fin_count":2.0,"thickness_m":0.003,"material":"Cardboard","name":"Freeform Fin Set"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.1778,"tip_chord_m":0.0762,"span_m":0.0762,"sweep_m":0.1016,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"AeroTech","designation":"K400C"}]},{"type":"transition","shape":"conical","length_m":0.075,"fore_d_m":0.08254,"aft_d_m":0.05,"material":"Cardboard","name":"Transition"}],"motors":[{"manufacturer":"AeroTech","designation":"K400C"}]}]}
</design>
```
</details>

### V1-017 · MEDIUM
**Prompt:** I need a rocket on a F39T motor that gets up close to 217 m.
**Rocket:** `ork/Final rocket design 2.ork` · **Sim:** 5mph F39 · **Motor:** F39T
**Why medium: 2 requirements: apogee, motor**
**Targets:** apogee 217.139 m · max velocity 68.111 m/s · time to apogee 6.743 s · flight time 33.285 s · touchdown 8.556 m/s · wind 2.2352 m/s
**Parts:** nose cone, 2 body tubes, transition, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I need a rocket on a F39T motor that gets up close to 217 m.

2. PROPULSION & ASCENT:
- Motor: F39T
- Simulated apogee: 217 m (712 ft)
- Time to apogee: 6.7 s
- Peak velocity: 68 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 33 s; descent from apogee takes 27 s
- Touchdown velocity: 8.56 m/s
</thought>
<design>
{"flight":{"motor":"F39T","wind_ms":2.2352},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.0762,"base_radius_m":0.03302,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.011,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.06604,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.0895,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.17,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.00025,"fore_d_m":0.06604,"aft_d_m":0.06604,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.3302,"outer_d_m":0.06604,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"innertube","length_m":0.13716,"outer_d_m":0.02794,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"engineblock","name":"Engine Block"},{"type":"railbutton","name":"Rail Button"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.09398,"tip_chord_m":0.1,"span_m":0.0635,"sweep_m":0.05588,"thickness_m":0.003,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"masscomponent","name":"parachute Protector","mass_kg":0.008,"kind":"masscomponent"}],"motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]}]}
</design>
```
</details>

### V1-018 · MEDIUM
**Prompt:** Make a rocket that hits 252 m and stays up about 38 s.
**Rocket:** `ork/Final rocket design 2.ork` · **Sim:** 5mph F51 · **Motor:** F51NT
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 251.669 m · max velocity 80.302 m/s · time to apogee 7.017 s · flight time 38.428 s · touchdown 8.397 m/s · wind 2.2352 m/s
**Parts:** nose cone, 2 body tubes, transition, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 252 m and stays up about 38 s.

2. PROPULSION & ASCENT:
- Motor: F51NT
- Simulated apogee: 252 m (826 ft)
- Time to apogee: 7.0 s
- Peak velocity: 80 m/s (Mach 0.24)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 38 s; descent from apogee takes 31 s
- Touchdown velocity: 8.40 m/s
</thought>
<design>
{"flight":{"motor":"F51NT","wind_ms":2.2352},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.0762,"base_radius_m":0.03302,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.011,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.06604,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.0895,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.17,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.00025,"fore_d_m":0.06604,"aft_d_m":0.06604,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.3302,"outer_d_m":0.06604,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"innertube","length_m":0.13716,"outer_d_m":0.02794,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"engineblock","name":"Engine Block"},{"type":"railbutton","name":"Rail Button"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.09398,"tip_chord_m":0.1,"span_m":0.0635,"sweep_m":0.05588,"thickness_m":0.003,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"masscomponent","name":"parachute Protector","mass_kg":0.008,"kind":"masscomponent"}],"motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]}]}
</design>
```
</details>

### V1-019 · MEDIUM
**Prompt:** I want a rocket that climbs about 246 m and comes down gently, under 8.8 m/s.
**Rocket:** `ork/Final rocket design 2.ork` · **Sim:** 5 mph F42 · **Motor:** F42T/L
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 245.838 m · max velocity 73.154 m/s · time to apogee 7.115 s · flight time 35.572 s · touchdown 8.791 m/s · wind 2.2352 m/s
**Parts:** nose cone, 2 body tubes, transition, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I want a rocket that climbs about 246 m and comes down gently, under 8.8 m/s.

2. PROPULSION & ASCENT:
- Motor: F42T/L
- Simulated apogee: 246 m (807 ft)
- Time to apogee: 7.1 s
- Peak velocity: 73 m/s (Mach 0.22)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 36 s; descent from apogee takes 28 s
- Touchdown velocity: 8.79 m/s
</thought>
<design>
{"flight":{"motor":"F42T/L","wind_ms":2.2352},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.0762,"base_radius_m":0.03302,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.011,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.06604,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.0895,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.17,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.00025,"fore_d_m":0.06604,"aft_d_m":0.06604,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.3302,"outer_d_m":0.06604,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"innertube","length_m":0.13716,"outer_d_m":0.02794,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"engineblock","name":"Engine Block"},{"type":"railbutton","name":"Rail Button"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.09398,"tip_chord_m":0.1,"span_m":0.0635,"sweep_m":0.05588,"thickness_m":0.003,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"masscomponent","name":"parachute Protector","mass_kg":0.008,"kind":"masscomponent"}],"motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]}]}
</design>
```
</details>

### V1-020 · MEDIUM
**Prompt:** Design a rocket that goes to about 250 m apogee, reaching about 71.4 m/s max velocity.
**Rocket:** `ork/Final rocket design 2.ork` · **Sim:** 5mph F32 · **Motor:** F32T
**Why medium: 2 requirements: apogee, max velocity**
**Targets:** apogee 250.046 m · max velocity 71.353 m/s · time to apogee 7.501 s · flight time 37.648 s · touchdown 8.709 m/s · wind 2.2352 m/s
**Parts:** nose cone, 2 body tubes, transition, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 250 m apogee, reaching about 71.4 m/s max velocity.

2. PROPULSION & ASCENT:
- Motor: F32T
- Simulated apogee: 250 m (820 ft)
- Time to apogee: 7.5 s
- Peak velocity: 71 m/s (Mach 0.21)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 38 s; descent from apogee takes 30 s
- Touchdown velocity: 8.71 m/s
</thought>
<design>
{"flight":{"motor":"F32T","wind_ms":2.2352},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.0762,"base_radius_m":0.03302,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.011,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.06604,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.0895,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.17,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.00025,"fore_d_m":0.06604,"aft_d_m":0.06604,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.3302,"outer_d_m":0.06604,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"innertube","length_m":0.13716,"outer_d_m":0.02794,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"engineblock","name":"Engine Block"},{"type":"railbutton","name":"Rail Button"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.09398,"tip_chord_m":0.1,"span_m":0.0635,"sweep_m":0.05588,"thickness_m":0.003,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"masscomponent","name":"parachute Protector","mass_kg":0.008,"kind":"masscomponent"}],"motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F32T"},{"manufacturer":"AeroTech","designation":"F51NT"},{"manufacturer":"AeroTech","designation":"F42T/L"},{"manufacturer":"AeroTech","designation":"F39T"}]}]}
</design>
```
</details>

### V1-023 · MEDIUM
**Prompt:** Design a rocket that goes to apogee in about 18.7 s with a total flight of about 98.3 s.
**Rocket:** `ork/NASA_Rocket_V1.ork` · **Sim:** Simulation 4 · **Motor:** L1170FJ
**Why medium: 2 requirements: time to apogee, flight time**
**Targets:** apogee 1731 m · max velocity 210.67 m/s · time to apogee 18.701 s · flight time 98.252 s · touchdown 6.165 m/s · wind 0 m/s
**Parts:** nose cone, 3 body tubes, 4 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to apogee in about 18.7 s with a total flight of about 98.3 s.

2. PROPULSION & ASCENT:
- Motor: L1170FJ
- Simulated apogee: 1,731 m (5,679 ft)
- Time to apogee: 18.7 s
- Peak velocity: 211 m/s (Mach 0.62)

3. RECOVERY & DESCENT:
- Parachute 3.05 m diameter, deploys at 213 m (700 ft)
- Parachute 0.61 m diameter, deploys at apogee
- Total flight time 98 s; descent from apogee takes 80 s
- Touchdown velocity: 6.17 m/s
</thought>
<design>
{"flight":{"motor":"L1170FJ","wind_ms":0.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.381,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Nose cone","contains":[{"type":"masscomponent","name":"Payload","mass_kg":1.36078,"kind":"masscomponent"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.9144,"outer_d_m":0.15672,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Body tube","contains":[{"type":"parachute","diameter_m":3.048,"deploy_event":"altitude","deploy_altitude_m":213.36,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.0762,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Body tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Avionics","mass_kg":1.36078,"kind":"masscomponent"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}]},{"type":"bodytube","length_m":1.2192,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering Ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering Ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering Ring"},{"type":"innertube","length_m":0.6858,"outer_d_m":0.07924,"wall_thickness_m":0.00152,"material":"Fiberglass","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"L1170FJ"},{"manufacturer":"AeroTech","designation":"L900DM"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"L1040DM"}]},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.381,"tip_chord_m":0.0762,"span_m":0.1524,"sweep_m":0.32682,"thickness_m":0.00317,"material":"Fiberglass","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"L1170FJ"},{"manufacturer":"AeroTech","designation":"L900DM"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"L1040DM"}]}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"L1170FJ"},{"manufacturer":"AeroTech","designation":"L900DM"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"L1040DM"}]}]}
</design>
```
</details>

### V1-026 · MEDIUM
**Prompt:** Design a rocket that goes to apogee in about 8.7 s with a total flight of about 103.4 s.
**Rocket:** `ork/Navya_L1.ork` · **Sim:** Simulation 7 · **Motor:** H143SS
**Why medium: 2 requirements: time to apogee, flight time**
**Targets:** apogee 441.68 m · max velocity 134.2 m/s · time to apogee 8.6821 s · flight time 103.41 s · touchdown 4.6126 m/s · wind 4.4704 m/s
**Parts:** nose cone, 1 body tube, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to apogee in about 8.7 s with a total flight of about 103.4 s.

2. PROPULSION & ASCENT:
- Motor: H143SS
- Simulated apogee: 442 m (1,449 ft)
- Time to apogee: 8.7 s
- Peak velocity: 134 m/s (Mach 0.40)

3. RECOVERY & DESCENT:
- Parachute 1.22 m diameter, deploys at apogee
- Total flight time 103 s; descent from apogee takes 95 s
- Touchdown velocity: 4.61 m/s
</thought>
<design>
{"flight":{"motor":"H143SS","wind_ms":4.4704},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"conical","length_m":0.15748,"wall_thickness_m":0.002,"material":"PLA Plastic","name":"Nose cone w hole in it","contains":[{"type":"masscomponent","name":"altimeter","mass_kg":0.02,"kind":"altimeter"},{"type":"bulkhead","material":"Plywood (birch)","name":"bulkhead (nose cone lid)"},{"type":"masscomponent","name":"weights (dump washers in epoxy and pour??)","mass_kg":0.3,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.8636,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Kraft phenolic","name":"Booster tube","contains":[{"type":"innertube","length_m":0.21844,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Kraft phenolic","name":"Inner Tube"},{"type":"innertube","length_m":0.0127,"outer_d_m":0.038,"wall_thickness_m":0.0,"material":"Masking Tape","name":"diy thrust ring (tape)","motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Birch","name":"Centering ring"},{"type":"parachute","diameter_m":1.2192,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.14732,"tip_chord_m":0.0889,"span_m":0.1016,"sweep_m":0.07566,"thickness_m":0.00635,"material":"Plywood (birch)","name":"Trapezoidal fin set"},{"type":"masscomponent","name":"motor retainer ring","mass_kg":0.0227,"kind":"masscomponent"},{"type":"masscomponent","name":"rail button #1","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"rail button #2","mass_kg":0.0019,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H143SS"}]}]}
</design>
```
</details>

### V1-030 · MEDIUM
**Prompt:** Design a rocket that goes to about 210.8 m/s max velocity at about 132.8 m/s² max acceleration.
**Rocket:** `ork/Parallel booster staging.ork` · **Sim:** Simulation 1 · **Motor:** I115W, E12
**Why medium: 2 requirements: max velocity, max acceleration**
**Targets:** apogee 1120.36 m · max velocity 210.802 m/s · time to apogee 13.049 s · flight time 224.366 s · touchdown 5.53 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 6 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 210.8 m/s max velocity at about 132.8 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: I115W, E12
- Simulated apogee: 1,120 m (3,676 ft)
- Time to apogee: 13.0 s
- Peak velocity: 211 m/s (Mach 0.62)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at ejection
- Total flight time 224 s; descent from apogee takes 211 s
- Touchdown velocity: 5.53 m/s
</thought>
<design>
{"flight":{"motor":"I115W, E12","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.2794,"base_radius_m":0.0287,"wall_thickness_m":0.00229,"material":"Polycarbonate","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.14175,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.8636,"outer_d_m":0.0574,"wall_thickness_m":0.00152,"material":"Paper","name":"Body Tube","contains":[{"type":"pod_set","count":2.0,"name":"Booster Set","contains":[{"type":"nosecone","shape":"conical","length_m":0.04445,"base_radius_m":0.01683,"material":"Balsa","name":"Nose Cone"},{"type":"bodytube","length_m":0.127,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","name":"Booster Body Tube","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0762,"tip_chord_m":0.05,"span_m":0.0508,"sweep_m":0.025,"thickness_m":0.00635,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0762,"tip_chord_m":0.05,"span_m":0.0508,"sweep_m":0.025,"thickness_m":0.00635,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"centeringring","material":"Fiber","name":"Centering Ring"},{"type":"centeringring","material":"Fiber","name":"Centering Ring"},{"type":"innertube","length_m":0.1016,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Booster Motor Tube","contains":[{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"E12"}]}],"motors":[{"manufacturer":"Estes","designation":"E12"}]}]},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.0762,"tip_chord_m":0.05,"span_m":0.0508,"sweep_m":0.025,"thickness_m":0.00635,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","name":"Parachute, 36 in., nylon, 8 lines"},{"type":"railbutton","name":"Rail Button"}],"motors":[{"manufacturer":"AeroTech","designation":"I115W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"I115W"}]}]}
</design>
```
</details>

### V1-031 · MEDIUM
**Prompt:** Design a rocket that goes to about 848 m apogee in about 11.1 s to apogee.
**Rocket:** `ork/Parallel booster staging.ork` · **Sim:** Simulation 2 · **Motor:** I115W
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 848.398 m · max velocity 188.761 m/s · time to apogee 11.149 s · flight time 163.367 s · touchdown 5.739 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 6 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 848 m apogee in about 11.1 s to apogee.

2. PROPULSION & ASCENT:
- Motor: I115W
- Simulated apogee: 848 m (2,783 ft)
- Time to apogee: 11.1 s
- Peak velocity: 189 m/s (Mach 0.56)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at ejection
- Total flight time 163 s; descent from apogee takes 152 s
- Touchdown velocity: 5.74 m/s
</thought>
<design>
{"flight":{"motor":"I115W","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.2794,"base_radius_m":0.0287,"wall_thickness_m":0.00229,"material":"Polycarbonate","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.14175,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.8636,"outer_d_m":0.0574,"wall_thickness_m":0.00152,"material":"Paper","name":"Body Tube","contains":[{"type":"pod_set","count":2.0,"name":"Booster Set","contains":[{"type":"nosecone","shape":"conical","length_m":0.04445,"base_radius_m":0.01683,"material":"Balsa","name":"Nose Cone"},{"type":"bodytube","length_m":0.127,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","name":"Booster Body Tube","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0762,"tip_chord_m":0.05,"span_m":0.0508,"sweep_m":0.025,"thickness_m":0.00635,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0762,"tip_chord_m":0.05,"span_m":0.0508,"sweep_m":0.025,"thickness_m":0.00635,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"centeringring","material":"Fiber","name":"Centering Ring"},{"type":"centeringring","material":"Fiber","name":"Centering Ring"},{"type":"innertube","length_m":0.1016,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Booster Motor Tube","contains":[{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"E12"}]}],"motors":[{"manufacturer":"Estes","designation":"E12"}]}]},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.0762,"tip_chord_m":0.05,"span_m":0.0508,"sweep_m":0.025,"thickness_m":0.00635,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","name":"Parachute, 36 in., nylon, 8 lines"},{"type":"railbutton","name":"Rail Button"}],"motors":[{"manufacturer":"AeroTech","designation":"I115W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"I115W"}]}]}
</design>
```
</details>

### V1-032 · MEDIUM
**Prompt:** Design a rocket that goes through about 63.7 m/s² max acceleration over a 63.7 s flight.
**Rocket:** `ork/Parth_L1.ork` · **Sim:** Simulation 2 · **Motor:** H123
**Why medium: 2 requirements: flight time, max acceleration**
**Targets:** apogee 477.37 m · max velocity 104.25 m/s · time to apogee 9.8087 s · flight time 63.703 s · touchdown 8.9358 m/s · wind 4.4704 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes through about 63.7 m/s² max acceleration over a 63.7 s flight.

2. PROPULSION & ASCENT:
- Motor: H123
- Simulated apogee: 477 m (1,566 ft)
- Time to apogee: 9.8 s
- Peak velocity: 104 m/s (Mach 0.31)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at ejection
- Total flight time 64 s; descent from apogee takes 54 s
- Touchdown velocity: 8.94 m/s
</thought>
<design>
{"flight":{"motor":"H123","wind_ms":4.4704},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.50292,"base_radius_m":0.0508,"wall_thickness_m":0.002,"material":"PLA","name":"Nose cone"},{"type":"bodytube","length_m":0.3,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Body tube","contains":[{"type":"masscomponent","name":"Camera+Avionics","mass_kg":1.1,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.69,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Body tube","contains":[{"type":"innertube","length_m":0.2,"outer_d_m":0.0415,"wall_thickness_m":0.0014,"material":"Kraft Paper","name":"Inner Tube","motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Freeform fin set"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"}]}]}
</design>
```
</details>

### V1-033 · MEDIUM
**Prompt:** Design a rocket that goes to about 100.8 m/s max velocity at about 45.1 m/s² max acceleration.
**Rocket:** `ork/Parth_L1.ork` · **Sim:** Simulation 3 · **Motor:** H123
**Why medium: 2 requirements: max velocity, max acceleration**
**Targets:** apogee 500.41 m · max velocity 100.8 m/s · time to apogee 10.744 s · flight time 74.487 s · touchdown 7.8759 m/s · wind 4.4704 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 100.8 m/s max velocity at about 45.1 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: H123
- Simulated apogee: 500 m (1,642 ft)
- Time to apogee: 10.7 s
- Peak velocity: 101 m/s (Mach 0.30)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at ejection
- Total flight time 74 s; descent from apogee takes 64 s
- Touchdown velocity: 7.88 m/s
</thought>
<design>
{"flight":{"motor":"H123","wind_ms":4.4704},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.50292,"base_radius_m":0.0508,"wall_thickness_m":0.002,"material":"PLA","name":"Nose cone"},{"type":"bodytube","length_m":0.3,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Body tube","contains":[{"type":"masscomponent","name":"Camera+Avionics","mass_kg":1.1,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.69,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Body tube","contains":[{"type":"innertube","length_m":0.2,"outer_d_m":0.0415,"wall_thickness_m":0.0014,"material":"Kraft Paper","name":"Inner Tube","motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Freeform fin set"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"}]}]}
</design>
```
</details>

### V1-037 · MEDIUM
**Prompt:** I need a rocket on a F27 motor that gets up close to 184 m.
**Rocket:** `ork/RocketV1.1.ork` · **Sim:** Simulation 3 · **Motor:** F27
**Why medium: 2 requirements: apogee, motor**
**Targets:** apogee 184.26 m · max velocity 53.438 m/s · time to apogee 6.6712 s · flight time 27.326 s · touchdown 7.6807 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 3 parachutes recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I need a rocket on a F27 motor that gets up close to 184 m.

2. PROPULSION & ASCENT:
- Motor: F27
- Simulated apogee: 184 m (605 ft)
- Time to apogee: 6.7 s
- Peak velocity: 53 m/s (Mach 0.16)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 27 s; descent from apogee takes 21 s
- Touchdown velocity: 7.68 m/s
</thought>
<design>
{"flight":{"motor":"F27","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"conical","length_m":0.13,"base_radius_m":0.03,"wall_thickness_m":0.002,"material":"PLA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.1,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.52,"wall_thickness_m":0.002,"material":"PLA","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.003,"material":"PLA","name":"Freeform fin set"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 1"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 2"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 3"},{"type":"masscomponent","name":"Egg 1","mass_kg":0.06,"kind":"payload"},{"type":"masscomponent","name":"Egg 2","mass_kg":0.06,"kind":"payload"},{"type":"masscomponent","name":"Egg 3","mass_kg":0.06,"kind":"payload"}],"motors":[{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"AeroTech","designation":"F23FJ"},{"manufacturer":"AeroTech","designation":"F39"},{"manufacturer":"Apogee","designation":"F10"},{"manufacturer":"AeroTech","designation":"F42T"},{"manufacturer":"AeroTech","designation":"F40"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F35W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"AeroTech","designation":"F23FJ"},{"manufacturer":"AeroTech","designation":"F39"},{"manufacturer":"Apogee","designation":"F10"},{"manufacturer":"AeroTech","designation":"F42T"},{"manufacturer":"AeroTech","designation":"F40"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F35W"}]}]}
</design>
```
</details>

### V1-038 · MEDIUM
**Prompt:** Make a rocket that hits 245 m and stays up about 42 s.
**Rocket:** `ork/RocketV1.1.ork` · **Sim:** Simulation 4 · **Motor:** F23FJ
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 244.9 m · max velocity 67.116 m/s · time to apogee 6.9838 s · flight time 42.274 s · touchdown 7.0489 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 3 parachutes recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 245 m and stays up about 42 s.

2. PROPULSION & ASCENT:
- Motor: F23FJ
- Simulated apogee: 245 m (803 ft)
- Time to apogee: 7.0 s
- Peak velocity: 67 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 42 s; descent from apogee takes 35 s
- Touchdown velocity: 7.05 m/s
</thought>
<design>
{"flight":{"motor":"F23FJ","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"conical","length_m":0.13,"base_radius_m":0.03,"wall_thickness_m":0.002,"material":"PLA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.1,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.52,"wall_thickness_m":0.002,"material":"PLA","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.003,"material":"PLA","name":"Freeform fin set"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 1"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 2"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute 3"},{"type":"masscomponent","name":"Egg 1","mass_kg":0.06,"kind":"payload"},{"type":"masscomponent","name":"Egg 2","mass_kg":0.06,"kind":"payload"},{"type":"masscomponent","name":"Egg 3","mass_kg":0.06,"kind":"payload"}],"motors":[{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"AeroTech","designation":"F23FJ"},{"manufacturer":"AeroTech","designation":"F39"},{"manufacturer":"Apogee","designation":"F10"},{"manufacturer":"AeroTech","designation":"F42T"},{"manufacturer":"AeroTech","designation":"F40"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F35W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"AeroTech","designation":"F23FJ"},{"manufacturer":"AeroTech","designation":"F39"},{"manufacturer":"Apogee","designation":"F10"},{"manufacturer":"AeroTech","designation":"F42T"},{"manufacturer":"AeroTech","designation":"F40"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F35W"}]}]}
</design>
```
</details>

### V1-039 · MEDIUM
**Prompt:** Design a rocket that goes on a H123 motor to apogee in about 9.4 s.
**Rocket:** `ork/Sainath_L1.ork` · **Sim:** Simulation 9 · **Motor:** H123
**Why medium: 2 requirements: time to apogee, motor**
**Targets:** apogee 480.23 m · max velocity 127.32 m/s · time to apogee 9.3957 s · flight time 51.756 s · touchdown 5.8215 m/s · wind 6.7056 m/s
**Parts:** nose cone, 2 body tubes, 4 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes on a H123 motor to apogee in about 9.4 s.

2. PROPULSION & ASCENT:
- Motor: H123
- Simulated apogee: 480 m (1,576 ft)
- Time to apogee: 9.4 s
- Peak velocity: 127 m/s (Mach 0.38)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at 91 m (300 ft)
- Parachute 0.41 m diameter, deploys at ejection
- Total flight time 52 s; descent from apogee takes 42 s
- Touchdown velocity: 5.82 m/s
</thought>
<design>
{"flight":{"motor":"H123","wind_ms":6.7056},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.254,"base_radius_m":0.0508,"wall_thickness_m":0.002,"material":"PLA","name":"3D Printed Nose cone"},{"type":"bodytube","length_m":0.381,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Upper Body tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead 1"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead 2"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead 3 (epoxyed)"},{"type":"masscomponent","name":"1/4'' Threaded Rod","mass_kg":0.032,"kind":"masscomponent"},{"type":"masscomponent","name":"1/4'' Threaded Rod","mass_kg":0.032,"kind":"masscomponent"},{"type":"masscomponent","name":"Altimeter","mass_kg":0.161,"kind":"altimeter"},{"type":"masscomponent","name":"Eye Hook and bolt for altimeter","mass_kg":0.005,"kind":"recoveryhardware"},{"type":"masscomponent","name":"Camera","mass_kg":0.02835,"kind":"masscomponent"},{"type":"masscomponent","name":"Eye Hook and bolt for the shock chord end 1","mass_kg":0.005,"kind":"recoveryhardware"}]},{"type":"bodytube","length_m":0.4826,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Booster Section tube","contains":[{"type":"innertube","length_m":0.2032,"outer_d_m":0.042,"wall_thickness_m":0.00127,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"masscomponent","name":"Motor retainer","mass_kg":0.025,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"},{"manufacturer":"Cesaroni Technology","designation":"H143SS"},{"manufacturer":"Cesaroni Technology","designation":"H400-Vmax"},{"manufacturer":"Cesaroni Technology","designation":"244H153"},{"manufacturer":"Cesaroni Technology","designation":"H120-14A"},{"manufacturer":"Cesaroni Technology","designation":"H125-Classic"},{"manufacturer":"Cesaroni Technology","designation":"H225-14A"},{"manufacturer":"Cesaroni Technology","designation":"269-H110-WH-14A"},{"manufacturer":"Cesaroni Technology","designation":"H152BS"},{"manufacturer":"Cesaroni Technology","designation":"H565"},{"manufacturer":"Cesaroni Technology","designation":"H100-IM"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.178,"tip_chord_m":0.0508,"span_m":0.127,"sweep_m":0.127,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Trapezoidal fin set"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":91.44,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"parachute","diameter_m":0.4064,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Drogue Chute"},{"type":"launchlug","length_m":0.03,"name":"Rail Buttons"},{"type":"launchlug","length_m":0.03,"name":"Rail Buttons"},{"type":"masscomponent","name":"Eye Hook and bolt for the shock chord end 2","mass_kg":0.005,"kind":"recoveryhardware"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"},{"manufacturer":"Cesaroni Technology","designation":"H143SS"},{"manufacturer":"Cesaroni Technology","designation":"H400-Vmax"},{"manufacturer":"Cesaroni Technology","designation":"244H153"},{"manufacturer":"Cesaroni Technology","designation":"H120-14A"},{"manufacturer":"Cesaroni Technology","designation":"H125-Classic"},{"manufacturer":"Cesaroni Technology","designation":"H225-14A"},{"manufacturer":"Cesaroni Technology","designation":"269-H110-WH-14A"},{"manufacturer":"Cesaroni Technology","designation":"H152BS"},{"manufacturer":"Cesaroni Technology","designation":"H565"},{"manufacturer":"Cesaroni Technology","designation":"H100-IM"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"},{"manufacturer":"Cesaroni Technology","designation":"H143SS"},{"manufacturer":"Cesaroni Technology","designation":"H400-Vmax"},{"manufacturer":"Cesaroni Technology","designation":"244H153"},{"manufacturer":"Cesaroni Technology","designation":"H120-14A"},{"manufacturer":"Cesaroni Technology","designation":"H125-Classic"},{"manufacturer":"Cesaroni Technology","designation":"H225-14A"},{"manufacturer":"Cesaroni Technology","designation":"269-H110-WH-14A"},{"manufacturer":"Cesaroni Technology","designation":"H152BS"},{"manufacturer":"Cesaroni Technology","designation":"H565"},{"manufacturer":"Cesaroni Technology","designation":"H100-IM"}]}]}
</design>
```
</details>

### V1-040 · MEDIUM
**Prompt:** Design a rocket that goes to apogee in about 9.4 s with a total flight of about 53.1 s.
**Rocket:** `ork/Sainath_L1.ork` · **Sim:** Simulation 10 · **Motor:** H143SS
**Why medium: 2 requirements: time to apogee, flight time**
**Targets:** apogee 487.3 m · max velocity 132.8 m/s · time to apogee 9.371 s · flight time 53.134 s · touchdown 5.8259 m/s · wind 6.7056 m/s
**Parts:** nose cone, 2 body tubes, 4 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to apogee in about 9.4 s with a total flight of about 53.1 s.

2. PROPULSION & ASCENT:
- Motor: H143SS
- Simulated apogee: 487 m (1,599 ft)
- Time to apogee: 9.4 s
- Peak velocity: 133 m/s (Mach 0.40)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at 91 m (300 ft)
- Parachute 0.41 m diameter, deploys at ejection
- Total flight time 53 s; descent from apogee takes 44 s
- Touchdown velocity: 5.83 m/s
</thought>
<design>
{"flight":{"motor":"H143SS","wind_ms":6.7056},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.254,"base_radius_m":0.0508,"wall_thickness_m":0.002,"material":"PLA","name":"3D Printed Nose cone"},{"type":"bodytube","length_m":0.381,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Upper Body tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead 1"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead 2"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead 3 (epoxyed)"},{"type":"masscomponent","name":"1/4'' Threaded Rod","mass_kg":0.032,"kind":"masscomponent"},{"type":"masscomponent","name":"1/4'' Threaded Rod","mass_kg":0.032,"kind":"masscomponent"},{"type":"masscomponent","name":"Altimeter","mass_kg":0.161,"kind":"altimeter"},{"type":"masscomponent","name":"Eye Hook and bolt for altimeter","mass_kg":0.005,"kind":"recoveryhardware"},{"type":"masscomponent","name":"Camera","mass_kg":0.02835,"kind":"masscomponent"},{"type":"masscomponent","name":"Eye Hook and bolt for the shock chord end 1","mass_kg":0.005,"kind":"recoveryhardware"}]},{"type":"bodytube","length_m":0.4826,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Kraft Paper","name":"Booster Section tube","contains":[{"type":"innertube","length_m":0.2032,"outer_d_m":0.042,"wall_thickness_m":0.00127,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"masscomponent","name":"Motor retainer","mass_kg":0.025,"kind":"masscomponent"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"},{"manufacturer":"Cesaroni Technology","designation":"H143SS"},{"manufacturer":"Cesaroni Technology","designation":"H400-Vmax"},{"manufacturer":"Cesaroni Technology","designation":"244H153"},{"manufacturer":"Cesaroni Technology","designation":"H120-14A"},{"manufacturer":"Cesaroni Technology","designation":"H125-Classic"},{"manufacturer":"Cesaroni Technology","designation":"H225-14A"},{"manufacturer":"Cesaroni Technology","designation":"269-H110-WH-14A"},{"manufacturer":"Cesaroni Technology","designation":"H152BS"},{"manufacturer":"Cesaroni Technology","designation":"H565"},{"manufacturer":"Cesaroni Technology","designation":"H100-IM"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.178,"tip_chord_m":0.0508,"span_m":0.127,"sweep_m":0.127,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Trapezoidal fin set"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"altitude","deploy_altitude_m":91.44,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"parachute","diameter_m":0.4064,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Drogue Chute"},{"type":"launchlug","length_m":0.03,"name":"Rail Buttons"},{"type":"launchlug","length_m":0.03,"name":"Rail Buttons"},{"type":"masscomponent","name":"Eye Hook and bolt for the shock chord end 2","mass_kg":0.005,"kind":"recoveryhardware"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"},{"manufacturer":"Cesaroni Technology","designation":"H143SS"},{"manufacturer":"Cesaroni Technology","designation":"H400-Vmax"},{"manufacturer":"Cesaroni Technology","designation":"244H153"},{"manufacturer":"Cesaroni Technology","designation":"H120-14A"},{"manufacturer":"Cesaroni Technology","designation":"H125-Classic"},{"manufacturer":"Cesaroni Technology","designation":"H225-14A"},{"manufacturer":"Cesaroni Technology","designation":"269-H110-WH-14A"},{"manufacturer":"Cesaroni Technology","designation":"H152BS"},{"manufacturer":"Cesaroni Technology","designation":"H565"},{"manufacturer":"Cesaroni Technology","designation":"H100-IM"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"H123"},{"manufacturer":"Cesaroni Technology","designation":"H143SS"},{"manufacturer":"Cesaroni Technology","designation":"H400-Vmax"},{"manufacturer":"Cesaroni Technology","designation":"244H153"},{"manufacturer":"Cesaroni Technology","designation":"H120-14A"},{"manufacturer":"Cesaroni Technology","designation":"H125-Classic"},{"manufacturer":"Cesaroni Technology","designation":"H225-14A"},{"manufacturer":"Cesaroni Technology","designation":"269-H110-WH-14A"},{"manufacturer":"Cesaroni Technology","designation":"H152BS"},{"manufacturer":"Cesaroni Technology","designation":"H565"},{"manufacturer":"Cesaroni Technology","designation":"H100-IM"}]}]}
</design>
```
</details>

### V1-043 · MEDIUM
**Prompt:** Give me a rocket that tops out near 1,723 m and lands under 6.2 m/s.
**Rocket:** `ork/Scale_model_Nasa.ork` · **Sim:** Simulation 4 · **Motor:** H55W
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 1723 m · max velocity 209.58 m/s · time to apogee 18.651 s · flight time 97.32 s · touchdown 6.1843 m/s · wind 0 m/s
**Parts:** nose cone, 3 body tubes, 4 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Give me a rocket that tops out near 1,723 m and lands under 6.2 m/s.

2. PROPULSION & ASCENT:
- Motor: H55W
- Simulated apogee: 1,723 m (5,653 ft)
- Time to apogee: 18.7 s
- Peak velocity: 210 m/s (Mach 0.62)

3. RECOVERY & DESCENT:
- Parachute 0.71 m diameter, deploys at 213 m (700 ft)
- Parachute 0.41 m diameter, deploys at apogee
- Total flight time 97 s; descent from apogee takes 79 s
- Touchdown velocity: 6.18 m/s
</thought>
<design>
{"flight":{"motor":"H55W","wind_ms":0.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1905,"wall_thickness_m":0.00097,"material":"Fiberglass","name":"Nose cone","contains":[{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.15642,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.4446,"outer_d_m":0.0762,"wall_thickness_m":0.00105,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.7112,"deploy_event":"altitude","deploy_altitude_m":213.36,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.03705,"wall_thickness_m":0.00105,"material":"Cardboard","name":"Body tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.5928,"wall_thickness_m":0.00105,"material":"Cardboard","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.1905,"tip_chord_m":0.03705,"span_m":0.0635,"sweep_m":0.15891,"thickness_m":0.00146,"material":"Plywood (birch)","name":"Trapezoidal fin set"},{"type":"innertube","length_m":0.2032,"outer_d_m":0.03132,"wall_thickness_m":0.00104,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"H55W"},{"manufacturer":"AeroTech","designation":"G80NBT"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"parachute","diameter_m":0.4064,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"H55W"},{"manufacturer":"AeroTech","designation":"G80NBT"}]}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"H55W"},{"manufacturer":"AeroTech","designation":"G80NBT"}]}]}
</design>
```
</details>

### V1-044 · MEDIUM
**Prompt:** Design a rocket that goes to about 289 m apogee in about 8.1 s to apogee.
**Rocket:** `ork/Scale_model_Nasa.ork` · **Sim:** Simulation 6 · **Motor:** G80NBT
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 288.53 m · max velocity 73.777 m/s · time to apogee 8.0525 s · flight time 42.422 s · touchdown 7.2839 m/s · wind 6.7056 m/s
**Parts:** nose cone, 3 body tubes, 4 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 289 m apogee in about 8.1 s to apogee.

2. PROPULSION & ASCENT:
- Motor: G80NBT
- Simulated apogee: 289 m (947 ft)
- Time to apogee: 8.1 s
- Peak velocity: 74 m/s (Mach 0.22)

3. RECOVERY & DESCENT:
- Parachute 0.71 m diameter, deploys at 213 m (700 ft)
- Parachute 0.41 m diameter, deploys at apogee
- Total flight time 42 s; descent from apogee takes 34 s
- Touchdown velocity: 7.28 m/s
</thought>
<design>
{"flight":{"motor":"G80NBT","wind_ms":6.7056},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1905,"wall_thickness_m":0.00097,"material":"Fiberglass","name":"Nose cone","contains":[{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.15642,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.4446,"outer_d_m":0.0762,"wall_thickness_m":0.00105,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.7112,"deploy_event":"altitude","deploy_altitude_m":213.36,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.03705,"wall_thickness_m":0.00105,"material":"Cardboard","name":"Body tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.5928,"wall_thickness_m":0.00105,"material":"Cardboard","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.1905,"tip_chord_m":0.03705,"span_m":0.0635,"sweep_m":0.15891,"thickness_m":0.00146,"material":"Plywood (birch)","name":"Trapezoidal fin set"},{"type":"innertube","length_m":0.2032,"outer_d_m":0.03132,"wall_thickness_m":0.00104,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"H55W"},{"manufacturer":"AeroTech","designation":"G80NBT"}]},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"parachute","diameter_m":0.4064,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"H55W"},{"manufacturer":"AeroTech","designation":"G80NBT"}]}],"motors":[{"manufacturer":"AeroTech","designation":"L1420R"},{"manufacturer":"AeroTech","designation":"M685W-PS"},{"manufacturer":"AeroTech","designation":"L1390G"},{"manufacturer":"AeroTech","designation":"H55W"},{"manufacturer":"AeroTech","designation":"G80NBT"}]}]}
</design>
```
</details>

### V1-045 · MEDIUM
**Prompt:** Design a rocket that goes to about 751 m apogee in about 10.1 s to apogee.
**Rocket:** `ork/SimpleL1.ork` · **Sim:** Simulation 1 · **Motor:** HP-H195NT
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 751.348 m · max velocity 233.444 m/s · time to apogee 10.087 s · flight time 167.682 s · touchdown 5.075 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 751 m apogee in about 10.1 s to apogee.

2. PROPULSION & ASCENT:
- Motor: HP-H195NT
- Simulated apogee: 751 m (2,465 ft)
- Time to apogee: 10.1 s
- Peak velocity: 233 m/s (Mach 0.69)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at ejection
- Total flight time 168 s; descent from apogee takes 158 s
- Touchdown velocity: 5.08 m/s
</thought>
<design>
{"flight":{"motor":"HP-H195NT","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":0.138,"base_radius_m":0.03937,"wall_thickness_m":0.00196,"material":"Polypropylene","name":"Nose Cone"},{"type":"bodytube","length_m":0.9144,"outer_d_m":0.07874,"wall_thickness_m":0.00127,"material":"Paper","preset":"LOC/Precision BT-3.00","name":"Body Tube","contains":[{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.1,"kind":"masscomponent"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.08,"tip_chord_m":0.06,"span_m":0.075,"sweep_m":0.07,"thickness_m":0.00317,"material":"Birch","name":"Trapezoidal Fin Set"},{"type":"innertube","length_m":0.2032,"outer_d_m":0.03236,"wall_thickness_m":0.00157,"material":"Vulcanized Fiber","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"HP-H195NT"},{"manufacturer":"AeroTech","designation":"H169WS-13"}]}],"motors":[{"manufacturer":"AeroTech","designation":"HP-H195NT"},{"manufacturer":"AeroTech","designation":"H169WS-13"}]}],"motors":[{"manufacturer":"AeroTech","designation":"HP-H195NT"},{"manufacturer":"AeroTech","designation":"H169WS-13"}]}]}
</design>
```
</details>

### V1-046 · MEDIUM
**Prompt:** Design a rocket that goes to about 754 m apogee in about 10.2 s to apogee.
**Rocket:** `ork/SimpleL1.ork` · **Sim:** Simulation 2 · **Motor:** H169WS-13
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 753.601 m · max velocity 216.734 m/s · time to apogee 10.196 s · flight time 167.872 s · touchdown 5.129 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 754 m apogee in about 10.2 s to apogee.

2. PROPULSION & ASCENT:
- Motor: H169WS-13
- Simulated apogee: 754 m (2,472 ft)
- Time to apogee: 10.2 s
- Peak velocity: 217 m/s (Mach 0.64)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at ejection
- Total flight time 168 s; descent from apogee takes 158 s
- Touchdown velocity: 5.13 m/s
</thought>
<design>
{"flight":{"motor":"H169WS-13","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":0.138,"base_radius_m":0.03937,"wall_thickness_m":0.00196,"material":"Polypropylene","name":"Nose Cone"},{"type":"bodytube","length_m":0.9144,"outer_d_m":0.07874,"wall_thickness_m":0.00127,"material":"Paper","preset":"LOC/Precision BT-3.00","name":"Body Tube","contains":[{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"centeringring","material":"Birch","name":"Centering Ring"},{"type":"parachute","diameter_m":0.9144,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"masscomponent","name":"Mass Component","mass_kg":0.1,"kind":"masscomponent"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.08,"tip_chord_m":0.06,"span_m":0.075,"sweep_m":0.07,"thickness_m":0.00317,"material":"Birch","name":"Trapezoidal Fin Set"},{"type":"innertube","length_m":0.2032,"outer_d_m":0.03236,"wall_thickness_m":0.00157,"material":"Vulcanized Fiber","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"HP-H195NT"},{"manufacturer":"AeroTech","designation":"H169WS-13"}]}],"motors":[{"manufacturer":"AeroTech","designation":"HP-H195NT"},{"manufacturer":"AeroTech","designation":"H169WS-13"}]}],"motors":[{"manufacturer":"AeroTech","designation":"HP-H195NT"},{"manufacturer":"AeroTech","designation":"H169WS-13"}]}]}
</design>
```
</details>

### V1-047 · MEDIUM
**Prompt:** Design a rocket that goes to about 1110.1 m/s max velocity at about 354.8 m/s² max acceleration.
**Rocket:** `ork/Skyshot.ork` · **Sim:** Simulation 5 · **Motor:** O5500X-PS
**Why medium: 2 requirements: max velocity, max acceleration**
**Targets:** apogee 16660 m · max velocity 1110.14 m/s · time to apogee 49.617 s · flight time 906.205 s · touchdown 6.979 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 4 fins, 1 stage, 2 parachutes recovery
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 1110.1 m/s max velocity at about 354.8 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: O5500X-PS
- Simulated apogee: 16,660 m (54,659 ft)
- Time to apogee: 49.6 s
- Peak velocity: 1110 m/s (Mach 3.36)

3. RECOVERY & DESCENT:
- Parachute 1.22 m diameter, deploys at 457 m (1500 ft)
- Parachute 0.76 m diameter, deploys at apogee
- Total flight time 906 s; descent from apogee takes 857 s
- Touchdown velocity: 6.98 m/s
</thought>
<design>
{"flight":{"motor":"O5500X-PS","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.5,"base_radius_m":0.051,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Nose Cone","contains":[{"type":"parachute","diameter_m":1.2192,"deploy_event":"altitude","deploy_altitude_m":457.20000000000005,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-048-S","name":"Iris Ultra Compact Parachute [Cd 2.2 (4.3 oz) 26.0 in^3]"}]},{"type":"bodytube","length_m":0.15,"outer_d_m":0.102,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Body Tube"},{"type":"bodytube","length_m":0.1,"outer_d_m":0.102,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Body Tube"},{"type":"bodytube","length_m":1.9,"outer_d_m":0.102,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Body Tube","contains":[{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.3,"tip_chord_m":0.075,"span_m":0.11,"sweep_m":0.2,"thickness_m":0.006,"material":"Fiberglass","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":0.762,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","preset":"Fruity Chutes IFC-030-S","name":"Iris Ultra Compact Parachute [Cd 2.2 (1.88 oz) 10.5 in^3]"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"21062O3400-P"},{"manufacturer":"Cesaroni Technology","designation":"20146N5800-P"},{"manufacturer":"AeroTech","designation":"O5500X-PS"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"21062O3400-P"},{"manufacturer":"Cesaroni Technology","designation":"20146N5800-P"},{"manufacturer":"AeroTech","designation":"O5500X-PS"}]}]}
</design>
```
</details>

### V1-049 · MEDIUM
**Prompt:** Design a rocket that goes to about 19 m apogee with a total flight time of about 6.0 s.
**Rocket:** `ork/TestLaunch_Fall2022.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 19.427 m · max velocity 16.067 m/s · time to apogee 2.2919 s · flight time 5.9528 s · touchdown 5.2708 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 19 m apogee with a total flight time of about 6.0 s.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 19 m (64 ft)
- Time to apogee: 2.3 s
- Peak velocity: 16 m/s (Mach 0.05)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 6 s; descent from apogee takes 4 s
- Touchdown velocity: 5.27 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06858,"base_radius_m":0.0127,"wall_thickness_m":0.00102,"material":"PVC","name":"Nose cone"},{"type":"bodytube","length_m":0.2032,"outer_d_m":0.0254,"wall_thickness_m":0.00038,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.0762,"wall_thickness_m":0.00038,"material":"PVC","name":"Engine Mount","contains":[{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00317,"material":"Fiberglass","name":"Freeform fin set"}],"motors":[{"manufacturer":"Estes","designation":"A8"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"}]}]}
</design>
```
</details>

### V1-050 · MEDIUM
**Prompt:** Design a rocket that goes to about 318 m apogee, hitting about Mach 0.36 and 180.4 m/s² max acceleration.
**Rocket:** `ork/TheBoringRocket.ork` · **Sim:** Simulation 1 · **Motor:** E30
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 317.7 m · max velocity 120.78 m/s · time to apogee 6.0876 s · flight time 46.594 s · touchdown 7.9701 m/s · wind 6 m/s
**Parts:** nose cone, 1 body tube, 4 fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 318 m apogee, hitting about Mach 0.36 and 180.4 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: E30
- Simulated apogee: 318 m (1,042 ft)
- Time to apogee: 6.1 s
- Peak velocity: 121 m/s (Mach 0.36)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 47 s; descent from apogee takes 41 s
- Touchdown velocity: 7.97 m/s
</thought>
<design>
{"flight":{"motor":"E30","wind_ms":6.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.15,"base_radius_m":0.0325,"wall_thickness_m":0.0008,"material":"PLA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.06,"kind":"masscomponent"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.008,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.5,"wall_thickness_m":0.0008,"material":"PLA","name":"Body tube","contains":[{"type":"tubefin","fin_count":4.0,"thickness_m":0.0008,"material":"PLA","name":"Tube fin set"},{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":4.0,"material":"Rip stop nylon","preset":"Public Missiles PML Xform","name":"Parachute"}],"motors":[{"manufacturer":"AeroTech","designation":"E30"}]}],"motors":[{"manufacturer":"AeroTech","designation":"E30"}]}]}
</design>
```
</details>

### V1-051 · MEDIUM
**Prompt:** Design a rocket that goes to about 245 m apogee, hitting about 118.0 m/s² max acceleration.
**Rocket:** `ork/Three-stage rocket.ork` · **Sim:** Simulation 1 · **Motor:** A8, B6
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 245.06 m · max velocity 78.63 m/s · time to apogee 5.9729 s · flight time 64.973 s · touchdown 4.3358 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 2 fins, 3 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 245 m apogee, hitting about 118.0 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: A8, B6
- Simulated apogee: 245 m (804 ft)
- Time to apogee: 6.0 s
- Peak velocity: 79 m/s (Mach 0.23)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 65 s; descent from apogee takes 59 s
- Touchdown velocity: 4.34 m/s
</thought>
<design>
{"flight":{"motor":"A8, B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1,"base_radius_m":0.0125,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose cone"},{"type":"bodytube","length_m":0.3,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube","contains":[{"type":"trapezoidfin","root_chord_m":0.05,"tip_chord_m":0.05,"span_m":0.03,"sweep_m":0.025,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal fin set"},{"type":"innertube","length_m":0.075,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"masscomponent","name":"Wadding","mass_kg":0.002,"kind":"masscomponent"},{"type":"launchlug","length_m":0.035,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.08,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"freeformfinset","thickness_m":0.002,"material":"Cardboard","name":"Freeform fin set"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.08,"outer_d_m":0.05,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"trapezoidfin","root_chord_m":0.08,"tip_chord_m":0.03,"span_m":0.04,"sweep_m":0.025,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.035,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-053 · MEDIUM
**Prompt:** Design a rocket that goes about 995 m and is back down in under 50 seconds.
**Rocket:** `ork/TrinetraOne.ork` · **Sim:** Simulation 1 · **Motor:** HP-I65W
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 995.064 m · max velocity 104.097 m/s · time to apogee 16.651 s · flight time 49.772 s · touchdown 31.334 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, transition, 3 fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes about 995 m and is back down in under 50 seconds.

2. PROPULSION & ASCENT:
- Motor: HP-I65W
- Simulated apogee: 995 m (3,265 ft)
- Time to apogee: 16.7 s
- Peak velocity: 104 m/s (Mach 0.31)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 50 s; descent from apogee takes 33 s
- Touchdown velocity: 31.33 m/s
</thought>
<design>
{"flight":{"motor":"HP-I65W","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.3048,"base_radius_m":0.0381,"wall_thickness_m":0.00127,"material":"Fiberglass","name":"Nose Cone"},{"type":"bodytube","length_m":0.2032,"outer_d_m":0.0762,"wall_thickness_m":0.00127,"material":"Blue tube","name":"Payload Tube","contains":[{"type":"masscomponent","name":"Payload","mass_kg":2.26796,"kind":"payload"}]},{"type":"transition","shape":"conical","length_m":0.075,"fore_d_m":0.0762,"aft_d_m":0.0574,"material":"Fiberglass","name":"Transition","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.254,"outer_d_m":0.0574,"wall_thickness_m":0.00127,"material":"Blue tube","name":"Parachute Tube","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Bulkhead"},{"type":"parachute","diameter_m":0.3,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.381,"outer_d_m":0.0574,"wall_thickness_m":0.00127,"material":"Blue tube","name":"Booster Tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.0574,"tip_chord_m":0.032,"span_m":0.03048,"sweep_m":0.0254,"thickness_m":0.003,"material":"Fiberglass","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"AeroTech","designation":"HP-I65W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"HP-I65W"}]}]}
</design>
```
</details>

### V1-055 · MEDIUM
**Prompt:** Make a rocket that hits 238 m and stays up about 19 s.
**Rocket:** `ork/Tube Fin.ork` · **Sim:** Simulation 1 · **Motor:** D12
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 237.55 m · max velocity 99.4 m/s · time to apogee 5.7534 s · flight time 18.7 s · touchdown 22.901 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 6 fins, 1 stage, 1 streamer recovery
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 238 m and stays up about 19 s.

2. PROPULSION & ASCENT:
- Motor: D12
- Simulated apogee: 238 m (779 ft)
- Time to apogee: 5.8 s
- Peak velocity: 99 m/s (Mach 0.29)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 19 s; descent from apogee takes 13 s
- Touchdown velocity: 22.90 m/s
</thought>
<design>
{"flight":{"motor":"D12","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.15,"wall_thickness_m":0.002,"material":"Cardboard","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Spiral-Wound Paper/Glassine","preset":"FlisKits BT-50-18","name":"Body tube","contains":[{"type":"tubefin","fin_count":6.0,"thickness_m":0.002,"material":"Cardboard","name":"Tube fin set"},{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.05,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"}],"motors":[{"manufacturer":"Estes","designation":"D12"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"}]}]}
</design>
```
</details>

### V1-056 · MEDIUM
**Prompt:** Design a rocket that goes about 676 m and is back down in under 64 seconds.
**Rocket:** `ork/Two stage high power rocket.ork` · **Sim:** Simulation 1 · **Motor:** H148R
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 675.97 m · max velocity 158.916 m/s · time to apogee 11.049 s · flight time 64.412 s · touchdown 6.204 m/s · wind 1.99827 m/s
**Parts:** nose cone, 8 body tubes, 6 fins, 2 stages, 3 parachutes recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes about 676 m and is back down in under 64 seconds.

2. PROPULSION & ASCENT:
- Motor: H148R
- Simulated apogee: 676 m (2,218 ft)
- Time to apogee: 11.0 s
- Peak velocity: 159 m/s (Mach 0.47)

3. RECOVERY & DESCENT:
- Parachute 0.91 m diameter, deploys at ejection
- Parachute 0.30 m diameter, deploys at ejection
- Parachute 0.61 m diameter, deploys at ejection
- Total flight time 64 s; descent from apogee takes 53 s
- Touchdown velocity: 6.20 m/s
</thought>
<design>
{"flight":{"motor":"H148R","wind_ms":1.9982688},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.32385,"base_radius_m":0.0508,"wall_thickness_m":0.00152,"material":"Polypropylene","name":"Nose Cone"},{"type":"bodytube","length_m":0.0762,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Payload Bay"},{"type":"bodytube","length_m":0.4318,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Sustainer Forward Airframe","contains":[{"type":"parachute","diameter_m":0.9144,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":10.0,"material":"Nylon fabric","name":"Sustainer Main"}]},{"type":"bodytube","length_m":0.0254,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Sustainer Switch Band","contains":[{"type":"railbutton","name":"Rail Button"}]},{"type":"bodytube","length_m":0.381,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Sustainer Aft Airframe","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Nylon fabric","name":"Sustainer Drogue"}]},{"type":"bodytube","length_m":0.1778,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Sustainer Fin Section","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.14605,"tip_chord_m":0.0762,"span_m":0.1524,"sweep_m":0.0381,"thickness_m":0.00317,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"},{"type":"innertube","length_m":0.15875,"outer_d_m":0.07874,"wall_thickness_m":0.00127,"material":"Paper","name":"Inner Tube","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.15875,"outer_d_m":0.04128,"wall_thickness_m":0.00133,"material":"Paper","name":"Sustainer Motor Mount","motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I59WN"}]}]},{"type":"centeringring","material":"Plywood","name":"Centering Ring"}],"motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I59WN"}]}],"motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I59WN"}]},{"type":"stage_marker","name":"Booster","contains":[{"type":"bodytube","length_m":0.0762,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Interstage","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.0508,"outer_d_m":0.07874,"wall_thickness_m":0.00127,"material":"Paper","name":"Inner Tube"},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"railbutton","name":"Rail Button"}]},{"type":"bodytube","length_m":0.381,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Booster airframe","contains":[{"type":"parachute","diameter_m":0.6096,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Nylon fabric","name":"Booster Chute"}]},{"type":"bodytube","length_m":0.1778,"outer_d_m":0.1016,"wall_thickness_m":0.00127,"material":"Paper","name":"Booster fin section","contains":[{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"innertube","length_m":0.15875,"outer_d_m":0.04128,"wall_thickness_m":0.00133,"material":"Paper","name":"Booster motor mount","motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I357T"}]},{"type":"centeringring","material":"Plywood","name":"Centering Ring"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.14605,"tip_chord_m":0.0762,"span_m":0.1651,"sweep_m":0.0381,"thickness_m":0.003,"material":"Plywood (birch)","name":"Trapezoidal Fin Set"}],"motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I357T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"H148R"},{"manufacturer":"AeroTech","designation":"I357T"}]}]}
</design>
```
</details>

### V1-058 · MEDIUM
**Prompt:** Design a rocket that goes to about 50 m apogee, hitting about 142.1 m/s² max acceleration.
**Rocket:** `ork/base_23.09.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 50.381 m · max velocity 29.212 m/s · time to apogee 3.447 s · flight time 15.882 s · touchdown 3.952 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 50 m apogee, hitting about 142.1 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 50 m (165 ft)
- Time to apogee: 3.4 s
- Peak velocity: 29 m/s (Mach 0.09)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 16 s; descent from apogee takes 12 s
- Touchdown velocity: 3.95 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1,"base_radius_m":0.0124,"wall_thickness_m":0.002,"material":"PLA - 100% infill","name":"Nose cone","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.012,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.3,"outer_d_m":0.0248,"wall_thickness_m":0.00035,"material":"Cardboard","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00317,"material":"Balsa","name":"Freeform fin set"},{"type":"innertube","length_m":0.075,"outer_d_m":0.0187,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"masscomponent","name":"Wadding","mass_kg":0.0012,"kind":"masscomponent"},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-059 · MEDIUM
**Prompt:** Design a rocket that goes through about 229.6 m/s² max acceleration over a 308.7 s flight.
**Rocket:** `ork/baseline_rocket.ork` · **Sim:** Simulation 2 · **Motor:** H128W
**Why medium: 2 requirements: flight time, max acceleration**
**Targets:** apogee 637.081 m · max velocity 189.325 m/s · time to apogee 9.743 s · flight time 308.714 s · touchdown 2.718 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 4 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes through about 229.6 m/s² max acceleration over a 308.7 s flight.

2. PROPULSION & ASCENT:
- Motor: H128W
- Simulated apogee: 637 m (2,090 ft)
- Time to apogee: 9.7 s
- Peak velocity: 189 m/s (Mach 0.56)

3. RECOVERY & DESCENT:
- Parachute 1.83 m diameter, deploys at apogee
- Total flight time 309 s; descent from apogee takes 299 s
- Touchdown velocity: 2.72 m/s
</thought>
<design>
{"flight":{"motor":"H128W","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.3,"base_radius_m":0.0375,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Nose Cone"},{"type":"bodytube","length_m":1.0,"outer_d_m":0.075,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"innertube","length_m":0.2,"outer_d_m":0.03086,"wall_thickness_m":0.00095,"material":"Paper","name":"Inner Tube","motors":[{"manufacturer":"AeroTech","designation":"H128W"}]},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.044,"tip_chord_m":0.05,"span_m":0.045,"sweep_m":0.0,"thickness_m":0.003,"material":"Balsa","name":"Trapezoidal Fin Set"},{"type":"parachute","diameter_m":1.8288,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":4.0,"material":"Ripstop nylon","preset":"Rocketman LS-06","name":"Light Std Parabolic Parachute [Cd .97 (3.4 oz) 12.70 in^3]"}],"motors":[{"manufacturer":"AeroTech","designation":"H128W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"H128W"}]}]}
</design>
```
</details>

### V1-062 · MEDIUM
**Prompt:** Design a rocket that goes to about 2,626 m apogee, hitting about 207.0 m/s² max acceleration.
**Rocket:** `ork/endurance.ork` · **Sim:** Simulation 11 · **Motor:** M6000ST
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 2626.5 m · max velocity 272.56 m/s · time to apogee 22.261 s · flight time 188.72 s · touchdown 6.3675 m/s · wind 4.4704 m/s
**Parts:** nose cone, 3 body tubes, 3 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 2,626 m apogee, hitting about 207.0 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: M6000ST
- Simulated apogee: 2,626 m (8,617 ft)
- Time to apogee: 22.3 s
- Peak velocity: 273 m/s (Mach 0.80)

3. RECOVERY & DESCENT:
- Parachute 1.27 m diameter, deploys at apogee
- Parachute 2.44 m diameter, deploys at 213 m (700 ft)
- Total flight time 189 s; descent from apogee takes 166 s
- Touchdown velocity: 6.37 m/s
</thought>
<design>
{"flight":{"motor":"M6000ST","wind_ms":4.4704},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.9144,"base_radius_m":0.07836,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Nose cone","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Lower Bulkhead"},{"type":"bulkhead","material":"PLA","name":"Upper Bulkhead"},{"type":"masscomponent","name":"Metal Tip","mass_kg":0.03317,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Ballast","mass_kg":4.53592,"kind":"masscomponent"}]},{"type":"bodytube","length_m":1.016,"wall_thickness_m":0.0023,"material":"Fiberglass","name":"Mid-airframe 5'","contains":[{"type":"parachute","diameter_m":1.27,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":3.0,"material":"Ripstop nylon","name":"Drogue"},{"type":"parachute","diameter_m":2.4384,"deploy_event":"altitude","deploy_altitude_m":213.36,"deploy_delay_s":0.0,"line_count":14.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Quick Links + TD + Misc.","mass_kg":0.90718,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.0508,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Switchband"},{"type":"bodytube","length_m":0.9144,"wall_thickness_m":0.00254,"material":"Fiberglass","name":"Booster Tube","contains":[{"type":"centeringring","material":"Aluminum","name":"Bottom Centering ring"},{"type":"masscomponent","name":"Fin Can?","mass_kg":1.36078,"kind":"masscomponent"},{"type":"masscomponent","name":"N Casing + Motor Adapter","mass_kg":2.26796,"kind":"masscomponent"},{"type":"masscomponent","name":"Thrust Plate and Retainer","mass_kg":0.492,"kind":"masscomponent"},{"type":"innertube","length_m":0.7493,"outer_d_m":0.0983,"wall_thickness_m":0.00015,"material":"Aluminum","name":"Inner Tube"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.2794,"tip_chord_m":0.127,"span_m":0.15875,"sweep_m":0.127,"thickness_m":0.00635,"material":"Fiberglass","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"N2000W"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"M6000ST"}]}],"motors":[{"manufacturer":"AeroTech","designation":"N2000W"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"M6000ST"}]}]}
</design>
```
</details>

### V1-064 · MEDIUM
**Prompt:** I want a rocket that climbs about 2,473 m and comes down gently, under 7.5 m/s.
**Rocket:** `ork/endurance.ork` · **Sim:** Trajectory · **Motor:** M6000ST
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 2473.3 m · max velocity 267.04 m/s · time to apogee 21.711 s · flight time 173.43 s · touchdown 7.4987 m/s · wind 4.4704 m/s
**Parts:** nose cone, 3 body tubes, 3 fins, 1 stage, 2 parachutes recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I want a rocket that climbs about 2,473 m and comes down gently, under 7.5 m/s.

2. PROPULSION & ASCENT:
- Motor: M6000ST
- Simulated apogee: 2,473 m (8,115 ft)
- Time to apogee: 21.7 s
- Peak velocity: 267 m/s (Mach 0.79)

3. RECOVERY & DESCENT:
- Parachute 1.27 m diameter, deploys at apogee
- Parachute 2.44 m diameter, deploys at 213 m (700 ft)
- Total flight time 173 s; descent from apogee takes 152 s
- Touchdown velocity: 7.50 m/s
</thought>
<design>
{"flight":{"motor":"M6000ST","wind_ms":4.4704},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.9144,"base_radius_m":0.07836,"wall_thickness_m":0.00216,"material":"Fiberglass","name":"Nose cone","contains":[{"type":"bulkhead","material":"Plywood (birch)","name":"Lower Bulkhead"},{"type":"bulkhead","material":"PLA","name":"Upper Bulkhead"},{"type":"masscomponent","name":"Metal Tip","mass_kg":0.03317,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Threaded Rod","mass_kg":0.0,"kind":"masscomponent"},{"type":"masscomponent","name":"Ballast","mass_kg":4.53592,"kind":"masscomponent"}]},{"type":"bodytube","length_m":1.016,"wall_thickness_m":0.0023,"material":"Fiberglass","name":"Mid-airframe 5'","contains":[{"type":"parachute","diameter_m":1.27,"deploy_event":"apogee","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":3.0,"material":"Ripstop nylon","name":"Drogue"},{"type":"parachute","diameter_m":2.4384,"deploy_event":"altitude","deploy_altitude_m":213.36,"deploy_delay_s":0.0,"line_count":14.0,"material":"Ripstop nylon","name":"Main Parachute"},{"type":"bulkhead","material":"Cardboard","name":"Bulkhead"},{"type":"masscomponent","name":"Quick Links + TD + Misc.","mass_kg":0.90718,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.0508,"wall_thickness_m":0.002,"material":"Fiberglass","name":"Switchband"},{"type":"bodytube","length_m":0.9144,"wall_thickness_m":0.00254,"material":"Fiberglass","name":"Booster Tube","contains":[{"type":"centeringring","material":"Aluminum","name":"Bottom Centering ring"},{"type":"masscomponent","name":"Fin Can?","mass_kg":1.36078,"kind":"masscomponent"},{"type":"masscomponent","name":"N Casing + Motor Adapter","mass_kg":2.26796,"kind":"masscomponent"},{"type":"masscomponent","name":"Thrust Plate and Retainer","mass_kg":0.492,"kind":"masscomponent"},{"type":"innertube","length_m":0.7493,"outer_d_m":0.0983,"wall_thickness_m":0.00015,"material":"Aluminum","name":"Inner Tube"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.2794,"tip_chord_m":0.127,"span_m":0.15875,"sweep_m":0.127,"thickness_m":0.00635,"material":"Fiberglass","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"N2000W"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"M6000ST"}]}],"motors":[{"manufacturer":"AeroTech","designation":"N2000W"},{"manufacturer":"AeroTech","designation":"L2200G"},{"manufacturer":"AeroTech","designation":"M6000ST"}]}]}
</design>
```
</details>

### V1-065 · MEDIUM
**Prompt:** Design a rocket that goes about 62 m and is back down in under 20 seconds.
**Rocket:** `ork/estes_alpha_vi_1958.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 61.866 m · max velocity 35.509 m/s · time to apogee 3.718 s · flight time 20.067 s · touchdown 3.855 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes about 62 m and is back down in under 20 seconds.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 62 m (203 ft)
- Time to apogee: 3.7 s
- Peak velocity: 36 m/s (Mach 0.11)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 20 s; descent from apogee takes 16 s
- Touchdown velocity: 3.85 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.06667,"base_radius_m":0.01239,"wall_thickness_m":0.0005,"material":"Polystyrene PS","name":"Nose cone","contains":[{"type":"masscomponent","name":"Mass Component - Nose Cone Screw","mass_kg":3e-05,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.0249,"wall_thickness_m":0.00038,"material":"Paper","name":"BT-50 Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"}]},{"type":"bodytube","length_m":0.05715,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube - Plastic Fin Can","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.001,"material":"Polystyrene PS","name":"Fin set - Alpha VI"},{"type":"centeringring","material":"Paper","name":"Centering ring - Front"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"Motor Mount Tube - 18 mm","motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"innertube","length_m":0.0078,"outer_d_m":0.0193,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Mylar Retainer Tube"},{"type":"centeringring","material":"Paper","name":"Centering ring - Rear"},{"type":"masscomponent","name":"Mass Component - Engine Hook","mass_kg":0.00028,"kind":"masscomponent"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-066 · MEDIUM
**Prompt:** Design a rocket that goes to about 171 m apogee, hitting about Mach 0.20 and 202.0 m/s² max acceleration.
**Rocket:** `ork/estes_alpha_vi_1958.ork` · **Sim:** Simulation 2 · **Motor:** B6
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 171.129 m · max velocity 65.967 m/s · time to apogee 5.302 s · flight time 48.797 s · touchdown 3.947 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 171 m apogee, hitting about Mach 0.20 and 202.0 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 171 m (561 ft)
- Time to apogee: 5.3 s
- Peak velocity: 66 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 49 s; descent from apogee takes 43 s
- Touchdown velocity: 3.95 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.06667,"base_radius_m":0.01239,"wall_thickness_m":0.0005,"material":"Polystyrene PS","name":"Nose cone","contains":[{"type":"masscomponent","name":"Mass Component - Nose Cone Screw","mass_kg":3e-05,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.0249,"wall_thickness_m":0.00038,"material":"Paper","name":"BT-50 Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"}]},{"type":"bodytube","length_m":0.05715,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube - Plastic Fin Can","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.001,"material":"Polystyrene PS","name":"Fin set - Alpha VI"},{"type":"centeringring","material":"Paper","name":"Centering ring - Front"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"Motor Mount Tube - 18 mm","motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"innertube","length_m":0.0078,"outer_d_m":0.0193,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Mylar Retainer Tube"},{"type":"centeringring","material":"Paper","name":"Centering ring - Rear"},{"type":"masscomponent","name":"Mass Component - Engine Hook","mass_kg":0.00028,"kind":"masscomponent"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-067 · MEDIUM
**Prompt:** Design a rocket that goes to about 380 m apogee with a total flight time of about 103.5 s.
**Rocket:** `ork/estes_alpha_vi_1958.ork` · **Sim:** Simulation 3 · **Motor:** C6
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 380.214 m · max velocity 111.455 m/s · time to apogee 7.337 s · flight time 103.47 s · touchdown 3.918 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 380 m apogee with a total flight time of about 103.5 s.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 380 m (1,247 ft)
- Time to apogee: 7.3 s
- Peak velocity: 111 m/s (Mach 0.33)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 103 s; descent from apogee takes 96 s
- Touchdown velocity: 3.92 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.06667,"base_radius_m":0.01239,"wall_thickness_m":0.0005,"material":"Polystyrene PS","name":"Nose cone","contains":[{"type":"masscomponent","name":"Mass Component - Nose Cone Screw","mass_kg":3e-05,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.0249,"wall_thickness_m":0.00038,"material":"Paper","name":"BT-50 Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"}]},{"type":"bodytube","length_m":0.05715,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube - Plastic Fin Can","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.001,"material":"Polystyrene PS","name":"Fin set - Alpha VI"},{"type":"centeringring","material":"Paper","name":"Centering ring - Front"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"Motor Mount Tube - 18 mm","motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"innertube","length_m":0.0078,"outer_d_m":0.0193,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Mylar Retainer Tube"},{"type":"centeringring","material":"Paper","name":"Centering ring - Rear"},{"type":"masscomponent","name":"Mass Component - Engine Hook","mass_kg":0.00028,"kind":"masscomponent"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-068 · MEDIUM
**Prompt:** Design a rocket that goes to about 119 m apogee and touches down at about 4.7 m/s.
**Rocket:** `ork/estes_antar_7310.ork` · **Sim:** Simulation 1 · **Motor:** C6
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 119.327 m · max velocity 45.743 m/s · time to apogee 5.472 s · flight time 29.928 s · touchdown 4.709 m/s · wind 3.57632 m/s
**Parts:** nose cone, 4 body tubes, transition, freeform fins, 2 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 119 m apogee and touches down at about 4.7 m/s.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 119 m (391 ft)
- Time to apogee: 5.5 s
- Peak velocity: 46 m/s (Mach 0.14)

3. RECOVERY & DESCENT:
- Parachute 0.38 m diameter, deploys at ejection
- Total flight time 30 s; descent from apogee takes 24 s
- Touchdown velocity: 4.71 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.30000000000000004,"length_m":0.005,"base_radius_m":0.0035,"wall_thickness_m":0.0,"material":"Polystyrene PS","name":"Nose cone","contains":[{"type":"masscomponent","name":"Clay","mass_kg":0.01417,"kind":"masscomponent"}]},{"type":"transition","shape":"ogive","length_m":0.21,"fore_d_m":0.007,"aft_d_m":0.04166,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.3302,"outer_d_m":0.04166,"wall_thickness_m":0.00071,"material":"Cellulose Acetate Propionate","name":"Main Body tube","contains":[{"type":"parachute","diameter_m":0.381,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute - 15'"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Fin #1 (Dorsal)"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Dorsal fin"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Fin #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Fin #3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Wing - L"},{"type":"pod_set","count":1.0,"name":"Pod Set for Winglets - L","contains":[{"type":"bodytube","length_m":0.0,"wall_thickness_m":0.0,"material":"Cardboard","name":"(Phantom BT)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.05715,"tip_chord_m":0.0,"span_m":0.00965,"sweep_m":0.043,"thickness_m":0.00317,"material":"Cardboard","name":"Trapezoidal Wing Fin Set"}]}]},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Cardboard","name":"Wing - R"},{"type":"pod_set","count":1.0,"name":"Pod Set for Winglets - R","contains":[{"type":"bodytube","length_m":0.0,"wall_thickness_m":0.0,"material":"Cardboard","name":"(Phantom BT)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.05715,"tip_chord_m":0.0,"span_m":0.00965,"sweep_m":0.043,"thickness_m":0.00317,"material":"Cardboard","name":"Trapezoidal Wing Fin Set"}]}]},{"type":"launchlug","length_m":0.01905,"name":"Launch Lug - F"},{"type":"launchlug","length_m":0.01905,"name":"Launch Lug - R"},{"type":"innertube","length_m":0.059,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Paper","name":"Motor tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Quest","designation":"D20W"}]},{"type":"centeringring","material":"Cardboard","name":"Centering Ring - F"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring - R"},{"type":"pod_set","count":1.0,"name":"Pod Set - Vanes","contains":[{"type":"bodytube","length_m":0.011,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Paper","name":"Body Tube (for MMT Vanes)","contains":[{"type":"freeformfinset","fin_count":8.0,"thickness_m":8e-05,"material":"Cardboard","name":"Vanes Fin Set MMT"}]}]},{"type":"innertube","length_m":0.0082,"outer_d_m":0.01956,"wall_thickness_m":0.00038,"material":"Cardboard","name":"Retainer Ring"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Quest","designation":"D20W"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Quest","designation":"D20W"}]}]}
</design>
```
</details>

### V1-070 · MEDIUM
**Prompt:** Design a rocket that goes to about 46 m apogee and touches down at about 2.4 m/s.
**Rocket:** `ork/estes_big_bertha.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 46.38 m · max velocity 29.701 m/s · time to apogee 3.2615 s · flight time 20.85 s · touchdown 2.4236 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 46 m apogee and touches down at about 2.4 m/s.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 46 m (152 ft)
- Time to apogee: 3.3 s
- Peak velocity: 30 m/s (Mach 0.09)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 21 s; descent from apogee takes 18 s
- Touchdown velocity: 2.42 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.3,"length_m":0.07938,"base_radius_m":0.02079,"material":"Balsa","preset":"SEMROC Astronautics BNC-60L","name":"BNC-60L with comments"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.04158,"wall_thickness_m":0.00053,"material":"Paper","name":"BT-60","contains":[{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00238,"material":"Balsa","name":"Freeform fin set"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (thin)","name":"Parachute PK-18"},{"type":"launchlug","length_m":0.127,"name":"Launch lug LL-1C"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"BT-20J","contains":[{"type":"engineblock","name":"Engine block EB-20B"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"RA-2060"},{"type":"centeringring","material":"Cardboard","name":"RA-2060"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-071 · MEDIUM
**Prompt:** Design a rocket that goes to about 103 m apogee and touches down at about 2.6 m/s.
**Rocket:** `ork/estes_big_bertha.ork` · **Sim:** Simulation 2 · **Motor:** B4
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 103.47 m · max velocity 50.571 m/s · time to apogee 4.4934 s · flight time 43.469 s · touchdown 2.5657 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 103 m apogee and touches down at about 2.6 m/s.

2. PROPULSION & ASCENT:
- Motor: B4
- Simulated apogee: 103 m (339 ft)
- Time to apogee: 4.5 s
- Peak velocity: 51 m/s (Mach 0.15)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 43 s; descent from apogee takes 39 s
- Touchdown velocity: 2.57 m/s
</thought>
<design>
{"flight":{"motor":"B4","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.3,"length_m":0.07938,"base_radius_m":0.02079,"material":"Balsa","preset":"SEMROC Astronautics BNC-60L","name":"BNC-60L with comments"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.04158,"wall_thickness_m":0.00053,"material":"Paper","name":"BT-60","contains":[{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00238,"material":"Balsa","name":"Freeform fin set"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (thin)","name":"Parachute PK-18"},{"type":"launchlug","length_m":0.127,"name":"Launch lug LL-1C"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"BT-20J","contains":[{"type":"engineblock","name":"Engine block EB-20B"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"RA-2060"},{"type":"centeringring","material":"Cardboard","name":"RA-2060"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-072 · MEDIUM
**Prompt:** Design a rocket that goes about 229 m and is back down in under 70 seconds.
**Rocket:** `ork/estes_boosted_bertha_1946.ork` · **Sim:** Simulation 1 · **Motor:** C6
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 228.688 m · max velocity 68.632 m/s · time to apogee 8.143 s · flight time 69.602 s · touchdown 3.746 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 2 stages, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes about 229 m and is back down in under 70 seconds.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 229 m (750 ft)
- Time to apogee: 8.1 s
- Peak velocity: 69 m/s (Mach 0.21)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 70 s; descent from apogee takes 61 s
- Touchdown velocity: 3.75 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage - Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.0635,"base_radius_m":0.02083,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"PNC-60"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.04158,"wall_thickness_m":0.00053,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"launchlug","length_m":0.06,"name":"Launch lug"},{"type":"centeringring","material":"Paper","name":"Centering Ring - F"},{"type":"centeringring","material":"Paper","name":"Centering Ring - R"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Paper","name":"Motor Tube, 18 mm","contains":[{"type":"engineblock","name":"Engine block"},{"type":"innertube","length_m":0.0,"wall_thickness_m":0.0,"material":"PVC","name":"Estes 18 mm Motor Retainer (inner ring)","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"innertube","length_m":0.00257,"outer_d_m":0.02256,"wall_thickness_m":0.00172,"material":"PVC","name":"Inner Ring Base","contains":[{"type":"innertube","length_m":0.00775,"outer_d_m":0.01912,"wall_thickness_m":0.0,"material":"Cardboard","name":"\"Smooth Inner tube"}]},{"type":"innertube","length_m":0.00694,"outer_d_m":0.02168,"wall_thickness_m":0.00128,"material":"PVC","name":"Threaded Section","contains":[{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"}]},{"type":"innertube","length_m":0.00274,"outer_d_m":0.02136,"wall_thickness_m":0.00177,"material":"PVC","name":"Inner Ring Peak"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.02582,"wall_thickness_m":0.00153,"material":"PVC","name":"Estes 18mm Motor Retainer Cap (Outer Ring)","contains":[{"type":"innertube","length_m":0.00962,"outer_d_m":0.02582,"wall_thickness_m":0.00155,"material":"PVC","name":"Outer Ring Base and grips","contains":[{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02566,"wall_thickness_m":0.00139,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.0255,"wall_thickness_m":0.00139,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02518,"wall_thickness_m":0.00123,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02486,"wall_thickness_m":0.00107,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02454,"wall_thickness_m":0.00091,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02422,"wall_thickness_m":0.00076,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.0239,"wall_thickness_m":0.0006,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02358,"wall_thickness_m":0.00044,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02328,"wall_thickness_m":0.00028,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02296,"wall_thickness_m":0.00012,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02264,"wall_thickness_m":0.0028,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02232,"wall_thickness_m":0.00334,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":8e-05,"outer_d_m":0.02216,"wall_thickness_m":0.00334,"material":"PVC","name":"Slope"},{"type":"engineblock","name":"Engine block"}]}]}],"motors":[{"manufacturer":"Estes","designation":"C6"}]},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Sustainer Fin 1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Sustainer Fin 2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Sustainer Fin 3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Sustainer Fin 4 (W)"}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Stage - Booster","contains":[{"type":"bodytube","length_m":0.1143,"outer_d_m":0.04166,"wall_thickness_m":0.00064,"material":"Paper","name":"Body tube","contains":[{"type":"innertube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Paper","name":"Motor Mount Tube, 18 mm","contains":[{"type":"engineblock","name":"Engine block - F"},{"type":"engineblock","name":"Engine block - R"},{"type":"innertube","length_m":0.0,"wall_thickness_m":0.0,"material":"PVC","name":"Estes 18 mm Motor Retainer (inner ring)","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"innertube","length_m":0.00257,"outer_d_m":0.02256,"wall_thickness_m":0.00172,"material":"PVC","name":"Inner Ring Base","contains":[{"type":"innertube","length_m":0.00775,"outer_d_m":0.01912,"wall_thickness_m":0.0,"material":"Cardboard","name":"\"Smooth Inner tube"}]},{"type":"innertube","length_m":0.00694,"outer_d_m":0.02168,"wall_thickness_m":0.00128,"material":"PVC","name":"Threaded Section","contains":[{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"}]},{"type":"innertube","length_m":0.00274,"outer_d_m":0.02136,"wall_thickness_m":0.00177,"material":"PVC","name":"Inner Ring Peak"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.02582,"wall_thickness_m":0.00153,"material":"PVC","name":"Estes 18mm Motor Retainer Cap (Outer Ring)","contains":[{"type":"innertube","length_m":0.00962,"outer_d_m":0.02582,"wall_thickness_m":0.00155,"material":"PVC","name":"Outer Ring Base and grips","contains":[{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02566,"wall_thickness_m":0.00139,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.0255,"wall_thickness_m":0.00139,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02518,"wall_thickness_m":0.00123,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02486,"wall_thickness_m":0.00107,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02454,"wall_thickness_m":0.00091,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02422,"wall_thickness_m":0.00076,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.0239,"wall_thickness_m":0.0006,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02358,"wall_thickness_m":0.00044,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02328,"wall_thickness_m":0.00028,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02296,"wall_thickness_m":0.00012,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02264,"wall_thickness_m":0.0028,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02232,"wall_thickness_m":0.00334,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":8e-05,"outer_d_m":0.02216,"wall_thickness_m":0.00334,"material":"PVC","name":"Slope"},{"type":"engineblock","name":"Engine block"}]}]},{"type":"innertube","length_m":0.00025,"outer_d_m":0.004,"wall_thickness_m":0.002,"material":"Cardboard","name":"CR Vent Holes - F"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.004,"wall_thickness_m":0.002,"material":"Cardboard","name":"CR Vent Holes - R"}],"motors":[{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Paper","name":"Centering Ring - F"},{"type":"centeringring","material":"Paper","name":"Centering Ring - R"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Balsa","name":"Booster Fin 1 (W)"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Balsa","name":"Booster Fin 2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Balsa","name":"Booster Fin 3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Balsa","name":"Booster Fin 4"}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-073 · MEDIUM
**Prompt:** Design a rocket that goes through about 128.7 m/s² max acceleration over a 91.6 s flight.
**Rocket:** `ork/estes_boosted_bertha_1946_mod24.ork` · **Sim:** Simulation 2 · **Motor:** C6, D12
**Why medium: 2 requirements: flight time, max acceleration**
**Targets:** apogee 313.057 m · max velocity 74.245 m/s · time to apogee 8.151 s · flight time 91.591 s · touchdown 3.751 m/s · wind 3.57632 m/s
**Parts:** nose cone, 3 body tubes, transition, freeform fins, pods, 2 stages, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes through about 128.7 m/s² max acceleration over a 91.6 s flight.

2. PROPULSION & ASCENT:
- Motor: C6, D12
- Simulated apogee: 313 m (1,027 ft)
- Time to apogee: 8.2 s
- Peak velocity: 74 m/s (Mach 0.22)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 92 s; descent from apogee takes 83 s
- Touchdown velocity: 3.75 m/s
</thought>
<design>
{"flight":{"motor":"C6, D12","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage - Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.0635,"base_radius_m":0.02083,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"PNC-60"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.04158,"wall_thickness_m":0.00053,"material":"Paper","name":"Body tube","contains":[{"type":"pod_set","count":1.0,"name":"Pod Set - Unversal AstroCam","contains":[{"type":"nosecone","shape":"power","shape_param":0.1,"length_m":0.01016,"base_radius_m":0.00955,"material":"Cardboard","name":"Nose Cone - UAC"},{"type":"bodytube","length_m":0.03365,"outer_d_m":0.0191,"material":"Cardboard","name":"Body Tube - UAC"},{"type":"transition","shape":"conical","length_m":0.00762,"fore_d_m":0.05,"aft_d_m":0.01652,"material":"Cardboard","name":"Transition - UAC"},{"type":"transition","shape":"conical","length_m":0.00254,"aft_d_m":0.00508,"material":"Cardboard","name":"Transition - UAC"}]},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"launchlug","length_m":0.06,"name":"Launch lug"},{"type":"centeringring","material":"Paper","name":"Centering Ring - F"},{"type":"centeringring","material":"Paper","name":"Centering Ring - R"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Paper","name":"Motor Tube, 18 mm","contains":[{"type":"engineblock","name":"Engine block"},{"type":"innertube","length_m":0.0,"wall_thickness_m":0.0,"material":"PVC","name":"Estes 18 mm Motor Retainer (inner ring)","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"innertube","length_m":0.00257,"outer_d_m":0.02256,"wall_thickness_m":0.00172,"material":"PVC","name":"Inner Ring Base","contains":[{"type":"innertube","length_m":0.00775,"outer_d_m":0.01912,"wall_thickness_m":0.0,"material":"Cardboard","name":"\"Smooth Inner tube"}]},{"type":"innertube","length_m":0.00694,"outer_d_m":0.02168,"wall_thickness_m":0.00128,"material":"PVC","name":"Threaded Section","contains":[{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"}]},{"type":"innertube","length_m":0.00274,"outer_d_m":0.02136,"wall_thickness_m":0.00177,"material":"PVC","name":"Inner Ring Peak"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.02582,"wall_thickness_m":0.00153,"material":"PVC","name":"Estes 18mm Motor Retainer Cap (Outer Ring)","contains":[{"type":"innertube","length_m":0.00962,"outer_d_m":0.02582,"wall_thickness_m":0.00155,"material":"PVC","name":"Outer Ring Base and grips","contains":[{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.00962,"outer_d_m":0.00194,"wall_thickness_m":0.00097,"material":"PVC","name":"Grip"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02566,"wall_thickness_m":0.00139,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.0255,"wall_thickness_m":0.00139,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02518,"wall_thickness_m":0.00123,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02486,"wall_thickness_m":0.00107,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02454,"wall_thickness_m":0.00091,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02422,"wall_thickness_m":0.00076,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.0239,"wall_thickness_m":0.0006,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02358,"wall_thickness_m":0.00044,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02328,"wall_thickness_m":0.00028,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02296,"wall_thickness_m":0.00012,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02264,"wall_thickness_m":0.0028,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00015,"outer_d_m":0.02232,"wall_thickness_m":0.00334,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":8e-05,"outer_d_m":0.02216,"wall_thickness_m":0.00334,"material":"PVC","name":"Slope"},{"type":"engineblock","name":"Engine block"}]}]}],"motors":[{"manufacturer":"Estes","designation":"C6"}]},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Sustainer Fin 1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Sustainer Fin 2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Sustainer Fin 3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Sustainer Fin 4 (W)"}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Stage - Booster","contains":[{"type":"bodytube","length_m":0.1143,"outer_d_m":0.04166,"wall_thickness_m":0.00064,"material":"Paper","name":"Body tube","contains":[{"type":"innertube","length_m":0.1016,"outer_d_m":0.0249,"wall_thickness_m":0.00038,"material":"Paper","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block - F"}],"motors":[{"manufacturer":"Estes","designation":"D12"}]},{"type":"centeringring","material":"Paper","name":"Centering Ring - F"},{"type":"centeringring","material":"Paper","name":"Centering Ring - R"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Balsa","name":"Booster Fin 1 (W)"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Balsa","name":"Booster Fin 2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Balsa","name":"Booster Fin 3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Balsa","name":"Booster Fin 4"}],"motors":[{"manufacturer":"Estes","designation":"D12"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"}]}]}
</design>
```
</details>

### V1-074 · MEDIUM
**Prompt:** I need a rocket on a D13W motor that gets up close to 85 m.
**Rocket:** `ork/estes_explorer_aquarius_2016-7253.ork` · **Sim:** Simulation 2 · **Motor:** D13W
**Why medium: 2 requirements: apogee, motor**
**Targets:** apogee 85.223 m · max velocity 53.997 m/s · time to apogee 3.553 s · flight time 20.356 s · touchdown 4.666 m/s · wind 3.57632 m/s
**Parts:** nose cone, 24 body tubes, transition, 3 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- I need a rocket on a D13W motor that gets up close to 85 m.

2. PROPULSION & ASCENT:
- Motor: D13W
- Simulated apogee: 85 m (280 ft)
- Time to apogee: 3.6 s
- Peak velocity: 54 m/s (Mach 0.16)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 20 s; descent from apogee takes 17 s
- Touchdown velocity: 4.67 m/s
</thought>
<design>
{"flight":{"motor":"D13W","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.07303,"base_radius_m":0.03397,"wall_thickness_m":0.0003,"material":"Polystyrene PS","name":"Nose Cone - Upper"},{"type":"transition","shape":"power","length_m":0.0127,"fore_d_m":0.06794,"aft_d_m":0.03352,"material":"Polystyrene PS","name":"Nose Cone - Middle"},{"type":"bodytube","length_m":0.00476,"outer_d_m":0.03352,"wall_thickness_m":0.00053,"material":"Polystyrene","name":"Nose Cone - Lower"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.03352,"wall_thickness_m":0.00051,"material":"Spiral/Glassine","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute"},{"type":"innertube","length_m":0.0889,"outer_d_m":0.0249,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring - F"},{"type":"centeringring","material":"Cardboard","name":"Centering ring - R"},{"type":"centeringring","material":"Cardboard","name":"Sleeve"},{"type":"engineblock","name":"Engine block"},{"type":"masscomponent","name":"Engine Hook E","mass_kg":0.00185,"kind":"masscomponent"}],"motors":[{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Estes Industries, Inc.","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.06667,"tip_chord_m":0.06667,"span_m":0.08572,"sweep_m":0.0,"thickness_m":0.00238,"material":"Balsa","name":"Fin set #1"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.06667,"tip_chord_m":0.06667,"span_m":0.08572,"sweep_m":0.0,"thickness_m":0.00238,"material":"Balsa","name":"Fin set #2"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.06667,"tip_chord_m":0.06667,"span_m":0.08572,"sweep_m":0.0,"thickness_m":0.00238,"material":"Balsa","name":"Fin set #3"},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 1","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U1","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 2","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U2","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 3","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U3","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 4","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U4","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 5","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U5","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 6","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U6","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M1","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M2","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M3","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M4","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M5","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M6","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L1","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L2","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L3","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L4","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L5","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L6","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Nozzle Assembly","contains":[{"type":"bodytube","length_m":0.02222,"outer_d_m":0.03252,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle Shoulder - W1"},{"type":"transition","shape":"conical","length_m":0.0019,"fore_d_m":0.05,"aft_d_m":0.02032,"material":"Cardboard","name":"Nozzle Transition - W2"},{"type":"bodytube","length_m":0.00444,"outer_d_m":0.02032,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle - W3"},{"type":"bodytube","length_m":0.00165,"outer_d_m":0.02236,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle Collar - W4"},{"type":"bodytube","length_m":0.00698,"outer_d_m":0.02032,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle - S1"},{"type":"transition","shape":"conical","length_m":0.00521,"fore_d_m":0.05,"aft_d_m":0.0169,"material":"Cardboard","name":"Nozzle Bell Top - S2"},{"type":"transition","shape":"conical","length_m":0.00521,"fore_d_m":0.0169,"aft_d_m":0.02032,"material":"Cardboard","name":"Nozzle Bell Top - S3"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.0169,"aft_d_m":0.02032,"material":"Cardboard","name":"Nozzle Bell Ridge - B1"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0208,"aft_d_m":0.02174,"material":"Cardboard","name":"Nozzle Bell Band - B1"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.0241,"aft_d_m":0.0241,"material":"Cardboard","name":"Nozzle Bell Ridge - B2"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0241,"aft_d_m":0.02664,"material":"Cardboard","name":"Nozzle Bell Band - B2"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.02802,"aft_d_m":0.02802,"material":"Cardboard","name":"Nozzle Bell Ridge - B3"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.02768,"aft_d_m":0.0296,"material":"Cardboard","name":"Nozzle Bell Band - B3"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.0301,"aft_d_m":0.0301,"material":"Cardboard","name":"Nozzle Bell Ridge - B4"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0301,"aft_d_m":0.03148,"material":"Cardboard","name":"Nozzle Bell Band - B4"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03252,"aft_d_m":0.03252,"material":"Cardboard","name":"Nozzle Bell Ridge - B5"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.03226,"aft_d_m":0.0331,"material":"Cardboard","name":"Nozzle Bell Band - B5"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03442,"aft_d_m":0.03442,"material":"Cardboard","name":"Nozzle Bell Ridge - B6"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.03384,"aft_d_m":0.03432,"material":"Cardboard","name":"Nozzle Bell Band - B6"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03508,"aft_d_m":0.03508,"material":"Cardboard","name":"Nozzle Bell Ridge - B7"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.03442,"aft_d_m":0.03456,"material":"Cardboard","name":"Nozzle Bell Band - B7"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03586,"aft_d_m":0.03586,"material":"Cardboard","name":"Nozzle Bell Ridge - B8"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0349,"aft_d_m":0.03528,"material":"Cardboard","name":"Nozzle Bell Band - B8"}]}],"motors":[{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Estes Industries, Inc.","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}],"motors":[{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Estes Industries, Inc.","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}]}
</design>
```
</details>

### V1-076 · MEDIUM
**Prompt:** Design a rocket that goes to about 80 m apogee and touches down at about 4.7 m/s.
**Rocket:** `ork/estes_explorer_aquarius_2016-7253.ork` · **Sim:** Simulation 4 · **Motor:** D12
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 79.937 m · max velocity 39.683 m/s · time to apogee 3.837 s · flight time 21.06 s · touchdown 4.661 m/s · wind 3.57632 m/s
**Parts:** nose cone, 24 body tubes, transition, 3 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 80 m apogee and touches down at about 4.7 m/s.

2. PROPULSION & ASCENT:
- Motor: D12
- Simulated apogee: 80 m (262 ft)
- Time to apogee: 3.8 s
- Peak velocity: 40 m/s (Mach 0.12)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 21 s; descent from apogee takes 17 s
- Touchdown velocity: 4.66 m/s
</thought>
<design>
{"flight":{"motor":"D12","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.07303,"base_radius_m":0.03397,"wall_thickness_m":0.0003,"material":"Polystyrene PS","name":"Nose Cone - Upper"},{"type":"transition","shape":"power","length_m":0.0127,"fore_d_m":0.06794,"aft_d_m":0.03352,"material":"Polystyrene PS","name":"Nose Cone - Middle"},{"type":"bodytube","length_m":0.00476,"outer_d_m":0.03352,"wall_thickness_m":0.00053,"material":"Polystyrene","name":"Nose Cone - Lower"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.03352,"wall_thickness_m":0.00051,"material":"Spiral/Glassine","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute"},{"type":"innertube","length_m":0.0889,"outer_d_m":0.0249,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring - F"},{"type":"centeringring","material":"Cardboard","name":"Centering ring - R"},{"type":"centeringring","material":"Cardboard","name":"Sleeve"},{"type":"engineblock","name":"Engine block"},{"type":"masscomponent","name":"Engine Hook E","mass_kg":0.00185,"kind":"masscomponent"}],"motors":[{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Estes Industries, Inc.","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.06667,"tip_chord_m":0.06667,"span_m":0.08572,"sweep_m":0.0,"thickness_m":0.00238,"material":"Balsa","name":"Fin set #1"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.06667,"tip_chord_m":0.06667,"span_m":0.08572,"sweep_m":0.0,"thickness_m":0.00238,"material":"Balsa","name":"Fin set #2"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.06667,"tip_chord_m":0.06667,"span_m":0.08572,"sweep_m":0.0,"thickness_m":0.00238,"material":"Balsa","name":"Fin set #3"},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 1","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U1","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 2","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U2","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 3","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U3","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 4","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U4","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 5","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U5","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Upper - 6","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - U6","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M1","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M2","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M3","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M4","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M5","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Mid","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - M6","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L1","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L2","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L3","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L4","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L5","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Fuel Tank- Lower","contains":[{"type":"nosecone","shape":"power","shape_param":0.0,"length_m":0.0016,"base_radius_m":0.025,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.21907,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Spiral/Glassine","name":"Body tube - L6","contains":[{"type":"bulkhead","material":"Aircraft plywood (Birch)","name":"Bulkhead"}]}]},{"type":"pod_set","count":1.0,"name":"Nozzle Assembly","contains":[{"type":"bodytube","length_m":0.02222,"outer_d_m":0.03252,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle Shoulder - W1"},{"type":"transition","shape":"conical","length_m":0.0019,"fore_d_m":0.05,"aft_d_m":0.02032,"material":"Cardboard","name":"Nozzle Transition - W2"},{"type":"bodytube","length_m":0.00444,"outer_d_m":0.02032,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle - W3"},{"type":"bodytube","length_m":0.00165,"outer_d_m":0.02236,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle Collar - W4"},{"type":"bodytube","length_m":0.00698,"outer_d_m":0.02032,"wall_thickness_m":0.00203,"material":"Polystyrene","name":"Nozzle - S1"},{"type":"transition","shape":"conical","length_m":0.00521,"fore_d_m":0.05,"aft_d_m":0.0169,"material":"Cardboard","name":"Nozzle Bell Top - S2"},{"type":"transition","shape":"conical","length_m":0.00521,"fore_d_m":0.0169,"aft_d_m":0.02032,"material":"Cardboard","name":"Nozzle Bell Top - S3"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.0169,"aft_d_m":0.02032,"material":"Cardboard","name":"Nozzle Bell Ridge - B1"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0208,"aft_d_m":0.02174,"material":"Cardboard","name":"Nozzle Bell Band - B1"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.0241,"aft_d_m":0.0241,"material":"Cardboard","name":"Nozzle Bell Ridge - B2"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0241,"aft_d_m":0.02664,"material":"Cardboard","name":"Nozzle Bell Band - B2"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.02802,"aft_d_m":0.02802,"material":"Cardboard","name":"Nozzle Bell Ridge - B3"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.02768,"aft_d_m":0.0296,"material":"Cardboard","name":"Nozzle Bell Band - B3"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.0301,"aft_d_m":0.0301,"material":"Cardboard","name":"Nozzle Bell Ridge - B4"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0301,"aft_d_m":0.03148,"material":"Cardboard","name":"Nozzle Bell Band - B4"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03252,"aft_d_m":0.03252,"material":"Cardboard","name":"Nozzle Bell Ridge - B5"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.03226,"aft_d_m":0.0331,"material":"Cardboard","name":"Nozzle Bell Band - B5"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03442,"aft_d_m":0.03442,"material":"Cardboard","name":"Nozzle Bell Ridge - B6"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.03384,"aft_d_m":0.03432,"material":"Cardboard","name":"Nozzle Bell Band - B6"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03508,"aft_d_m":0.03508,"material":"Cardboard","name":"Nozzle Bell Ridge - B7"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.03442,"aft_d_m":0.03456,"material":"Cardboard","name":"Nozzle Bell Band - B7"},{"type":"transition","shape":"conical","length_m":0.00084,"fore_d_m":0.03586,"aft_d_m":0.03586,"material":"Cardboard","name":"Nozzle Bell Ridge - B8"},{"type":"transition","shape":"conical","length_m":0.00178,"fore_d_m":0.0349,"aft_d_m":0.03528,"material":"Cardboard","name":"Nozzle Bell Band - B8"}]}],"motors":[{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Estes Industries, Inc.","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}],"motors":[{"manufacturer":"AeroTech","designation":"D13W"},{"manufacturer":"Estes Industries, Inc.","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}]}
</design>
```
</details>

### V1-081 · MEDIUM
**Prompt:** Design a rocket that goes to about 36 m apogee, hitting about 69.8 m/s² max acceleration.
**Rocket:** `ork/estes_rubicon_2189.ork` · **Sim:** Simulation 4 · **Motor:** C11
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 36.099 m · max velocity 24.286 m/s · time to apogee 3.079 s · flight time 9.482 s · touchdown 6.06 m/s · wind 3.57632 m/s
**Parts:** nose cone, 10 body tubes, transition, freeform fins, 12 fins, pods, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 36 m apogee, hitting about 69.8 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: C11
- Simulated apogee: 36 m (118 ft)
- Time to apogee: 3.1 s
- Peak velocity: 24 m/s (Mach 0.07)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 9 s; descent from apogee takes 6 s
- Touchdown velocity: 6.06 m/s
</thought>
<design>
{"flight":{"motor":"C11","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":3e-05,"base_radius_m":0.00635,"wall_thickness_m":0.00508,"material":"Polystyrene","name":"Nose Cone"},{"type":"transition","shape":"conical","length_m":0.1524,"fore_d_m":0.015,"aft_d_m":0.082,"material":"Custom","name":"Transition"},{"type":"bodytube","length_m":0.154,"outer_d_m":0.082,"wall_thickness_m":0.0005,"material":"Carbon fiber","name":"Body tube","contains":[{"type":"pod_set","count":1.0,"name":"Pod Set - Front Launch Lug","contains":[{"type":"bodytube","length_m":0.007,"outer_d_m":0.008,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body Tube (Launch Lug - R)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - L"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.007,"tip_chord_m":0.007,"span_m":0.01524,"sweep_m":0.0,"thickness_m":0.001,"material":"Cardboard","name":"Trapezoidal Fin Set - M"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - R"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Rear Launch Lug","contains":[{"type":"bodytube","length_m":0.007,"outer_d_m":0.008,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body Tube (Launch Lug - R)","contains":[{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - L"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.007,"tip_chord_m":0.007,"span_m":0.01524,"sweep_m":0.0,"thickness_m":0.001,"material":"Cardboard","name":"Trapezoidal Fin Set - M"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.003,"tip_chord_m":0.003,"span_m":0.00889,"sweep_m":0.0,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal Fin Set - R"}]}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"bulkhead","material":"Polycarbonate","name":"Bulkhead"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"innertube","length_m":0.3175,"outer_d_m":0.025,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Engine Mount Tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"C11"}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"innertube","length_m":0.01,"outer_d_m":0.026,"wall_thickness_m":0.0005,"material":"Polycarbonate","name":"Engine Tubes","contains":[{"type":"innertube","length_m":0.254,"outer_d_m":0.025,"wall_thickness_m":0.0,"material":"Cardboard","name":"Engine Tube","contains":[{"type":"innertube","length_m":0.065,"outer_d_m":0.0265,"wall_thickness_m":0.01325,"material":"Cardboard","name":"Inner Tube - Lower Silver Sleeve","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"},{"type":"centeringring","material":"Cardboard","name":"Centering Ring"}]}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Fin","contains":[{"type":"bodytube","length_m":0.254,"wall_thickness_m":0.0,"material":"Paper","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.0015,"material":"Polycarbonate","name":"Main Fin set"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.062,"tip_chord_m":0.062,"span_m":0.007,"sweep_m":0.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin Set - Silver Fin Brace/Attachment Point"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set - Engine Hook","contains":[{"type":"bodytube","length_m":0.0762,"wall_thickness_m":0.0,"material":"Cardboard","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Steel","name":"Freeform fin set #2"}]}]},{"type":"pod_set","count":1.0,"name":"Pod Set","contains":[{"type":"transition","shape":"conical","length_m":0.23564,"aft_d_m":0.082,"material":"Cardboard","name":"Base Vortex"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"C11"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"C11"}]}]}
</design>
```
</details>

### V1-082 · MEDIUM
**Prompt:** Design a rocket that goes to about 512 m apogee, reaching about 133.0 m/s max velocity.
**Rocket:** `ork/estes_sky_raider.ork` · **Sim:** Simulation 1 · **Motor:** E9
**Why medium: 2 requirements: apogee, max velocity**
**Targets:** apogee 512.46 m · max velocity 133 m/s · time to apogee 9.0418 s · flight time 96.125 s · touchdown 3.0721 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 512 m apogee, reaching about 133.0 m/s max velocity.

2. PROPULSION & ASCENT:
- Motor: E9
- Simulated apogee: 512 m (1,681 ft)
- Time to apogee: 9.0 s
- Peak velocity: 133 m/s (Mach 0.39)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at 100 m (328 ft)
- Total flight time 96 s; descent from apogee takes 87 s
- Touchdown velocity: 3.07 m/s
</thought>
<design>
{"flight":{"motor":"E9","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.13724,"base_radius_m":0.01683,"wall_thickness_m":0.00317,"material":"Polystyrene PS","preset":"Estes PNC-55AC","name":"Nose cone"},{"type":"bodytube","length_m":0.2286,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-55IJ","contains":[{"type":"bulkhead","material":"Balsa","name":"Bulkhead"}]},{"type":"bodytube","length_m":0.4572,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-55","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"altitude","deploy_altitude_m":100.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00239,"material":"Balsa","name":"Freeform fin set"},{"type":"innertube","length_m":0.127,"outer_d_m":0.02514,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","motors":[{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]},{"type":"centeringring","material":"lite ply","name":"Centering ring"},{"type":"centeringring","material":"lite ply","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}],"motors":[{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"Estes","designation":"D12"}]}]}
</design>
```
</details>

### V1-084 · MEDIUM
**Prompt:** Design a rocket that goes on a E16 motor to apogee in about 6.8 s.
**Rocket:** `ork/falconHeavey.ork` · **Sim:** Simulation 3 · **Motor:** E16
**Why medium: 2 requirements: time to apogee, motor**
**Targets:** apogee 174.58 m · max velocity 56.912 m/s · time to apogee 6.8308 s · flight time 40.084 s · touchdown 5.1873 m/s · wind 5 m/s
**Parts:** nose cone, 3 body tubes, transition, freeform fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes on a E16 motor to apogee in about 6.8 s.

2. PROPULSION & ASCENT:
- Motor: E16
- Simulated apogee: 175 m (573 ft)
- Time to apogee: 6.8 s
- Peak velocity: 57 m/s (Mach 0.17)

3. RECOVERY & DESCENT:
- Parachute 0.40 m diameter, deploys at 152 m (500 ft)
- Total flight time 40 s; descent from apogee takes 33 s
- Touchdown velocity: 5.19 m/s
</thought>
<design>
{"flight":{"motor":"E16","wind_ms":5.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.04,"base_radius_m":0.0375,"wall_thickness_m":0.0012,"material":"PLA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.037,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.094,"outer_d_m":0.075,"wall_thickness_m":0.0012,"material":"PLA","name":"Body tube","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.06,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.03,"aft_d_m":0.05,"material":"PLA","name":"Transition"},{"type":"bodytube","length_m":0.331,"outer_d_m":0.05,"wall_thickness_m":0.0008,"material":"PLA","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":2.0,"thickness_m":0.004,"material":"PLA","name":"Freeform fin set"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.12,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.15,"outer_d_m":0.05,"wall_thickness_m":0.0012,"material":"PLA","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4037,"deploy_event":"altitude","deploy_altitude_m":152.4,"deploy_delay_s":0.0,"line_count":4.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.004,"material":"PLA","name":"Freeform fin set"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.013,"kind":"masscomponent"}],"motors":[{"manufacturer":"Estes","designation":"E16"},{"manufacturer":"AeroTech","designation":"E20"},{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"Estes","designation":"E30"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F23FJ"}]}],"motors":[{"manufacturer":"Estes","designation":"E16"},{"manufacturer":"AeroTech","designation":"E20"},{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"Estes","designation":"E30"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F23FJ"}]}]}
</design>
```
</details>

### V1-085 · MEDIUM
**Prompt:** Design a rocket that goes to about 172 m apogee with a total flight time of about 33.6 s.
**Rocket:** `ork/falconHeavey.ork` · **Sim:** Simulation 4 · **Motor:** E20
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 171.51 m · max velocity 55.029 m/s · time to apogee 6.3309 s · flight time 33.626 s · touchdown 5.9839 m/s · wind 6 m/s
**Parts:** nose cone, 3 body tubes, transition, freeform fins, 1 stage, 1 parachute recovery, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 172 m apogee with a total flight time of about 33.6 s.

2. PROPULSION & ASCENT:
- Motor: E20
- Simulated apogee: 172 m (563 ft)
- Time to apogee: 6.3 s
- Peak velocity: 55 m/s (Mach 0.17)

3. RECOVERY & DESCENT:
- Parachute 0.40 m diameter, deploys at 152 m (500 ft)
- Total flight time 34 s; descent from apogee takes 27 s
- Touchdown velocity: 5.98 m/s
</thought>
<design>
{"flight":{"motor":"E20","wind_ms":6.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"haack","shape_param":0.0,"length_m":0.04,"base_radius_m":0.0375,"wall_thickness_m":0.0012,"material":"PLA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.037,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.094,"outer_d_m":0.075,"wall_thickness_m":0.0012,"material":"PLA","name":"Body tube","contains":[{"type":"masscomponent","name":"Unspecified","mass_kg":0.06,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.03,"aft_d_m":0.05,"material":"PLA","name":"Transition"},{"type":"bodytube","length_m":0.331,"outer_d_m":0.05,"wall_thickness_m":0.0008,"material":"PLA","name":"Body tube","contains":[{"type":"freeformfinset","fin_count":2.0,"thickness_m":0.004,"material":"PLA","name":"Freeform fin set"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.12,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.15,"outer_d_m":0.05,"wall_thickness_m":0.0012,"material":"PLA","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4037,"deploy_event":"altitude","deploy_altitude_m":152.4,"deploy_delay_s":0.0,"line_count":4.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.004,"material":"PLA","name":"Freeform fin set"},{"type":"masscomponent","name":"Unspecified","mass_kg":0.013,"kind":"masscomponent"}],"motors":[{"manufacturer":"Estes","designation":"E16"},{"manufacturer":"AeroTech","designation":"E20"},{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"Estes","designation":"E30"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F23FJ"}]}],"motors":[{"manufacturer":"Estes","designation":"E16"},{"manufacturer":"AeroTech","designation":"E20"},{"manufacturer":"AeroTech","designation":"F27"},{"manufacturer":"Estes","designation":"E30"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"F32"},{"manufacturer":"AeroTech","designation":"F23FJ"}]}]}
</design>
```
</details>

### V1-088 · MEDIUM
**Prompt:** Design a rocket that goes to about 505 m apogee, reaching about 124.9 m/s max velocity.
**Rocket:** `ork/locprecision_starburst_pk-28.ork` · **Sim:** Simulation 2 · **Motor:** F39T
**Why medium: 2 requirements: apogee, max velocity**
**Targets:** apogee 504.611 m · max velocity 124.949 m/s · time to apogee 9.53 s · flight time 64.445 s · touchdown 9.19 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 505 m apogee, reaching about 124.9 m/s max velocity.

2. PROPULSION & ASCENT:
- Motor: F39T
- Simulated apogee: 505 m (1,656 ft)
- Time to apogee: 9.5 s
- Peak velocity: 125 m/s (Mach 0.37)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 64 s; descent from apogee takes 55 s
- Touchdown velocity: 9.19 m/s
</thought>
<design>
{"flight":{"motor":"F39T","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.2286,"base_radius_m":0.03302,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.254,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Paper","name":"Body tube","contains":[{"type":"bulkhead","material":"Birch","name":"Bulkhead"},{"type":"masscomponent","name":"Large Screw Eye","mass_kg":0.00621,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.762,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute"},{"type":"innertube","length_m":0.3048,"outer_d_m":0.0254,"wall_thickness_m":0.00064,"material":"Paper","name":"Engine Tube x2 (24mm)","motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]},{"type":"centeringring","material":"Birch","name":"Centering Ring - F"},{"type":"centeringring","material":"Birch","name":"Centering Ring - R"},{"type":"launchlug","length_m":0.1524,"name":"Launch lug"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.20066,"tip_chord_m":0.0,"span_m":0.08052,"sweep_m":0.16149,"thickness_m":0.00317,"material":"Birch","name":"Fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]}]}
</design>
```
</details>

### V1-089 · MEDIUM
**Prompt:** Design a rocket that goes through about 109.6 m/s² max acceleration over a 60.5 s flight.
**Rocket:** `ork/locprecision_starburst_pk-28.ork` · **Sim:** Simulation 3 · **Motor:** F24W
**Why medium: 2 requirements: flight time, max acceleration**
**Targets:** apogee 471.589 m · max velocity 106.056 m/s · time to apogee 9.487 s · flight time 60.46 s · touchdown 9.262 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes through about 109.6 m/s² max acceleration over a 60.5 s flight.

2. PROPULSION & ASCENT:
- Motor: F24W
- Simulated apogee: 472 m (1,547 ft)
- Time to apogee: 9.5 s
- Peak velocity: 106 m/s (Mach 0.31)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 60 s; descent from apogee takes 51 s
- Touchdown velocity: 9.26 m/s
</thought>
<design>
{"flight":{"motor":"F24W","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.2286,"base_radius_m":0.03302,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.254,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Paper","name":"Body tube","contains":[{"type":"bulkhead","material":"Birch","name":"Bulkhead"},{"type":"masscomponent","name":"Large Screw Eye","mass_kg":0.00621,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.762,"outer_d_m":0.0668,"wall_thickness_m":0.00089,"material":"Paper","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute"},{"type":"innertube","length_m":0.3048,"outer_d_m":0.0254,"wall_thickness_m":0.00064,"material":"Paper","name":"Engine Tube x2 (24mm)","motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]},{"type":"centeringring","material":"Birch","name":"Centering Ring - F"},{"type":"centeringring","material":"Birch","name":"Centering Ring - R"},{"type":"launchlug","length_m":0.1524,"name":"Launch lug"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.20066,"tip_chord_m":0.0,"span_m":0.08052,"sweep_m":0.16149,"thickness_m":0.00317,"material":"Birch","name":"Fin set"}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F35W"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"F52C"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"}]}]}
</design>
```
</details>

### V1-091 · MEDIUM
**Prompt:** Design a rocket that goes to apogee in about 5.3 s with a total flight of about 52.5 s.
**Rocket:** `ork/quest_astra_1004.ork` · **Sim:** Simulation 2 · **Motor:** B6
**Why medium: 2 requirements: time to apogee, flight time**
**Targets:** apogee 180.587 m · max velocity 69.543 m/s · time to apogee 5.324 s · flight time 52.484 s · touchdown 3.854 m/s · wind 3.57632 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to apogee in about 5.3 s with a total flight of about 52.5 s.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 181 m (592 ft)
- Time to apogee: 5.3 s
- Peak velocity: 70 m/s (Mach 0.21)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 52 s; descent from apogee takes 47 s
- Touchdown velocity: 3.85 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":0.9,"length_m":0.08,"base_radius_m":0.01257,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.2286,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50AE, 30354","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute 12\""},{"type":"launchlug","length_m":0.0254,"name":"Launch lug"},{"type":"innertube","length_m":0.0762,"outer_d_m":0.01998,"wall_thickness_m":0.00051,"material":"Paper","name":"Engine Mount tube","contains":[{"type":"centeringring","material":"Paper","name":"Engine Block Ring"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Paper","name":"Centering Ring - F"},{"type":"centeringring","material":"Paper","name":"Centering Ring - R"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Fin #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Fin #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Balsa","name":"Fin #3"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### V1-094 · MEDIUM
**Prompt:** Give me a rocket that tops out near 123 m and lands under 7.6 m/s.
**Rocket:** `ork/rocketarium_trident.ork` · **Sim:** Simulation 1 · **Motor:** B6
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 122.79 m · max velocity 49.676 m/s · time to apogee 5.1491 s · flight time 22.268 s · touchdown 7.5505 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Give me a rocket that tops out near 123 m and lands under 7.6 m/s.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 123 m (403 ft)
- Time to apogee: 5.1 s
- Peak velocity: 50 m/s (Mach 0.15)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 22 s; descent from apogee takes 17 s
- Touchdown velocity: 7.55 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.18,"base_radius_m":0.0208,"wall_thickness_m":0.0,"material":"Polystyrene","name":"Plastic Nose Cone"},{"type":"bodytube","length_m":0.1905,"outer_d_m":0.0416,"wall_thickness_m":0.00084,"material":"Spiral/Glassine","name":"Payload Tube"},{"type":"bodytube","length_m":0.2159,"outer_d_m":0.0416,"wall_thickness_m":0.00084,"material":"Spiral/Glassine","name":"Main Body Tube","contains":[{"type":"bulkhead","material":"Basswood","name":"Bulkhead plus eyebolt"},{"type":"bulkhead","material":"Basswood","name":"Balsawood Cluster Bulkhead"},{"type":"innertube","length_m":0.34544,"outer_d_m":0.0187,"wall_thickness_m":0.00035,"material":"Spiral/Glassine","name":"Motor Tubes 1","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]},{"type":"innertube","length_m":0.345,"outer_d_m":0.0187,"wall_thickness_m":0.00035,"material":"Spiral/Glassine","name":"Motor Tubes 2","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]},{"type":"innertube","length_m":0.345,"outer_d_m":0.0187,"wall_thickness_m":0.00035,"material":"Spiral/Glassine","name":"Motor Tubes 3","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]},{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon thin","name":"12\" Nylon Parachute"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]},{"type":"bodytube","length_m":0.267,"wall_thickness_m":0.0,"material":"Cardboard","name":"Fake body tube","contains":[{"type":"launchlug","length_m":0.0508,"name":"Launch lug lower"},{"type":"launchlug","length_m":0.0508,"name":"Launch lug upper"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.003,"material":"Basswood","name":"Fin set #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.003,"material":"Basswood","name":"Fin set #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.003,"material":"Basswood","name":"Fin set #3"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]}]}
</design>
```
</details>

### V1-095 · MEDIUM
**Prompt:** Design a rocket that goes to apogee in about 8.1 s with a total flight of about 50.4 s.
**Rocket:** `ork/rocketarium_trident.ork` · **Sim:** Simulation 2 · **Motor:** C6
**Why medium: 2 requirements: time to apogee, flight time**
**Targets:** apogee 314.9 m · max velocity 87.811 m/s · time to apogee 8.0822 s · flight time 50.417 s · touchdown 7.5334 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to apogee in about 8.1 s with a total flight of about 50.4 s.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 315 m (1,033 ft)
- Time to apogee: 8.1 s
- Peak velocity: 88 m/s (Mach 0.26)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 50 s; descent from apogee takes 42 s
- Touchdown velocity: 7.53 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.18,"base_radius_m":0.0208,"wall_thickness_m":0.0,"material":"Polystyrene","name":"Plastic Nose Cone"},{"type":"bodytube","length_m":0.1905,"outer_d_m":0.0416,"wall_thickness_m":0.00084,"material":"Spiral/Glassine","name":"Payload Tube"},{"type":"bodytube","length_m":0.2159,"outer_d_m":0.0416,"wall_thickness_m":0.00084,"material":"Spiral/Glassine","name":"Main Body Tube","contains":[{"type":"bulkhead","material":"Basswood","name":"Bulkhead plus eyebolt"},{"type":"bulkhead","material":"Basswood","name":"Balsawood Cluster Bulkhead"},{"type":"innertube","length_m":0.34544,"outer_d_m":0.0187,"wall_thickness_m":0.00035,"material":"Spiral/Glassine","name":"Motor Tubes 1","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]},{"type":"innertube","length_m":0.345,"outer_d_m":0.0187,"wall_thickness_m":0.00035,"material":"Spiral/Glassine","name":"Motor Tubes 2","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]},{"type":"innertube","length_m":0.345,"outer_d_m":0.0187,"wall_thickness_m":0.00035,"material":"Spiral/Glassine","name":"Motor Tubes 3","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]},{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon thin","name":"12\" Nylon Parachute"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]},{"type":"bodytube","length_m":0.267,"wall_thickness_m":0.0,"material":"Cardboard","name":"Fake body tube","contains":[{"type":"launchlug","length_m":0.0508,"name":"Launch lug lower"},{"type":"launchlug","length_m":0.0508,"name":"Launch lug upper"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.003,"material":"Basswood","name":"Fin set #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.003,"material":"Basswood","name":"Fin set #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.003,"material":"Basswood","name":"Fin set #3"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"D16"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"A8"}]}]}
</design>
```
</details>

### V1-096 · MEDIUM
**Prompt:** Design a rocket that goes to about 395 m apogee, hitting about 210.8 m/s² max acceleration.
**Rocket:** `ork/semroc_starfire_kv-20.ork` · **Sim:** Simulation 1 · **Motor:** C6
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 395.231 m · max velocity 111.577 m/s · time to apogee 8.484 s · flight time 113.053 s · touchdown 3.766 m/s · wind 3.57632 m/s
**Parts:** nose cone, 1 body tube, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 395 m apogee, hitting about 210.8 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 395 m (1,297 ft)
- Time to apogee: 8.5 s
- Peak velocity: 112 m/s (Mach 0.33)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 113 s; descent from apogee takes 105 s
- Touchdown velocity: 3.77 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.12065,"base_radius_m":0.01151,"material":"Balsa","name":"Nose cone","contains":[{"type":"masscomponent","name":"Screw Eye","mass_kg":0.00028,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.2032,"outer_d_m":0.02306,"wall_thickness_m":0.00054,"material":"Spiral/Glassine","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"SEMROC CP-12RW","name":"Parachute kit, plastic, 12 in, red/white"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Paper","name":"Body tube - motor mount","contains":[{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Paper","name":"Centering ring (F)"},{"type":"centeringring","material":"Paper","name":"Centering ring (R)"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"}]},{"type":"launchlug","length_m":0.05715,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"}]},{"type":"transition","shape":"conical","length_m":0.03016,"fore_d_m":0.02306,"aft_d_m":0.0188,"material":"Paper","name":"Transition - boat tail","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Custom Fin PURPLE"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Custom Fin PURPLE"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Custom Fin BLACK"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"}]}]}
</design>
```
</details>

### V1-097 · MEDIUM
**Prompt:** Give me a rocket that tops out near 173 m and lands under 3.8 m/s.
**Rocket:** `ork/semroc_starfire_kv-20.ork` · **Sim:** Simulation 2 · **Motor:** B6
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 173.198 m · max velocity 66.164 m/s · time to apogee 5.292 s · flight time 50.746 s · touchdown 3.82 m/s · wind 3.57632 m/s
**Parts:** nose cone, 1 body tube, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Give me a rocket that tops out near 173 m and lands under 3.8 m/s.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 173 m (568 ft)
- Time to apogee: 5.3 s
- Peak velocity: 66 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 51 s; descent from apogee takes 45 s
- Touchdown velocity: 3.82 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.12065,"base_radius_m":0.01151,"material":"Balsa","name":"Nose cone","contains":[{"type":"masscomponent","name":"Screw Eye","mass_kg":0.00028,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.2032,"outer_d_m":0.02306,"wall_thickness_m":0.00054,"material":"Spiral/Glassine","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"SEMROC CP-12RW","name":"Parachute kit, plastic, 12 in, red/white"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Paper","name":"Body tube - motor mount","contains":[{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Paper","name":"Centering ring (F)"},{"type":"centeringring","material":"Paper","name":"Centering ring (R)"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"}]},{"type":"launchlug","length_m":0.05715,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"}]},{"type":"transition","shape":"conical","length_m":0.03016,"fore_d_m":0.02306,"aft_d_m":0.0188,"material":"Paper","name":"Transition - boat tail","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Custom Fin PURPLE"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Custom Fin PURPLE"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Custom Fin BLACK"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"}]}]}
</design>
```
</details>

### V1-098 · MEDIUM
**Prompt:** Design a rocket that goes to about 177 m apogee and touches down at about 3.8 m/s.
**Rocket:** `ork/semroc_starfire_kv-20.ork` · **Sim:** Simulation 3 · **Motor:** B6
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 177.045 m · max velocity 66.089 m/s · time to apogee 5.973 s · flight time 51.92 s · touchdown 3.834 m/s · wind 3.57632 m/s
**Parts:** nose cone, 1 body tube, transition, freeform fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 177 m apogee and touches down at about 3.8 m/s.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 177 m (581 ft)
- Time to apogee: 6.0 s
- Peak velocity: 66 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 52 s; descent from apogee takes 46 s
- Touchdown velocity: 3.83 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.12065,"base_radius_m":0.01151,"material":"Balsa","name":"Nose cone","contains":[{"type":"masscomponent","name":"Screw Eye","mass_kg":0.00028,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.2032,"outer_d_m":0.02306,"wall_thickness_m":0.00054,"material":"Spiral/Glassine","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"SEMROC CP-12RW","name":"Parachute kit, plastic, 12 in, red/white"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0188,"wall_thickness_m":0.00038,"material":"Paper","name":"Body tube - motor mount","contains":[{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Paper","name":"Centering ring (F)"},{"type":"centeringring","material":"Paper","name":"Centering ring (R)"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"}]},{"type":"launchlug","length_m":0.05715,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"}]},{"type":"transition","shape":"conical","length_m":0.03016,"fore_d_m":0.02306,"aft_d_m":0.0188,"material":"Paper","name":"Transition - boat tail","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Custom Fin PURPLE"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Custom Fin PURPLE"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00239,"material":"Balsa","name":"Custom Fin BLACK"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"}]}]}
</design>
```
</details>

### V1-102 · MEDIUM
**Prompt:** Give me a rocket that tops out near 183 m and lands under 5.0 m/s.
**Rocket:** `ork/siriusrocketry_eradicator_s-0017.ork` · **Sim:** Simulation 3 · **Motor:** F24W
**Why medium: 2 requirements: apogee, touchdown speed**
**Targets:** apogee 182.926 m · max velocity 58.152 m/s · time to apogee 6.27 s · flight time 43.044 s · touchdown 5.015 m/s · wind 3.57632 m/s
**Parts:** nose cone, 4 body tubes, transition, freeform fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Give me a rocket that tops out near 183 m and lands under 5.0 m/s.

2. PROPULSION & ASCENT:
- Motor: F24W
- Simulated apogee: 183 m (600 ft)
- Time to apogee: 6.3 s
- Peak velocity: 58 m/s (Mach 0.17)

3. RECOVERY & DESCENT:
- Parachute 0.76 m diameter, deploys at ejection
- Total flight time 43 s; descent from apogee takes 37 s
- Touchdown velocity: 5.01 m/s
</thought>
<design>
{"flight":{"motor":"F24W","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.00239,"base_radius_m":0.00237,"wall_thickness_m":0.00201,"material":"Polystyrene","name":"Nose cone"},{"type":"transition","shape":"ogive","length_m":0.27701,"fore_d_m":0.05,"aft_d_m":0.0762,"material":"Cardboard","name":"Transition"},{"type":"bodytube","length_m":0.4318,"outer_d_m":0.07672,"wall_thickness_m":0.00057,"material":"Paper","name":"Body tube, Upper, 3\"","contains":[{"type":"parachute","diameter_m":0.762,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Rip stop nylon","name":"Parachute - 30\""},{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - F"},{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - R"},{"type":"masscomponent","name":"Mass - (1/8\" Quick Connect)","mass_kg":0.02268,"kind":"masscomponent"},{"type":"railbutton","name":"Rail Button - F"}]},{"type":"bodytube","length_m":0.4318,"outer_d_m":0.057,"wall_thickness_m":0.0005,"material":"Paper","name":"Body tube, Lower, 2 1/4\"","contains":[{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - F"},{"type":"centeringring","material":"1/8 Aircraft Plywood","name":"Centering ring - R"},{"type":"freeformfinset","fin_count":8.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set - 8 Strakes"},{"type":"innertube","length_m":0.5588,"outer_d_m":0.031,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube, 29mm MMT","contains":[{"type":"innertube","length_m":0.0,"wall_thickness_m":0.0,"material":"PVC","name":"Estes Pro Series II 29mm Motor Retainer (PN 072412)(inner Ring)","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"innertube","length_m":0.00422,"outer_d_m":0.03698,"wall_thickness_m":0.00282,"material":"PVC","name":"Inner Ring Base","contains":[{"type":"innertube","length_m":0.0127,"outer_d_m":0.03134,"wall_thickness_m":0.0,"material":"Cardboard","name":"\"Smooth Inner tube"}]},{"type":"innertube","length_m":0.01137,"outer_d_m":0.03554,"wall_thickness_m":0.0021,"material":"PVC","name":"Threaded Section","contains":[{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"}]},{"type":"innertube","length_m":0.0045,"outer_d_m":0.03502,"wall_thickness_m":0.00291,"material":"PVC","name":"Inner Ring Peak"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.04232,"wall_thickness_m":0.00251,"material":"PVC","name":"Estes Pro Series II 29mm Motor Retainer (072412)(Outer Ring)","contains":[{"type":"innertube","length_m":0.01577,"outer_d_m":0.04232,"wall_thickness_m":0.00254,"material":"PVC","name":"Outer Ring Base and grips","contains":[{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"innertube","length_m":0.01577,"outer_d_m":0.00318,"wall_thickness_m":0.00159,"material":"PVC","name":"Grip"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"centeringring","material":"PVC","name":"Thread"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04206,"wall_thickness_m":0.00228,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.0418,"wall_thickness_m":0.00228,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04128,"wall_thickness_m":0.00202,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04076,"wall_thickness_m":0.00176,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.04024,"wall_thickness_m":0.0015,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03972,"wall_thickness_m":0.00124,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.0392,"wall_thickness_m":0.00098,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03868,"wall_thickness_m":0.00072,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03816,"wall_thickness_m":0.00046,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03764,"wall_thickness_m":0.0002,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.0371,"wall_thickness_m":0.00458,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00025,"outer_d_m":0.03658,"wall_thickness_m":0.00547,"material":"PVC","name":"Slope"},{"type":"innertube","length_m":0.00013,"outer_d_m":0.03632,"wall_thickness_m":0.00547,"material":"PVC","name":"Slope"},{"type":"engineblock","name":"Engine block"}]}]}],"motors":[{"manufacturer":"AeroTech","designation":"H180W"},{"manufacturer":"AeroTech","designation":"G40W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"G80T"},{"manufacturer":"AeroTech","designation":"HP-H135W"},{"manufacturer":"AeroTech","designation":"HP-I205W"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"G64W"},{"manufacturer":"AeroTech","designation":"F40W"},{"manufacturer":"AeroTech","designation":"HP-G138T"},{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"H128W"}]},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"1/8 Aircraft Plywood","name":"Fin set, 4 with Strakes #4"},{"type":"pod_set","count":1.0,"name":"Pod Set - F Ring Fin","contains":[{"type":"bodytube","length_m":0.0254,"outer_d_m":0.0762,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube - F, Ring Fin"}]},{"type":"pod_set","count":1.0,"name":"Pod Set - R Ring Fin","contains":[{"type":"bodytube","length_m":0.0254,"outer_d_m":0.0762,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube - R, Ring Fin","contains":[{"type":"railbutton","name":"Rail Button - R"}]}]}],"motors":[{"manufacturer":"AeroTech","designation":"H180W"},{"manufacturer":"AeroTech","designation":"G40W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"G80T"},{"manufacturer":"AeroTech","designation":"HP-H135W"},{"manufacturer":"AeroTech","designation":"HP-I205W"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"G64W"},{"manufacturer":"AeroTech","designation":"F40W"},{"manufacturer":"AeroTech","designation":"HP-G138T"},{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"H128W"}]}],"motors":[{"manufacturer":"AeroTech","designation":"H180W"},{"manufacturer":"AeroTech","designation":"G40W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"G80T"},{"manufacturer":"AeroTech","designation":"HP-H135W"},{"manufacturer":"AeroTech","designation":"HP-I205W"},{"manufacturer":"Quest","designation":"E35W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"G64W"},{"manufacturer":"AeroTech","designation":"F40W"},{"manufacturer":"AeroTech","designation":"HP-G138T"},{"manufacturer":"AeroTech","designation":"F67W"},{"manufacturer":"AeroTech","designation":"H128W"}]}]}
</design>
```
</details>

### V1-104 · MEDIUM
**Prompt:** Design a rocket that goes to about 331 m apogee, hitting about 156.0 m/s² max acceleration.
**Rocket:** `ork/starfire73_talon.ork` · **Sim:** Simulation 2 · **Motor:** E28T
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 331 m · max velocity 106.073 m/s · time to apogee 7.544 s · flight time 60.478 s · touchdown 6.152 m/s · wind 3.57632 m/s
**Parts:** nose cone, 3 body tubes, transition, freeform fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 331 m apogee, hitting about 156.0 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: E28T
- Simulated apogee: 331 m (1,086 ft)
- Time to apogee: 7.5 s
- Peak velocity: 106 m/s (Mach 0.31)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 60 s; descent from apogee takes 53 s
- Touchdown velocity: 6.15 m/s
</thought>
<design>
{"flight":{"motor":"E28T","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":0.00305,"base_radius_m":0.00533,"wall_thickness_m":0.00102,"material":"Polystyrene PS","name":"Nose cone"},{"type":"transition","shape":"haack","length_m":0.13335,"fore_d_m":0.01066,"aft_d_m":0.04546,"material":"Polystyrene PS","name":"Nose Cone Base Transition"},{"type":"bodytube","length_m":0.127,"outer_d_m":0.04546,"wall_thickness_m":0.00063,"material":"Polystyrene PS","name":"Clear Payload Section BT-65","contains":[{"type":"masscomponent","name":"Mass - Altimeter2","mass_kg":0.01417,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.00279,"fore_d_m":0.0455,"aft_d_m":0.04546,"material":"Polystyrene PS","name":"Tube Adapter Transition"},{"type":"bodytube","length_m":0.458,"outer_d_m":0.04546,"wall_thickness_m":0.00063,"material":"Cardboard","name":"BT-65 Body tube","contains":[{"type":"masscomponent","name":"Mass - JLCR","mass_kg":0.01417,"kind":"masscomponent"},{"type":"pod_set","count":1.0,"name":"Pod Set - Unversal Astro Cam","contains":[{"type":"nosecone","shape":"power","shape_param":0.1,"length_m":0.01016,"base_radius_m":0.009,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.03048,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube"},{"type":"transition","shape":"conical","length_m":0.01016,"fore_d_m":0.05,"aft_d_m":0.01524,"material":"Cardboard","name":"Transition"}]},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Aircraft plywood (Birch)","name":"Custom Fin set #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Aircraft plywood (Birch)","name":"Custom Fin set #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Aircraft plywood (Birch)","name":"Custom Fin set #3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Aircraft plywood (Birch)","name":"Custom Fin set #4"},{"type":"launchlug","length_m":0.06033,"name":"3/16\" Launch lug"},{"type":"innertube","length_m":0.1,"outer_d_m":0.02488,"wall_thickness_m":0.00038,"material":"Paper","name":"Engine Mount tube","contains":[{"type":"engineblock","name":"Green Engine block"},{"type":"centeringring","material":"Paper","name":"Forward Centering ring"},{"type":"centeringring","material":"Paper","name":"Center Centering ring"},{"type":"centeringring","material":"Paper","name":"Aft Centering ring"}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F32T"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.02558,"wall_thickness_m":0.0,"material":"PVC","name":"Motor Retainer (PN 72417)(Collar)","contains":[{"type":"centeringring","material":"PVC","name":"Collar Forward End Detail"},{"type":"centeringring","material":"PVC","name":"Collar Back End Detail (Threaded section)"},{"type":"centeringring","material":"PVC","name":"Collar Inner Lip (and Throat)"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.0314,"wall_thickness_m":0.0,"material":"PVC","name":"Motor Retainer (PN 72417)(Jacket)","contains":[{"type":"centeringring","material":"PVC","name":"Outer Jacket"},{"type":"centeringring","material":"PVC","name":"Jacket Threaded Section"},{"type":"centeringring","material":"PVC","name":"Jacket Inner Lip (and Throat)"},{"type":"innertube","length_m":0.0,"outer_d_m":0.0314,"wall_thickness_m":0.0,"material":"PVC","name":"Grip Details","contains":[{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"}]}]}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F32T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F32T"}]}]}
</design>
```
</details>

### V1-105 · MEDIUM
**Prompt:** Design a rocket that goes through about 123.4 m/s² max acceleration over a 73.6 s flight.
**Rocket:** `ork/starfire73_talon.ork` · **Sim:** Simulation 3 · **Motor:** F24W
**Why medium: 2 requirements: flight time, max acceleration**
**Targets:** apogee 402.78 m · max velocity 109.016 m/s · time to apogee 8.323 s · flight time 73.555 s · touchdown 6.157 m/s · wind 2.2352 m/s
**Parts:** nose cone, 3 body tubes, transition, freeform fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes through about 123.4 m/s² max acceleration over a 73.6 s flight.

2. PROPULSION & ASCENT:
- Motor: F24W
- Simulated apogee: 403 m (1,321 ft)
- Time to apogee: 8.3 s
- Peak velocity: 109 m/s (Mach 0.32)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 74 s; descent from apogee takes 65 s
- Touchdown velocity: 6.16 m/s
</thought>
<design>
{"flight":{"motor":"F24W","wind_ms":2.2352000000000003},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":0.00305,"base_radius_m":0.00533,"wall_thickness_m":0.00102,"material":"Polystyrene PS","name":"Nose cone"},{"type":"transition","shape":"haack","length_m":0.13335,"fore_d_m":0.01066,"aft_d_m":0.04546,"material":"Polystyrene PS","name":"Nose Cone Base Transition"},{"type":"bodytube","length_m":0.127,"outer_d_m":0.04546,"wall_thickness_m":0.00063,"material":"Polystyrene PS","name":"Clear Payload Section BT-65","contains":[{"type":"masscomponent","name":"Mass - Altimeter2","mass_kg":0.01417,"kind":"masscomponent"}]},{"type":"transition","shape":"conical","length_m":0.00279,"fore_d_m":0.0455,"aft_d_m":0.04546,"material":"Polystyrene PS","name":"Tube Adapter Transition"},{"type":"bodytube","length_m":0.458,"outer_d_m":0.04546,"wall_thickness_m":0.00063,"material":"Cardboard","name":"BT-65 Body tube","contains":[{"type":"masscomponent","name":"Mass - JLCR","mass_kg":0.01417,"kind":"masscomponent"},{"type":"pod_set","count":1.0,"name":"Pod Set - Unversal Astro Cam","contains":[{"type":"nosecone","shape":"power","shape_param":0.1,"length_m":0.01016,"base_radius_m":0.009,"material":"Cardboard","name":"Nose Cone"},{"type":"bodytube","length_m":0.03048,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube"},{"type":"transition","shape":"conical","length_m":0.01016,"fore_d_m":0.05,"aft_d_m":0.01524,"material":"Cardboard","name":"Transition"}]},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","name":"Parachute"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Aircraft plywood (Birch)","name":"Custom Fin set #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Aircraft plywood (Birch)","name":"Custom Fin set #2"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Aircraft plywood (Birch)","name":"Custom Fin set #3"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00318,"material":"Aircraft plywood (Birch)","name":"Custom Fin set #4"},{"type":"launchlug","length_m":0.06033,"name":"3/16\" Launch lug"},{"type":"innertube","length_m":0.1,"outer_d_m":0.02488,"wall_thickness_m":0.00038,"material":"Paper","name":"Engine Mount tube","contains":[{"type":"engineblock","name":"Green Engine block"},{"type":"centeringring","material":"Paper","name":"Forward Centering ring"},{"type":"centeringring","material":"Paper","name":"Center Centering ring"},{"type":"centeringring","material":"Paper","name":"Aft Centering ring"}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F32T"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.02558,"wall_thickness_m":0.0,"material":"PVC","name":"Motor Retainer (PN 72417)(Collar)","contains":[{"type":"centeringring","material":"PVC","name":"Collar Forward End Detail"},{"type":"centeringring","material":"PVC","name":"Collar Back End Detail (Threaded section)"},{"type":"centeringring","material":"PVC","name":"Collar Inner Lip (and Throat)"}]},{"type":"innertube","length_m":0.0,"outer_d_m":0.0314,"wall_thickness_m":0.0,"material":"PVC","name":"Motor Retainer (PN 72417)(Jacket)","contains":[{"type":"centeringring","material":"PVC","name":"Outer Jacket"},{"type":"centeringring","material":"PVC","name":"Jacket Threaded Section"},{"type":"centeringring","material":"PVC","name":"Jacket Inner Lip (and Throat)"},{"type":"innertube","length_m":0.0,"outer_d_m":0.0314,"wall_thickness_m":0.0,"material":"PVC","name":"Grip Details","contains":[{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"},{"type":"innertube","length_m":0.01567,"outer_d_m":0.002,"wall_thickness_m":0.001,"material":"PVC","name":"Grip Detail"}]}]}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F32T"}]}],"motors":[{"manufacturer":"AeroTech","designation":"E28T"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F39T"},{"manufacturer":"AeroTech","designation":"F32T"}]}]}
</design>
```
</details>

### V1-106 · MEDIUM
**Prompt:** Design a rocket that goes to about 188 m apogee, reaching about 58.2 m/s max velocity.
**Rocket:** `ork/starfire_bell_x-1.ork` · **Sim:** Simulation 2 · **Motor:** D12
**Why medium: 2 requirements: apogee, max velocity**
**Targets:** apogee 187.89 m · max velocity 58.205 m/s · time to apogee 6.674 s · flight time 44.179 s · touchdown 5.038 m/s · wind 3.57632 m/s
**Parts:** nose cone, 4 body tubes, transition, freeform fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 188 m apogee, reaching about 58.2 m/s max velocity.

2. PROPULSION & ASCENT:
- Motor: D12
- Simulated apogee: 188 m (616 ft)
- Time to apogee: 6.7 s
- Peak velocity: 58 m/s (Mach 0.17)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 44 s; descent from apogee takes 38 s
- Touchdown velocity: 5.04 m/s
</thought>
<design>
{"flight":{"motor":"D12","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"parabolic","shape_param":0.6,"length_m":0.00635,"base_radius_m":0.00114,"wall_thickness_m":0.0,"material":"Basswood","name":"Nose Cone"},{"type":"bodytube","length_m":0.01905,"outer_d_m":0.00228,"material":"Basswood","name":"Body Tube"},{"type":"transition","shape":"ogive","length_m":0.127,"fore_d_m":0.00228,"aft_d_m":0.03366,"material":"Cardboard","name":"Transition","contains":[{"type":"masscomponent","name":"Mass Component - 4.3 oz. epoxy/lead","mass_kg":0.1219,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.2286,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","name":"Main Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes PK-18, 2266","name":"Parachute - 18\""},{"type":"masscomponent","name":"screw  eye (SE-1)","mass_kg":0.00071,"kind":"masscomponent"},{"type":"launchlug","length_m":0.2286,"name":"Launch lug"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Motor Mount Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]},{"type":"centeringring","material":"Paper","name":"Ring"},{"type":"centeringring","material":"Paper","name":"Ring - rear"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Wing - Left"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Wing - Right"},{"type":"pod_set","count":1.0,"name":"Pod Set - Elevator Mount","contains":[{"type":"bodytube","length_m":0.02857,"outer_d_m":0.0028,"material":"Cardboard","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Freeform Fin Set #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Freeform Fin Set #2"}]}]},{"type":"pod_set","count":2.0,"name":"Pod Set - Wing Pods","contains":[{"type":"nosecone","shape":"parabolic","shape_param":0.6,"length_m":0.00635,"base_radius_m":0.00114,"wall_thickness_m":0.0,"material":"Basswood","name":"Nose Cone"},{"type":"bodytube","length_m":0.04813,"outer_d_m":0.00228,"material":"Basswood","name":"Body Tube"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]},{"type":"transition","shape":"ogive","length_m":0.01905,"fore_d_m":0.03366,"aft_d_m":0.0248,"material":"Paper","name":"Transition","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Rudder"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]}]}
</design>
```
</details>

### V1-107 · MEDIUM
**Prompt:** Design a rocket that goes to about 361 m apogee, hitting about 127.8 m/s² max acceleration.
**Rocket:** `ork/starfire_bell_x-1.ork` · **Sim:** Simulation 3 · **Motor:** E12
**Why medium: 2 requirements: apogee, max acceleration**
**Targets:** apogee 360.829 m · max velocity 85.345 m/s · time to apogee 8.753 s · flight time 79.582 s · touchdown 5.082 m/s · wind 3.57632 m/s
**Parts:** nose cone, 4 body tubes, transition, freeform fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 361 m apogee, hitting about 127.8 m/s² max acceleration.

2. PROPULSION & ASCENT:
- Motor: E12
- Simulated apogee: 361 m (1,184 ft)
- Time to apogee: 8.8 s
- Peak velocity: 85 m/s (Mach 0.25)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 80 s; descent from apogee takes 71 s
- Touchdown velocity: 5.08 m/s
</thought>
<design>
{"flight":{"motor":"E12","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"parabolic","shape_param":0.6,"length_m":0.00635,"base_radius_m":0.00114,"wall_thickness_m":0.0,"material":"Basswood","name":"Nose Cone"},{"type":"bodytube","length_m":0.01905,"outer_d_m":0.00228,"material":"Basswood","name":"Body Tube"},{"type":"transition","shape":"ogive","length_m":0.127,"fore_d_m":0.00228,"aft_d_m":0.03366,"material":"Cardboard","name":"Transition","contains":[{"type":"masscomponent","name":"Mass Component - 4.3 oz. epoxy/lead","mass_kg":0.1219,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.2286,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","name":"Main Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes PK-18, 2266","name":"Parachute - 18\""},{"type":"masscomponent","name":"screw  eye (SE-1)","mass_kg":0.00071,"kind":"masscomponent"},{"type":"launchlug","length_m":0.2286,"name":"Launch lug"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Motor Mount Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]},{"type":"centeringring","material":"Paper","name":"Ring"},{"type":"centeringring","material":"Paper","name":"Ring - rear"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Wing - Left"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Wing - Right"},{"type":"pod_set","count":1.0,"name":"Pod Set - Elevator Mount","contains":[{"type":"bodytube","length_m":0.02857,"outer_d_m":0.0028,"material":"Cardboard","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Freeform Fin Set #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Freeform Fin Set #2"}]}]},{"type":"pod_set","count":2.0,"name":"Pod Set - Wing Pods","contains":[{"type":"nosecone","shape":"parabolic","shape_param":0.6,"length_m":0.00635,"base_radius_m":0.00114,"wall_thickness_m":0.0,"material":"Basswood","name":"Nose Cone"},{"type":"bodytube","length_m":0.04813,"outer_d_m":0.00228,"material":"Basswood","name":"Body Tube"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]},{"type":"transition","shape":"ogive","length_m":0.01905,"fore_d_m":0.03366,"aft_d_m":0.0248,"material":"Paper","name":"Transition","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Rudder"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]}]}
</design>
```
</details>

### V1-108 · MEDIUM
**Prompt:** Design a rocket that goes to about 553 m apogee in about 9.6 s to apogee.
**Rocket:** `ork/starfire_bell_x-1.ork` · **Sim:** Simulation 4 · **Motor:** E18W
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 552.513 m · max velocity 123.729 m/s · time to apogee 9.618 s · flight time 114.306 s · touchdown 5.231 m/s · wind 3.57632 m/s
**Parts:** nose cone, 4 body tubes, transition, freeform fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 553 m apogee in about 9.6 s to apogee.

2. PROPULSION & ASCENT:
- Motor: E18W
- Simulated apogee: 553 m (1,813 ft)
- Time to apogee: 9.6 s
- Peak velocity: 124 m/s (Mach 0.37)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 114 s; descent from apogee takes 105 s
- Touchdown velocity: 5.23 m/s
</thought>
<design>
{"flight":{"motor":"E18W","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"parabolic","shape_param":0.6,"length_m":0.00635,"base_radius_m":0.00114,"wall_thickness_m":0.0,"material":"Basswood","name":"Nose Cone"},{"type":"bodytube","length_m":0.01905,"outer_d_m":0.00228,"material":"Basswood","name":"Body Tube"},{"type":"transition","shape":"ogive","length_m":0.127,"fore_d_m":0.00228,"aft_d_m":0.03366,"material":"Cardboard","name":"Transition","contains":[{"type":"masscomponent","name":"Mass Component - 4.3 oz. epoxy/lead","mass_kg":0.1219,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.2286,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","name":"Main Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes PK-18, 2266","name":"Parachute - 18\""},{"type":"masscomponent","name":"screw  eye (SE-1)","mass_kg":0.00071,"kind":"masscomponent"},{"type":"launchlug","length_m":0.2286,"name":"Launch lug"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Motor Mount Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]},{"type":"centeringring","material":"Paper","name":"Ring"},{"type":"centeringring","material":"Paper","name":"Ring - rear"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Wing - Left"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Wing - Right"},{"type":"pod_set","count":1.0,"name":"Pod Set - Elevator Mount","contains":[{"type":"bodytube","length_m":0.02857,"outer_d_m":0.0028,"material":"Cardboard","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Freeform Fin Set #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Freeform Fin Set #2"}]}]},{"type":"pod_set","count":2.0,"name":"Pod Set - Wing Pods","contains":[{"type":"nosecone","shape":"parabolic","shape_param":0.6,"length_m":0.00635,"base_radius_m":0.00114,"wall_thickness_m":0.0,"material":"Basswood","name":"Nose Cone"},{"type":"bodytube","length_m":0.04813,"outer_d_m":0.00228,"material":"Basswood","name":"Body Tube"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]},{"type":"transition","shape":"ogive","length_m":0.01905,"fore_d_m":0.03366,"aft_d_m":0.0248,"material":"Paper","name":"Transition","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Rudder"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]}]}
</design>
```
</details>

### V1-109 · MEDIUM
**Prompt:** Design a rocket that goes to about 685 m apogee, reaching about 151.4 m/s max velocity.
**Rocket:** `ork/starfire_bell_x-1.ork` · **Sim:** Simulation 5 · **Motor:** F24W
**Why medium: 2 requirements: apogee, max velocity**
**Targets:** apogee 684.542 m · max velocity 151.425 m/s · time to apogee 9.791 s · flight time 138.831 s · touchdown 5.23 m/s · wind 3.57632 m/s
**Parts:** nose cone, 4 body tubes, transition, freeform fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 685 m apogee, reaching about 151.4 m/s max velocity.

2. PROPULSION & ASCENT:
- Motor: F24W
- Simulated apogee: 685 m (2,246 ft)
- Time to apogee: 9.8 s
- Peak velocity: 151 m/s (Mach 0.45)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 139 s; descent from apogee takes 129 s
- Touchdown velocity: 5.23 m/s
</thought>
<design>
{"flight":{"motor":"F24W","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"parabolic","shape_param":0.6,"length_m":0.00635,"base_radius_m":0.00114,"wall_thickness_m":0.0,"material":"Basswood","name":"Nose Cone"},{"type":"bodytube","length_m":0.01905,"outer_d_m":0.00228,"material":"Basswood","name":"Body Tube"},{"type":"transition","shape":"ogive","length_m":0.127,"fore_d_m":0.00228,"aft_d_m":0.03366,"material":"Cardboard","name":"Transition","contains":[{"type":"masscomponent","name":"Mass Component - 4.3 oz. epoxy/lead","mass_kg":0.1219,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.2286,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","name":"Main Body tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes PK-18, 2266","name":"Parachute - 18\""},{"type":"masscomponent","name":"screw  eye (SE-1)","mass_kg":0.00071,"kind":"masscomponent"},{"type":"launchlug","length_m":0.2286,"name":"Launch lug"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Motor Mount Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]},{"type":"centeringring","material":"Paper","name":"Ring"},{"type":"centeringring","material":"Paper","name":"Ring - rear"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Wing - Left"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Wing - Right"},{"type":"pod_set","count":1.0,"name":"Pod Set - Elevator Mount","contains":[{"type":"bodytube","length_m":0.02857,"outer_d_m":0.0028,"material":"Cardboard","name":"Body Tube","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Freeform Fin Set #1"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Freeform Fin Set #2"}]}]},{"type":"pod_set","count":2.0,"name":"Pod Set - Wing Pods","contains":[{"type":"nosecone","shape":"parabolic","shape_param":0.6,"length_m":0.00635,"base_radius_m":0.00114,"wall_thickness_m":0.0,"material":"Basswood","name":"Nose Cone"},{"type":"bodytube","length_m":0.04813,"outer_d_m":0.00228,"material":"Basswood","name":"Body Tube"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]},{"type":"transition","shape":"ogive","length_m":0.01905,"fore_d_m":0.03366,"aft_d_m":0.0248,"material":"Paper","name":"Transition","contains":[{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00317,"material":"Basswood","name":"Rudder"}]}],"motors":[{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"F24W"},{"manufacturer":"AeroTech","designation":"F44W"},{"manufacturer":"AeroTech","designation":"E26W"},{"manufacturer":"AeroTech","designation":"E20W"},{"manufacturer":"Quest","designation":"E35W"}]}]}
</design>
```
</details>

### V1-110 · MEDIUM
**Prompt:** Design a rocket that goes on a C6 motor to apogee in about 5.3 s.
**Rocket:** `ork/starfire_star_crusher.ork` · **Sim:** Simulation 2 · **Motor:** C6
**Why medium: 2 requirements: time to apogee, motor**
**Targets:** apogee 165.24 m · max velocity 66.371 m/s · time to apogee 5.256 s · flight time 43.087 s · touchdown 4.39 m/s · wind 3.57632 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes on a C6 motor to apogee in about 5.3 s.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 165 m (542 ft)
- Time to apogee: 5.3 s
- Peak velocity: 66 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 43 s; descent from apogee takes 38 s
- Touchdown velocity: 4.39 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":3.57632},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.1016,"base_radius_m":0.0124,"wall_thickness_m":0.00157,"material":"Polystyrene","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass - Nose Weight","mass_kg":0.00921,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.3302,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","name":"Body Tube","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"SEMROC CP-12RW","name":"Parachute kit, plastic, 12 in, red/white"},{"type":"freeformfinset","fin_count":2.0,"thickness_m":0.003,"material":"Cardboard","name":"Fins  - Canard"},{"type":"innertube","length_m":0.0762,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"AeroTech","designation":"D13W"}]},{"type":"centeringring","material":"Fiber","name":"Centering Ring - F"},{"type":"centeringring","material":"Fiber","name":"Centering Ring - R"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.003,"material":"Cardboard","name":"Fin - Rudder"},{"type":"freeformfinset","fin_count":2.0,"thickness_m":0.003,"material":"Cardboard","name":"Fins - Wings"},{"type":"launchlug","length_m":0.05652,"name":"Launch Lug"},{"type":"pod_set","count":2.0,"name":"Pod Set","contains":[{"type":"bodytube","length_m":0.07112,"outer_d_m":2e-05,"wall_thickness_m":1e-05,"material":"Cardboard","name":"Body Tube","contains":[{"type":"tubefin","fin_count":1.0,"thickness_m":0.00033,"material":"Cardboard","name":"Tube Fin Set"}]}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"AeroTech","designation":"D13W"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"AeroTech","designation":"D13W"}]}]}
</design>
```
</details>

### V1-114 · MEDIUM
**Prompt:** Design a rocket that goes to about 238 m apogee in about 7.0 s to apogee.
**Rocket:** `ork/tlp_phoenix_k-017.ork` · **Sim:** Simulation 2 · **Motor:** D12
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 238.37 m · max velocity 73.312 m/s · time to apogee 6.956 s · flight time 61.388 s · touchdown 4.6209 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 238 m apogee in about 7.0 s to apogee.

2. PROPULSION & ASCENT:
- Motor: D12
- Simulated apogee: 238 m (782 ft)
- Time to apogee: 7.0 s
- Peak velocity: 73 m/s (Mach 0.22)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 61 s; descent from apogee takes 54 s
- Touchdown velocity: 4.62 m/s
</thought>
<design>
{"flight":{"motor":"D12","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.11747,"base_radius_m":0.02079,"wall_thickness_m":0.00159,"material":"Polystyrene","name":"Nose cone","contains":[{"type":"masscomponent","name":"Mass component","mass_kg":0.05245}]},{"type":"bodytube","length_m":0.3048,"wall_thickness_m":0.0006,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.09525,"outer_d_m":0.02514,"wall_thickness_m":0.00051,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.0381,"tip_chord_m":0.0381,"span_m":0.03175,"sweep_m":0.0,"thickness_m":0.00238,"material":"Basswood","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.0635,"name":"Launch lug"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Mylar","name":"Parachute"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]}]}
</design>
```
</details>

### V1-115 · MEDIUM
**Prompt:** Design a rocket that goes to about 394 m apogee in about 9.2 s to apogee.
**Rocket:** `ork/tlp_phoenix_k-017.ork` · **Sim:** Simulation 3 · **Motor:** E9
**Why medium: 2 requirements: apogee, time to apogee**
**Targets:** apogee 393.9 m · max velocity 94.422 m/s · time to apogee 9.2174 s · flight time 96.319 s · touchdown 4.7334 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 394 m apogee in about 9.2 s to apogee.

2. PROPULSION & ASCENT:
- Motor: E9
- Simulated apogee: 394 m (1,292 ft)
- Time to apogee: 9.2 s
- Peak velocity: 94 m/s (Mach 0.28)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 96 s; descent from apogee takes 87 s
- Touchdown velocity: 4.73 m/s
</thought>
<design>
{"flight":{"motor":"E9","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.11747,"base_radius_m":0.02079,"wall_thickness_m":0.00159,"material":"Polystyrene","name":"Nose cone","contains":[{"type":"masscomponent","name":"Mass component","mass_kg":0.05245}]},{"type":"bodytube","length_m":0.3048,"wall_thickness_m":0.0006,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.09525,"outer_d_m":0.02514,"wall_thickness_m":0.00051,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.0381,"tip_chord_m":0.0381,"span_m":0.03175,"sweep_m":0.0,"thickness_m":0.00238,"material":"Basswood","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.0635,"name":"Launch lug"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Mylar","name":"Parachute"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]}]}
</design>
```
</details>

### V1-116 · MEDIUM
**Prompt:** Design a rocket that goes about 254 m and is back down in under 63 seconds.
**Rocket:** `ork/tlp_phoenix_k-017.ork` · **Sim:** Simulation 6 · **Motor:** D9
**Why medium: 2 requirements: apogee, flight time**
**Targets:** apogee 253.63 m · max velocity 77.327 m/s · time to apogee 7.3842 s · flight time 62.722 s · touchdown 4.3762 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 4 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes about 254 m and is back down in under 63 seconds.

2. PROPULSION & ASCENT:
- Motor: D9
- Simulated apogee: 254 m (832 ft)
- Time to apogee: 7.4 s
- Peak velocity: 77 m/s (Mach 0.23)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 63 s; descent from apogee takes 55 s
- Touchdown velocity: 4.38 m/s
</thought>
<design>
{"flight":{"motor":"D9","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.11747,"base_radius_m":0.02079,"wall_thickness_m":0.00159,"material":"Polystyrene","name":"Nose cone","contains":[{"type":"masscomponent","name":"Mass component","mass_kg":0.05245}]},{"type":"bodytube","length_m":0.3048,"wall_thickness_m":0.0006,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.09525,"outer_d_m":0.02514,"wall_thickness_m":0.00051,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]},{"type":"freeformfinset","fin_count":4.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"trapezoidfin","fin_count":4.0,"root_chord_m":0.0381,"tip_chord_m":0.0381,"span_m":0.03175,"sweep_m":0.0,"thickness_m":0.00238,"material":"Basswood","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.0635,"name":"Launch lug"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Mylar","name":"Parachute"}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]}],"motors":[{"manufacturer":"Estes","designation":"C11"},{"manufacturer":"Estes","designation":"D12"},{"manufacturer":"Estes","designation":"E9"},{"manufacturer":"AeroTech","designation":"D9"},{"manufacturer":"Estes","designation":"E12"},{"manufacturer":"AeroTech","designation":"E18W"},{"manufacturer":"AeroTech","designation":"E28"}]}]}
</design>
```
</details>

<a id="hard-13"></a>

## 🔴 Hard (13)

### NEW-006 · HARD
**Prompt:** Design a small rocket that stays up for a bit more than a minute.
**Rocket:** `ork/ESTES Alpha 3.ork` · **Sim:** Simulation 2 · **Motor:** B4
**Why hard: 1 requirement: flight time**
**Targets:** apogee 237.68 m · max velocity 85.849 m/s · time to apogee 5.88 s · flight time 63.704 s · touchdown 3.872 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a small rocket that stays up for a bit more than a minute.

2. PROPULSION & ASCENT:
- Motor: B4
- Simulated apogee: 238 m (780 ft)
- Time to apogee: 5.9 s
- Peak velocity: 86 m/s (Mach 0.25)

3. RECOVERY & DESCENT:
- Parachute 0.25 m diameter, deploys at ejection
- Total flight time 64 s; descent from apogee takes 58 s
- Touchdown velocity: 3.87 m/s
</thought>
<design>
{"flight":{"motor":"B4","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Hauptstufe","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.065,"base_radius_m":0.0124,"wall_thickness_m":0.002,"material":"PVC","name":"Spitze"},{"type":"bodytube","length_m":0.139,"outer_d_m":0.0248,"wall_thickness_m":0.0004,"material":"Cardboard","name":"K\u00f6rperrohr","contains":[{"type":"parachute","diameter_m":0.25,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (thin)","name":"Fallschirm"}]},{"type":"bodytube","length_m":0.057,"outer_d_m":0.0248,"wall_thickness_m":0.002,"material":"PVC","name":"K\u00f6rperrohr","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.057,"tip_chord_m":0.03,"span_m":0.04,"sweep_m":0.07,"thickness_m":0.0001,"material":"PVC","name":"Trapezoide Leitwerke"},{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Innenrohr","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]}],"motors":[{"manufacturer":"Klima","designation":"A6"},{"manufacturer":"Klima","designation":"B4"},{"manufacturer":"Klima","designation":"C6"}]}]}
</design>
```
</details>

### NEW-015 · HARD
**Prompt:** Make a rocket that shoots up fast and is back on the ground in under 20 seconds.
**Rocket:** `ork/Estes_Mark2.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why hard: 1 requirement: flight time**
**Targets:** apogee 179.58 m · max velocity 83.133 m/s · time to apogee 5.487 s · flight time 17.262 s · touchdown 17.5 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 streamer recovery
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that shoots up fast and is back on the ground in under 20 seconds.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 180 m (589 ft)
- Time to apogee: 5.5 s
- Peak velocity: 83 m/s (Mach 0.24)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 17 s; descent from apogee takes 12 s
- Touchdown velocity: 17.50 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.05558,"base_radius_m":0.00972,"material":"Balsa","name":"BNC-30E"},{"type":"bodytube","length_m":0.0889,"wall_thickness_m":0.00053,"material":"Cardboard","name":"BT-30A","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.0254,"deploy_event":"ejection","material":"Ripstop nylon","name":"Streamer"}]},{"type":"bodytube","length_m":0.06985,"wall_thickness_m":0.00053,"material":"Cardboard","name":"BT-30J","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00159,"material":"Balsa","name":"Freeform fin set"},{"type":"launchlug","length_m":0.03175,"name":"LL-2A"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-017 · HARD
**Prompt:** Design a short, snappy flight that is over in under 15 seconds.
**Rocket:** `ork/Estes Wizard.ork` · **Sim:** Simulation 2 · **Motor:** A8
**Why hard: 1 requirement: flight time**
**Targets:** apogee 176.616 m · max velocity 77.908 m/s · time to apogee 5.548 s · flight time 14.144 s · touchdown 25.582 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, freeform fins, 1 stage, 1 streamer recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a short, snappy flight that is over in under 15 seconds.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 177 m (579 ft)
- Time to apogee: 5.5 s
- Peak velocity: 78 m/s (Mach 0.23)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 14 s; descent from apogee takes 9 s
- Touchdown velocity: 25.58 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"parabolic","shape_param":1.0,"length_m":0.07,"base_radius_m":0.00935,"wall_thickness_m":0.00159,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.221,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes EST 3085","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"streamer","strip_length_m":0.45,"strip_width_m":0.03,"deploy_event":"ejection","material":"Polyethylene (thin)","name":"Streamer"},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00157,"material":"Balsa","name":"Freeform fin set"}],"motors":[{"manufacturer":"Estes","designation":"A8"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"}]}]}
</design>
```
</details>

### NEW-020 · HARD
**Prompt:** Build a small, low flight that is over in under 10 seconds.
**Rocket:** `ork/FlipFlyer.ork` · **Sim:** Simulation 1 · **Motor:** B6
**Why hard: 1 requirement: flight time**
**Targets:** apogee 59.117 m · max velocity 31.33 m/s · time to apogee 3.82 s · flight time 8.668 s · touchdown 19.815 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 3 fins, 2 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Build a small, low flight that is over in under 10 seconds.

2. PROPULSION & ASCENT:
- Motor: B6
- Simulated apogee: 59 m (194 ft)
- Time to apogee: 3.8 s
- Peak velocity: 31 m/s (Mach 0.09)

3. RECOVERY & DESCENT:
- Parachute 0.23 m diameter, deploys at ejection
- Total flight time 9 s; descent from apogee takes 5 s
- Touchdown velocity: 19.82 m/s
</thought>
<design>
{"flight":{"motor":"B6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Nose","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06985,"base_radius_m":0.0124,"wall_thickness_m":0.00157,"material":"Polystyrene","preset":"Estes PNC-50KA","name":"Nose cone","contains":[{"type":"masscomponent","name":"Nose Clay","mass_kg":0.01451,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.128,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50, 30352","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"parachute","diameter_m":0.2286,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes parachute_9in, 002268","name":"Parachute"}]}]},{"type":"stage_marker","name":"Sustainer","contains":[{"type":"bodytube","length_m":0.2,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50, 30352","name":"Body tube","contains":[{"type":"launchlug","length_m":0.055,"name":"Launch lug"}]},{"type":"bodytube","length_m":0.065,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"PVC","name":"Engine mount and fin box","contains":[{"type":"engineblock","name":"Engine block"},{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Motor Mount","motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.001,"material":"PVC","name":"Notched PVC Fins"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.23,"tip_chord_m":0.22,"span_m":0.001,"sweep_m":0.025,"thickness_m":0.025,"material":"PVC","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-023 · HARD
**Prompt:** Make a rocket with a really long, slow descent.
**Rocket:** `ork/OpenRocket Estes Super Shot Design.ork` · **Sim:** Fight Path Recovery · **Motor:** C6
**Why hard: 1 requirement: flight time**
**Targets:** apogee 247.058 m · max velocity 81.115 m/s · time to apogee 6.965 s · flight time 91.752 s · touchdown 2.931 m/s · wind 6.7056 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 2 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket with a really long, slow descent.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 247 m (811 ft)
- Time to apogee: 7.0 s
- Peak velocity: 81 m/s (Mach 0.24)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 92 s; descent from apogee takes 85 s
- Touchdown velocity: 2.93 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":6.7056},"components":[{"type":"stage_marker","name":"Sustainer"},{"type":"stage_marker","name":"Stage","contains":[{"type":"nosecone","shape":"power","shape_param":0.5,"length_m":0.11639,"base_radius_m":0.01231,"wall_thickness_m":0.001,"material":"Styrene Plastic","name":"Nose Cone"},{"type":"bodytube","length_m":0.229,"outer_d_m":0.0248,"wall_thickness_m":0.00045,"material":"Cardboard","name":"Estes Super Shot Body Tube","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes parachute_18in, 035823","name":"Parachute, plastic, preassembled, 18 in., Der Red Max, PN 035823"},{"type":"masscomponent","name":"Estes Altimeter","mass_kg":0.01177,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.229,"outer_d_m":0.0248,"wall_thickness_m":0.00045,"material":"Cardboard","name":"Estes Super Shot Body Tube","contains":[{"type":"launchlug","length_m":0.058,"name":"Launch Lug"}]},{"type":"bodytube","length_m":0.09289,"outer_d_m":0.05,"wall_thickness_m":0.002,"material":"Styrene Plastic","name":"Fin Tube","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.0,"material":"Styrene Plastic","name":"Freeform Fin Set"},{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### NEW-026 · HARD
**Prompt:** Make a big, slow-floating rocket that stays up well over a minute.
**Rocket:** `ork/Renegade.ork` · **Sim:** Simulation 1 · **Motor:** E9
**Why hard: 1 requirement: flight time**
**Targets:** apogee 377.12 m · max velocity 97.433 m/s · time to apogee 8.687 s · flight time 99.608 s · touchdown 3.929 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, freeform fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a big, slow-floating rocket that stays up well over a minute.

2. PROPULSION & ASCENT:
- Motor: E9
- Simulated apogee: 377 m (1,237 ft)
- Time to apogee: 8.7 s
- Peak velocity: 97 m/s (Mach 0.29)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 100 s; descent from apogee takes 91 s
- Touchdown velocity: 3.93 m/s
</thought>
<design>
{"flight":{"motor":"E9","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.17145,"base_radius_m":0.02079,"wall_thickness_m":0.00317,"material":"Polystyrene PS","preset":"Estes PNC-60AH","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"wall_thickness_m":0.00056,"material":"Cardboard","name":"BT-60","contains":[{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.2159,"wall_thickness_m":0.00056,"material":"Cardboard","name":"BT-60HE","contains":[{"type":"freeformfinset","fin_count":3.0,"thickness_m":0.00317,"material":"Balsa","name":"Freeform fin set"},{"type":"innertube","length_m":0.381,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Cardboard","name":"BT-50KE","motors":[{"manufacturer":"Estes","designation":"E9"}]},{"type":"centeringring","material":"Fiber","name":"Centering ring"},{"type":"centeringring","material":"Fiber","name":"Centering ring"},{"type":"centeringring","material":"Fiber","name":"Centering ring"}],"motors":[{"manufacturer":"Estes","designation":"E9"}]}],"motors":[{"manufacturer":"Estes","designation":"E9"}]}]}
</design>
```
</details>

### NEW-033 · HARD
**Prompt:** Build a rocket that goes really high for a low-power motor.
**Rocket:** `ork/estes-007275–STERLING_SILVER.ork` · **Sim:** Simulation 3 · **Motor:** C6
**Why hard: 0 requirements (no target value stated in the prompt)**
**Targets:** apogee 642.5 m · max velocity 156.64 m/s · time to apogee 10.412 s · flight time 34.775 s · touchdown 28.755 m/s · wind 2 m/s
**Parts:** nose cone, 3 body tubes, 6 fins, 2 stages, 1 streamer recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Build a rocket that goes really high for a low-power motor.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 642 m (2,108 ft)
- Time to apogee: 10.4 s
- Peak velocity: 157 m/s (Mach 0.46)

3. RECOVERY & DESCENT:
- Streamer recovery
- Total flight time 35 s; descent from apogee takes 24 s
- Touchdown velocity: 28.75 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.06731,"base_radius_m":0.00935,"wall_thickness_m":0.00159,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.3048,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes EST 3085","name":"Body tube","contains":[{"type":"streamer","strip_length_m":0.762,"strip_width_m":0.03175,"deploy_event":"ejection","material":"Polyethylene (thin)","name":"Streamer"}]},{"type":"bodytube","length_m":0.07,"wall_thickness_m":0.00035,"material":"Cardboard","name":"Body tube","contains":[{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.043,"tip_chord_m":0.0255,"span_m":0.03188,"sweep_m":0.03188,"thickness_m":0.00234,"material":"Balsa","name":"Trapezoidal fin set"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"stage_marker","name":"Booster stage","contains":[{"type":"bodytube","length_m":0.08916,"wall_thickness_m":0.00035,"material":"Cardboard","name":"Body tube","contains":[{"type":"engineblock","name":"Engine block"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.06186,"tip_chord_m":0.04116,"span_m":0.04743,"sweep_m":0.04743,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### U-020 · HARD
**Prompt:** Design a rocket that goes on a C11 motor to apogee in about 2.4 s.
**Rocket:** `ork/rockets__bt_55.ork` · **Sim:** Simulation 1 · **Motor:** C6
**Why hard: 1 requirement: time to apogee**
**Targets:** apogee 84.351 m · max velocity 67.805 m/s · time to apogee 2.357 s · flight time 30.891 s · touchdown 3.169 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 parachute recovery, motor mount
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes on a C11 motor to apogee in about 2.4 s.

2. PROPULSION & ASCENT:
- Motor: C6
- Simulated apogee: 84 m (277 ft)
- Time to apogee: 2.4 s
- Peak velocity: 68 m/s (Mach 0.20)

3. RECOVERY & DESCENT:
- Parachute 0.46 m diameter, deploys at ejection
- Total flight time 31 s; descent from apogee takes 29 s
- Touchdown velocity: 3.17 m/s
</thought>
<design>
{"flight":{"motor":"C6","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1016,"base_radius_m":0.01683,"wall_thickness_m":0.00317,"material":"Polystyrene PS","name":"Nose cone"},{"type":"bodytube","length_m":0.4572,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","preset":"Estes EST 3087","name":"Body tube","contains":[{"type":"innertube","length_m":0.07,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"launchlug","length_m":0.03175,"name":"Launch lug"},{"type":"parachute","diameter_m":0.4572,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene LDPE","preset":"Estes 302267","name":"Parachute"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.09,"tip_chord_m":0.035,"span_m":0.05,"sweep_m":0.025,"thickness_m":0.003,"material":"Cardboard","name":"Trapezoidal fin set"}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}],"motors":[{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Estes","designation":"C11"}]}]}
</design>
```
</details>

### U-199 · HARD
**Prompt:** Design a rocket that goes to about 5,899 m apogee with a total flight time of about 317 s.
**Rocket:** `ork/ASCENSION.ork` · **Sim:** Simulation 1 (Florida baseline) · **Motor:** L1115
**Why hard: 1 requirement: apogee**
**⚠️ prompt/target mismatch:** prompt asks for 5,899 m apogee / 317 s flight; rocket actually flies 5,748 m and lands after 28.5 s
**Targets:** apogee 5747.8 m · max velocity 612.43 m/s · time to apogee 28.39 s · flight time 28.49 s · touchdown — m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 1 fins, 1 stage, 1 parachute + 1 streamer recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Design a rocket that goes to about 5,899 m apogee with a total flight time of about 317 s.

2. PROPULSION & ASCENT:
- Motor: L1115
- Simulated apogee: 5,748 m (18,858 ft)
- Time to apogee: 28.4 s
- Peak velocity: 612 m/s (Mach 1.83)

3. RECOVERY & DESCENT:
- Streamer recovery
- Parachute 1.47 m diameter, deploys at 600 m (1969 ft)
- Total flight time 28 s; descent from apogee takes 0 s
</thought>
<design>
{"flight":{"motor":"L1115","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.18,"base_radius_m":0.0525,"wall_thickness_m":0.003,"material":"PVC","name":"Nose cone","contains":[{"type":"masscomponent","name":"Avionics","mass_kg":0.2,"kind":"altimeter"}]},{"type":"bodytube","length_m":0.32,"outer_d_m":0.105,"wall_thickness_m":0.003,"material":"Carbon fiber","name":"Body tube 1","contains":[{"type":"streamer","strip_length_m":0.5,"strip_width_m":0.06,"deploy_event":"altitude","material":"Ripstop nylon","name":"Streamer"},{"type":"parachute","diameter_m":1.47,"deploy_event":"altitude","deploy_altitude_m":600.0,"deploy_delay_s":0.0,"line_count":8.0,"material":"Ripstop nylon","name":"Parachute"}]},{"type":"bodytube","length_m":0.655,"outer_d_m":0.105,"wall_thickness_m":0.003,"material":"Carbon fiber","name":"Body tube 2","contains":[{"type":"engineblock","name":"Engine block"},{"type":"centeringring","material":"Plywood (birch)","name":"Centering ring"},{"type":"innertube","length_m":0.618,"outer_d_m":0.08,"wall_thickness_m":0.00025,"material":"Cardboard","name":"Inner Tube"},{"type":"engineblock","name":"Motor Retainer"},{"type":"trapezoidfin","root_chord_m":0.17,"tip_chord_m":0.05,"span_m":0.088,"sweep_m":0.2,"thickness_m":0.003,"material":"Aluminum","name":"Fins"}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"L1115"}]}],"motors":[{"manufacturer":"Cesaroni Technology","designation":"L1115"}]}]}
</design>
```
</details>

### U-441 · HARD
**Prompt:** Make a rocket that hits 244 m and stays up about 61 s, weighs around 84 g and is about 44 cm long.
**Rocket:** `ork/Pods--airframes and winglets.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why hard: 0 requirements (no target value stated in the prompt)**
**⚠️ prompt/target mismatch:** prompt asks for 244 m / 61 s; rocket actually flies 31.9 m over 10.3 s
**Targets:** apogee 31.928 m · max velocity 24.753 m/s · time to apogee 2.807 s · flight time 10.323 s · touchdown 4.892 m/s · wind 2.2352 m/s
**Parts:** nose cone, 3 body tubes, freeform fins, 5 fins, pods, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 244 m and stays up about 61 s, weighs around 84 g and is about 44 cm long.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 32 m (105 ft)
- Time to apogee: 2.8 s
- Peak velocity: 25 m/s (Mach 0.07)

3. RECOVERY & DESCENT:
- Parachute 0.30 m diameter, deploys at ejection
- Total flight time 10 s; descent from apogee takes 8 s
- Touchdown velocity: 4.89 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.2352},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.13653,"base_radius_m":0.01683,"wall_thickness_m":0.00093,"material":"Polystyrene","name":"Nose Cone","contains":[{"type":"masscomponent","name":"Mass Component","mass_kg":0.00992,"kind":"masscomponent"},{"type":"freeformfinset","fin_count":1.0,"thickness_m":0.00698,"material":"Balsa","name":"Cockpit"}]},{"type":"bodytube","length_m":0.3048,"outer_d_m":0.03366,"wall_thickness_m":0.00053,"material":"Paper","name":"Airframe","contains":[{"type":"parachute","diameter_m":0.3048,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","name":"Parachute kit, plastic, 12 in., PN 2263"},{"type":"launchlug","length_m":0.05239,"name":"Launch Lug"},{"type":"freeformfinset","fin_count":2.0,"thickness_m":0.00236,"material":"Balsa","name":"Wings"},{"type":"pod_set","count":2.0,"name":"Wing pods","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.0254,"base_radius_m":0.00687,"wall_thickness_m":0.00198,"material":"Polystyrene","name":"Pod nose"},{"type":"bodytube","length_m":0.0381,"outer_d_m":0.01374,"wall_thickness_m":0.00036,"material":"Paper","name":"Pod body"},{"type":"nosecone","shape":"ellipsoid","length_m":0.0127,"base_radius_m":0.00687,"material":"Balsa","name":"Pod tail"}]},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0508,"tip_chord_m":0.0254,"span_m":0.03175,"sweep_m":0.025,"thickness_m":0.00236,"material":"Balsa","name":"Vertical stabilizer"},{"type":"pod_set","count":1.0,"name":"Horizontal stab pod","contains":[{"type":"bodytube","length_m":0.0,"wall_thickness_m":0.0,"material":"Cardboard","name":"(phantom body)","contains":[{"type":"trapezoidfin","fin_count":2.0,"root_chord_m":0.02794,"tip_chord_m":0.0127,"span_m":0.01905,"sweep_m":0.0127,"thickness_m":0.00236,"material":"Balsa","name":"Horizontal stabilizer"}]}]},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0762,"tip_chord_m":0.0381,"span_m":0.01588,"sweep_m":0.03175,"thickness_m":0.00236,"material":"Balsa","name":"Left ventral fin"},{"type":"trapezoidfin","fin_count":1.0,"root_chord_m":0.0762,"tip_chord_m":0.0381,"span_m":0.01588,"sweep_m":0.03175,"thickness_m":0.00236,"material":"Balsa","name":"Right ventral fin"},{"type":"innertube","length_m":0.06985,"outer_d_m":0.0187,"wall_thickness_m":0.00033,"material":"Paper","name":"18mm Motor mount","contains":[{"type":"centeringring","material":"Fiber","name":"Forward centering ring"},{"type":"centeringring","material":"Fiber","name":"Aft centering ring"},{"type":"engineblock","name":"Engine Block"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"C12"},{"manufacturer":"Quest","designation":"D16"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"C12"},{"manufacturer":"Quest","designation":"D16"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"},{"manufacturer":"Quest","designation":"C12"},{"manufacturer":"Quest","designation":"D16"}]}]}
</design>
```
</details>

### U-443 · HARD
**Prompt:** Make a rocket that hits 263 m and stays up about 73 s, weighs around 88 g and is about 50 cm long.
**Rocket:** `ork/Deployable payload.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why hard: 0 requirements (no target value stated in the prompt)**
**⚠️ prompt/target mismatch:** prompt asks for 263 m / 73 s; rocket actually flies 31.8 m over 10.8 s
**Targets:** apogee 31.783 m · max velocity 21.802 m/s · time to apogee 2.867 s · flight time 10.759 s · touchdown 4.398 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 2 stages, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 263 m and stays up about 73 s, weighs around 88 g and is about 50 cm long.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 32 m (104 ft)
- Time to apogee: 2.9 s
- Peak velocity: 22 m/s (Mach 0.07)

3. RECOVERY & DESCENT:
- Parachute 0.20 m diameter, deploys at ejection
- Total flight time 11 s; descent from apogee takes 8 s
- Touchdown velocity: 4.40 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Deployable Payload","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1,"base_radius_m":0.0125,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose cone"},{"type":"bodytube","length_m":0.1016,"outer_d_m":0.025,"wall_thickness_m":0.002,"material":"Cardboard","name":"Body Tube","contains":[{"type":"masscomponent","name":"Payload","mass_kg":0.01417,"kind":"payload"}]}]},{"type":"stage_marker","name":"Booster","contains":[{"type":"bodytube","length_m":0.3,"outer_d_m":0.025,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube","contains":[{"type":"parachute","diameter_m":0.2032,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene film","preset":"Estes PK-8, 2260","name":"Parachute kit, plastic, 8 in., PN 2260"},{"type":"masscomponent","name":"Wadding","mass_kg":0.002,"kind":"masscomponent"},{"type":"launchlug","length_m":0.035,"name":"Launch lug"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.0508,"tip_chord_m":0.0127,"span_m":0.03,"sweep_m":0.0254,"thickness_m":0.002,"material":"Cardboard","name":"Trapezoidal fin set"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"innertube","length_m":0.075,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### U-444 · HARD
**Prompt:** Make a rocket that hits 273 m and stays up about 70 s, weighs around 81 g and is about 33 cm long.
**Rocket:** `ork/3D printable nose cone and fins.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why hard: 0 requirements (no target value stated in the prompt)**
**⚠️ prompt/target mismatch:** prompt asks for 273 m / 70 s; rocket actually flies 38.7 m over 12.2 s
**Targets:** apogee 38.733 m · max velocity 24.764 m/s · time to apogee 3.085 s · flight time 12.194 s · touchdown 4.691 m/s · wind 2 m/s
**Parts:** nose cone, 2 body tubes, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 273 m and stays up about 70 s, weighs around 81 g and is about 33 cm long.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 39 m (127 ft)
- Time to apogee: 3.1 s
- Peak velocity: 25 m/s (Mach 0.07)

3. RECOVERY & DESCENT:
- Parachute 0.31 m diameter, deploys at ejection
- Total flight time 12 s; descent from apogee takes 9 s
- Touchdown velocity: 4.69 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ogive","shape_param":1.0,"length_m":0.1,"base_radius_m":0.0124,"wall_thickness_m":0.0019,"material":"PETG - 100% infill","name":"Printable nose cone","contains":[{"type":"masscomponent","name":"Screw Eye","mass_kg":0.0009,"kind":"recoveryhardware"}]},{"type":"bodytube","length_m":0.1524,"outer_d_m":0.0248,"wall_thickness_m":0.00033,"material":"Paper","preset":"Estes BT-50FE, 30359","name":"Paper Body Tube -- DO NOT PRINT","contains":[{"type":"parachute","diameter_m":0.31,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Polyethylene (heavy)","name":"Parachute"},{"type":"masscomponent","name":"Wadding","mass_kg":0.002,"kind":"masscomponent"}]},{"type":"bodytube","length_m":0.0762,"outer_d_m":0.0248,"wall_thickness_m":0.0008,"material":"PETG - 100% infill","name":"Printable Fin Can and Motor Mount","contains":[{"type":"launchlug","length_m":0.035,"name":"Launch lug"},{"type":"trapezoidfin","fin_count":3.0,"root_chord_m":0.0508,"tip_chord_m":0.0508,"span_m":0.03,"sweep_m":0.0254,"thickness_m":0.002,"material":"PETG - 100% infill","name":"Trapezoidal fin set"},{"type":"centeringring","material":"PETG - 100% infill","name":"Centering ring"},{"type":"centeringring","material":"PETG - 100% infill","name":"Centering ring"},{"type":"innertube","length_m":0.075,"outer_d_m":0.0217,"wall_thickness_m":0.0015,"material":"PETG - 100% infill","name":"Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B6"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>

### U-452 · HARD
**Prompt:** Make a rocket that hits 307 m and stays up about 59 s, weighs around 262 g and is about 70 cm long.
**Rocket:** `ork/Clustered motors.ork` · **Sim:** Simulation 1 · **Motor:** A8
**Why hard: 0 requirements (no target value stated in the prompt)**
**⚠️ prompt/target mismatch:** prompt asks for 307 m / 59 s; rocket actually flies 57.9 m over 13.7 s
**Targets:** apogee 57.857 m · max velocity 32.36 m/s · time to apogee 3.622 s · flight time 13.745 s · touchdown 6.27 m/s · wind 2 m/s
**Parts:** nose cone, 1 body tube, 3 fins, 1 stage, 1 parachute recovery, motor mount, mass/ballast
<details><summary>Full model answer</summary>

```
<thought>
1. REQUIREMENTS PARSED:
- Make a rocket that hits 307 m and stays up about 59 s, weighs around 262 g and is about 70 cm long.

2. PROPULSION & ASCENT:
- Motor: A8
- Simulated apogee: 58 m (190 ft)
- Time to apogee: 3.6 s
- Peak velocity: 32 m/s (Mach 0.10)

3. RECOVERY & DESCENT:
- Parachute 0.40 m diameter, deploys at ejection
- Total flight time 14 s; descent from apogee takes 10 s
- Touchdown velocity: 6.27 m/s
</thought>
<design>
{"flight":{"motor":"A8","wind_ms":2.0},"components":[{"type":"stage_marker","name":"Sustainer","contains":[{"type":"nosecone","shape":"ellipsoid","length_m":0.1,"base_radius_m":0.0275,"wall_thickness_m":0.002,"material":"Polystyrene","name":"Nose cone"},{"type":"bodytube","length_m":0.6,"outer_d_m":0.055,"wall_thickness_m":0.001,"material":"Cardboard","name":"Body tube","contains":[{"type":"innertube","length_m":0.075,"outer_d_m":0.019,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Clustered Inner Tube","contains":[{"type":"engineblock","name":"Engine block"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"C6"}]},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"parachute","diameter_m":0.4,"deploy_event":"ejection","deploy_altitude_m":200.0,"deploy_delay_s":0.0,"line_count":6.0,"material":"Ripstop nylon","name":"Parachute"},{"type":"masscomponent","name":"Wadding","mass_kg":0.002,"kind":"masscomponent"},{"type":"launchlug","length_m":0.035,"name":"Launch lug"},{"type":"launchlug","length_m":0.035,"name":"Launch lug"},{"type":"innertube","length_m":0.38,"outer_d_m":0.02,"wall_thickness_m":0.0005,"material":"Cardboard","name":"Pressure distribution tube"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"centeringring","material":"Cardboard","name":"Centering ring"},{"type":"ellipticalfin","fin_count":3.0,"root_chord_m":0.06,"span_m":0.06,"thickness_m":0.003,"material":"Cardboard","name":"Elliptical fin set"}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"C6"}]}],"motors":[{"manufacturer":"Estes","designation":"A8"},{"manufacturer":"Estes","designation":"B4"},{"manufacturer":"Estes","designation":"C6"}]}]}
</design>
```
</details>
