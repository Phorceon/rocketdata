# More .ork Prompts — Short / Engineering Brief / Optimization

Source: `rocket_files/reports/more_ork_files_sim_data.csv` (52 sim rows).
3 styles per row = 156 prompts, grouped by rocket type. SFT use: Short = easy instruction, Brief = constraint-following target (ask for sim numbers back), Optimization = reasoning/comparison target.

## Format note (mass/length)

- Liftoff mass and total length live in the `.ork` structure, not in the CSV, and are NOT fabricated here.
- Only the Green Eggs row keeps mass/length clauses — those numbers (166 g, 57 cm) were supplied with the example and are reproduced verbatim as the reference.
- All other Short prompts substitute the motor (`on a {motor} motor`); all other Briefs omit the mass/length clauses. Bands: apogee ±3%, flight −5%/+5% rounded outward, velocity = nice-ceiling, ground-hit = ceil+1. Power class derived from motor letters (≤D low, E–G mid, H+ high).

## 1. Rocket type: Raketa — 15 sims × 3 styles
(`Simulation 1` GragasMAY24)
Short: > Make a rocket that hits 618 m and stays up about 147 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 599-636 m, flight time 139-154 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 618 m apogee with a 147 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 2` GragasMAY24)
Short: > Make a rocket that hits 635 m and stays up about 24 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 616-654 m, flight time 23-26 s, max velocity at most 200 m/s, ground-hit velocity at most 75 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 635 m apogee with a 24 s flight and lands under 75 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 3` GragasMAY24)
Short: > Make a rocket that hits 640 m and stays up about 25 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 620-659 m, flight time 23-26 s, max velocity at most 200 m/s, ground-hit velocity at most 76 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 640 m apogee with a 25 s flight and lands under 76 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 4` GragasMAY24)
Short: > Make a rocket that hits 644 m and stays up about 25 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 625-664 m, flight time 23-26 s, max velocity at most 200 m/s, ground-hit velocity at most 75 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 644 m apogee with a 25 s flight and lands under 75 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 5` GragasMAY24)
Short: > Make a rocket that hits 620 m and stays up about 24 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 601-638 m, flight time 23-25 s, max velocity at most 200 m/s, ground-hit velocity at most 77 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 620 m apogee with a 24 s flight and lands under 77 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 6` GragasMAY24)
Short: > Make a rocket that hits 613 m and stays up about 24 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 595-631 m, flight time 23-25 s, max velocity at most 200 m/s, ground-hit velocity at most 76 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 613 m apogee with a 24 s flight and lands under 76 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 7` GragasMAY24)
Short: > Make a rocket that hits 611 m and stays up about 186 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 593-630 m, flight time 177-196 s, max velocity at most 200 m/s, ground-hit velocity at most 5 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 611 m apogee with a 186 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 8` GragasMAY24)
Short: > Make a rocket that hits 616 m and stays up about 188 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 597-634 m, flight time 178-197 s, max velocity at most 200 m/s, ground-hit velocity at most 5 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 616 m apogee with a 188 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 9` GragasMAY24)
Short: > Make a rocket that hits 622 m and stays up about 189 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 603-640 m, flight time 180-199 s, max velocity at most 200 m/s, ground-hit velocity at most 5 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 622 m apogee with a 189 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 10` GragasMAY24)
Short: > Make a rocket that hits 620 m and stays up about 189 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 601-638 m, flight time 180-199 s, max velocity at most 200 m/s, ground-hit velocity at most 5 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 620 m apogee with a 189 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 11` GragasMAY24)
Short: > Make a rocket that hits 638 m and stays up about 161 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 619-658 m, flight time 153-169 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 638 m apogee with a 161 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 12` GragasMAY24)
Short: > Make a rocket that hits 629 m and stays up about 159 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 610-648 m, flight time 151-167 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 629 m apogee with a 159 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 13` GragasMAY24)
Short: > Make a rocket that hits 644 m and stays up about 163 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 625-663 m, flight time 155-171 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 644 m apogee with a 163 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 14` GragasMAY24)
Short: > Make a rocket that hits 593 m and stays up about 141 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 575-610 m, flight time 134-148 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 593 m apogee with a 141 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 15` GragasMAY24)
Short: > Make a rocket that hits 581 m and stays up about 139 s on a GragasMAY24 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 564-599 m, flight time 132-146 s, max velocity at most 200 m/s, ground-hit velocity at most 6 m/s. Use motors in the class of GragasMAY24. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 581 m apogee with a 139 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

