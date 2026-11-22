# Rocket example with Elliptical Fins — 9 labeled prompts (deduplicated)

Label prefix `ELL`. Each prompt appears once in this file (source-format repeats removed). 0 prompt(s) are textually identical to prompts for another rocket type (same sim numbers reused across files) — flagged *shared*.

Sources merged: `more_ork_prompts.csv` (T0–T4), `more_ork_prompts_by_type` (performance/speed/mission), `more_ork_prompts_SFT_extra.md` (X0–X5), `more_ork_prompts_3style.md` (Short/Brief/Opt).

---
- **[ELL-001]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 1 · `RocketSerializer__rocket.ork`]
  > Design a rocket that goes to apogee in about 9.7 s with a total flight of about 25.1 s.
- **[ELL-002]** [SFT_extra:X3 · apogee,groundhit · Simulation 1 · `RocketSerializer__rocket.ork`]
  > Design a rocket that goes to about 662 m apogee and touches down at about 61.0 m/s.
- **[ELL-003]** [by_type:mission · motor,timetoapogee · Simulation 1 · `RocketSerializer__rocket.ork`]
  > Design a rocket that goes on a G66-LR motor to apogee in about 9.7 s.
- **[ELL-004]** [by_type:performance · apogee,flighttime · Simulation 1 · `RocketSerializer__rocket.ork`]
  > Design a rocket that goes to about 662 m apogee with a total flight time of about 25.1 s.
- **[ELL-005]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `RocketSerializer__rocket.ork`]
  > Design a rocket that goes to about 181.9 m/s max velocity at about 218.7 m/s² max acceleration.
- **[ELL-006]** [more_base:T1 · apogee,maxvelocity · Simulation 1 · `RocketSerializer__rocket.ork`]
  > Design a rocket that goes to about 662 m apogee, reaching about 181.9 m/s max velocity.
- **[ELL-007]** [3style:Brief · engineering brief · Simulation 1 · `rockets__bt_55.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 642-682 m, flight time 24-26 s, max velocity at most 200 m/s, ground-hit velocity at most 63 m/s. Use motors in the class of G66-LR. Output the OpenRocket simulation numbers for each requirement.
- **[ELL-008]** [3style:Opt · optimization · Simulation 1 · `rockets__bt_55.ork`]
  > Find the lightest, simplest rocket that still reaches 662 m apogee with a 25 s flight and lands under 63 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[ELL-009]** [3style:Short · short · Simulation 1 · `rockets__bt_55.ork`]
  > Make a rocket that hits 662 m and stays up about 25 s on a G66-LR motor.
