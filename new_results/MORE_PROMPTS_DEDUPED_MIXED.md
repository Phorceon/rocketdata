# More prompts, deduplicated & mixed (v2)

Replaces `rocket_prompts_more (1).md`. Numbers come from each design's highest-apogee saved simulation.

**What changed**

- **Removed 30 verbatim duplicates of `ALL_UNIQUE_LE3_PARAMS.md`**: all 23 "Optimization" prompts (= catalog U-375…U-430, identical "Find the lightest, simplest rocket…" text) and 7 "Short" prompts (= U-439, U-450, U-463, U-469, U-485, U-492, U-494).
- **Removed internal duplicates**: old #24 (repeated design 16, ARC payload) and old #25 (repeated design 21, three-stage; also had a max-velocity figure inconsistent with its own brief).
- **Merged** `orhelper__simple.ork` with its `project-prometeus__rocket(2).ork` twin (the catalog already treats them as the same rocket) into one entry.
- **Rewrote everything that remains** so no prompt reuses a catalog shell (`Make a rocket that hits…`, `Design a rocket that goes to about…`, `Find the lightest, simplest rocket…`) and no two prompts in this file share a sentence template. Each design now gets a different *trio* of framings (spec sheet / field request / review gate / mission card / trade study / coaching / troubleshooting / etc.), and the parameter combinations are rotated — apogee, flight time, max velocity, ground-hit velocity, mass, length and motor class appear in different subsets and orders.
- Kept the one prompt that is unique to this file: the American Rocketry Challenge 2027 egg-loft spec (old #26).

22 designs × 3 prompts + 1 ARC prompt = **67 prompts, no repeats**.

---

## 1. `ortools__simple.ork` — 51 m, 16 s, A8/B4/C6
**Spec sheet** > Spec sheet for a low-power build: apogee 49–52 m; total flight 15–17 s; max velocity no more than 32 m/s; ground-hit at or under 6 m/s; overall length 36–44 cm; motor from the A8, B4 or C6 class. Fill in the design and quote the OpenRocket simulation value against each line.

**Bench-parts request** > With nothing but A8, B4 or C6 motors on the bench, sketch me a rocket about 40 cm long that peaks near 51 m and spends roughly 16 s in the air — then show the simulated numbers.

**Three-build weigh-in** > Weigh three candidate builds against each other: every one has to reach ~51 m, hang aloft ~16 s, and touch down softer than 6 m/s. Vary at least motor, body diameter and fin planform between the three; put the sims side by side and recommend the most stable, with your reasons.

## 2. `rockets__bt_55.ork` — 84 m, 31 s, C11/C6
**Club demo request** > I need a flyer for a club demo that tops out around 84 m and comes down about 31 s later. Keep it near 56 cm overall, never faster than 75 m/s on the way up, and soft — 6 m/s or less — at touchdown. Use a C11 or C6 and give me the simulated figure behind every requirement.

**Design review question** > Design review question before I cut parts: can a C11- or C6-powered rocket hold apogee inside 82–87 m while staying up 29–32 s? Build the design that does and list the OpenRocket outputs for both targets.

**Route comparison** > Compare three routes to ~84 m apogee and ~31 s aloft — swap motor, body tube diameter, fin shape or recovery scheme between them — then rank the three on stability and on landing speed (≤ 6 m/s), justifying the winner with simulated numbers.

## 3. `Pods--powered_with_recovery_deployment.ork` — 91 m, 10 s, A10/A8
**Field rules** > Field rules where I fly: the box tops out near 91 m and we want the rocket down in about 10 s. A10 or A8 motors only, climb speed capped at 48 m/s, nothing faster than 6 m/s when it arrives. Sketch the build and back each number with a simulation result.

**One-liner** > How about a rocket that peaks near 91 m and spends only about 10 s in the air, on an A10 or an A8?

**Quick bake-off** > Run a quick bake-off for me: three A10/A8 rockets that all make ~91 m and get back to earth in ~10 s, none touching down faster than 6 m/s. Change motor choice, diameter, fin shape and recovery across the three, tabulate the sims, then pick the steadiest flyer and say why.

## 4. `numericalrocketry__green_eggs_openrocket_design.ork` — 101 m, 27 s, C11
**Priority requirements** > Requirements, in order of importance: reach 98–104 m apogee; stay up 26–29 s; never exceed 50 m/s; land at 6 m/s or under; total length 51–63 cm; liftoff mass at most 174 g; use a C11. Output the OpenRocket simulation numbers for every item.

**Reverse-engineering** > A teammate's sim landed on 101 m apogee, ~27 s aloft, ~166 g liftoff and ~57 cm of length on a C11. Reconstruct a design that reproduces those results and quote the simulated values back to me.

**Concept trio, pick on static margin** > Three concepts, one winner: each has to sit near 101 m apogee and ~27 s of flight, each under 6 m/s at ground contact. Vary motor, diameter, fins and recovery between them, put the simulation outputs side by side, and choose on static margin — explain the pick.

## 5. `Openrocket-projects__Bryant_Test_Rocket.ork` — 225 m, 23 s, C18W/D13W/D21T
**Two-tier targets** > Two tiers of targets here. Hard limits: apogee 218–231 m; flight 22–24 s; touchdown ≤ 6 m/s. Soft targets: length 47–58 cm, max velocity ≤ 95 m/s, motors drawn from C18W / D13W / D21T. Deliver the design with the simulated number against each line.

**Coaching walkthrough** > I'm new to OpenRocket — talk me through a rocket on a C18W, D13W or D21T motor that reaches about 225 m, drifts down after roughly 23 s, and stays near 53 cm long. Show the sim readouts you're leaning on.

**Shortlist scoring** > Three shortlisted concepts, all hitting ~225 m, ~23 s of flight and a touchdown under 6 m/s — I need them laid out side by side. Create the variants (motor, body diameter, fin shape, recovery), score them in a table, and tell me which flies most stably and why.

## 6. `Pods--airframes_and_winglets.ork` — 244 m, 61 s, A8/B6/C12/C6/D16
**Mission card** > Mission card — apogee: 237–251 m; aloft: 58–64 s; top speed: ≤ 140 m/s; touchdown: ≤ 6 m/s; length: 40–49 cm; mass: ≤ 88 g; motors: any of A8, B6, C12, C6, D16. Build to the card and report the simulated value for each field.

**Ranked goals** > Ranked goals for this build: (1) apogee 237–251 m, (2) 58–64 s of flight, (3) touchdown ≤ 6 m/s, (4) max speed ≤ 140 m/s, (5) length 40–49 cm, (6) liftoff mass ≤ 88 g, motors drawn from A8/B6/C12/C6/D16. Show sim numbers against every goal.

**Pitch three flyers** > Pitch me three flyers that each reach ~244 m apogee, stay up ~61 s, and land under 6 m/s. Vary motor, diameter, fins and recovery across the three, rank them in a comparison table, and defend the most stable one with the simulated data.

## 7. `Deployable_payload.ork` — 263 m, 73 s, A8/B4/C6
**Troubleshooting a bad flight** > My last rocket overshot the box and came down hard. Size this one into the 255–271 m apogee band with 69–76 s of flight, touchdown ≤ 6 m/s, max speed ≤ 85 m/s, within 45–55 cm and 92 g, on an A8, B4 or C6 — and verify every bound with the simulation.

**Motor-first sizing** > Start from the motor: an A8, B4 or C6 should push an 88 g, 50 cm rocket to about 263 m with 73 s aloft. Choose the rest of the build and show me the simulated numbers.

**Three paths** > If I asked you for three different paths to ~263 m apogee and ~73 s of flight, each landing under 6 m/s, what would they look like? Change motor, body diameter, fin planform and recovery between them, tabulate the sims, and crown the most stable.

## 8. `3D_printable_nose_cone_and_fins.ork` — 273 m, 70 s, A8/B6/C6
**Acceptance pass** > Acceptance pass, please: apogee within 264–281 m; flight 66–73 s; max velocity ≤ 91 m/s; ground-hit ≤ 6 m/s; length 30–36 cm; liftoff mass ≤ 85 g; motor an A8, B6 or C6. Run the sim and list the measured value for each acceptance line.

**Printed-parts constraint** > Small and printable: nose cone and fins come off my 3D printer. Give me a design under 36 cm and 85 g that still reaches ~273 m and stays up ~70 s on an A8, B6 or C6, with the sim numbers to back it.

**Torn between three builds** > I'm torn between three builds that each reach ~273 m, fly ~70 s, and come in under 6 m/s — make the three variants by changing motor, diameter, fins and recovery, put their simulation results in one table, and pick the one with the best static margin.

## 9. `openrocket__asimple.ork` — 274 m, 72 s, A8/B4/C6
**Boxed-in site** > Because our launch site is boxed in, apogee must stay under 282 m — aim for 266–282 m — with 68–75 s aloft, max speed ≤ 95 m/s, touchdown ≤ 6 m/s, length 36–44 cm, mass ≤ 75 g, on an A8, B4 or C6. Cite the simulation result behind each bound.

**Simple ask** > Simple ask: about 274 m of altitude, about 72 s of flight, and a soft single-digit landing — under 6 m/s — on an A8, B4 or C6. What design gets me there?

**Trade-space exercise** > Treat it as an exercise in trade space: three builds that all land in the 266–282 m band with ~72 s aloft, all under 6 m/s at touchdown. Swap motor, body diameter, fin shape and recovery between them, tabulate the sims, and rank them by static margin.

## 10. `Tube_fin_rocket.ork` — 282 m, 76 s, D12
**Checklist sign-off** > Checklist sign-off for a tube-fin build: apogee 274–291 m; flight 72–79 s; max velocity ≤ 131 m/s; ground-hit ≤ 6 m/s; length 52–63 cm; mass ≤ 80 g; motor D12. Run the simulation and record the measured value against each line.

**The tube-fin catch** > The catch: fins are tubes, not flat plates, and the motor is a D12. Size the rest so it hits ~282 m, stays up ~76 s, stays under 80 g and 63 cm, and report the sim numbers.

**Three takes, fins fixed** > Three takes on the same target — ~282 m apogee, ~76 s of flight, touchdown under 6 m/s — with tube fins as the fixed constraint. Vary motor, diameter and recovery between the three, lay the sims out in a table, and choose the steadiest, with reasoning.

## 11. `openrocket-file-utils__CenturiArrow300.ork` — 291 m, 19 s, 1/2A6/A8/B6/C6
**Pre-launch sizing request** > Pre-launch request: an 84–102 cm airframe on a 1/2A6, A8, B6 or C6 that reaches 282–299 m, is back down in 18–20 s, never exceeds 101 m/s, and touches down at ≤ 6 m/s. Send the simulated number for every requirement.

**Vintage airframe** > This vintage Arrow 300 airframe is nearly a meter long but flies small motors. On a 1/2A6, A8, B6 or C6 it should reach ~291 m and be down in ~19 s — build to that and show the sims.

**Three designs, one meter-long class** > Head-to-head, three designs: each has to make ~291 m apogee, ~19 s of flight and a touchdown under 6 m/s, in an airframe between 84 and 102 cm. Change motor, diameter, fin planform and recovery across the three, tabulate results, and pick the most stable with justification.

## 12. `Clustered_motors.ork` — 307 m, 59 s, A8/B4/C6
**Negotiated spec** > Negotiated spec for a clustered-motor bird: hard limits — apogee 298–316 m, flight 56–62 s, touchdown ≤ 6 m/s. Soft targets — length 63–77 cm, liftoff mass ≤ 275 g, max velocity ≤ 108 m/s, A8/B4/C6 motors (clustered). Deliver the design with the sim value per line.

**Clustering changes the math** > Clustering changes the math: two or more A8/B4/C6 motors firing together, a 262 g, 70 cm rig, ~307 m apogee, ~59 s of flight. Work out the design and show me the simulated numbers.

**Choose among three clusters** > I'm choosing between three clustered builds that each hit ~307 m and ~59 s aloft and land under 6 m/s. Vary the cluster composition, body diameter, fin shape and recovery between them, score them in a comparison table, and tell me which is the most stable and why.

## 13. `orhelper__simple.ork` (same rocket: `project-prometeus__rocket.ork`, `project-prometeus__rocket2.ork`) — 314 m, 83 s, A8/B4/C6
**Review gate** > Review gate: apogee must land inside 305–324 m and flight inside 79–87 s, with ground-hit ≤ 6 m/s, max velocity ≤ 104 m/s, length 36–44 cm (a stretched ~60 cm Prometeus variant is acceptable), mass ≤ 75 g, motors A8/B4/C6. Back each gate with a simulated figure.

**Classic simple rocket** > A classic simple rocket — around 71 g, ~40 cm, A8/B4/C6 motors — should be good for ~314 m and about 83 s in the air. Build it and quote the sim.

**Rank on margins** > Rank three candidate builds that all reach ~314 m, stay up ~83 s, and touch down under 6 m/s: change motor, body diameter, fin planform and recovery between them, put the sims in one table, and pick the most stable, explaining the margins.

## 14. `A_simple_model_rocket.ork` — 320 m, 84 s, A8/B4/C6
**Design exercise** > Treat this as a design exercise: with an apogee band of 310–329 m, a flight window of 80–89 s, a 105 m/s speed ceiling, a 6 m/s touchdown ceiling, 36–44 cm of length, 75 g of mass and A8/B4/C6 motors, produce a rocket and cite every simulation figure.

**Boilerplate version** > Boilerplate version: a ~40 cm, ~71 g rocket on A8, B4 or C6 motors that peaks near 320 m and is airborne about 84 s — show the design and the sim readouts.

**A triple of concepts** > A triple of concepts for me, all near 320 m apogee and ~84 s of flight, all under 6 m/s at touchdown: vary motor, diameter, fins and recovery between them, tabulate the simulations, and choose on static margin — with your reasoning.

## 15. `ARC_payload_rocket.ork` — 451 m, 110 s, F50T
**Requirements-vs-simulation table** > Deliverable: a payload-capable rocket plus a requirements-vs-simulation table — apogee 438–465 m, flight 104–115 s, max velocity ≤ 165 m/s, ground-hit ≤ 6 m/s, length 96–117 cm, liftoff mass ≤ 375 g, F50T motor.

**Heavyweight ask** > Heavyweight ask: an F50T-powered, 357 g, ~107 cm rocket that goes to ~451 m and takes ~110 s to finish the flight. Size it and show the sim numbers.

**Three designs, one pick** > Three designs, one pick: each reaching ~451 m, ~110 s of flight, touchdown under 6 m/s, mass within 375 g. Swap motor, body diameter, fin shape and recovery across the three, lay the results side by side, and recommend the most stable with justification.

## 16. `OpenRocket-Design__Rocket_Model.ork` — 461 m, 81 s, G54
**Prioritized constraints** > Constraint set with priorities: apogee 447–475 m and flight 77–85 s are non-negotiable, as is touchdown ≤ 6 m/s; length 72–88 cm, mass ≤ 657 g and max speed ≤ 121 m/s are secondary; the motor is a G54. Return the design with the simulated number for each constraint.

**On a G54** > On a G54 motor, a 626 g, 80 cm rocket should sit near 461 m apogee with ~81 s of flight — put that design together and quote the sim outputs.

**Weigh three G54 options** > Weigh three G54-class options against each other: all near ~461 m, ~81 s aloft, under 6 m/s at touchdown. Vary body diameter, fin planform, recovery and mass distribution between them, tabulate the sims, and pick the steadiest — with reasons.

## 17. `openrocketdoc__example_simple_1.ork` — 474 m, 24 s, F15
**Field constraints, restated** > Field constraints, restated: the box allows 460–489 m of apogee and we want only 23–26 s of flight. Speed stays ≤ 113 m/s on the way up and touchdown ≤ 6 m/s; airframe 41–50 cm; motor F15. Sketch the rocket and back every number with a simulation.

**Short and fast profile** > Short and fast profile: ~474 m apogee, only ~24 s from liftoff to ground, an F15 motor, ~45 cm long. Design it and show the simulated values.

**Same brief, three answers** > If I wanted three different answers to the same brief — ~474 m, ~24 s, under 6 m/s at touchdown, F15 available — what are they? Vary motor choice, diameter, fins and recovery, put the sims in a table, and name the most stable.

## 18. `Chute_release.ork` — 488 m, 65 s, G40W/G80T
**Big-bird priority list** > Big-bird priority list: (1) apogee 473–503 m, (2) 62–68 s of flight, (3) touchdown ≤ 6 m/s, (4) max speed ≤ 117 m/s, (5) length 93–114 cm, (6) mass ≤ 1091 g, motors from G40W/G80T with a chute-release style recovery. Show the sim numbers against every item.

**Chute-release rig** > Chute-release recovery on a heavy G-class rig: ~1039 g, ~104 cm, ~488 m apogee, ~65 s of flight. Work out the design and give me the simulated figures.

**Three heavy concepts side by side** > Three heavy concepts side by side, each hitting ~488 m and ~65 s of flight and landing under 6 m/s: vary motor (G40W vs G80T), diameter, fin shape and recovery details between them, rank them in a table, and justify the most stable pick.

## 19. `czech-rocket-challenge-2025__Raketa.ork` — 644 m, 25 s, GragasMAY24
**Straight spec list** > Challenge bird spec, straight list: apogee 625–664 m; flight 23–26 s; max velocity ≤ 159 m/s; ground-hit ≤ 6 m/s; length 61–74 cm; GragasMAY24 motor. Simulate it and report a measured number for each line.

**Single motor type** > Challenge rocket, single motor type: a GragasMAY24 taking a ~67 cm airframe to ~644 m and back down in ~25 s. Show me the design and the sim readouts.

**Three design studies** > Three design studies for the GragasMAY24 problem: each reaches ~644 m, flies ~25 s, lands under 6 m/s. Vary body diameter, fin planform, mass and recovery between them, tabulate the sims, and select the most stable with your reasoning.

## 20. `Three_stage_low_power_rocket.ork` — 645 m, 166 s, A8/B6/C6
**Three-stage mission card** > Mission card for a three-stage low-power stack — apogee: 626–664 m; aloft: 158–174 s; top speed: ≤ 143 m/s; touchdown: ≤ 6 m/s; length: 50–62 cm; mass: ≤ 156 g; motors: A8, B6, C6 across the stages. Build to the card and report every simulated value.

**Staging is the trick** > Staging is the whole trick here: three light motors (A8/B6/C6), 149 g total, 56 cm stacked, ~645 m apogee, and a lazy ~166 s flight. Lay out the stage design and show the sims.

**Compare staging approaches** > Compare three staging approaches that all reach ~645 m and ~166 s of flight with touchdown under 6 m/s: change stage motors, interstage diameter, fin shape and recovery scheme between them, put the simulation outputs in one table, and pick the most stable, with justification.

## 21. `RocketSerializer__rocket.ork` — 662 m, 25 s, G66-LR
**Split-priority spec** > Split-priority spec: the non-negotiables are apogee 642–682 m, flight 24–26 s and touchdown ≤ 6 m/s; the softer numbers are 66–81 cm length, ≤ 534 g mass and ≤ 200 m/s max speed, all on a G66-LR. Deliver the design with a simulated value per line.

**Elliptical fins** > Elliptical fins, G66-LR motor, ~509 g and ~74 cm: it should reach ~662 m and finish the flight in ~25 s. Build it and quote the sim outputs.

**Three-way bake-off** > Three-way bake-off on the elliptical-fin bird: each concept makes ~662 m apogee, ~25 s of flight and a touchdown under 6 m/s. Vary motor, body diameter, fin planform and recovery between the three, rank them in a comparison table, and defend the most stable one with data.

## 22. `openrocket-web__test-rocket.ork` — 706 m, 141 s, G74W/G80T
**Pre-window request** > Quick ask before the launch window: a G74W- or G80T-powered rocket of 102–125 cm and at most 596 g that reaches 685–728 m, stays up 134–148 s, never exceeds 202 m/s, and arrives at ≤ 6 m/s. Send the simulated figure for every requirement.

**Big-and-slow profile** > Big-and-slow profile: a ~113 cm, ~568 g rig on a G74W or G80T that goes to ~706 m and takes ~141 s to finish. Put the design together and show the sim numbers.

**Score three candidates** > Score three candidates for the big bird: each ~706 m apogee, ~141 s of flight, touchdown under 6 m/s. Swap motor (G74W or G80T), diameter, fins and recovery between them, put the sims in a table, and crown the most stable with your reasoning.

## 23. American Rocketry Challenge 2027 egg-loft (unique spec, no source .ork)

**ARC 2027 rules** > Design an OpenRocket model rocket that complies with the 2027 American Rocketry Challenge rules. It must completely enclose two raw Grade A Large eggs (55–63 g each, 45 mm diameter or less) in any orientation. Target an apogee of exactly 800 ft (243.8 m) and a total flight time of 37–40 s, measured from first motion at liftoff until the first part touches the ground. Liftoff mass must be 650 g or less including both eggs and the motor(s). Total length must be 650 mm or more. Use only NAR-certified motors from the ARC 2027 approved engine list, with total impulse of 80 N·s or less. The intended motor range is low-end F (45–55 N·s). Use at least two body tubes whose diameters differ by 10 mm or more, with one section at least 12 in of T80 tube. All parts must stay tethered together and descend under a single parachute. The design must be stable (at least 1 caliber static margin at launch) with a low ground-hit velocity (about 5 m/s or less). Report apogee, max velocity, time to apogee, flight time, ground-hit velocity, liftoff mass and total length from the simulation.
