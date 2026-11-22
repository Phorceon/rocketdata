# Rocket — 44 labeled prompts (deduplicated)

Label prefix `ROK`. Each prompt appears once in this file (source-format repeats removed). 0 prompt(s) are textually identical to prompts for another rocket type (same sim numbers reused across files) — flagged *shared*.

Sources merged: `more_ork_prompts.csv` (T0–T4), `more_ork_prompts_by_type` (performance/speed/mission), `more_ork_prompts_SFT_extra.md` (X0–X5), `more_ork_prompts_3style.md` (Short/Brief/Opt).

---
- **[ROK-001]** [3style:Brief · engineering brief · High Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 423-450 m, flight time 73-80 s, max velocity at most 200 m/s, ground-hit velocity at most 8 m/s. Use motors in the class of G54. Output the OpenRocket simulation numbers for each requirement.
- **[ROK-002]** [3style:Opt · optimization · High Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Find the lightest, simplest rocket that still reaches 436 m apogee with a 76 s flight and lands under 8 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ROK-003]** [3style:Short · short · High Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Make a rocket that hits 436 m and stays up about 76 s on a G54 motor.
- **[ROK-004]** [SFT_extra:X2 · timetoapogee,flighttime · High Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to apogee in about 9.2 s with a total flight of about 76.3 s.
- **[ROK-005]** [SFT_extra:X3 · apogee,groundhit · High Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 436 m apogee and touches down at about 6.5 m/s.
- **[ROK-006]** [by_type:mission · motor,timetoapogee · High Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes on a G54 motor to apogee in about 9.2 s.
- **[ROK-007]** [by_type:speed · maxvelocity,maxaccel · High Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 108.6 m/s max velocity at about 121.2 m/s² max acceleration.
- **[ROK-008]** [by_type:performance, more_base:T0 · apogee,flighttime · High Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 436 m apogee with a total flight time of about 76.3 s.
- **[ROK-009]** [3style:Brief · engineering brief · Low Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 447-475 m, flight time 77-85 s, max velocity at most 200 m/s, ground-hit velocity at most 8 m/s. Use motors in the class of G54. Output the OpenRocket simulation numbers for each requirement.
- **[ROK-010]** [3style:Opt · optimization · Low Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Find the lightest, simplest rocket that still reaches 461 m apogee with a 81 s flight and lands under 8 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ROK-011]** [3style:Short · short · Low Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Make a rocket that hits 461 m and stays up about 81 s on a G54 motor.
- **[ROK-012]** [SFT_extra:X4 · maxaccel,flighttime · Low Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes through about 119.3 m/s² max acceleration over a 80.9 s flight.
- **[ROK-013]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Low Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 109.9 m/s on a G54 motor, reaching apogee in about 9.5 s.
- **[ROK-014]** [by_type:mission · motor,timetoapogee · Low Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes on a G54 motor to apogee in about 9.5 s.
- **[ROK-015]** [by_type:performance · apogee,flighttime · Low Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 461 m apogee with a total flight time of about 80.9 s.
- **[ROK-016]** [by_type:speed · maxvelocity,maxaccel · Low Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 109.9 m/s max velocity at about 119.3 m/s² max acceleration.
- **[ROK-017]** [more_base:T3 · apogee,timetoapogee,motor · Low Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 461 m apogee in about 9.5 s to apogee on a G54 motor.
- **[ROK-018]** [3style:Brief · engineering brief · Medium Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 442-470 m, flight time 76-84 s, max velocity at most 200 m/s, ground-hit velocity at most 8 m/s. Use motors in the class of G54. Output the OpenRocket simulation numbers for each requirement.
- **[ROK-019]** [3style:Opt · optimization · Medium Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Find the lightest, simplest rocket that still reaches 456 m apogee with a 80 s flight and lands under 8 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ROK-020]** [3style:Short · short · Medium Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Make a rocket that hits 456 m and stays up about 80 s on a G54 motor.
- **[ROK-021]** [SFT_extra:X0 · motor,apogee,timetoapogee · Medium Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 456 m apogee on a G54 motor, taking about 9.4 s to apogee.
- **[ROK-022]** [SFT_extra:X1 · maxvelocity,maxaccel · Medium Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 109.7 m/s max velocity at about 120.0 m/s² peak acceleration.
- **[ROK-023]** [by_type:mission · motor,timetoapogee · Medium Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes on a G54 motor to apogee in about 9.4 s.
- **[ROK-024]** [by_type:performance · apogee,flighttime · Medium Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 456 m apogee with a total flight time of about 79.6 s.
- **[ROK-025]** [by_type:speed · maxvelocity,maxaccel · Medium Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 109.7 m/s max velocity at about 120.0 m/s² max acceleration.
- **[ROK-026]** [more_base:T4 · maxvelocity,flighttime,groundhit · Medium Wind · `OpenRocket-Design__Rocket_Model.ork`]
  > Design a rocket that goes to about 109.7 m/s max velocity with a 79.6 s flight and touchdown at about 6.4 m/s.
- **[ROK-027]** [3style:Brief · engineering brief · Simulation 1 · `openrocketdoc__example_simple_1.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 460-489 m, flight time 23-26 s, max velocity at most 200 m/s, ground-hit velocity at most 45 m/s. Use motors in the class of F15. Output the OpenRocket simulation numbers for each requirement.
- **[ROK-028]** [3style:Opt · optimization · Simulation 1 · `openrocketdoc__example_simple_1.ork`]
  > Find the lightest, simplest rocket that still reaches 474 m apogee with a 24 s flight and lands under 45 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ROK-029]** [3style:Short · short · Simulation 1 · `openrocketdoc__example_simple_1.ork`]
  > Make a rocket that hits 474 m and stays up about 24 s on a F15 motor.
- **[ROK-030]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 1 · `openrocketdoc__example_simple_1.ork`]
  > Design a rocket that goes through about 67.9 m/s² max acceleration over a 24.4 s flight.
- **[ROK-031]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 1 · `openrocketdoc__example_simple_1.ork`]
  > Design a rocket that goes to about 102.5 m/s on a F15 motor, reaching apogee in about 10.2 s.
- **[ROK-032]** [by_type:mission · motor,timetoapogee · Simulation 1 · `openrocketdoc__example_simple_1.ork`]
  > Design a rocket that goes on a F15 motor to apogee in about 10.2 s.
- **[ROK-033]** [by_type:performance · apogee,flighttime · Simulation 1 · `openrocketdoc__example_simple_1.ork`]
  > Design a rocket that goes to about 474 m apogee with a total flight time of about 24.4 s.
- **[ROK-034]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `openrocketdoc__example_simple_1.ork`]
  > Design a rocket that goes to about 102.5 m/s max velocity at about 67.9 m/s² max acceleration.
- **[ROK-035]** [more_base:T4 · maxvelocity,flighttime,groundhit · Simulation 1 · `openrocketdoc__example_simple_1.ork`]
  > Design a rocket that goes to about 102.5 m/s max velocity with a 24.4 s flight and touchdown at about 43.8 m/s.
- **[ROK-036]** [3style:Brief · engineering brief · Simulation 1 · `rockets__bt_55.ork`]
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 82-87 m, flight time 29-32 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes C (e.g. C11, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ROK-037]** [3style:Opt · optimization · Simulation 1 · `rockets__bt_55.ork`]
  > Find the lightest, simplest rocket that still reaches 84 m apogee with a 31 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ROK-038]** [3style:Short · short · Simulation 1 · `rockets__bt_55.ork`]
  > Make a rocket that hits 84 m and stays up about 31 s on a C11 motor.
- **[ROK-039]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 1 · `rockets__bt_55.ork`]
  > Design a rocket that goes to about 84 m apogee on a C11 motor, taking about 2.4 s to apogee.
- **[ROK-040]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 1 · `rockets__bt_55.ork`]
  > Design a rocket that goes to about 67.8 m/s max velocity at about 156.6 m/s² peak acceleration.
- **[ROK-041]** [by_type:mission · motor,timetoapogee · Simulation 1 · `rockets__bt_55.ork`]
  > Design a rocket that goes on a C11 motor to apogee in about 2.4 s.
- **[ROK-042]** [by_type:performance · apogee,flighttime · Simulation 1 · `rockets__bt_55.ork`]
  > Design a rocket that goes to about 84 m apogee with a total flight time of about 30.9 s.
- **[ROK-043]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `rockets__bt_55.ork`]
  > Design a rocket that goes to about 67.8 m/s max velocity at about 156.6 m/s² max acceleration.
- **[ROK-044]** [more_base:T3 · apogee,timetoapogee,motor · Simulation 1 · `rockets__bt_55.ork`]
  > Design a rocket that goes to about 84 m apogee in about 2.4 s to apogee on a C11 motor.
