# A simple model rocket — 96 labeled prompts (deduplicated)

Label prefix `ASM`. Each prompt appears once in this file (source-format repeats removed). 30 prompt(s) are textually identical to prompts for another rocket type (same sim numbers reused across files) — flagged *shared*.

Sources merged: `more_ork_prompts.csv` (T0–T4), `more_ork_prompts_by_type` (performance/speed/mission), `more_ork_prompts_SFT_extra.md` (X0–X5), `more_ork_prompts_3style.md` (Short/Brief/Opt).

---
- **[ASM-001]** [3style:Brief · engineering brief · Simulation 1 · `openrocket__asimple.ork`]
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 47-49 m, flight time 15-16 s, max velocity at most 50 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-002]** [3style:Opt · optimization · Simulation 1 · `openrocket__asimple.ork`]
  > Find the lightest, simplest rocket that still reaches 48 m apogee with a 16 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-003]** [3style:Short · short · Simulation 1 · `openrocket__asimple.ork`]
  > Make a rocket that hits 48 m and stays up about 16 s on a A8 motor.
- **[ASM-004]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 1 · `openrocket__asimple.ork`]
  > Design a rocket that goes through about 88.9 m/s² max acceleration over a 15.5 s flight.
- **[ASM-005]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 1 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 28.4 m/s on a A8 motor, reaching apogee in about 3.3 s.
- **[ASM-006]** [by_type:mission · motor,timetoapogee · Simulation 1 · `openrocket__asimple.ork`]
  > Design a rocket that goes on a A8 motor to apogee in about 3.3 s.
- **[ASM-007]** [by_type:performance · apogee,flighttime · Simulation 1 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 48 m apogee with a total flight time of about 15.5 s.
- **[ASM-008]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 28.4 m/s max velocity at about 88.9 m/s² max acceleration.
- **[ASM-009]** [more_base:T2 · apogee,maxaccel · Simulation 1 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 48 m apogee, hitting about 88.9 m/s² max acceleration.
- **[ASM-010]** [3style:Brief · engineering brief · Simulation 2 · `openrocket__asimple.ork`]
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 119-127 m, flight time 33-37 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-011]** [3style:Opt · optimization · Simulation 2 · `openrocket__asimple.ork`]
  > Find the lightest, simplest rocket that still reaches 123 m apogee with a 35 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-012]** [3style:Short · short · Simulation 2 · `openrocket__asimple.ork`]
  > Make a rocket that hits 123 m and stays up about 35 s on a A8 motor.
- **[ASM-013]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 2 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 123 m apogee on a A8 motor, taking about 5.0 s to apogee.
- **[ASM-014]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 2 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 51.1 m/s max velocity at about 54.0 m/s² peak acceleration.
- **[ASM-015]** [by_type:mission · motor,timetoapogee · Simulation 2 · `openrocket__asimple.ork`]
  > Design a rocket that goes on a A8 motor to apogee in about 5.0 s.
- **[ASM-016]** [by_type:performance · apogee,flighttime · Simulation 2 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 123 m apogee with a total flight time of about 35.2 s.
- **[ASM-017]** [by_type:speed · maxvelocity,maxaccel · Simulation 2 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 51.1 m/s max velocity at about 54.0 m/s² max acceleration.
- **[ASM-018]** [more_base:T3 · apogee,timetoapogee,motor · Simulation 2 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 123 m apogee in about 5.0 s to apogee on a A8 motor.
- **[ASM-019]** [3style:Brief · engineering brief · Simulation 3 - too short delay · `openrocket__asimple.ork`]
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 244-259 m, flight time 63-70 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-020]** [3style:Opt · optimization · Simulation 3 - too short delay · `openrocket__asimple.ork`]
  > Find the lightest, simplest rocket that still reaches 251 m apogee with a 66 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-021]** [3style:Short · short · Simulation 3 - too short delay · `openrocket__asimple.ork`]
  > Make a rocket that hits 251 m and stays up about 66 s on a A8 motor.
- **[ASM-022]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 3 - too short delay · `openrocket__asimple.ork`]
  > Design a rocket that goes to apogee in about 5.3 s with a total flight of about 66.3 s.
