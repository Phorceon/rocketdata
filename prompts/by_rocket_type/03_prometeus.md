# Prometeus — 54 labeled prompts (deduplicated)

Label prefix `PRO`. Each prompt appears once in this file (source-format repeats removed). 30 prompt(s) are textually identical to prompts for another rocket type (same sim numbers reused across files) — flagged *shared*.

Sources merged: `more_ork_prompts.csv` (T0–T4), `more_ork_prompts_by_type` (performance/speed/mission), `more_ork_prompts_SFT_extra.md` (X0–X5), `more_ork_prompts_3style.md` (Short/Brief/Opt).

---
- **[PRO-001]** [3style:Brief · engineering brief · Simulation 1 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 49-52 m, flight time 15-17 s, max velocity at most 50 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[PRO-002]** [3style:Opt · optimization · Simulation 1 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Find the lightest, simplest rocket that still reaches 50 m apogee with a 16 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[PRO-003]** [3style:Short · short · Simulation 1 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Make a rocket that hits 50 m and stays up about 16 s on a A8 motor.
- **[PRO-004]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 1 · `project-prometeus__rocket.ork`]
  > Design a rocket that goes to apogee in about 3.5 s with a total flight of about 15.9 s.
- **[PRO-005]** [SFT_extra:X3 · apogee,groundhit · Simulation 1 · `project-prometeus__rocket.ork`]
  > Design a rocket that goes to about 50 m apogee and touches down at about 4.0 m/s.
- **[PRO-006]** [by_type:mission · motor,timetoapogee · Simulation 1 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes on a A8 motor to apogee in about 3.5 s.
- **[PRO-007]** [by_type:performance · apogee,flighttime · Simulation 1 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 50 m apogee with a total flight time of about 15.9 s.
- **[PRO-008]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 29.2 m/s max velocity at about 142.1 m/s² max acceleration.
- **[PRO-009]** [more_base:T4 · maxvelocity,flighttime,groundhit · Simulation 1 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork'])
  > Design a rocket that goes to about 29.2 m/s max velocity with a 15.9 s flight and touchdown at about 4.0 m/s.
- **[PRO-010]** [3style:Brief · engineering brief · Simulation 2 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 130-138 m, flight time 36-40 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[PRO-011]** [3style:Opt · optimization · Simulation 2 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Find the lightest, simplest rocket that still reaches 134 m apogee with a 38 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[PRO-012]** [3style:Short · short · Simulation 2 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Make a rocket that hits 134 m and stays up about 38 s on a A8 motor.
- **[PRO-013]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 2 · `project-prometeus__rocket.ork`]
  > Design a rocket that goes through about 180.0 m/s² max acceleration over a 37.9 s flight.
- **[PRO-014]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 2 · `project-prometeus__rocket.ork`]
  > Design a rocket that goes to about 53.1 m/s on a A8 motor, reaching apogee in about 5.2 s.
- **[PRO-015]** [by_type:mission · motor,timetoapogee · Simulation 2 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes on a A8 motor to apogee in about 5.2 s.
- **[PRO-016]** [by_type:speed · maxvelocity,maxaccel · Simulation 2 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 53.1 m/s max velocity at about 180.0 m/s² max acceleration.
- **[PRO-017]** [by_type:performance, more_base:T0 · apogee,flighttime · Simulation 2 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 134 m apogee with a total flight time of about 37.9 s.
- **[PRO-018]** [3style:Brief · engineering brief · Simulation 3 - too short delay · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 267-284 m, flight time 68-76 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[PRO-019]** [3style:Opt · optimization · Simulation 3 - too short delay · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Find the lightest, simplest rocket that still reaches 275 m apogee with a 72 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[PRO-020]** [3style:Short · short · Simulation 3 - too short delay · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Make a rocket that hits 275 m and stays up about 72 s on a A8 motor.
- **[PRO-021]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 3 - too short delay · `project-prometeus__rocket.ork`]
  > Design a rocket that goes to about 275 m apogee on a A8 motor, taking about 5.4 s to apogee.
- **[PRO-022]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 3 - too short delay · `project-prometeus__rocket.ork`]
  > Design a rocket that goes to about 94.2 m/s max velocity at about 188.2 m/s² peak acceleration.
- **[PRO-023]** [by_type:mission · motor,timetoapogee · Simulation 3 - too short delay · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes on a A8 motor to apogee in about 5.4 s.
- **[PRO-024]** [by_type:performance · apogee,flighttime · Simulation 3 - too short delay · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 275 m apogee with a total flight time of about 71.9 s.
- **[PRO-025]** [by_type:speed · maxvelocity,maxaccel · Simulation 3 - too short delay · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 94.2 m/s max velocity at about 188.2 m/s² max acceleration.
- **[PRO-026]** [more_base:T1 · apogee,maxvelocity · Simulation 3 - too short delay · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork'])
  > Design a rocket that goes to about 275 m apogee, reaching about 94.2 m/s max velocity.
- **[PRO-027]** [3style:Brief · engineering brief · Simulation 4 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 302-321 m, flight time 78-87 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[PRO-028]** [3style:Opt · optimization · Simulation 4 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Find the lightest, simplest rocket that still reaches 312 m apogee with a 82 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[PRO-029]** [3style:Short · short · Simulation 4 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Make a rocket that hits 312 m and stays up about 82 s on a A8 motor.
- **[PRO-030]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 4 · `project-prometeus__rocket.ork`]
  > Design a rocket that goes to apogee in about 7.3 s with a total flight of about 82.5 s.
- **[PRO-031]** [SFT_extra:X3 · apogee,groundhit · Simulation 4 · `project-prometeus__rocket.ork`]
  > Design a rocket that goes to about 312 m apogee and touches down at about 4.4 m/s.
- **[PRO-032]** [by_type:mission · motor,timetoapogee · Simulation 4 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes on a A8 motor to apogee in about 7.3 s.
- **[PRO-033]** [by_type:performance · apogee,flighttime · Simulation 4 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 312 m apogee with a total flight time of about 82.5 s.
- **[PRO-034]** [by_type:speed · maxvelocity,maxaccel · Simulation 4 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 94.7 m/s max velocity at about 188.2 m/s² max acceleration.
- **[PRO-035]** [more_base:T2 · apogee,maxaccel · Simulation 4 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork'])
  > Design a rocket that goes to about 312 m apogee, hitting about 188.2 m/s² max acceleration.
- **[PRO-036]** [3style:Brief · engineering brief · Simulation 5 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 305-324 m, flight time 79-87 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[PRO-037]** [3style:Opt · optimization · Simulation 5 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Find the lightest, simplest rocket that still reaches 314 m apogee with a 83 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[PRO-038]** [3style:Short · short · Simulation 5 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Make a rocket that hits 314 m and stays up about 83 s on a A8 motor.
- **[PRO-039]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 5 · `project-prometeus__rocket.ork`]
  > Design a rocket that goes through about 188.3 m/s² max acceleration over a 83.2 s flight.
- **[PRO-040]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 5 · `project-prometeus__rocket.ork`]
  > Design a rocket that goes to about 94.4 m/s on a A8 motor, reaching apogee in about 7.8 s.
- **[PRO-041]** [by_type:mission · motor,timetoapogee · Simulation 5 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes on a A8 motor to apogee in about 7.8 s.
- **[PRO-042]** [by_type:performance · apogee,flighttime · Simulation 5 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 314 m apogee with a total flight time of about 83.2 s.
- **[PRO-043]** [by_type:speed · maxvelocity,maxaccel · Simulation 5 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork']) *shared with ['A simple model rocket']*
  > Design a rocket that goes to about 94.4 m/s max velocity at about 188.3 m/s² max acceleration.
- **[PRO-044]** [more_base:T3 · apogee,timetoapogee,motor · Simulation 5 · `project-prometeus__rocket.ork`] (also in file: ['project-prometeus__rocket2.ork'])
  > Design a rocket that goes to about 314 m apogee in about 7.8 s to apogee on a A8 motor.
- **[PRO-045]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 1 · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes to about 50 m apogee on a A8 motor, taking about 3.5 s to apogee.
- **[PRO-046]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 1 · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes to about 29.2 m/s max velocity at about 142.1 m/s² peak acceleration.
- **[PRO-047]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 2 · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes to apogee in about 5.2 s with a total flight of about 37.9 s.
- **[PRO-048]** [SFT_extra:X3 · apogee,groundhit · Simulation 2 · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes to about 134 m apogee and touches down at about 4.4 m/s.
- **[PRO-049]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 3 - too short delay · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes through about 188.2 m/s² max acceleration over a 71.9 s flight.
- **[PRO-050]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 3 - too short delay · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes to about 94.2 m/s on a A8 motor, reaching apogee in about 5.4 s.
- **[PRO-051]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 4 · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes to about 312 m apogee on a A8 motor, taking about 7.3 s to apogee.
- **[PRO-052]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 4 · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes to about 94.7 m/s max velocity at about 188.2 m/s² peak acceleration.
- **[PRO-053]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 5 · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes to apogee in about 7.8 s with a total flight of about 83.2 s.
- **[PRO-054]** [SFT_extra:X3 · apogee,groundhit · Simulation 5 · `project-prometeus__rocket2.ork`]
  > Design a rocket that goes to about 314 m apogee and touches down at about 3.9 m/s.
