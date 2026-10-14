# More .ork Prompts — SFT-Ready (grouped by rocket type)

Source: `rocket_files/prompts/more_ork_prompts.csv` (52 rows) + `more_ork_prompts.txt` (52 lines),
from `rocket_files/reports/more_ork_files_sim_data.csv` (52 sim rows, 15 files, 9 rocket types).
This file merges both into one SFT-ready doc: one **USER prompt** (underspecified, 2–3 params)
paired with one **ASSISTANT target** (full sim spec) per row, grouped by rocket type.

## How to use for SFT

- System prompt (use for every example):
  `You design model rockets from performance requirements. Given a partial requirement, output a complete rocket specification.`
- Train on USER → ASSISTANT pairs below. Compute loss on ASSISTANT only.
- Each USER prompt is intentionally partial (2–3 params). The ASSISTANT target is the full spec JSON — that is the supervision signal.
- Dedup warning: identical sim vectors repeat across files (orhelper↔Prometeus sims 1–5; CenturiArrow300↔rocket; see § Leakage). Split train/val by **file family**, not by row, or the model will memorize duplicates.
- Suggested split: train on Raketa + A-simple + Centuri + Rocket + X-Ray + Bryant + Elliptical + Green-Eggs; hold out BOTH Prometeus files as the near-duplicate generalization test (or vice versa).

## Leakage map (must read before splitting)

- EXACT duplicates: `orhelper__simple.ork` sims 1–5 = `project-prometeus__rocket.ork` sims 1–5 = `project-prometeus__rocket2.ork` sims 1–5 (same apogee/velocity/accel/time values).
- EXACT duplicates: `openrocket-file-utils__CenturiArrow300.ork` sims 1–3 = `openrocket-file-utils__rocket.ork` sims 1–3.
- NEAR duplicates: `openrocket__asimple.ork` sims 1–5 ≈ orhelper family (same motors A8,B4,C6, different numbers — genuinely different sims, safe to keep but same template family).
- Generic name alert: rocket_name `Rocket` covers 3 unrelated designs (Rocket_Model/G54, example_simple_1/F15, bt_55/C11,C6) — grouped under one heading below but split into sub-groups by file; do not treat them as one design.

## 1. Rocket type: Raketa — 15 pairs
- Files: `czech-rocket-challenge-2025__Raketa.ork`
- Motors: `GragasMAY24`
- Apogee range: 581–644 m

**USER** (`Simulation 1`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 618 m apogee with a total flight time of about 146.7 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 1",
 "apogee_m": 617.783,
 "max_velocity_mps": 127.543,
 "max_accel_mps2": 71.07,
 "time_to_apogee_s": 11.408,
 "flight_time_s": 146.734,
 "ground_hit_velocity_mps": 4.495
}
```

**USER** (`Simulation 2`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 635 m apogee, reaching about 142.5 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 2",
 "apogee_m": 635.263,
 "max_velocity_mps": 142.491,
 "max_accel_mps2": 82.03,
 "time_to_apogee_s": 11.151,
 "flight_time_s": 24.488,
 "ground_hit_velocity_mps": 73.894
}
```

**USER** (`Simulation 3`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 640 m apogee, hitting about 82.0 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 3",
 "apogee_m": 639.553,
 "max_velocity_mps": 142.552,
 "max_accel_mps2": 82.007,
 "time_to_apogee_s": 11.19,
 "flight_time_s": 24.576,
 "ground_hit_velocity_mps": 74.011
}
```

**USER** (`Simulation 4`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 644 m apogee in about 11.1 s to apogee on a GragasMAY24 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 4",
 "apogee_m": 644.421,
 "max_velocity_mps": 144.14,
 "max_accel_mps2": 83.186,
 "time_to_apogee_s": 11.149,
 "flight_time_s": 24.678,
 "ground_hit_velocity_mps": 73.671
}
```

