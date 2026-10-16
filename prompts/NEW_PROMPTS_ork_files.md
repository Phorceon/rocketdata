# New Prompts for .ork Files (2-3 params each, mixed detail levels)

33 new prompts for 10 .ork files. Each prompt lists the .ork file and the simulation it was written from, so it can be checked. Detail levels are mixed on purpose: **Detailed** (3 params), **Semi-detailed** (2 params), **Vague** (1-2 params, mostly no exact numbers) so the model learns the idea instead of memorizing one template.

**Where the numbers came from:** the results saved inside each .ork file (apogee, flight time, ground-hit speed). Some files were saved with old results. Those are flagged "OUTDATED" or "NOT SIMULATED" below. Open the file in OpenRocket, run that sim, and fix the numbers in the prompt if they changed.

**Not used on purpose:** landing speeds above 6 m/s (Mark 2, Wizard, Sterling Silver, Alpha III sim 3 all land hard), since the project reward ladder treats touchdown over 6.0 m/s as unsafe. Those prompts only ask for apogee, motor, and flight time.

---

## Comet Chaser (`Comet_Chaser.ork`)

- **[NEW-001]** (Detailed; params: apogee, motor, flight time)
  > Design a rocket on a B6 motor that reaches about 170 m and stays up just over a minute.
  - File: `Comet_Chaser.ork` | Sim: `Simulation 5` | Status: saved results are current
  - Saved sim values: motor B6; apogee 171.4 m; flight time 66.4 s; ground hit 3.0 m/s; max velocity 88.3 m/s

- **[NEW-002]** (Semi-detailed; params: flight time, ground hit)
  > I want a small rocket that comes down gently, around 3 m/s, after a long floaty flight of over a minute.
  - File: `Comet_Chaser.ork` | Sim: `Simulation 5` | Status: saved results are current
  - Saved sim values: motor B6; apogee 171.4 m; flight time 66.4 s; ground hit 3.0 m/s; max velocity 88.3 m/s

- **[NEW-003]** (Vague; params: apogee)
  > Make a rocket that goes up a few hundred feet and drifts back down slowly.
  - File: `Comet_Chaser.ork` | Sim: `Simulation 5` | Status: saved results are current
  - Saved sim values: motor B6; apogee 171.4 m; flight time 66.4 s; ground hit 3.0 m/s; max velocity 88.3 m/s

## Estes Alpha III (`ESTES_Alpha_3.ork`)

- **[NEW-004]** (Detailed; params: motor, apogee, flight time)
  > Build a rocket on an A6 motor that reaches about 105 m and hangs in the air for about 30 seconds.
  - File: `ESTES_Alpha_3.ork` | Sim: `Simulation 1` | Status: marked NOT SIMULATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor A6; apogee 105.3 m; flight time 30.5 s; ground hit 4.5 m/s; max velocity 50.6 m/s

- **[NEW-005]** (Semi-detailed; params: apogee, ground hit)
  > Give me something that climbs to around 240 m and lands softly, under 4 m/s.
  - File: `ESTES_Alpha_3.ork` | Sim: `Simulation 2` | Status: marked NOT SIMULATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor B4; apogee 237.7 m; flight time 63.7 s; ground hit 3.9 m/s; max velocity 85.8 m/s

- **[NEW-006]** (Vague; params: flight time)
  > Design a small rocket that stays up for a bit more than a minute.
  - File: `ESTES_Alpha_3.ork` | Sim: `Simulation 2` | Status: marked NOT SIMULATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor B4; apogee 237.7 m; flight time 63.7 s; ground hit 3.9 m/s; max velocity 85.8 m/s

- **[NEW-007]** (Semi-detailed; params: motor, apogee)
  > I need a rocket on a C6 motor that gets up close to 450 m.
  - File: `ESTES_Alpha_3.ork` | Sim: `Simulation 3` | Status: marked NOT SIMULATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor C6; apogee 451.1 m; flight time 20.5 s; ground hit 52.1 m/s; max velocity 145.0 m/s

## Estes Impulse (`Estes_Impulse.ork`)

- **[NEW-008]** (Detailed; params: motor, apogee, flight time)
  > Make a rocket on a D12 motor that reaches about 150 m and flies for roughly 34 seconds.
  - File: `Estes_Impulse.ork` | Sim: `Simulation 1` | Status: saved results are OUTDATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor D12; apogee 153.2 m; flight time 33.9 s; ground hit 5.5 m/s; max velocity 52.0 m/s

- **[NEW-009]** (Semi-detailed; params: flight time, ground hit)
  > Design a rocket with a half-minute flight that touches down at around 5.5 m/s.
  - File: `Estes_Impulse.ork` | Sim: `Simulation 1` | Status: saved results are OUTDATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor D12; apogee 153.2 m; flight time 33.9 s; ground hit 5.5 m/s; max velocity 52.0 m/s

