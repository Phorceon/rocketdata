# Bryant's Test Rocket — 8 labeled prompts (deduplicated)

Label prefix `BRY`. Each prompt appears once in this file (source-format repeats removed). 0 prompt(s) are textually identical to prompts for another rocket type (same sim numbers reused across files) — flagged *shared*.

Sources merged: `more_ork_prompts.csv` (T0–T4), `more_ork_prompts_by_type` (performance/speed/mission), `more_ork_prompts_SFT_extra.md` (X0–X5), `more_ork_prompts_3style.md` (Short/Brief/Opt).

---
- **[BRY-001]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 1 · `Openrocket-projects__Bryant_Test_Rocket.ork`]
  > Design a rocket that goes to about 225 m apogee on a C18W motor, taking about 6.0 s to apogee.
- **[BRY-002]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 1 · `Openrocket-projects__Bryant_Test_Rocket.ork`]
  > Design a rocket that goes to about 86.6 m/s max velocity at about 179.0 m/s² peak acceleration.
- **[BRY-003]** [by_type:mission · motor,timetoapogee · Simulation 1 · `Openrocket-projects__Bryant_Test_Rocket.ork`]
  > Design a rocket that goes on a C18W motor to apogee in about 6.0 s.
- **[BRY-004]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `Openrocket-projects__Bryant_Test_Rocket.ork`]
  > Design a rocket that goes to about 86.6 m/s max velocity at about 179.0 m/s² max acceleration.
- **[BRY-005]** [by_type:performance, more_base:T0 · apogee,flighttime · Simulation 1 · `Openrocket-projects__Bryant_Test_Rocket.ork`]
  > Design a rocket that goes to about 225 m apogee with a total flight time of about 22.9 s.
- **[BRY-006]** [3style:Brief · engineering brief · Simulation 1 · `rockets__bt_55.ork`]
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 218-231 m, flight time 22-24 s, max velocity at most 100 m/s, ground-hit velocity at most 16 m/s. Use motors in motor classes C/D (e.g. C18W, D13W, D21T). Output the OpenRocket simulation numbers for each requirement.
- **[BRY-007]** [3style:Opt · optimization · Simulation 1 · `rockets__bt_55.ork`]
  > Find the lightest, simplest rocket that still reaches 225 m apogee with a 23 s flight and lands under 16 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[BRY-008]** [3style:Short · short · Simulation 1 · `rockets__bt_55.ork`]
  > Make a rocket that hits 225 m and stays up about 23 s on a C18W motor.