**USER** (`Simulation 5`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 135.9 m/s max velocity with a 24.2 s flight and touchdown at about 75.2 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 5",
 "apogee_m": 619.515,
 "max_velocity_mps": 135.929,
 "max_accel_mps2": 77.377,
 "time_to_apogee_s": 11.147,
 "flight_time_s": 24.197,
 "ground_hit_velocity_mps": 75.211
}
```

**USER** (`Simulation 6`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 613 m apogee with a total flight time of about 24.0 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 6",
 "apogee_m": 612.92,
 "max_velocity_mps": 135.789,
 "max_accel_mps2": 77.39,
 "time_to_apogee_s": 11.105,
 "flight_time_s": 24.042,
 "ground_hit_velocity_mps": 74.992
}
```

**USER** (`Simulation 7`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 611 m apogee, reaching about 135.5 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 7",
 "apogee_m": 611.342,
 "max_velocity_mps": 135.548,
 "max_accel_mps2": 77.235,
 "time_to_apogee_s": 11.083,
 "flight_time_s": 186.378,
 "ground_hit_velocity_mps": 3.448
}
```

**USER** (`Simulation 8`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 616 m apogee, hitting about 77.2 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 8",
 "apogee_m": 615.892,
 "max_velocity_mps": 135.602,
 "max_accel_mps2": 77.223,
 "time_to_apogee_s": 11.14,
 "flight_time_s": 187.688,
 "ground_hit_velocity_mps": 3.513
}
```

**USER** (`Simulation 9`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 622 m apogee in about 11.2 s to apogee on a GragasMAY24 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 9",
 "apogee_m": 621.774,
 "max_velocity_mps": 135.703,
 "max_accel_mps2": 77.209,
 "time_to_apogee_s": 11.193,
 "flight_time_s": 189.337,
 "ground_hit_velocity_mps": 3.445
}
```

**USER** (`Simulation 10`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 136.1 m/s max velocity with a 189.3 s flight and touchdown at about 3.5 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 10",
 "apogee_m": 619.832,
 "max_velocity_mps": 136.116,
 "max_accel_mps2": 77.52,
 "time_to_apogee_s": 11.167,
 "flight_time_s": 189.318,
 "ground_hit_velocity_mps": 3.459
}
```

**USER** (`Simulation 11`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 638 m apogee with a total flight time of about 160.9 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 11",
 "apogee_m": 638.45,
 "max_velocity_mps": 140.364,
 "max_accel_mps2": 80.396,
 "time_to_apogee_s": 11.234,
 "flight_time_s": 160.851,
 "ground_hit_velocity_mps": 4.219
}
```

**USER** (`Simulation 12`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 629 m apogee, reaching about 140.3 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 12",
 "apogee_m": 629.354,
 "max_velocity_mps": 140.259,
 "max_accel_mps2": 80.453,
 "time_to_apogee_s": 11.149,
 "flight_time_s": 158.74,
 "ground_hit_velocity_mps": 4.225
}
```

**USER** (`Simulation 13`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 644 m apogee, hitting about 81.0 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 13",
 "apogee_m": 644.123,
 "max_velocity_mps": 141.489,
 "max_accel_mps2": 81.04,
 "time_to_apogee_s": 11.258,
 "flight_time_s": 162.887,
 "ground_hit_velocity_mps": 4.203
}
```

**USER** (`Simulation 14`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 593 m apogee in about 11.1 s to apogee on a GragasMAY24 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 14",
 "apogee_m": 592.526,
 "max_velocity_mps": 127.175,
 "max_accel_mps2": 71.277,
 "time_to_apogee_s": 11.144,
 "flight_time_s": 141.338,
 "ground_hit_velocity_mps": 4.516
}
```

