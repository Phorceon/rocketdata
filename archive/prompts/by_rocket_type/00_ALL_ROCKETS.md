# ALL ROCKET PROMPTS — by rocket type (compiled, deduplicated, labeled)

Compilation of `by_rocket_type/` per-type files. 462 labeled (rocket,prompt) entries from 543 raw entries (81 source-format repeats removed: same prompt in .csv/.txt/.md/SFT for the same rocket kept once). Globally unique prompt strings: 430. 32 strings are shared across rocket types (identical sim numbers reused in duplicate .ork files, e.g. orhelper↔Prometeus, CenturiArrow300↔rocket) — kept under each rocket with a *shared* flag so no rocket file is left incomplete.

## Index

| Prefix | Rocket type | File | Count |
|---|---|---|---|
| `RAK` | Raketa | `01_raketa.md` | 121 |
| `ASM` | A simple model rocket | `02_a_simple_model_rocket.md` | 96 |
| `PRO` | Prometeus | `03_prometeus.md` | 54 |
| `CEN` | Centuri Arrow 300 | `04_centuri_arrow_300.md` | 29 |
| `ROK` | Rocket | `05_rocket.md` | 44 |
| `XRY` | X-Ray | `06_x_ray.md` | 17 |
| `BRY` | Bryant's Test Rocket | `07_bryants_test_rocket.md` | 8 |
| `ELL` | Rocket example with Elliptical Fins | `08_elliptical_fins.md` | 9 |
| `GRN` | OpenRocket Comparison of Green Eggs | `09_green_eggs.md` | 9 |
| `ORK` | Diverse .ork singletons | `10_ork_singletons.md` | 75 |

---

## Raketa (121 prompts)

