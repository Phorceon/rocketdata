SOURCES USED - Shamik
1. https://openrocket.info/ - OpenRocket app, simulator description
2. https://github.com/openrocket/openrocket - 16x `.ork` examples from `core/src/main/resources/datafiles/examples/`, GPL
3. https://www.rocketrychallenge.org/ - ARC 2026 targets (750 ft / 36-39s), winners, 1107 teams
4. https://www.rocketrychallenge.org/resources/ - ARC resource index
5. https://www.rocketrychallenge.org/resource/arc-2027-parameters/ + https://www.rocketrychallenge.org/wp-content/uploads/ARC2027_Parameters.pdf - 2027 params
6. https://www.rocketrychallenge.org/resource/2027-american-rocketry-challenge-rules/ + https://www.rocketrychallenge.org/wp-content/uploads/2027-American-Rocketry-Challenge-Rules-.pdf - 800 ft / 37-40s / 2x eggs
7. https://www.rocketrychallenge.org/resource/approved-motors-list/ + https://www.rocketrychallenge.org/wp-content/uploads/Rocket-Motors-Approved-for-ARC-2027-6-Jul-2026.pdf - NAR approved motors
8. https://www.rocketrychallenge.org/result/2026/ - 2026 finals scores
9. https://www.thrustcurve.org/ + https://www.thrustcurve.org/info/simulation.html + https://www.thrustcurve.org/info/api.html - 11x motor files via `/api/v1/search.json` + `/api/v1/download.json`
10. https://www.apogeerockets.com/ - kit / ARC Supplies / altimeter category reference
11. https://estesrockets.com/ - kit reference
12. https://jollylogic.com/products/altimeterone/ - AltimeterOne specs
13. https://jollylogic.com/products/altimetertwo/ + https://jollylogic.com/wp-content/uploads/2019/08/AltimeterTwo-Flight-Log.xlsx + https://jollylogic.com/wp-content/uploads/2022/09/JollyLogicAltimeterTwo-Gen64G-SmallWeb.pdf - 10 flight stats, log template
14. https://github.com/davesrocketshop/Rocket - FreeCAD workbench that imports `.ork`
15. https://science.nasa.gov/3d-resources/ + https://github.com/nasa/NASA-3D-Resources - NASA SLS Block 1 + Saturn V STLs (public domain, excluded Saturn V parts from final zip)
16. https://github.com/olexam/printable_rocket - GPLv3 printable flyable system (audited, excluded parts from final STL-only zip)
17. https://github.com/Freefootsoldier/SEEC-2025-3D-Printable-Rocket - CC BY-NC 4.0 capsule rocket (audited, excluded parts from final zip)
18. Estes body tube sizes BT-20/50/55/60/70/80/101 + NAR 18/24/29/38mm mounts - dimension source for 51 parametric full assemblies (generated CC0, mm)
19. https://github.com/RocketshipGames/rockettools - OpenSCAD method reference for parametric generation
20. https://github.com/MrRocketman/RocketTo3D - RockSim-to-STL method reference
21. https://www.thrustcurve.org/info/api.html (`/api/v1/motorguide.json`) - 463 sim projections, inputs Cd 0.45 / 1m guide / estimated dry mass
22. https://www.thrustcurve.org/info/simulation.html - sim background (apogee-focused, stops at apogee)
23. ThrustCurve motor files via `/api/v1/download.json` (C6, D12, E12, E16, F15, E20, E26, E30, F32, F39) - NAR/static-test curves via John Coker
24. Researched, not redistributed (no open license): https://github.com/scottbybee/rockets, https://github.com/Kyrylo-Bakumenko/TARC, https://github.com/Nasadude211/3D-printed-model-rocket-18mm-estes-engine-, https://github.com/JamesLewisENGR/3D-Printed-Model-Rocket




Prompts-Shamik


Make a rocket with 451 m apogee, ground hit velocity ~4.6 m/s (low), liftoff mass ~357 g, length ~107 cm, flight time ~110 s, max velocity ~150 m/s, time to apogee ~8.2 s, F50T motor(s).

Make a rocket with 645 m apogee, ground hit velocity ~4.7 m/s (low), liftoff mass ~149 g, length ~56 cm, flight time ~166 s, max velocity ~130 m/s, time to apogee ~11.9 s, A8, B6, C6 motor(s).

Design an OpenRocket model rocket that complies with the 2027 American Rocketry Challenge rules. It must completely enclose two raw Grade A Large eggs (55-63 g each, 45 mm diameter or less) in any orientation. Target an apogee of exactly 800 ft (243.8 m) and a total flight time of 37-40 s, measured from first motion at liftoff until the first part touches the ground. Liftoff mass must be 650 g or less including both eggs and the motor(s). Total length must be 650 mm or more. Use only NAR-certified motors from the ARC 2027 approved engine list, with total impulse of 80 N·s or less. The intended motor range is low-end F (45-55 N·s). Use at least two body tubes whose diameters differ by 10 mm or more, with one section at least 12 in of T80 tube. All parts must stay tethered together and descend under a single parachute. The design must be stable (at least 1 caliber static margin at launch) with a low ground-hit velocity (about 5 m/s or less). Report apogee, max velocity, time to apogee, flight time, ground-hit velocity, liftoff mass and total length from the simulation.