**USER** (`Simulation 15`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 126.9 m/s max velocity with a 138.9 s flight and touchdown at about 4.5 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Raketa",
 "file": "czech-rocket-challenge-2025__Raketa.ork",
 "motors": "GragasMAY24",
 "simulation": "Simulation 15",
 "apogee_m": 581.496,
 "max_velocity_mps": 126.914,
 "max_accel_mps2": 71.43,
 "time_to_apogee_s": 11.062,
 "flight_time_s": 138.882,
 "ground_hit_velocity_mps": 4.512
}
```

## 2. Rocket type: A simple model rocket — 11 pairs
- Files: `openrocket__asimple.ork`, `orhelper__simple.ork`, `ortools__simple.ork`
- Motors: `A8,B4,C6`
- Apogee range: 48–314 m
- Sub-groups: 3 files (pairs listed per file below)

### File: `openrocket__asimple.ork`
**USER** (`Simulation 1`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 48 m apogee, hitting about 88.9 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "openrocket__asimple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 1",
 "apogee_m": 48.01,
 "max_velocity_mps": 28.387,
 "max_accel_mps2": 88.894,
 "time_to_apogee_s": 3.2507,
 "flight_time_s": 15.509,
 "ground_hit_velocity_mps": 4.01
}
```

**USER** (`Simulation 2`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 123 m apogee in about 5.0 s to apogee on a A8 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "openrocket__asimple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 2",
 "apogee_m": 122.92,
 "max_velocity_mps": 51.139,
 "max_accel_mps2": 54.016,
 "time_to_apogee_s": 5.0346,
 "flight_time_s": 35.188,
 "ground_hit_velocity_mps": 3.9279
}
```

**USER** (`Simulation 3 - too short delay`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 88.3 m/s max velocity with a 66.3 s flight and touchdown at about 4.4 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "openrocket__asimple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 3 - too short delay",
 "apogee_m": 251.16,
 "max_velocity_mps": 88.283,
 "max_accel_mps2": 74.725,
 "time_to_apogee_s": 5.3184,
 "flight_time_s": 66.255,
 "ground_hit_velocity_mps": 4.4004
}
```

**USER** (`Simulation 4`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 274 m apogee with a total flight time of about 73.5 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "openrocket__asimple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 4",
 "apogee_m": 274.0,
 "max_velocity_mps": 86.784,
 "max_accel_mps2": 74.957,
 "time_to_apogee_s": 7.0425,
 "flight_time_s": 73.462,
 "ground_hit_velocity_mps": 3.9825
}
```

**USER** (`Simulation 5`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 274 m apogee, reaching about 86.8 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "openrocket__asimple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 5",
 "apogee_m": 274.09,
 "max_velocity_mps": 86.758,
 "max_accel_mps2": 75.683,
 "time_to_apogee_s": 7.1736,
 "flight_time_s": 71.694,
 "ground_hit_velocity_mps": 3.8711
}
```

### File: `orhelper__simple.ork`
**USER** (`Simulation 1`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 50 m apogee, hitting about 142.1 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "orhelper__simple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 1",
 "apogee_m": 50.488,
 "max_velocity_mps": 29.24,
 "max_accel_mps2": 142.13,
 "time_to_apogee_s": 3.4564,
 "flight_time_s": 15.93,
 "ground_hit_velocity_mps": 3.9812
}
```

**USER** (`Simulation 2`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 134 m apogee in about 5.2 s to apogee on a A8 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "orhelper__simple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 2",
 "apogee_m": 133.92,
 "max_velocity_mps": 53.084,
 "max_accel_mps2": 180.04,
 "time_to_apogee_s": 5.2496,
 "flight_time_s": 37.9,
 "ground_hit_velocity_mps": 4.384
}
```

**USER** (`Simulation 3 - too short delay`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 94.2 m/s max velocity with a 71.9 s flight and touchdown at about 4.0 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "orhelper__simple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 3 - too short delay",
 "apogee_m": 275.33,
 "max_velocity_mps": 94.216,
 "max_accel_mps2": 188.22,
 "time_to_apogee_s": 5.4409,
 "flight_time_s": 71.933,
 "ground_hit_velocity_mps": 4.0058
}
```

**USER** (`Simulation 4`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 312 m apogee with a total flight time of about 82.5 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "orhelper__simple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 4",
 "apogee_m": 311.57,
 "max_velocity_mps": 94.701,
 "max_accel_mps2": 188.25,
 "time_to_apogee_s": 7.2982,
 "flight_time_s": 82.455,
 "ground_hit_velocity_mps": 4.3962
}
```