- **[NEW-010]** (Semi-detailed; params: motor, apogee)
  > Build me a rocket for an E26W motor that tops out near 295 m.
  - File: `Estes_Impulse.ork` | Sim: `Simulation 3` | Status: saved results are OUTDATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor E26W; apogee 295.0 m; flight time 60.1 s; ground hit 5.6 m/s; max velocity 96.7 m/s

- **[NEW-011]** (Detailed; params: motor, apogee, flight time)
  > Design a rocket on an E20W motor that gets up around 345 m and stays in the air about 64 seconds.
  - File: `Estes_Impulse.ork` | Sim: `Simulation 4` | Status: saved results are current
  - Saved sim values: motor E20W; apogee 344.1 m; flight time 64.5 s; ground hit 6.1 m/s; max velocity 95.5 m/s

## Estes Mark 2 (`Estes_Mark2.ork`)

- **[NEW-012]** (Detailed; params: motor, apogee, flight time)
  > Build a streamer-recovery rocket on an A8 motor that reaches about 180 m in under 20 seconds.
  - File: `Estes_Mark2.ork` | Sim: `Simulation 1` | Status: saved results are current
  - Saved sim values: motor A8; apogee 179.6 m; flight time 17.3 s; ground hit 17.5 m/s; max velocity 83.1 m/s

- **[NEW-013]** (Semi-detailed; params: apogee, flight time)
  > I want a quick flight, about 25 seconds total, that goes up around 285 m.
  - File: `Estes_Mark2.ork` | Sim: `Simulation 2` | Status: saved results are current
  - Saved sim values: motor B6; apogee 285.2 m; flight time 24.5 s; ground hit 17.1 m/s; max velocity 137.7 m/s

- **[NEW-014]** (Detailed; params: motor, apogee, flight time)
  > Make a rocket on a C6 motor that goes close to 470 m and is back down in about 36 seconds.
  - File: `Estes_Mark2.ork` | Sim: `Simulation 3` | Status: saved results are current
  - Saved sim values: motor C6; apogee 468.7 m; flight time 36.3 s; ground hit 16.9 m/s; max velocity 173.9 m/s

- **[NEW-015]** (Vague; params: flight time)
  > Make a rocket that shoots up fast and is back on the ground in under 20 seconds.
  - File: `Estes_Mark2.ork` | Sim: `Simulation 1` | Status: saved results are current
  - Saved sim values: motor A8; apogee 179.6 m; flight time 17.3 s; ground hit 17.5 m/s; max velocity 83.1 m/s

## Estes Wizard (`Estes_Wizard.ork`)

- **[NEW-016]** (Detailed; params: motor, apogee, flight time)
  > Make a rocket on an A8 motor that reaches about 175 m and is back down in about 14 seconds.
  - File: `Estes_Wizard.ork` | Sim: `Simulation 2` | Status: marked NOT SIMULATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor A8; apogee 176.6 m; flight time 14.1 s; ground hit 25.6 m/s; max velocity 77.9 m/s

- **[NEW-017]** (Vague; params: flight time)
  > Design a short, snappy flight that is over in under 15 seconds.
  - File: `Estes_Wizard.ork` | Sim: `Simulation 2` | Status: marked NOT SIMULATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor A8; apogee 176.6 m; flight time 14.1 s; ground hit 25.6 m/s; max velocity 77.9 m/s

## Estes Flip Flyer (`FlipFlyer.ork`)

- **[NEW-018]** (Semi-detailed; params: motor, apogee)
  > Design a rocket on a B6 motor that only goes up about 60 m.
  - File: `FlipFlyer.ork` | Sim: `Simulation 1` | Status: saved results are current
  - Saved sim values: motor B6; apogee 59.1 m; flight time 8.7 s; ground hit 19.8 m/s; max velocity 31.3 m/s

- **[NEW-019]** (Detailed; params: motor, apogee, flight time)
  > Make a rocket that reaches about 175 m on a C6 motor and is down in about 24 seconds.
  - File: `FlipFlyer.ork` | Sim: `Simulation 3` | Status: saved results are current
  - Saved sim values: motor C6; apogee 175.6 m; flight time 23.9 s; ground hit 14.5 m/s; max velocity 56.6 m/s

- **[NEW-020]** (Vague; params: flight time)
  > Build a small, low flight that is over in under 10 seconds.
  - File: `FlipFlyer.ork` | Sim: `Simulation 1` | Status: saved results are current
  - Saved sim values: motor B6; apogee 59.1 m; flight time 8.7 s; ground hit 19.8 m/s; max velocity 31.3 m/s

## Estes Super Shot 5320 (`OpenRocket_Estes_Super_Shot_Design.ork`)

- **[NEW-021]** (Detailed; params: motor, apogee, flight time)
  > Design a rocket on a C6 motor that reaches around 245 m and floats down for about a minute and a half.
  - File: `OpenRocket_Estes_Super_Shot_Design.ork` | Sim: `Fight Path Recovery` | Status: saved results are current
  - Saved sim values: motor C6; apogee 247.1 m; flight time 91.8 s; ground hit 2.9 m/s; max velocity 81.1 m/s