## 2. Rocket type: A simple model rocket — 11 sims × 3 styles
### File: `openrocket__asimple.ork`
(`Simulation 1` A8,B4,C6)
Short: > Make a rocket that hits 48 m and stays up about 16 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 47-49 m, flight time 15-16 s, max velocity at most 50 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 48 m apogee with a 16 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 2` A8,B4,C6)
Short: > Make a rocket that hits 123 m and stays up about 35 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 119-127 m, flight time 33-37 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 123 m apogee with a 35 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 3 - too short delay` A8,B4,C6)
Short: > Make a rocket that hits 251 m and stays up about 66 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 244-259 m, flight time 63-70 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 251 m apogee with a 66 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 4` A8,B4,C6)
Short: > Make a rocket that hits 274 m and stays up about 73 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 266-282 m, flight time 70-77 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 274 m apogee with a 73 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 5` A8,B4,C6)
Short: > Make a rocket that hits 274 m and stays up about 72 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 266-282 m, flight time 68-75 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 274 m apogee with a 72 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

### File: `orhelper__simple.ork`
(`Simulation 1` A8,B4,C6)
Short: > Make a rocket that hits 50 m and stays up about 16 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 49-52 m, flight time 15-17 s, max velocity at most 50 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 50 m apogee with a 16 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 2` A8,B4,C6)
Short: > Make a rocket that hits 134 m and stays up about 38 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 130-138 m, flight time 36-40 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 134 m apogee with a 38 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 3 - too short delay` A8,B4,C6)
Short: > Make a rocket that hits 275 m and stays up about 72 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 267-284 m, flight time 68-76 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 275 m apogee with a 72 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 4` A8,B4,C6)
Short: > Make a rocket that hits 312 m and stays up about 82 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 302-321 m, flight time 78-87 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 312 m apogee with a 82 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 5` A8,B4,C6)
Short: > Make a rocket that hits 314 m and stays up about 83 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 305-324 m, flight time 79-87 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 314 m apogee with a 83 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

### File: `ortools__simple.ork`
(`Simulation 1` A8,B4,C6)
Short: > Make a rocket that hits 51 m and stays up about 16 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 49-52 m, flight time 15-17 s, max velocity at most 50 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 51 m apogee with a 16 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

## 3. Rocket type: Prometeus — 10 sims × 3 styles
### File: `project-prometeus__rocket.ork`
(`Simulation 1` A8,B4,C6)
Short: > Make a rocket that hits 50 m and stays up about 16 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 49-52 m, flight time 15-17 s, max velocity at most 50 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 50 m apogee with a 16 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 2` A8,B4,C6)
Short: > Make a rocket that hits 134 m and stays up about 38 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 130-138 m, flight time 36-40 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 134 m apogee with a 38 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 3 - too short delay` A8,B4,C6)
Short: > Make a rocket that hits 275 m and stays up about 72 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 267-284 m, flight time 68-76 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 275 m apogee with a 72 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 4` A8,B4,C6)
Short: > Make a rocket that hits 312 m and stays up about 82 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 302-321 m, flight time 78-87 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 312 m apogee with a 82 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 5` A8,B4,C6)
Short: > Make a rocket that hits 314 m and stays up about 83 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 305-324 m, flight time 79-87 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 314 m apogee with a 83 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