**USER** (`Simulation 5`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 314 m apogee, reaching about 94.4 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "orhelper__simple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 5",
 "apogee_m": 314.23,
 "max_velocity_mps": 94.358,
 "max_accel_mps2": 188.26,
 "time_to_apogee_s": 7.7516,
 "flight_time_s": 83.165,
 "ground_hit_velocity_mps": 3.8988
}
```

### File: `ortools__simple.ork`
**USER** (`Simulation 1`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 51 m apogee, hitting about 142.2 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "A simple model rocket",
 "file": "ortools__simple.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 1",
 "apogee_m": 50.588,
 "max_velocity_mps": 29.367,
 "max_accel_mps2": 142.24,
 "time_to_apogee_s": 3.4811,
 "flight_time_s": 15.996,
 "ground_hit_velocity_mps": 4.4122
}
```

## 3. Rocket type: Prometeus — 10 pairs
- Files: `project-prometeus__rocket.ork`, `project-prometeus__rocket2.ork`
- Motors: `A8,B4,C6`
- Apogee range: 50–314 m
- Sub-groups: 2 files (pairs listed per file below)

### File: `project-prometeus__rocket.ork`
**USER** (`Simulation 1`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 29.2 m/s max velocity with a 15.9 s flight and touchdown at about 4.0 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 1",
 "apogee_m": 50.488,
 "max_velocity_mps": 29.24,
 "max_accel_mps2": 142.13,
 "time_to_apogee_s": 3.4564,
 "flight_time_s": 15.93,
 "ground_hit_velocity_mps": 3.9812
}
```

**USER** (`Simulation 2`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 134 m apogee with a total flight time of about 37.9 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 2",
 "apogee_m": 133.92,
 "max_velocity_mps": 53.084,
 "max_accel_mps2": 180.04,
 "time_to_apogee_s": 5.2496,
 "flight_time_s": 37.9,
 "ground_hit_velocity_mps": 4.384
}
```

**USER** (`Simulation 3 - too short delay`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 275 m apogee, reaching about 94.2 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 3 - too short delay",
 "apogee_m": 275.33,
 "max_velocity_mps": 94.216,
 "max_accel_mps2": 188.22,
 "time_to_apogee_s": 5.4409,
 "flight_time_s": 71.933,
 "ground_hit_velocity_mps": 4.0058
}
```

**USER** (`Simulation 4`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 312 m apogee, hitting about 188.2 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 4",
 "apogee_m": 311.57,
 "max_velocity_mps": 94.701,
 "max_accel_mps2": 188.25,
 "time_to_apogee_s": 7.2982,
 "flight_time_s": 82.455,
 "ground_hit_velocity_mps": 4.3962
}
```

**USER** (`Simulation 5`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 314 m apogee in about 7.8 s to apogee on a A8 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 5",
 "apogee_m": 314.23,
 "max_velocity_mps": 94.358,
 "max_accel_mps2": 188.26,
 "time_to_apogee_s": 7.7516,
 "flight_time_s": 83.165,
 "ground_hit_velocity_mps": 3.8988
}
```

### File: `project-prometeus__rocket2.ork`
**USER** (`Simulation 1`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 29.2 m/s max velocity with a 15.9 s flight and touchdown at about 4.0 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket2.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 1",
 "apogee_m": 50.488,
 "max_velocity_mps": 29.24,
 "max_accel_mps2": 142.13,
 "time_to_apogee_s": 3.4564,
 "flight_time_s": 15.93,
 "ground_hit_velocity_mps": 3.9812
}
```

**USER** (`Simulation 2`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 134 m apogee with a total flight time of about 37.9 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket2.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 2",
 "apogee_m": 133.92,
 "max_velocity_mps": 53.084,
 "max_accel_mps2": 180.04,
 "time_to_apogee_s": 5.2496,
 "flight_time_s": 37.9,
 "ground_hit_velocity_mps": 4.384
}
```

**USER** (`Simulation 3 - too short delay`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 275 m apogee, reaching about 94.2 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket2.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 3 - too short delay",
 "apogee_m": 275.33,
 "max_velocity_mps": 94.216,
 "max_accel_mps2": 188.22,
 "time_to_apogee_s": 5.4409,
 "flight_time_s": 71.933,
 "ground_hit_velocity_mps": 4.0058
}
```

