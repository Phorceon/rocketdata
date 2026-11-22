# Centuri Arrow 300 — 29 labeled prompts (deduplicated)

Label prefix `CEN`. Each prompt appears once in this file (source-format repeats removed). 0 prompt(s) are textually identical to prompts for another rocket type (same sim numbers reused across files) — flagged *shared*.

Sources merged: `more_ork_prompts.csv` (T0–T4), `more_ork_prompts_by_type` (performance/speed/mission), `more_ork_prompts_SFT_extra.md` (X0–X5), `more_ork_prompts_3style.md` (Short/Brief/Opt).

---
- **[CEN-001]** [3style:Brief · engineering brief · Simulation 1 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 132-140 m, flight time 13-14 s, max velocity at most 100 m/s, ground-hit velocity at most 33 m/s. Use motors in motor classes 1/A/B/C (e.g. 1/2A6, A8, B6, C6). Output the OpenRocket simulation numbers for each requirement.
- **[CEN-002]** [3style:Opt · optimization · Simulation 1 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Find the lightest, simplest rocket that still reaches 136 m apogee with a 13 s flight and lands under 33 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[CEN-003]** [3style:Short · short · Simulation 1 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Make a rocket that hits 136 m and stays up about 13 s on a 1/2A6 motor.
- **[CEN-004]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 1 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to about 136 m apogee on a 1/2A6 motor, taking about 5.5 s to apogee.
- **[CEN-005]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 1 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to about 57.2 m/s max velocity at about 116.3 m/s² peak acceleration.
- **[CEN-006]** [by_type:mission · motor,timetoapogee · Simulation 1 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes on a 1/2A6 motor to apogee in about 5.5 s.
- **[CEN-007]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to about 57.2 m/s max velocity at about 116.3 m/s² max acceleration.
- **[CEN-008]** [more_base:T2 · apogee,maxaccel · Simulation 1 · `openrocket-file-utils__CenturiArrow300.ork`]
  > Design a rocket that goes to about 136 m apogee, hitting about 116.3 m/s² max acceleration.
- **[CEN-009]** [3style:Brief · engineering brief · Simulation 2 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 190-201 m, flight time 34-38 s, max velocity at most 100 m/s, ground-hit velocity at most 9 m/s. Use motors in motor classes 1/A/B/C (e.g. 1/2A6, A8, B6, C6). Output the OpenRocket simulation numbers for each requirement.
- **[CEN-010]** [3style:Opt · optimization · Simulation 2 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Find the lightest, simplest rocket that still reaches 196 m apogee with a 36 s flight and lands under 9 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[CEN-011]** [3style:Short · short · Simulation 2 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Make a rocket that hits 196 m and stays up about 36 s on a 1/2A6 motor.
- **[CEN-012]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 2 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to apogee in about 6.3 s with a total flight of about 36.1 s.
- **[CEN-013]** [SFT_extra:X3 · apogee,groundhit · Simulation 2 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to about 196 m apogee and touches down at about 7.5 m/s.
- **[CEN-014]** [by_type:mission · motor,timetoapogee · Simulation 2 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes on a 1/2A6 motor to apogee in about 6.3 s.
- **[CEN-015]** [by_type:performance · apogee,flighttime · Simulation 2 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to about 196 m apogee with a total flight time of about 36.1 s.
- **[CEN-016]** [by_type:speed · maxvelocity,maxaccel · Simulation 2 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to about 71.5 m/s max velocity at about 128.1 m/s² max acceleration.
- **[CEN-017]** [more_base:T3 · apogee,timetoapogee,motor · Simulation 2 · `openrocket-file-utils__CenturiArrow300.ork`]
  > Design a rocket that goes to about 196 m apogee in about 6.3 s to apogee on a 1/2A6 motor.
- **[CEN-018]** [3style:Brief · engineering brief · Simulation 3 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 282-299 m, flight time 18-20 s, max velocity at most 100 m/s, ground-hit velocity at most 35 m/s. Use motors in motor classes 1/A/B/C (e.g. 1/2A6, A8, B6, C6). Output the OpenRocket simulation numbers for each requirement.
- **[CEN-019]** [3style:Opt · optimization · Simulation 3 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Find the lightest, simplest rocket that still reaches 291 m apogee with a 19 s flight and lands under 35 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[CEN-020]** [3style:Short · short · Simulation 3 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Make a rocket that hits 291 m and stays up about 19 s on a 1/2A6 motor.
- **[CEN-021]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 3 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes through about 152.9 m/s² max acceleration over a 19.2 s flight.
- **[CEN-022]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 3 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to about 91.6 m/s on a 1/2A6 motor, reaching apogee in about 7.7 s.
- **[CEN-023]** [by_type:mission · motor,timetoapogee · Simulation 3 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes on a 1/2A6 motor to apogee in about 7.7 s.
- **[CEN-024]** [by_type:performance · apogee,flighttime · Simulation 3 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to about 291 m apogee with a total flight time of about 19.2 s.
- **[CEN-025]** [by_type:speed · maxvelocity,maxaccel · Simulation 3 · `openrocket-file-utils__CenturiArrow300.ork`] (also in file: ['openrocket-file-utils__rocket.ork'])
  > Design a rocket that goes to about 91.6 m/s max velocity at about 152.9 m/s² max acceleration.
- **[CEN-026]** [more_base:T4 · maxvelocity,flighttime,groundhit · Simulation 3 · `openrocket-file-utils__CenturiArrow300.ork`]
  > Design a rocket that goes to about 91.6 m/s max velocity with a 19.2 s flight and touchdown at about 33.5 m/s.
- **[CEN-027]** [by_type:performance, more_base:T0 · apogee,flighttime · Simulation 1 · `openrocket-file-utils__rocket.ork`] (also in file: ['openrocket-file-utils__CenturiArrow300.ork'])
  > Design a rocket that goes to about 136 m apogee with a total flight time of about 13.4 s.
- **[CEN-028]** [more_base:T1 · apogee,maxvelocity · Simulation 2 · `openrocket-file-utils__rocket.ork`]
  > Design a rocket that goes to about 196 m apogee, reaching about 71.5 m/s max velocity.
- **[CEN-029]** [more_base:T2 · apogee,maxaccel · Simulation 3 · `openrocket-file-utils__rocket.ork`]
  > Design a rocket that goes to about 291 m apogee, hitting about 152.9 m/s² max acceleration.