- **[RAK-001]** [3style:Brief · engineering brief · Simulation 1 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 599-636 m, flight time 139-154 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-002]** [3style:Opt · optimization · Simulation 1 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 618 m apogee with a 147 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-003]** [3style:Short · short · Simulation 1 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 618 m and stays up about 147 s on a GragasMAY24 motor.
- **[RAK-004]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 1 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 618 m apogee on a GragasMAY24 motor, taking about 11.4 s to apogee.
- **[RAK-005]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 1 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 127.5 m/s max velocity at about 71.1 m/s² peak acceleration.
- **[RAK-006]** [by_type:mission · motor,timetoapogee · Simulation 1 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes on a GragasMAY24 motor to apogee in about 11.4 s.
- **[RAK-007]** [by_type:speed · maxvelocity,maxaccel · Simulation 1 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 127.5 m/s max velocity at about 71.1 m/s² max acceleration.
- **[RAK-008]** [by_type:performance, more_base:T0 · apogee,flighttime · Simulation 1 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 618 m apogee with a total flight time of about 146.7 s.
- **[RAK-009]** [3style:Brief · engineering brief · Simulation 10 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 601-638 m, flight time 180-199 s, max velocity at most 200 m/s, ground-hit velocity at most 5 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-010]** [3style:Opt · optimization · Simulation 10 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 620 m apogee with a 189 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-011]** [3style:Short · short · Simulation 10 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 620 m and stays up about 189 s on a GragasMAY24 motor.
- **[RAK-012]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 10 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 620 m apogee on a GragasMAY24 motor, taking about 11.2 s to apogee.
- **[RAK-013]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 10 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 136.1 m/s max velocity at about 77.5 m/s² peak acceleration.
- **[RAK-014]** [by_type:performance · apogee,flighttime · Simulation 10 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 620 m apogee with a total flight time of about 189.3 s.
- **[RAK-015]** [by_type:speed · maxvelocity,maxaccel · Simulation 10 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 136.1 m/s max velocity at about 77.5 m/s² max acceleration.
- **[RAK-016]** [more_base:T4 · maxvelocity,flighttime,groundhit · Simulation 10 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 136.1 m/s max velocity with a 189.3 s flight and touchdown at about 3.5 m/s.
- **[RAK-017]** [3style:Brief · engineering brief · Simulation 11 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 619-658 m, flight time 153-169 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-018]** [3style:Opt · optimization · Simulation 11 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 638 m apogee with a 161 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-019]** [3style:Short · short · Simulation 11 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 638 m and stays up about 161 s on a GragasMAY24 motor.
- **[RAK-020]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 11 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to apogee in about 11.2 s with a total flight of about 160.9 s.
- **[RAK-021]** [SFT_extra:X3 · apogee,groundhit · Simulation 11 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 638 m apogee and touches down at about 4.2 m/s.
- **[RAK-022]** [by_type:speed · maxvelocity,maxaccel · Simulation 11 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 140.4 m/s max velocity at about 80.4 m/s² max acceleration.
- **[RAK-023]** [by_type:performance, more_base:T0 · apogee,flighttime · Simulation 11 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 638 m apogee with a total flight time of about 160.9 s.
- **[RAK-024]** [3style:Brief · engineering brief · Simulation 12 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 610-648 m, flight time 151-167 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-025]** [3style:Opt · optimization · Simulation 12 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 629 m apogee with a 159 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-026]** [3style:Short · short · Simulation 12 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 629 m and stays up about 159 s on a GragasMAY24 motor.
- **[RAK-027]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 12 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes through about 80.5 m/s² max acceleration over a 158.7 s flight.
- **[RAK-028]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 12 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 140.3 m/s on a GragasMAY24 motor, reaching apogee in about 11.1 s.
- **[RAK-029]** [by_type:performance · apogee,flighttime · Simulation 12 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 629 m apogee with a total flight time of about 158.7 s.
- **[RAK-030]** [by_type:speed · maxvelocity,maxaccel · Simulation 12 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 140.3 m/s max velocity at about 80.5 m/s² max acceleration.
- **[RAK-031]** [more_base:T1 · apogee,maxvelocity · Simulation 12 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 629 m apogee, reaching about 140.3 m/s max velocity.
- **[RAK-032]** [3style:Brief · engineering brief · Simulation 13 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 625-663 m, flight time 155-171 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-033]** [3style:Opt · optimization · Simulation 13 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 644 m apogee with a 163 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-034]** [3style:Short · short · Simulation 13 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 644 m and stays up about 163 s on a GragasMAY24 motor.
- **[RAK-035]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 13 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 644 m apogee on a GragasMAY24 motor, taking about 11.3 s to apogee.
- **[RAK-036]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 13 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 141.5 m/s max velocity at about 81.0 m/s² peak acceleration.
- **[RAK-037]** [by_type:mission · motor,timetoapogee · Simulation 13 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes on a GragasMAY24 motor to apogee in about 11.3 s.
- **[RAK-038]** [by_type:performance · apogee,flighttime · Simulation 13 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 644 m apogee with a total flight time of about 162.9 s.
- **[RAK-039]** [by_type:speed · maxvelocity,maxaccel · Simulation 13 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 141.5 m/s max velocity at about 81.0 m/s² max acceleration.
- **[RAK-040]** [more_base:T2 · apogee,maxaccel · Simulation 13 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 644 m apogee, hitting about 81.0 m/s² max acceleration.
- **[RAK-041]** [3style:Brief · engineering brief · Simulation 14 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 575-610 m, flight time 134-148 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-042]** [3style:Opt · optimization · Simulation 14 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 593 m apogee with a 141 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-043]** [3style:Short · short · Simulation 14 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 593 m and stays up about 141 s on a GragasMAY24 motor.
- **[RAK-044]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 14 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to apogee in about 11.1 s with a total flight of about 141.3 s.
- **[RAK-045]** [SFT_extra:X3 · apogee,groundhit · Simulation 14 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 593 m apogee and touches down at about 4.5 m/s.
- **[RAK-046]** [by_type:performance · apogee,flighttime · Simulation 14 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 593 m apogee with a total flight time of about 141.3 s.
- **[RAK-047]** [by_type:speed · maxvelocity,maxaccel · Simulation 14 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 127.2 m/s max velocity at about 71.3 m/s² max acceleration.
- **[RAK-048]** [more_base:T3 · apogee,timetoapogee,motor · Simulation 14 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 593 m apogee in about 11.1 s to apogee on a GragasMAY24 motor.
- **[RAK-049]** [3style:Brief · engineering brief · Simulation 15 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 564-599 m, flight time 132-146 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-050]** [3style:Opt · optimization · Simulation 15 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 581 m apogee with a 139 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-051]** [3style:Short · short · Simulation 15 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 581 m and stays up about 139 s on a GragasMAY24 motor.
- **[RAK-052]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 15 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes through about 71.4 m/s² max acceleration over a 138.9 s flight.
- **[RAK-053]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 15 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 126.9 m/s on a GragasMAY24 motor, reaching apogee in about 11.1 s.
- **[RAK-054]** [by_type:performance · apogee,flighttime · Simulation 15 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 581 m apogee with a total flight time of about 138.9 s.
- **[RAK-055]** [by_type:speed · maxvelocity,maxaccel · Simulation 15 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 126.9 m/s max velocity at about 71.4 m/s² max acceleration.
- **[RAK-056]** [more_base:T4 · maxvelocity,flighttime,groundhit · Simulation 15 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 126.9 m/s max velocity with a 138.9 s flight and touchdown at about 4.5 m/s.
- **[RAK-057]** [3style:Brief · engineering brief · Simulation 2 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 616-654 m, flight time 23-26 s, max velocity at most 200 m/s, ground-hit velocity at most 75 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-058]** [3style:Opt · optimization · Simulation 2 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 635 m apogee with a 24 s flight and lands under 75 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-059]** [3style:Short · short · Simulation 2 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 635 m and stays up about 24 s on a GragasMAY24 motor.
- **[RAK-060]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 2 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to apogee in about 11.2 s with a total flight of about 24.5 s.
- **[RAK-061]** [SFT_extra:X3 · apogee,groundhit · Simulation 2 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 635 m apogee and touches down at about 73.9 m/s.
- **[RAK-062]** [by_type:mission · motor,timetoapogee · Simulation 2 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes on a GragasMAY24 motor to apogee in about 11.2 s.
- **[RAK-063]** [by_type:performance · apogee,flighttime · Simulation 2 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 635 m apogee with a total flight time of about 24.5 s.
- **[RAK-064]** [by_type:speed · maxvelocity,maxaccel · Simulation 2 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 142.5 m/s max velocity at about 82.0 m/s² max acceleration.
- **[RAK-065]** [more_base:T1 · apogee,maxvelocity · Simulation 2 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 635 m apogee, reaching about 142.5 m/s max velocity.
- **[RAK-066]** [3style:Brief · engineering brief · Simulation 3 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 620-659 m, flight time 23-26 s, max velocity at most 200 m/s, ground-hit velocity at most 76 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-067]** [3style:Opt · optimization · Simulation 3 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 640 m apogee with a 25 s flight and lands under 76 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-068]** [3style:Short · short · Simulation 3 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 640 m and stays up about 25 s on a GragasMAY24 motor.
- **[RAK-069]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 3 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes through about 82.0 m/s² max acceleration over a 24.6 s flight.
- **[RAK-070]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 3 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 142.6 m/s on a GragasMAY24 motor, reaching apogee in about 11.2 s.
- **[RAK-071]** [by_type:performance · apogee,flighttime · Simulation 3 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 640 m apogee with a total flight time of about 24.6 s.
- **[RAK-072]** [by_type:speed · maxvelocity,maxaccel · Simulation 3 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 142.6 m/s max velocity at about 82.0 m/s² max acceleration.
- **[RAK-073]** [more_base:T2 · apogee,maxaccel · Simulation 3 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 640 m apogee, hitting about 82.0 m/s² max acceleration.
- **[RAK-074]** [3style:Brief · engineering brief · Simulation 4 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 625-664 m, flight time 23-26 s, max velocity at most 200 m/s, ground-hit velocity at most 75 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-075]** [3style:Opt · optimization · Simulation 4 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 644 m apogee with a 25 s flight and lands under 75 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-076]** [3style:Short · short · Simulation 4 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 644 m and stays up about 25 s on a GragasMAY24 motor.
- **[RAK-077]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 4 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 644 m apogee on a GragasMAY24 motor, taking about 11.1 s to apogee.
- **[RAK-078]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 4 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 144.1 m/s max velocity at about 83.2 m/s² peak acceleration.
- **[RAK-079]** [by_type:mission · motor,timetoapogee · Simulation 4 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes on a GragasMAY24 motor to apogee in about 11.1 s.
- **[RAK-080]** [by_type:performance · apogee,flighttime · Simulation 4 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 644 m apogee with a total flight time of about 24.7 s.
- **[RAK-081]** [by_type:speed · maxvelocity,maxaccel · Simulation 4 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 144.1 m/s max velocity at about 83.2 m/s² max acceleration.
- **[RAK-082]** [more_base:T3 · apogee,timetoapogee,motor · Simulation 4 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 644 m apogee in about 11.1 s to apogee on a GragasMAY24 motor.
- **[RAK-083]** [3style:Brief · engineering brief · Simulation 5 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 601-638 m, flight time 23-25 s, max velocity at most 200 m/s, ground-hit velocity at most 77 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-084]** [3style:Opt · optimization · Simulation 5 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 620 m apogee with a 24 s flight and lands under 77 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-085]** [3style:Short · short · Simulation 5 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 620 m and stays up about 24 s on a GragasMAY24 motor.
- **[RAK-086]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 5 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to apogee in about 11.1 s with a total flight of about 24.2 s.
- **[RAK-087]** [SFT_extra:X3 · apogee,groundhit · Simulation 5 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 620 m apogee and touches down at about 75.2 m/s.
- **[RAK-088]** [by_type:performance · apogee,flighttime · Simulation 5 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 620 m apogee with a total flight time of about 24.2 s.
- **[RAK-089]** [by_type:speed · maxvelocity,maxaccel · Simulation 5 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 135.9 m/s max velocity at about 77.4 m/s² max acceleration.
- **[RAK-090]** [more_base:T4 · maxvelocity,flighttime,groundhit · Simulation 5 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 135.9 m/s max velocity with a 24.2 s flight and touchdown at about 75.2 m/s.
- **[RAK-091]** [3style:Brief · engineering brief · Simulation 6 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 595-631 m, flight time 23-25 s, max velocity at most 200 m/s, ground-hit velocity at most 76 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-092]** [3style:Opt · optimization · Simulation 6 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 613 m apogee with a 24 s flight and lands under 76 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-093]** [3style:Short · short · Simulation 6 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 613 m and stays up about 24 s on a GragasMAY24 motor.
- **[RAK-094]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 6 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes through about 77.4 m/s² max acceleration over a 24.0 s flight.
- **[RAK-095]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 6 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 135.8 m/s on a GragasMAY24 motor, reaching apogee in about 11.1 s.
- **[RAK-096]** [by_type:speed · maxvelocity,maxaccel · Simulation 6 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 135.8 m/s max velocity at about 77.4 m/s² max acceleration.
- **[RAK-097]** [by_type:performance, more_base:T0 · apogee,flighttime · Simulation 6 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 613 m apogee with a total flight time of about 24.0 s.
- **[RAK-098]** [3style:Brief · engineering brief · Simulation 7 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 593-630 m, flight time 177-196 s, max velocity at most 200 m/s, ground-hit velocity at most 5 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-099]** [3style:Opt · optimization · Simulation 7 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 611 m apogee with a 186 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-100]** [3style:Short · short · Simulation 7 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 611 m and stays up about 186 s on a GragasMAY24 motor.
- **[RAK-101]** [SFT_extra:X0 · motor,apogee,timetoapogee · Simulation 7 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 611 m apogee on a GragasMAY24 motor, taking about 11.1 s to apogee.
- **[RAK-102]** [SFT_extra:X1 · maxvelocity,maxaccel · Simulation 7 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 135.5 m/s max velocity at about 77.2 m/s² peak acceleration.
- **[RAK-103]** [by_type:performance · apogee,flighttime · Simulation 7 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 611 m apogee with a total flight time of about 186.4 s.
- **[RAK-104]** [by_type:speed · maxvelocity,maxaccel · Simulation 7 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 135.5 m/s max velocity at about 77.2 m/s² max acceleration.
- **[RAK-105]** [more_base:T1 · apogee,maxvelocity · Simulation 7 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 611 m apogee, reaching about 135.5 m/s max velocity.
- **[RAK-106]** [3style:Brief · engineering brief · Simulation 8 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 597-634 m, flight time 178-197 s, max velocity at most 200 m/s, ground-hit velocity at most 5 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-107]** [3style:Opt · optimization · Simulation 8 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 616 m apogee with a 188 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-108]** [3style:Short · short · Simulation 8 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 616 m and stays up about 188 s on a GragasMAY24 motor.
- **[RAK-109]** [SFT_extra:X2 · timetoapogee,flighttime · Simulation 8 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to apogee in about 11.1 s with a total flight of about 187.7 s.
- **[RAK-110]** [SFT_extra:X3 · apogee,groundhit · Simulation 8 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 616 m apogee and touches down at about 3.5 m/s.
- **[RAK-111]** [by_type:performance · apogee,flighttime · Simulation 8 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 616 m apogee with a total flight time of about 187.7 s.
- **[RAK-112]** [by_type:speed · maxvelocity,maxaccel · Simulation 8 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 135.6 m/s max velocity at about 77.2 m/s² max acceleration.
- **[RAK-113]** [more_base:T2 · apogee,maxaccel · Simulation 8 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 616 m apogee, hitting about 77.2 m/s² max acceleration.
- **[RAK-114]** [3style:Brief · engineering brief · Simulation 9 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 603-640 m, flight time 180-199 s, max velocity at most 200 m/s, ground-hit velocity at most 5 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
- **[RAK-115]** [3style:Opt · optimization · Simulation 9 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Find the lightest, simplest rocket that still reaches 622 m apogee with a 189 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
- **[RAK-116]** [3style:Short · short · Simulation 9 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Make a rocket that hits 622 m and stays up about 189 s on a GragasMAY24 motor.
- **[RAK-117]** [SFT_extra:X4 · maxaccel,flighttime · Simulation 9 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes through about 77.2 m/s² max acceleration over a 189.3 s flight.
- **[RAK-118]** [SFT_extra:X5 · maxvelocity,motor,timetoapogee · Simulation 9 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 135.7 m/s on a GragasMAY24 motor, reaching apogee in about 11.2 s.
- **[RAK-119]** [by_type:performance · apogee,flighttime · Simulation 9 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 622 m apogee with a total flight time of about 189.3 s.
- **[RAK-120]** [by_type:speed · maxvelocity,maxaccel · Simulation 9 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 135.7 m/s max velocity at about 77.2 m/s² max acceleration.
- **[RAK-121]** [more_base:T3 · apogee,timetoapogee,motor · Simulation 9 · `czech-rocket-challenge-2025__Raketa.ork`]
  > Design a rocket that goes to about 622 m apogee in about 11.2 s to apogee on a GragasMAY24 motor.

---

## A simple model rocket (96 prompts)

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

---

## Prometeus (54 prompts)

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

---

## Centuri Arrow 300 (29 prompts)

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

---

## Rocket (44 prompts)

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

---

## X-Ray (17 prompts)

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

---

## Bryant's Test Rocket (8 prompts)

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

---

## Rocket example with Elliptical Fins (9 prompts)

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

---

## OpenRocket Comparison of Green Eggs (9 prompts)

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

---

## Diverse .ork singletons (75 prompts)


### APEX family (13)

- **[ORK-012]** [ork:T1 · apogee,maxvelocity · Simulation 2 · `APEX 20102020 (Longer BT)__02ca07.ork`]
  > Design a rocket that goes to about 3,571 m apogee, reaching about 439 m/s max velocity.
- **[ORK-013]** [ork:T2 · apogee,maxmach,maxacceleration · -2º Launch · `APEX 29.08.2021__179543.ork`]
  > Design a rocket that goes to about 2,851 m apogee, hitting about Mach 1.04 and 202 m/s² max acceleration.
- **[ORK-014]** [ork:T3 · stages,apogee,timetoapogee,motor · -2º Launch · `APEX 30.08.2021__10a283.ork`]
  > Design a rocket that goes to about 2,884 m apogee in about 21 s to apogee on a APEX | Cesaroni I216-CL(I)-14 motor.
- **[ORK-015]** [ork:T4 · apogee,deploymentvelocity,flighttime · APEX · `APEXJTentative__ec5252.ork`]
  > Design a rocket that goes to about 3,723 m apogee with deployment at about 58 m/s and a 21 s flight.
- **[ORK-016]** [ork:T0 · apogee,flighttime · Simulation 3 · `APEX_04.21__2a660f.ork`]
  > Design a rocket that goes to about 3,236 m apogee with a total flight time of about 89 s.
- **[ORK-017]** [ork:T1 · apogee,maxvelocity · Simulation 5 · `APEX_AeroTech__c07a5a.ork`]
  > Design a rocket that goes to about 2,912 m apogee, reaching about 342 m/s max velocity.
- **[ORK-018]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 1 · `APEX_Cesaroni__c75b0f.ork`]
  > Design a rocket that goes to about 2,758 m apogee, hitting about Mach 1.09 and 220 m/s² max acceleration.
- **[ORK-019]** [ork:T3 · stages,apogee,timetoapogee · Simulation 1 · `APEX_K_Dart__a7a1a4.ork`]
  > Design a 2-stage rocket that goes to about 6,105 m apogee in about 34 s to apogee.
- **[ORK-020]** [ork:T4 · apogee,deploymentvelocity,flighttime · Baseline · `APEX_K_SS__cb1d67.ork`]
  > Design a rocket that goes to about 5,804 m apogee with deployment at about 29 m/s and a 230 s flight.
- **[ORK-021]** [ork:T0 · apogee,flighttime · Simulation 1 · `APEX_Target__4ae962.ork`]
  > Design a rocket that goes to about 2,738 m apogee with a total flight time of about 150 s.
- **[ORK-022]** [ork:T1 · apogee,maxvelocity · Final Sim (?) · `APEX__4f8fe7.ork`]
  > Design a rocket that goes to about 2,892 m apogee, reaching about 367 m/s max velocity.
- **[ORK-023]** [ork:T2 · apogee,maxmach,maxacceleration · -2º Launch · `APEX__5761c9.ork`]
  > Design a rocket that goes to about 2,884 m apogee, hitting about Mach 1.08 and 212 m/s² max acceleration.
- **[ORK-024]** [ork:T3 · stages,apogee,timetoapogee · Simulation 1 · `APEX__bf43c5.ork`]
  > Design a rocket that goes to about 2,700 m apogee in about 21 s to apogee.

### ASTRA family (8)

- **[ORK-027]** [ork:T1 · apogee,maxvelocity · Simulation 1 · `ASTRA 11.04.2021__f71068.ork`]
  > Design a rocket that goes to about 543 m apogee, reaching about 95 m/s max velocity.
- **[ORK-028]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 1 · `ASTRA 13.06.2021__c8c6df.ork`] *shared with ['ASTRA__c3425a.ork']*
  > Design a rocket that goes to about 550 m apogee, hitting about Mach 0.27 and 88 m/s² max acceleration.
- **[ORK-029]** [ork:T3 · stages,apogee,timetoapogee · Simulation 3 · `ASTRA_08.03.21__1b3d83.ork`]
  > Design a rocket that goes to about 478 m apogee in about 10 s to apogee.
- **[ORK-030]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 3 · `ASTRA_11.03.21__3ec349.ork`]
  > Design a rocket that goes to about 478 m apogee with deployment at about 51 m/s and a 54 s flight.
- **[ORK-031]** [ork:T0 · apogee,flighttime · Simulation 4 · `ASTRA_V1__36e356.ork`]
  > Design a rocket that goes to about 779 m apogee with a total flight time of about 59 s.
- **[ORK-032]** [ork:T1 · apogee,maxvelocity · Simulation 5 · `ASTRA__bbbe1f.ork`]
  > Design a rocket that goes to about 1,244 m apogee, reaching about 260 m/s max velocity.
- **[ORK-033]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 1 · `ASTRA__c3425a.ork`] *shared with ['ASTRA 13.06.2021__c8c6df.ork']*
  > Design a rocket that goes to about 550 m apogee, hitting about Mach 0.27 and 88 m/s² max acceleration.
- **[ORK-034]** [ork:T3 · stages,apogee,timetoapogee · Simulation 5 · `ASTRAwFairing__1976e9.ork`]
  > Design a rocket that goes to about 1,244 m apogee in about 14 s to apogee.

### MDL / high-power testbeds (6)

- **[ORK-005]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 3 · `38MDL1__2cbbf2.ork`]
  > Design a rocket that goes to about 1,769 m apogee with deployment at about 38 m/s and a 96 s flight.
- **[ORK-006]** [ork:T0 · apogee,flighttime · Simulation 3 · `38MDL2__7e70a9.ork`]
  > Design a rocket that goes to about 1,769 m apogee with a total flight time of about 96 s.
- **[ORK-008]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 11 · `54ActiveAero__89c085.ork`]
  > Design a rocket that goes to about 2,735 m apogee, hitting about Mach 1.22 and 248 m/s² max acceleration.
- **[ORK-009]** [ork:T3 · stages,apogee,timetoapogee · Simulation 7 · `54MDL2__8d6955.ork`]
  > Design a 9-stage rocket that goes to about 5,520 m apogee in about 26 s to apogee.
- **[ORK-010]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 1 · `54SubminL3__e60737.ork`]
  > Design a rocket that goes to about 14,180 m apogee with deployment at about 30 m/s and a 547 s flight.
- **[ORK-011]** [ork:T0 · apogee,flighttime · Simulation 2 · `75MDL3__2ff3c4.ork`]
  > Design a rocket that goes to about 12,410 m apogee with a total flight time of about 402 s.

### Other singletons (38)

- **[ORK-003]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 4 · `24mmRocket__bd6d71.ork`]
  > Design a rocket that goes to about 744 m apogee, hitting about Mach 0.38 and 121 m/s² max acceleration.
- **[ORK-025]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 1 (Florida baseline) · `ASCENSION__269a6b.ork`]
  > Design a rocket that goes to about 5,748 m apogee with deployment at about None m/s and a 28 s flight.
- **[ORK-026]** [ork:T0 · apogee,flighttime · Simulation 1 (Florida baseline) · `ASCENSION__f5b937.ork`]
  > Design a rocket that goes to about 5,899 m apogee with a total flight time of about 317 s.
- **[ORK-035]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 2 · `DarkStar_Mini[1]__378a10.ork`]
  > Design a rocket that goes to about 965 m apogee with deployment at about 18 m/s and a 116 s flight.
- **[ORK-036]** [ork:T0 · apogee,flighttime · Simulation 5 · `K2050Sim__2ffdfd.ork`]
  > Design a rocket that goes to about 3,824 m apogee with a total flight time of about 234 s.
- **[ORK-037]** [ork:T1 · apogee,maxvelocity · Simulation 1 · `L1 Example__2358ed.ork`]
  > Design a rocket that goes to about 729 m apogee, reaching about 216 m/s max velocity.
- **[ORK-038]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 1 · `MockUpofASCENSION(StabilityIssue)__4de54a.ork`]
  > Design a rocket that goes to about 1,364 m apogee, hitting about Mach 2.05 and 320 m/s² max acceleration.
- **[ORK-039]** [ork:T3 · stages,apogee,timetoapogee · Mojave Sphinx, Launch 9 Simulation using Static Test 10 Thrust Curve · `Mojave Sphinx V1.2__c1c8d9.ork`]
  > Design a 2-stage rocket that goes to about 1,785 m apogee in about 19 s to apogee.
- **[ORK-040]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 1 · `OtherTwoStager__e12bf3.ork`]
  > Design a rocket that goes to about 2,396 m apogee with deployment at about 28 m/s and a 123 s flight.
- **[ORK-041]** [ork:T0 · apogee,flighttime · Simulation 1 · `PK37-Athena__3e873f.ork`]
  > Design a rocket that goes to about 673 m apogee with a total flight time of about 139 s.
- **[ORK-042]** [ork:T1 · apogee,maxvelocity · Simulation 1 · `RATO__e7d077.ork`]
  > Design a rocket that goes to about 399 m apogee, reaching about 131 m/s max velocity.
- **[ORK-044]** [ork:T3 · stages,apogee,timetoapogee · Simulation 2 · `SimpleL1__417247.ork`]
  > Design a 3-stage rocket that goes to about 754 m apogee in about 10 s to apogee.
- **[ORK-050]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 1 · `TwoStager__84a275.ork`]
  > Design a rocket that goes to about 2,718 m apogee with deployment at about 25 m/s and a 145 s flight.
- **[ORK-051]** [ork:T0 · apogee,flighttime · Simulation 1 · `aerotech_arreaux__ac75e5.ork`]
  > Design a rocket that goes to about 365 m apogee with a total flight time of about 65 s.
- **[ORK-052]** [ork:T1 · apogee,maxvelocity · Fenix Rocket Team · `rocket__188a6a.ork`]
  > Design a rocket that goes to about 3,181 m apogee, reaching about 326 m/s max velocity.
- **[ORK-053]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 28 · `rocket__19b6ba.ork`]
  > Design a rocket that goes to about 2,424 m apogee, hitting about Mach 0.80 and 89 m/s² max acceleration.
- **[ORK-054]** [ork:T3 · stages,apogee,timetoapogee · Simulation 7 · `rocket__1cd69d.ork`]
  > Design a rocket that goes to about 1,532 m apogee in about 18 s to apogee.
- **[ORK-055]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 3 · `rocket__2ba66a.ork`]
  > Design a rocket that goes to about 3,036 m apogee with deployment at about 229 m/s and a 48 s flight.
- **[ORK-056]** [ork:T0 · apogee,flighttime · M1520 BlueStreak 84_5 · `rocket__3b8501.ork`]
  > Design a rocket that goes to about 3,268 m apogee with a total flight time of about 200 s.
- **[ORK-057]** [ork:T1 · apogee,maxvelocity · EuRoC_84deg · `rocket__45ac95.ork`]
  > Design a rocket that goes to about 2,646 m apogee, reaching about 294 m/s max velocity.
- **[ORK-058]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 1 · `rocket__49c8de.ork`]
  > Design a rocket that goes to about 1,190 m apogee, hitting about Mach 0.56 and 122 m/s² max acceleration.
- **[ORK-059]** [ork:T3 · stages,apogee,timetoapogee,motor · Blue Streak · `rocket__504e63.ork`]
  > Design a 7-stage rocket that goes to about 3,796 m apogee in about 27 s to apogee on a Blue Streak motor.
- **[ORK-060]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 2 · `rocket__61cb00.ork`]
  > Design a rocket that goes to about 2,685 m apogee with deployment at about 34 m/s and a 188 s flight.
- **[ORK-061]** [ork:T0 · apogee,flighttime · Taranis Nominal Flight · `rocket__620f66.ork`]
  > Design a rocket that goes to about 9,365 m apogee with a total flight time of about 698 s.
- **[ORK-062]** [ork:T1 · apogee,maxvelocity · Simulation 5 · `rocket__7e1fd3.ork`]
  > Design a rocket that goes to about 9,080 m apogee, reaching about 472 m/s max velocity.
- **[ORK-063]** [ork:T2 · apogee,maxmach,maxacceleration · Stability vs Time · `rocket__a79076.ork`]
  > Design a rocket that goes to about 3,225 m apogee, hitting about Mach 0.71 and 62 m/s² max acceleration.
- **[ORK-064]** [ork:T3 · stages,apogee,timetoapogee · Simulation 60 · `rocket__b87d11.ork`]
  > Design a rocket that goes to about 9,188 m apogee in about 40 s to apogee.
- **[ORK-065]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 1 · `rocket__c08cee.ork`]
  > Design a rocket that goes to about 3,390 m apogee with deployment at about 34 m/s and a 180 s flight.
- **[ORK-066]** [ork:T0 · apogee,flighttime · EuRoC 2022 Launch at Santa Margarida Military Camp · `rocket__c3d681.ork`]
  > Design a rocket that goes to about 9,199 m apogee with a total flight time of about 448 s.
- **[ORK-067]** [ork:T1 · apogee,maxvelocity · EuRoC 2 m/s · `rocket__d5a7f2.ork`]
  > Design a rocket that goes to about 3,488 m apogee, reaching about 315 m/s max velocity.
- **[ORK-068]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 1 · `rocket__d73a6b.ork`]
  > Design a rocket that goes to about 662 m apogee, hitting about Mach 0.54 and 219 m/s² max acceleration.
- **[ORK-069]** [ork:T3 · stages,apogee,timetoapogee · finalSimulation · `rocket__d77051.ork`]
  > Design a rocket that goes to about 882 m apogee in about 15 s to apogee.
- **[ORK-070]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 1 · `rocket__e711b1.ork`]
  > Design a rocket that goes to about 3,598 m apogee with deployment at about 12 m/s and a 303 s flight.
- **[ORK-071]** [ork:T0 · apogee,flighttime · EuRoC Launch · `rocket__e9e655.ork`]
  > Design a rocket that goes to about 3,118 m apogee with a total flight time of about 53 s.
- **[ORK-072]** [ork:T1 · apogee,maxvelocity · Simulation 2 · `rocket__f39723.ork`]
  > Design a rocket that goes to about 3,041 m apogee, reaching about 312 m/s max velocity.
- **[ORK-073]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 1 · `rocket__f4bcc9.ork`]
  > Design a rocket that goes to about 3,339 m apogee, hitting about Mach 0.74 and 66 m/s² max acceleration.
- **[ORK-074]** [ork:T3 · stages,apogee,timetoapogee · 90deg_4mps · `rocket__fdc85b.ork`]
  > Design a rocket that goes to about 3,035 m apogee in about 26 s to apogee.
- **[ORK-075]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 8 · `superdx3__8c40bf.ork`]
  > Design a rocket that goes to about 1,340 m apogee with deployment at about 26 m/s and a 86 s flight.

### SIRIUS/Siruis family (6)

- **[ORK-043]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 2 · `SIRIUS__4f0e68.ork`]
  > Design a rocket that goes to about 10,220 m apogee, hitting about Mach 1.97 and 161 m/s² max acceleration.
- **[ORK-045]** [ork:T4 · apogee,deploymentvelocity,flighttime · Simulation 2 · `Siruis_N1560__962247.ork`]
  > Design a rocket that goes to about 8,306 m apogee with deployment at about 221 m/s and a 88 s flight.
- **[ORK-046]** [ork:T0 · apogee,flighttime · Simulation 2 · `Siruis_O3400__3b00eb.ork`]
  > Design a rocket that goes to about 8,212 m apogee with a total flight time of about 88 s.
- **[ORK-047]** [ork:T1 · apogee,maxvelocity · Simulation 5 · `Siruis_O3800_ACTUALmass__b07ddf.ork`]
  > Design a rocket that goes to about 8,608 m apogee, reaching about 782 m/s max velocity.
- **[ORK-048]** [ork:T2 · apogee,maxmach,maxacceleration · Simulation 2 · `Siruis_O3800_CADmasses__44ad19.ork`]
  > Design a rocket that goes to about 8,175 m apogee, hitting about Mach 1.79 and 152 m/s² max acceleration.
- **[ORK-049]** [ork:T3 · stages,apogee,timetoapogee · Simulation 2 · `Siruis_O3800__62b0d9.ork`]
  > Design a 12-stage rocket that goes to about 8,175 m apogee in about 36 s to apogee.

### Spline/Rounded/Linear (4)

- **[ORK-001]** [ork:T0 · apogee,flighttime · Simulation 1 · `1. Rounded Spline__70fe2c.ork`]
  > Design a rocket that goes to about 3,380 m apogee with a total flight time of about 401 s.
- **[ORK-002]** [ork:T1 · apogee,maxvelocity · Simulation 1 · `2. Rounded__ef26c0.ork`] *shared with ['4. Spline__763a0c.ork']*
  > Design a rocket that goes to about 3,380 m apogee, reaching about 435 m/s max velocity.
- **[ORK-004]** [ork:T3 · stages,apogee,timetoapogee · Simulation 1 · `3. Linear__3a296b.ork`]
  > Design a rocket that goes to about 3,380 m apogee in about 22 s to apogee.
- **[ORK-007]** [ork:T1 · apogee,maxvelocity · Simulation 1 · `4. Spline__763a0c.ork`] *shared with ['2. Rounded__ef26c0.ork']*
  > Design a rocket that goes to about 3,380 m apogee, reaching about 435 m/s max velocity.