### File: `project-prometeus__rocket2.ork`
(`Simulation 1` A8,B4,C6)
Short: > Make a rocket that hits 50 m and stays up about 16 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 49-52 m, flight time 15-17 s, max velocity at most 50 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 50 m apogee with a 16 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 2` A8,B4,C6)
Short: > Make a rocket that hits 134 m and stays up about 38 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 130-138 m, flight time 36-40 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 134 m apogee with a 38 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 3 - too short delay` A8,B4,C6)
Short: > Make a rocket that hits 275 m and stays up about 72 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 267-284 m, flight time 68-76 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 275 m apogee with a 72 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 4` A8,B4,C6)
Short: > Make a rocket that hits 312 m and stays up about 82 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 302-321 m, flight time 78-87 s, max velocity at most 100 m/s, ground-hit velocity at most 6 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 312 m apogee with a 82 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 5` A8,B4,C6)
Short: > Make a rocket that hits 314 m and stays up about 83 s on a A8 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 305-324 m, flight time 79-87 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes A/B/C (e.g. A8, B4, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 314 m apogee with a 83 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

## 4. Rocket type: Centuri Arrow 300 — 6 sims × 3 styles
### File: `openrocket-file-utils__CenturiArrow300.ork`
(`Simulation 1` 1/2A6,A8,B6,C6)
Short: > Make a rocket that hits 136 m and stays up about 13 s on a 1/2A6 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 132-140 m, flight time 13-14 s, max velocity at most 100 m/s, ground-hit velocity at most 33 m/s. Use motors in motor classes 1/A/B/C (e.g. 1/2A6, A8, B6, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 136 m apogee with a 13 s flight and lands under 33 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 2` 1/2A6,A8,B6,C6)
Short: > Make a rocket that hits 196 m and stays up about 36 s on a 1/2A6 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 190-201 m, flight time 34-38 s, max velocity at most 100 m/s, ground-hit velocity at most 9 m/s. Use motors in motor classes 1/A/B/C (e.g. 1/2A6, A8, B6, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 196 m apogee with a 36 s flight and lands under 9 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 3` 1/2A6,A8,B6,C6)
Short: > Make a rocket that hits 291 m and stays up about 19 s on a 1/2A6 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 282-299 m, flight time 18-20 s, max velocity at most 100 m/s, ground-hit velocity at most 35 m/s. Use motors in motor classes 1/A/B/C (e.g. 1/2A6, A8, B6, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 291 m apogee with a 19 s flight and lands under 35 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

### File: `openrocket-file-utils__rocket.ork`
(`Simulation 1` 1/2A6,A8,B6,C6)
Short: > Make a rocket that hits 136 m and stays up about 13 s on a 1/2A6 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 132-140 m, flight time 13-14 s, max velocity at most 100 m/s, ground-hit velocity at most 33 m/s. Use motors in motor classes 1/A/B/C (e.g. 1/2A6, A8, B6, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 136 m apogee with a 13 s flight and lands under 33 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 2` 1/2A6,A8,B6,C6)
Short: > Make a rocket that hits 196 m and stays up about 36 s on a 1/2A6 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 190-201 m, flight time 34-38 s, max velocity at most 100 m/s, ground-hit velocity at most 9 m/s. Use motors in motor classes 1/A/B/C (e.g. 1/2A6, A8, B6, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 196 m apogee with a 36 s flight and lands under 9 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 3` 1/2A6,A8,B6,C6)
Short: > Make a rocket that hits 291 m and stays up about 19 s on a 1/2A6 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 282-299 m, flight time 18-20 s, max velocity at most 100 m/s, ground-hit velocity at most 35 m/s. Use motors in motor classes 1/A/B/C (e.g. 1/2A6, A8, B6, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 291 m apogee with a 19 s flight and lands under 35 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

## 5. Rocket type: Rocket — 5 sims × 3 styles
### File: `OpenRocket-Design__Rocket_Model.ork`
(`Low Wind` G54)
Short: > Make a rocket that hits 461 m and stays up about 81 s on a G54 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 447-475 m, flight time 77-85 s, max velocity at most 200 m/s, ground-hit velocity at most 8 m/s. Use motors in the class of G54. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 461 m apogee with a 81 s flight and lands under 8 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Medium Wind` G54)
Short: > Make a rocket that hits 456 m and stays up about 80 s on a G54 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 442-470 m, flight time 76-84 s, max velocity at most 200 m/s, ground-hit velocity at most 8 m/s. Use motors in the class of G54. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 456 m apogee with a 80 s flight and lands under 8 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`High Wind` G54)
Short: > Make a rocket that hits 436 m and stays up about 76 s on a G54 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 423-450 m, flight time 73-80 s, max velocity at most 200 m/s, ground-hit velocity at most 8 m/s. Use motors in the class of G54. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 436 m apogee with a 76 s flight and lands under 8 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

### File: `openrocketdoc__example_simple_1.ork`
(`Simulation 1` F15)
Short: > Make a rocket that hits 474 m and stays up about 24 s on a F15 motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 460-489 m, flight time 23-26 s, max velocity at most 200 m/s, ground-hit velocity at most 45 m/s. Use motors in the class of F15. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 474 m apogee with a 24 s flight and lands under 45 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

### File: `rockets__bt_55.ork`
(`Simulation 1` C11,C6)
Short: > Make a rocket that hits 84 m and stays up about 31 s on a C11 motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 82-87 m, flight time 29-32 s, max velocity at most 100 m/s, ground-hit velocity at most 5 m/s. Use motors in motor classes C (e.g. C11, C6). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 84 m apogee with a 31 s flight and lands under 5 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

## 6. Rocket type: X-Ray — 2 sims × 3 styles
(`Simulation 1` G74W,G80T)
Short: > Make a rocket that hits 492 m and stays up about 117 s on a G74W motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 477-506 m, flight time 111-123 s, max velocity at most 200 m/s, ground-hit velocity at most 4 m/s. Use motors in motor classes G (e.g. G74W, G80T). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 492 m apogee with a 117 s flight and lands under 4 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

(`Simulation 2` G74W,G80T)
Short: > Make a rocket that hits 706 m and stays up about 141 s on a G74W motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 685-728 m, flight time 134-148 s, max velocity at most 200 m/s, ground-hit velocity at most 4 m/s. Use motors in motor classes G (e.g. G74W, G80T). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 706 m apogee with a 141 s flight and lands under 4 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

## 7. Rocket type: Bryant's Test Rocket — 1 sims × 3 styles
(`Simulation 1` C18W,D13W,D21T)
Short: > Make a rocket that hits 225 m and stays up about 23 s on a C18W motor.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 218-231 m, flight time 22-24 s, max velocity at most 100 m/s, ground-hit velocity at most 16 m/s. Use motors in motor classes C/D (e.g. C18W, D13W, D21T). Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 225 m apogee with a 23 s flight and lands under 16 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

## 8. Rocket type: Rocket example with Elliptical Fins — 1 sims × 3 styles
(`Simulation 1` G66-LR)
Short: > Make a rocket that hits 662 m and stays up about 25 s on a G66-LR motor.
Engineering brief: > Design a stable mid-power model rocket (static margin 1.0-2.0 cal) for an apogee of 642-682 m, flight time 24-26 s, max velocity at most 200 m/s, ground-hit velocity at most 63 m/s. Use motors in the class of G66-LR. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 662 m apogee with a 25 s flight and lands under 63 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.

## 9. Rocket type: OpenRocket Comparison of Green Eggs — 1 sims × 3 styles
(user-supplied reference)
Short: > Make a rocket that hits 101 m and stays up about 27 s, weighs around 166 g and is about 57 cm long.
Engineering brief: > Design a stable low-power model rocket (static margin 1.0-2.0 cal) for an apogee of 98-104 m, flight time 26-29 s, max velocity at most 50 m/s, ground-hit velocity at most 6 m/s, liftoff mass at most 174 g, total length 51-63 cm. Use motors in the class of C11. Output the OpenRocket simulation numbers for each requirement.
Optimization: > Find the lightest, simplest rocket that still reaches 101 m apogee with a 27 s flight and lands under 6 m/s. Try 3 different designs (change motor, body diameter, fin shape or recovery type), compare them in a table, and say which one is most stable and why.