- **[ASM-023]** [SFT_extra:X3 · apogee,groundhit · Simulation 3 - too short delay · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 251 m apogee and touches down at about 4.4 m/s.
- **[ASM-024]** [by_type:mission · motor,timetoapogee · Simulation 3 - too short delay · `openrocket__asimple.ork`]
  > Design a rocket that goes on a A8 motor to apogee in about 5.3 s.
- **[ASM-025]** [by_type:performance · apogee,flighttime · Simulation 3 - too short delay · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 251 m apogee with a total flight time of about 66.3 s.
- **[ASM-026]** [by_type:speed · maxvelocity,maxaccel · Simulation 3 - too short delay · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 88.3 m/s max velocity at about 74.7 m/s² max acceleration.
- **[ASM-027]** [more_base:T4 · maxvelocity,flighttime,groundhit · Simulation 3 - too short delay · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 88.3 m/s max velocity with a 66.3 s flight and touchdown at about 4.4 m/s.
- **[ASM-028]** [3style:Brief · engineering brief · Simulation 4 · `openrocket__asimple.ork`]
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 266-282 m, flight time 70-77 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-029]** [3style:Opt · optimization · Simulation 4 · `openrocket__asimple.ork`]
  > Find the lightest, simplest rocket that still reaches 274 m apogee with a 73 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-030]** [3style:Short · short · Simulation 4 · `openrocket__asimple.ork`]
  > Make a rocket that hits 274 m and stays up about 73 s on a A8 motor.
- **[ASM-031]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 4 · `openrocket__asimple.ork`]
  > Design a rocket that goes through about 75.0 m/s² max acceleration over a 73.5 s flight.
- **[ASM-032]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 4 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 86.8 m/s on a A8 motor, reaching apogee in about 7.0 s.
- **[ASM-033]** [by_type:mission · motor,timetoapogee · Simulation 4 · `openrocket__asimple.ork`]
  > Design a rocket that goes on a A8 motor to apogee in about 7.0 s.
- **[ASM-034]** [by_type:speed · maxvelocity,maxaccel · Simulation 4 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 86.8 m/s max velocity at about 75.0 m/s² max acceleration.
- **[ASM-035]** [by_type:performance, more_base:T0 · apogee,flighttime · Simulation 4 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 274 m apogee with a total flight time of about 73.5 s.
- **[ASM-036]** [3style:Brief · engineering brief · Simulation 5 · `openrocket__asimple.ork`]
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 266-282 m, flight time 68-75 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-037]** [3style:Opt · optimization · Simulation 5 · `openrocket__asimple.ork`]
  > Find the lightest, simplest rocket that still reaches 274 m apogee with a 72 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-038]** [3style:Short · short · Simulation 5 · `openrocket__asimple.ork`]
  > Make a rocket that hits 274 m and stays up about 72 s on a A8 motor.
- **[ASM-039]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 5 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 274 m apogee on a A8 motor, taking about 7.2 s to apogee.
- **[ASM-040]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 5 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 86.8 m/s max velocity at about 75.7 m/s² peak acceleration.
- **[ASM-041]** [by_type:mission · motor,timetoapogee · Simulation 5 · `openrocket__asimple.ork`]
  > Design a rocket that goes on a A8 motor to apogee in about 7.2 s.
- **[ASM-042]** [by_type:performance · apogee,flighttime · Simulation 5 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 274 m apogee with a total flight time of about 71.7 s.
- **[ASM-043]** [by_type:speed · maxvelocity,maxaccel · Simulation 5 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 86.8 m/s max velocity at about 75.7 m/s² max acceleration.
- **[ASM-044]** [more_base:T1 · apogee,maxvelocity · Simulation 5 · `openrocket__asimple.ork`]
  > Design a rocket that goes to about 274 m apogee, reaching about 86.8 m/s max velocity.
- **[ASM-045]** [3style:Brief · engineering brief · Simulation 1 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 49-52 m, flight time 15-17 s, max velocity at most 50 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-046]** [3style:Opt · optimization · Simulation 1 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Find the lightest, simplest rocket that still reaches 50 m apogee with a 16 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-047]** [3style:Short · short · Simulation 1 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Make a rocket that hits 50 m and stays up about 16 s on a A8 motor.
- **[ASM-048]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 1 · `orhelper__simple.ork`]
  > Design a rocket that goes through about 142.1 m/s² max acceleration over a 15.9 s flight.
- **[ASM-049]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 1 · `orhelper__simple.ork`]
  > Design a rocket that goes to about 29.2 m/s on a A8 motor, reaching apogee in about 3.5 s.
- **[ASM-050]** [by_type:mission · motor,timetoapogee · Simulation 1 · `orhelper__simple.ork`] (also in file: ['ortools__simple.ork']) *shared with ['Prometeus']*
  > Design a rocket that goes on a A8 motor to apogee in about 3.5 s.
- **[ASM-051]** [by_type:performance · apogee,flighttime · Simulation 1 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 50 m apogee with a total flight time of about 15.9 s.
- **[ASM-052]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 29.2 m/s max velocity at about 142.1 m/s² max acceleration.
- **[ASM-053]** [more_base:T2 · apogee,maxaccel · Simulation 1 · `orhelper__simple.ork`]
  > Design a rocket that goes to about 50 m apogee, hitting about 142.1 m/s² max acceleration.
- **[ASM-054]** [3style:Brief · engineering brief · Simulation 2 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 130-138 m, flight time 36-40 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-055]** [3style:Opt · optimization · Simulation 2 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Find the lightest, simplest rocket that still reaches 134 m apogee with a 38 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-056]** [3style:Short · short · Simulation 2 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Make a rocket that hits 134 m and stays up about 38 s on a A8 motor.
- **[ASM-057]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 2 · `orhelper__simple.ork`]
  > Design a rocket that goes to about 134 m apogee on a A8 motor, taking about 5.2 s to apogee.
- **[ASM-058]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 2 · `orhelper__simple.ork`]
  > Design a rocket that goes to about 53.1 m/s max velocity at about 180.0 m/s² peak acceleration.
- **[ASM-059]** [by_type:mission · motor,timetoapogee · Simulation 2 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes on a A8 motor to apogee in about 5.2 s.
- **[ASM-060]** [by_type:performance · apogee,flighttime · Simulation 2 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 134 m apogee with a total flight time of about 37.9 s.
- **[ASM-061]** [by_type:speed · maxvelocity,maxaccel · Simulation 2 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 53.1 m/s max velocity at about 180.0 m/s² max acceleration.
- **[ASM-062]** [more_base:T3 · apogee,timetoapogee,motor · Simulation 2 · `orhelper__simple.ork`]
  > Design a rocket that goes to about 134 m apogee in about 5.2 s to apogee on a A8 motor.
- **[ASM-063]** [3style:Brief · engineering brief · Simulation 3 - too short delay · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 267-284 m, flight time 68-76 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-064]** [3style:Opt · optimization · Simulation 3 - too short delay · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Find the lightest, simplest rocket that still reaches 275 m apogee with a 72 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-065]** [3style:Short · short · Simulation 3 - too short delay · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Make a rocket that hits 275 m and stays up about 72 s on a A8 motor.
- **[ASM-066]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 3 - too short delay · `orhelper__simple.ork`]
  > Design a rocket that goes to apogee in about 5.4 s with a total flight of about 71.9 s.
- **[ASM-067]** [SFT_extra:X3 · apogee,groundhit · Simulation 3 - too short delay · `orhelper__simple.ork`]
  > Design a rocket that goes to about 275 m apogee and touches down at about 4.0 m/s.
- **[ASM-068]** [by_type:mission · motor,timetoapogee · Simulation 3 - too short delay · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes on a A8 motor to apogee in about 5.4 s.
- **[ASM-069]** [by_type:performance · apogee,flighttime · Simulation 3 - too short delay · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 275 m apogee with a total flight time of about 71.9 s.
- **[ASM-070]** [by_type:speed · maxvelocity,maxaccel · Simulation 3 - too short delay · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 94.2 m/s max velocity at about 188.2 m/s² max acceleration.
- **[ASM-071]** [more_base:T4 · maxvelocity,flighttime,groundhit · Simulation 3 - too short delay · `orhelper__simple.ork`]
  > Design a rocket that goes to about 94.2 m/s max velocity with a 71.9 s flight and touchdown at about 4.0 m/s.
- **[ASM-072]** [3style:Brief · engineering brief · Simulation 4 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 302-321 m, flight time 78-87 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-073]** [3style:Opt · optimization · Simulation 4 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Find the lightest, simplest rocket that still reaches 312 m apogee with a 82 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-074]** [3style:Short · short · Simulation 4 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Make a rocket that hits 312 m and stays up about 82 s on a A8 motor.
- **[ASM-075]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 4 · `orhelper__simple.ork`]
  > Design a rocket that goes through about 188.2 m/s² max acceleration over a 82.5 s flight.
- **[ASM-076]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 4 · `orhelper__simple.ork`]
  > Design a rocket that goes to about 94.7 m/s on a A8 motor, reaching apogee in about 7.3 s.
- **[ASM-077]** [by_type:mission · motor,timetoapogee · Simulation 4 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes on a A8 motor to apogee in about 7.3 s.
- **[ASM-078]** [by_type:speed · maxvelocity,maxaccel · Simulation 4 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 94.7 m/s max velocity at about 188.2 m/s² max acceleration.
- **[ASM-079]** [by_type:performance, more_base:T0 · apogee,flighttime · Simulation 4 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 312 m apogee with a total flight time of about 82.5 s.
- **[ASM-080]** [3style:Brief · engineering brief · Simulation 5 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 305-324 m, flight time 79-87 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-081]** [3style:Opt · optimization · Simulation 5 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Find the lightest, simplest rocket that still reaches 314 m apogee with a 83 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-082]** [3style:Short · short · Simulation 5 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Make a rocket that hits 314 m and stays up about 83 s on a A8 motor.
- **[ASM-083]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 5 · `orhelper__simple.ork`]
  > Design a rocket that goes to about 314 m apogee on a A8 motor, taking about 7.8 s to apogee.
- **[ASM-084]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 5 · `orhelper__simple.ork`]
  > Design a rocket that goes to about 94.4 m/s max velocity at about 188.3 m/s² peak acceleration.
- **[ASM-085]** [by_type:mission · motor,timetoapogee · Simulation 5 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes on a A8 motor to apogee in about 7.8 s.
- **[ASM-086]** [by_type:performance · apogee,flighttime · Simulation 5 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 314 m apogee with a total flight time of about 83.2 s.
- **[ASM-087]** [by_type:speed · maxvelocity,maxaccel · Simulation 5 · `orhelper__simple.ork`] *shared with ['Prometeus']*
  > Design a rocket that goes to about 94.4 m/s max velocity at about 188.3 m/s² max acceleration.
- **[ASM-088]** [more_base:T1 · apogee,maxvelocity · Simulation 5 · `orhelper__simple.ork`]
  > Design a rocket that goes to about 314 m apogee, reaching about 94.4 m/s max velocity.
- **[ASM-089]** [3style:Brief · engineering brief · Simulation 1 · `ortools__simple.ork`]
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 49-52 m, flight time 15-17 s, max velocity at most 50 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
- **[ASM-090]** [3style:Opt · optimization · Simulation 1 · `ortools__simple.ork`]
  > Find the lightest, simplest rocket that still reaches 51 m apogee with a 16 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ASM-091]** [3style:Short · short · Simulation 1 · `ortools__simple.ork`]
  > Make a rocket that hits 51 m and stays up about 16 s on a A8 motor.
- **[ASM-092]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 1 · `ortools__simple.ork`]
  > Design a rocket that goes to apogee in about 3.5 s with a total flight of about 16.0 s.
- **[ASM-093]** [SFT_extra:X3 · apogee,groundhit · Simulation 1 · `ortools__simple.ork`]
  > Design a rocket that goes to about 51 m apogee and touches down at about 4.4 m/s.
- **[ASM-094]** [by_type:performance · apogee,flighttime · Simulation 1 · `ortools__simple.ork`]
  > Design a rocket that goes to about 51 m apogee with a total flight time of about 16.0 s.
- **[ASM-095]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `ortools__simple.ork`]
  > Design a rocket that goes to about 29.4 m/s max velocity at about 142.2 m/s² max acceleration.
- **[ASM-096]** [more_base:T2 · apogee,maxaccel · Simulation 1 · `ortools__simple.ork`]
  > Design a rocket that goes to about 51 m apogee, hitting about 142.2 m/s² max acceleration.