**USER** (`Simulation 4`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 312 m apogee, hitting about 188.2 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket2.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 4",
 "apogee_m": 311.57,
 "max_velocity_mps": 94.701,
 "max_accel_mps2": 188.25,
 "time_to_apogee_s": 7.2982,
 "flight_time_s": 82.455,
 "ground_hit_velocity_mps": 4.3962
}
```

**USER** (`Simulation 5`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 314 m apogee in about 7.8 s to apogee on a A8 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "Prometeus",
 "file": "project-prometeus__rocket2.ork",
 "motors": "A8,B4,C6",
 "simulation": "Simulation 5",
 "apogee_m": 314.23,
 "max_velocity_mps": 94.358,
 "max_accel_mps2": 188.26,
 "time_to_apogee_s": 7.7516,
 "flight_time_s": 83.165,
 "ground_hit_velocity_mps": 3.8988
}
```

## 4. Rocket type: Centuri Arrow 300 — 6 pairs
- Files: `openrocket-file-utils__CenturiArrow300.ork`, `openrocket-file-utils__rocket.ork`
- Motors: `1/2A6,A8,B6,C6`
- Apogee range: 136–291 m
- Sub-groups: 2 files (pairs listed per file below)

### File: `openrocket-file-utils__CenturiArrow300.ork`
**USER** (`Simulation 1`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 136 m apogee, hitting about 116.3 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "Centuri Arrow 300",
 "file": "openrocket-file-utils__CenturiArrow300.ork",
 "motors": "1/2A6,A8,B6,C6",
 "simulation": "Simulation 1",
 "apogee_m": 136.027,
 "max_velocity_mps": 57.169,
 "max_accel_mps2": 116.262,
 "time_to_apogee_s": 5.468,
 "flight_time_s": 13.394,
 "ground_hit_velocity_mps": 31.004
}
```

**USER** (`Simulation 2`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 196 m apogee in about 6.3 s to apogee on a 1/2A6 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "Centuri Arrow 300",
 "file": "openrocket-file-utils__CenturiArrow300.ork",
 "motors": "1/2A6,A8,B6,C6",
 "simulation": "Simulation 2",
 "apogee_m": 195.558,
 "max_velocity_mps": 71.483,
 "max_accel_mps2": 128.093,
 "time_to_apogee_s": 6.309,
 "flight_time_s": 36.1,
 "ground_hit_velocity_mps": 7.489
}
```

**USER** (`Simulation 3`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 91.6 m/s max velocity with a 19.2 s flight and touchdown at about 33.5 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Centuri Arrow 300",
 "file": "openrocket-file-utils__CenturiArrow300.ork",
 "motors": "1/2A6,A8,B6,C6",
 "simulation": "Simulation 3",
 "apogee_m": 290.708,
 "max_velocity_mps": 91.622,
 "max_accel_mps2": 152.856,
 "time_to_apogee_s": 7.734,
 "flight_time_s": 19.219,
 "ground_hit_velocity_mps": 33.488
}
```

### File: `openrocket-file-utils__rocket.ork`
**USER** (`Simulation 1`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 136 m apogee with a total flight time of about 13.4 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Centuri Arrow 300",
 "file": "openrocket-file-utils__rocket.ork",
 "motors": "1/2A6,A8,B6,C6",
 "simulation": "Simulation 1",
 "apogee_m": 136.027,
 "max_velocity_mps": 57.169,
 "max_accel_mps2": 116.262,
 "time_to_apogee_s": 5.468,
 "flight_time_s": 13.394,
 "ground_hit_velocity_mps": 31.004
}
```

