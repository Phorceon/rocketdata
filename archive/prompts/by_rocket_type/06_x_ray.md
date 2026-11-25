# X-Ray — 17 labeled prompts (deduplicated)

Label prefix `XRY`. Each prompt appears once in this file (source-format repeats removed). 0 prompt(s) are textually identical to prompts for another rocket type (same sim numbers reused across files) — flagged *shared*.

Sources merged: `more_ork_prompts.csv` (T0–T4), `more_ork_prompts_by_type` (performance/speed/mission), `more_ork_prompts_SFT_extra.md` (X0–X5), `more_ork_prompts_3style.md` (Short/Brief/Opt).

---
- **[XRY-001]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 1 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes to about 492 m apogee on a G74W motor, taking about 9.2 s to apogee.
- **[XRY-002]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 1 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes to about 141.3 m/s max velocity at about 161.7 m/s² peak acceleration.
- **[XRY-003]** [by_type:mission · motor,timetoapogee · Simulation 1 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes on a G74W motor to apogee in about 9.2 s.
- **[XRY-004]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes to about 141.3 m/s max velocity at about 161.7 m/s² max acceleration.
- **[XRY-005]** [by_type:performance, more_base:T0 · apogee,flighttime · Simulation 1 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes to about 492 m apogee with a total flight time of about 116.8 s.
- **[XRY-006]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 2 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes to apogee in about 10.4 s with a total flight of about 140.7 s.
- **[XRY-007]** [SFT_extra:X3 · apogee,groundhit · Simulation 2 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes to about 706 m apogee and touches down at about 2.7 m/s.
- **[XRY-008]** [by_type:mission · motor,timetoapogee · Simulation 2 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes on a G74W motor to apogee in about 10.4 s.
- **[XRY-009]** [by_type:performance · apogee,flighttime · Simulation 2 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes to about 706 m apogee with a total flight time of about 140.7 s.
- **[XRY-010]** [by_type:speed · maxvelocity,maxaccel · Simulation 2 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes to about 183.2 m/s max velocity at about 169.0 m/s² max acceleration.
- **[XRY-011]** [more_base:T1 · apogee,maxvelocity · Simulation 2 · `openrocket-web__test-rocket.ork`]
  > Design a rocket that goes to about 706 m apogee, reaching about 183.2 m/s max velocity.
- **[XRY-012]** [3style:Brief · engineering brief · Simulation 1 · `rockets__bt_55.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 477-506 m, flight time 111-123 s, max velocity at most 200 m/s, ground-hit velocity at most 4 m/s. Use motors in motor classes G (e.g. G74W, G80T). Output the OpenRocket simulation numbers for each requirement.
- **[XRY-013]** [3style:Opt · optimization · Simulation 1 · `rockets__bt_55.ork`]
  > Find the lightest, simplest rocket that still reaches 492 m apogee with a 117 s flight and lands under 4 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[XRY-014]** [3style:Short · short · Simulation 1 · `rockets__bt_55.ork`]
  > Make a rocket that hits 492 m and stays up about 117 s on a G74W motor.
- **[XRY-015]** [3style:Brief · engineering brief · Simulation 2 · `rockets__bt_55.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 685-728 m, flight time 134-148 s, max velocity at most 200 m/s, ground-hit velocity at most 4 m/s. Use motors in motor classes G (e.g. G74W, G80T). Output the OpenRocket simulation numbers for each requirement.
- **[XRY-016]** [3style:Opt · optimization · Simulation 2 · `rockets__bt_55.ork`]
  > Find the lightest, simplest rocket that still reaches 706 m apogee with a 141 s flight and lands under 4 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[XRY-017]** [3style:Short · short · Simulation 2 · `rockets__bt_55.ork`]
  > Make a rocket that hits 706 m and stays up about 141 s on a G74W motor.