- **[NEW-022]** (Semi-detailed; params: apogee, ground hit)
  > I need a really soft landing, about 3 m/s, from a couple hundred meters up.
  - File: `OpenRocket_Estes_Super_Shot_Design.ork` | Sim: `Fight Path Recovery` | Status: saved results are current
  - Saved sim values: motor C6; apogee 247.1 m; flight time 91.8 s; ground hit 2.9 m/s; max velocity 81.1 m/s

- **[NEW-023]** (Vague; params: flight time)
  > Make a rocket with a really long, slow descent.
  - File: `OpenRocket_Estes_Super_Shot_Design.ork` | Sim: `Fight Path Recovery` | Status: saved results are current
  - Saved sim values: motor C6; apogee 247.1 m; flight time 91.8 s; ground hit 2.9 m/s; max velocity 81.1 m/s

## Estes Renegade (`Renegade.ork`)

- **[NEW-024]** (Detailed; params: motor, apogee, flight time)
  > Design a rocket on an E9 motor that reaches about 375 m and stays up close to 100 seconds.
  - File: `Renegade.ork` | Sim: `Simulation 1` | Status: saved results are current
  - Saved sim values: motor E9; apogee 377.1 m; flight time 99.6 s; ground hit 3.9 m/s; max velocity 97.4 m/s

- **[NEW-025]** (Semi-detailed; params: apogee, ground hit)
  > I want a rocket that climbs a few hundred meters and comes down gently, under 4 m/s.
  - File: `Renegade.ork` | Sim: `Simulation 1` | Status: saved results are current
  - Saved sim values: motor E9; apogee 377.1 m; flight time 99.6 s; ground hit 3.9 m/s; max velocity 97.4 m/s

- **[NEW-026]** (Vague; params: flight time)
  > Make a big, slow-floating rocket that stays up well over a minute.
  - File: `Renegade.ork` | Sim: `Simulation 1` | Status: saved results are current
  - Saved sim values: motor E9; apogee 377.1 m; flight time 99.6 s; ground hit 3.9 m/s; max velocity 97.4 m/s

## Astron Drifter (`astron_drifter.ork`)

- **[NEW-027]** (Detailed; params: motor, apogee, flight time)
  > Build a rocket on an A8 motor that reaches about 115 m and floats for close to a minute.
  - File: `astron_drifter.ork` | Sim: `Simulation 1` | Status: saved results are OUTDATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor A8; apogee 115.0 m; flight time 52.1 s; ground hit 2.2 m/s; max velocity 56.2 m/s

- **[NEW-028]** (Semi-detailed; params: apogee, flight time)
  > Design a rocket that goes up about 230 m and stays in the air about 105 seconds.
  - File: `astron_drifter.ork` | Sim: `Simulation 2` | Status: saved results are OUTDATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor B6; apogee 231.6 m; flight time 105.9 s; ground hit 2.6 m/s; max velocity 105.1 m/s

- **[NEW-029]** (Semi-detailed; params: motor, ground hit)
  > Design a rocket on a B6 motor that touches down under 3 m/s.
  - File: `astron_drifter.ork` | Sim: `Simulation 2` | Status: saved results are OUTDATED - re-run in OpenRocket and update numbers
  - Saved sim values: motor B6; apogee 231.6 m; flight time 105.9 s; ground hit 2.6 m/s; max velocity 105.1 m/s

## Estes Sterling Silver (`estes-007275_STERLING_SILVER.ork`)

- **[NEW-030]** (Detailed; params: motor, apogee, flight time)
  > Make a rocket on an A8 motor that reaches about 190 m in around 15 seconds.
  - File: `estes-007275_STERLING_SILVER.ork` | Sim: `Simulation 1` | Status: saved results are current
  - Saved sim values: motor A8; apogee 192.6 m; flight time 15.5 s; ground hit 28.9 m/s; max velocity 70.5 m/s

- **[NEW-031]** (Semi-detailed; params: apogee, flight time)
  > Design a rocket that goes about 360 m and is back down in under 25 seconds.
  - File: `estes-007275_STERLING_SILVER.ork` | Sim: `Simulation 2` | Status: saved results are current
  - Saved sim values: motor B6; apogee 361.0 m; flight time 22.8 s; ground hit 28.9 m/s; max velocity 122.2 m/s

- **[NEW-032]** (Detailed; params: motor, apogee, flight time)
  > I want a rocket on a C6 motor that goes about 640 m and is down in around 35 seconds.
  - File: `estes-007275_STERLING_SILVER.ork` | Sim: `Simulation 3` | Status: saved results are current
  - Saved sim values: motor C6; apogee 642.5 m; flight time 34.8 s; ground hit 28.8 m/s; max velocity 156.6 m/s

- **[NEW-033]** (Vague; params: apogee)
  > Build a rocket that goes really high for a low-power motor.
  - File: `estes-007275_STERLING_SILVER.ork` | Sim: `Simulation 3` | Status: saved results are current
  - Saved sim values: motor C6; apogee 642.5 m; flight time 34.8 s; ground hit 28.8 m/s; max velocity 156.6 m/s

---
