SIM DATA for the STL rockets in this zip (Shamik- Rocket Research Files)
========================================================================
51 of 52 STLs have projected sim data here. The 52nd file,
NASA_SLS_Block1_complete.stl, is a NASA scale display model (arbitrary
model units, not a flyable airframe) so no motor sim applies to it.

1) sim_projections_all.csv - 463 rows. ThrustCurve MotorGuide simulator
   projections (https://www.thrustcurve.org/info/api.html, /api/v1/motorguide.json),
   run Oct 2026, one call per design per impulse class:
   - 18mm mounts: C + D classes, SU, available motors, top 5 each
   - 24mm mounts: E + F classes, SU, available, top 5 each
   - 29mm mounts: F + G classes, SU, available, top 5 each
   - 38mm mount (35_HPR_BT101): H class, all types, available (SU H motors
     effectively don't exist; returned Loki H90/H160 reloads)
   Columns per motor: thrust/weight, liftoff/burnout/apogee times,
   max altitude (m + ft), max velocity, burnout altitude, optimal delay,
   guide velocity, status. Altitudes assume dry mass in
   design_inputs_mass_dia.csv, Cd 0.45, 1m launch guide, no wind, no
   payload/egg mass. Add your payload mass and re-run before flying.
2) design_inputs_mass_dia.csv - inputs used: body dia/length, nose, fins,
   motor mount, estimated cardboard+balsa dry mass (kg). ESTIMATES ONLY.
   PLA-printed builds will be heavier and fly lower. Weigh your build.
3) motorguide_primary_raw.json / motorguide_secondary_raw.json - full API
   responses for transparency/reproducibility.
4) motors/ - 11 thrust-curve files (.eng RASP + .rse RockSim) for the most
   common recommended motors (C6, D12, E12, E16, F15, E20, E26, E30, F32,
   F39). Drop into OpenRocket/RockSim. Source: thrustcurve.org download API.

Method limits: MotorGuide is a simplified simulator (apogee-focused, stops
at apogee, no recovery/descent, no wind). For ARC scoring (altitude AND
42-44s-class durations) always verify in OpenRocket with your exact mass,
finish, chute size, and wind, then confirm with an altimeter (e.g. Jolly
Logic AltimeterTwo: max altitude, duration, ejection timing).