**USER** (`Simulation 2`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 196 m apogee, reaching about 71.5 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "Centuri Arrow 300",
 "file": "openrocket-file-utils__rocket.ork",
 "motors": "1/2A6,A8,B6,C6",
 "simulation": "Simulation 2",
 "apogee_m": 195.558,
 "max_velocity_mps": 71.483,
 "max_accel_mps2": 128.093,
 "time_to_apogee_s": 6.309,
 "flight_time_s": 36.1,
 "ground_hit_velocity_mps": 7.489
}
```

**USER** (`Simulation 3`, T2 [apogee,maxaccel]):
> Design a rocket that goes to about 291 m apogee, hitting about 152.9 m/s² max acceleration.
**ASSISTANT target:**
```json
{
 "rocket_name": "Centuri Arrow 300",
 "file": "openrocket-file-utils__rocket.ork",
 "motors": "1/2A6,A8,B6,C6",
 "simulation": "Simulation 3",
 "apogee_m": 290.708,
 "max_velocity_mps": 91.622,
 "max_accel_mps2": 152.856,
 "time_to_apogee_s": 7.734,
 "flight_time_s": 19.219,
 "ground_hit_velocity_mps": 33.488
}
```

## 5. Rocket type: Rocket — 5 pairs
- Files: `OpenRocket-Design__Rocket_Model.ork`, `openrocketdoc__example_simple_1.ork`, `rockets__bt_55.ork`
- Motors: `C11,C6`, `F15`, `G54`
- Apogee range: 84–474 m
- Sub-groups: 3 files (pairs listed per file below)

### File: `OpenRocket-Design__Rocket_Model.ork`
**USER** (`Low Wind`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 461 m apogee in about 9.5 s to apogee on a G54 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "Rocket",
 "file": "OpenRocket-Design__Rocket_Model.ork",
 "motors": "G54",
 "simulation": "Low Wind",
 "apogee_m": 460.83,
 "max_velocity_mps": 109.89,
 "max_accel_mps2": 119.33,
 "time_to_apogee_s": 9.4603,
 "flight_time_s": 80.909,
 "ground_hit_velocity_mps": 6.4072
}
```

**USER** (`Medium Wind`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 109.7 m/s max velocity with a 79.6 s flight and touchdown at about 6.4 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Rocket",
 "file": "OpenRocket-Design__Rocket_Model.ork",
 "motors": "G54",
 "simulation": "Medium Wind",
 "apogee_m": 456.01,
 "max_velocity_mps": 109.67,
 "max_accel_mps2": 119.97,
 "time_to_apogee_s": 9.4203,
 "flight_time_s": 79.556,
 "ground_hit_velocity_mps": 6.4
}
```

**USER** (`High Wind`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 436 m apogee with a total flight time of about 76.3 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Rocket",
 "file": "OpenRocket-Design__Rocket_Model.ork",
 "motors": "G54",
 "simulation": "High Wind",
 "apogee_m": 436.45,
 "max_velocity_mps": 108.61,
 "max_accel_mps2": 121.16,
 "time_to_apogee_s": 9.1506,
 "flight_time_s": 76.339,
 "ground_hit_velocity_mps": 6.55
}
```

### File: `openrocketdoc__example_simple_1.ork`
**USER** (`Simulation 1`, T4 [maxvelocity,flighttime,groundhit]):
> Design a rocket that goes to about 102.5 m/s max velocity with a 24.4 s flight and touchdown at about 43.8 m/s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Rocket",
 "file": "openrocketdoc__example_simple_1.ork",
 "motors": "F15",
 "simulation": "Simulation 1",
 "apogee_m": 474.48,
 "max_velocity_mps": 102.54,
 "max_accel_mps2": 67.906,
 "time_to_apogee_s": 10.217,
 "flight_time_s": 24.417,
 "ground_hit_velocity_mps": 43.819
}
```

### File: `rockets__bt_55.ork`
**USER** (`Simulation 1`, T3 [apogee,timetoapogee,motor]):
> Design a rocket that goes to about 84 m apogee in about 2.4 s to apogee on a C11 motor.
**ASSISTANT target:**
```json
{
 "rocket_name": "Rocket",
 "file": "rockets__bt_55.ork",
 "motors": "C11,C6",
 "simulation": "Simulation 1",
 "apogee_m": 84.351,
 "max_velocity_mps": 67.805,
 "max_accel_mps2": 156.63,
 "time_to_apogee_s": 2.3571,
 "flight_time_s": 30.891,
 "ground_hit_velocity_mps": 3.1694
}
```

## 6. Rocket type: X-Ray — 2 pairs
- Files: `openrocket-web__test-rocket.ork`
- Motors: `G74W,G80T`
- Apogee range: 492–706 m

**USER** (`Simulation 1`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 492 m apogee with a total flight time of about 116.8 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "X-Ray",
 "file": "openrocket-web__test-rocket.ork",
 "motors": "G74W,G80T",
 "simulation": "Simulation 1",
 "apogee_m": 491.609,
 "max_velocity_mps": 141.301,
 "max_accel_mps2": 161.696,
 "time_to_apogee_s": 9.17,
 "flight_time_s": 116.768,
 "ground_hit_velocity_mps": 2.669
}
```

