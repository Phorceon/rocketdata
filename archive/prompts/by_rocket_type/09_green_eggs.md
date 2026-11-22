# OpenRocket Comparison of Green Eggs — 9 labeled prompts (deduplicated)

Label prefix `GRN`. Each prompt appears once in this file (source-format repeats removed). 0 prompt(s) are textually identical to prompts for another rocket type (same sim numbers reused across files) — flagged *shared*.

Sources merged: `more_ork_prompts.csv` (T0–T4), `more_ork_prompts_by_type` (performance/speed/mission), `more_ork_prompts_SFT_extra.md` (X0–X5), `more_ork_prompts_3style.md` (Short/Brief/Opt).

---
- **[GRN-001]** [SFT_extra:X4 · maxaccel,flighttime · C-11 standard atmosphere · `numericalrocketry__green_eggs_openrocket_design.ork`]
  > Design a rocket that goes through about 123.9 m/s² max acceleration over a 27.2 s flight.
- **[GRN-002]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · C-11 standard atmosphere · `numericalrocketry__green_eggs_openrocket_design.ork`]
  > Design a rocket that goes to about 45.5 m/s on a C11 motor, reaching apogee in about 4.8 s.
- **[GRN-003]** [by_type:mission · motor,timetoapogee · C-11 standard atmosphere · `numericalrocketry__green_eggs_openrocket_design.ork`]
  > Design a rocket that goes on a C11 motor to apogee in about 4.8 s.
- **[GRN-004]** [by_type:performance · apogee,flighttime · C-11 standard atmosphere · `numericalrocketry__green_eggs_openrocket_design.ork`]
  > Design a rocket that goes to about 101 m apogee with a total flight time of about 27.2 s.
- **[GRN-005]** [by_type:speed · maxvelocity,maxaccel · C-11 standard atmosphere · `numericalrocketry__green_eggs_openrocket_design.ork`]
  > Design a rocket that goes to about 45.5 m/s max velocity at about 123.9 m/s² max acceleration.
- **[GRN-006]** [more_base:T1 · apogee,maxvelocity · C-11 standard atmosphere · `numericalrocketry__green_eggs_openrocket_design.ork`]
  > Design a rocket that goes to about 101 m apogee, reaching about 45.5 m/s max velocity.
- **[GRN-007]** [3style:Brief · engineering brief ·  · `rockets__bt_55.ork`]
  > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 98-104 m, flight time 26-29 s, max velocity at most 50 m/s, ground-hit velocity at most 6 m/s, liftoff mass at most 174 g, total length 51-63 cm. Use motors in the class of C11. Output the OpenRocket simulation numbers for each requirement.
- **[GRN-008]** [3style:Opt · optimization ·  · `rockets__bt_55.ork`]
  > Find the lightest, simplest rocket that still reaches 101 m apogee with a 27 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[GRN-009]** [3style:Short · short ·  · `rockets__bt_55.ork`]
  > Make a rocket that hits 101 m and stays up about 27 s, weighs around 166 g and is about 57 cm long.