**USER** (`Simulation 2`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 706 m apogee, reaching about 183.2 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "X-Ray",
 "file": "openrocket-web__test-rocket.ork",
 "motors": "G74W,G80T",
 "simulation": "Simulation 2",
 "apogee_m": 706.464,
 "max_velocity_mps": 183.21,
 "max_accel_mps2": 169.006,
 "time_to_apogee_s": 10.437,
 "flight_time_s": 140.726,
 "ground_hit_velocity_mps": 2.699
}
```

## 7. Rocket type: Bryant's Test Rocket — 1 pairs
- Files: `Openrocket-projects__Bryant_Test_Rocket.ork`
- Motors: `C18W,D13W,D21T`
- Apogee range: 225–225 m

**USER** (`Simulation 1`, T0 [apogee,flighttime]):
> Design a rocket that goes to about 225 m apogee with a total flight time of about 22.9 s.
**ASSISTANT target:**
```json
{
 "rocket_name": "Bryant's Test Rocket",
 "file": "Openrocket-projects__Bryant_Test_Rocket.ork",
 "motors": "C18W,D13W,D21T",
 "simulation": "Simulation 1",
 "apogee_m": 224.585,
 "max_velocity_mps": 86.629,
 "max_accel_mps2": 179.037,
 "time_to_apogee_s": 6.032,
 "flight_time_s": 22.907,
 "ground_hit_velocity_mps": 14.145
}
```

## 8. Rocket type: Rocket example with Elliptical Fins — 1 pairs
- Files: `RocketSerializer__rocket.ork`
- Motors: `G66-LR`
- Apogee range: 662–662 m

**USER** (`Simulation 1`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 662 m apogee, reaching about 181.9 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "Rocket example with Elliptical Fins",
 "file": "RocketSerializer__rocket.ork",
 "motors": "G66-LR",
 "simulation": "Simulation 1",
 "apogee_m": 662.045,
 "max_velocity_mps": 181.876,
 "max_accel_mps2": 218.701,
 "time_to_apogee_s": 9.735,
 "flight_time_s": 25.121,
 "ground_hit_velocity_mps": 61.047
}
```

## 9. Rocket type: OpenRocket Comparison of Green Eggs — 1 pairs
- Files: `numericalrocketry__green_eggs_openrocket_design.ork`
- Motors: `C11`
- Apogee range: 101–101 m

**USER** (`C-11 standard atmosphere`, T1 [apogee,maxvelocity]):
> Design a rocket that goes to about 101 m apogee, reaching about 45.5 m/s max velocity.
**ASSISTANT target:**
```json
{
 "rocket_name": "OpenRocket Comparison of Green Eggs",
 "file": "numericalrocketry__green_eggs_openrocket_design.ork",
 "motors": "C11",
 "simulation": "C-11 standard atmosphere",
 "apogee_m": 101.29,
 "max_velocity_mps": 45.533,
 "max_accel_mps2": 123.932,
 "time_to_apogee_s": 4.766,
 "flight_time_s": 27.194,
 "ground_hit_velocity_mps": 4.439
}
```
