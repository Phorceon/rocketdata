# The simulator helper protocol

`RocketSim.java` is a small Java program that drives OpenRocket 24.12. Python
(`sim.py`) starts it once and keeps it running. They talk in lines of JSON:
Python writes one request per line to the helper's standard input, and the
helper writes exactly one reply line per request to its standard output.
Nothing else is ever written to standard output. Log and error text goes to
standard error, which Python saves to a log file.

All field names below are fixed. The helper may add fields, never rename or
remove them. Units are in the names: `_m` metres, `_s` seconds, `_ms` metres
per second, `_ms2` metres per second squared, `_kg` kilograms, `_cal` calibres
(body diameters), `_deg` degrees, `_ns` newton-seconds.

Numbers that do not exist (for example the landing speed of a section that
never reached the ground) are `null`, never NaN or infinity.

## ping

```json
{"op": "ping", "id": "p1"}
```
```json
{"id": "p1", "ok": true, "openrocket": "24.12", "java": "17.0.21", "helper": 1}
```

## run

Load one design file, report where OpenRocket placed every part, then fly it
once per entry in `flights`.

```json
{"op": "run", "id": "r1",
 "ork": "/path/to/design.ork",
 "rail_m": 1.5,
 "flights": [{"wind_ms": 1.0, "seed": 1}, {"wind_ms": 2.0, "seed": 2}, {"wind_ms": 3.0, "seed": 3}],
 "launch": {"altitude_m": 0.0, "latitude_deg": 28.61, "longitude_deg": -80.6,
            "rod_angle_deg": 0.0, "rod_direction_deg": 90.0,
            "wind_turbulence": 0.1, "time_step_s": 0.05},
 "max_sim_time_s": 1200,
 "max_steps": 400000}
```

`launch` is optional; the values shown are the defaults. The helper sets every
launch condition itself and ignores any simulation stored in the file. It flies
the rocket's default flight configuration.

Reply when OpenRocket could read and build the design:

```json
{"id": "r1", "ok": true,
 "load_warnings": ["text of each warning OpenRocket gave while reading the file"],
 "rocket": {
   "length_m": 1.2, "max_diameter_m": 0.054, "stage_count": 1,
   "mass_kg": 1.31, "dry_mass_kg": 1.02,
   "cg_m": 0.71, "cp_m": 0.86, "stability_cal": 2.7,
   "motor_count": 1, "total_impulse_ns": 230.0, "config_id": "..."},
 "components": [
   {"index": 0, "parent": -1, "type": "NoseCone", "name": "Nose cone",
    "x0_m": 0.0, "length_m": 0.2,
    "outer_radius_fore_m": 0.0, "outer_radius_aft_m": 0.027, "inner_radius_m": null,
    "thickness_m": 0.002, "filled": false,
    "mass_kg": 0.08, "computed_mass_kg": 0.07, "mass_overridden": true,
    "cg_x_m": 0.13, "computed_cg_x_m": 0.14, "cg_overridden": false,
    "cd_overridden": false, "override_subcomponents": false,
    "fins": null, "motor": null, "recovery": null}
 ],
 "flights": [
   {"wind_ms": 1.0, "seed": 1, "ok": true, "abort": null,
    "apogee_m": 312.4, "max_velocity_ms": 88.1, "max_accel_ms2": 140.2, "max_mach": 0.26,
    "time_to_apogee_s": 7.9, "flight_time_s": 61.3,
    "rail_exit_ms": 17.2, "stability_rail_cal": 1.9, "stability_min_burn_cal": 1.6,
    "burnout_time_s": 1.8, "liftoff_twr": 9.4,
    "branches": [
      {"index": 0, "name": "Sustainer", "has_recovery": true,
       "deployed": true, "deploy_time_s": 9.9, "deploy_speed_ms": 12.3,
       "deploy_during_burn": false,
       "landed": true, "landing_time_s": 61.3,
       "landing_vertical_ms": 4.8, "landing_total_ms": 5.1}
    ],
    "warnings": ["text of each simulation warning"],
    "steps": 2412, "hit_step_cap": false, "hit_time_cap": false}
 ]}
```

Meaning of the less obvious fields:

* `x0_m`: distance from the tip of the nose to the front end of the part, as
  OpenRocket resolved it. `parent` is the `index` of the enclosing part.
* `mass_kg` is the mass OpenRocket uses (with any override); `computed_mass_kg`
  is the mass it would compute from the shape and material with no override.
  The same for `cg_x_m` and `computed_cg_x_m` (measured from the nose tip).
  The helper reports what the file it is given holds. The reward's cleaning
  removes every override before a design is flown (DESIGN.md section 5), so
  in scoring these pairs are equal and `mass_overridden`, `cg_overridden`,
  `cd_overridden` and `override_subcomponents` are false (the example above
  shows a file that still had an override).
* `fins` (fin sets only): `{"count", "root_chord_m", "tip_chord_m", "span_m",
  "sweep_m", "thickness_m", "cant_deg", "root_x0_m", "root_radius_m",
  "points": [[x, y], ...]}` where `root_radius_m` is the radius of the body at
  the fin root and `points` is the outline of one fin.
* `motor` (motor mounts with a motor in the flown configuration):
  `{"manufacturer", "designation", "digest", "diameter_m", "length_m",
  "x0_m", "overhang_m", "total_impulse_ns", "burn_time_s", "ignition_event",
  "ignition_delay_s"}`.
* `recovery` (parachutes and streamers): `{"kind", "diameter_m", "cd",
  "deploy_event", "deploy_altitude_m", "deploy_delay_s"}`.
* `stability_rail_cal`: stability margin when the rocket leaves the rail.
  `stability_min_burn_cal`: its lowest value from leaving the rail to the last
  motor burnout.
* A branch is one separately flying section (the sustainer, a dropped
  booster). `landing_vertical_ms` (downward) and `landing_total_ms` (with
  sideways drift) are the speeds at the touchdown sample: the sample
  OpenRocket stored at the branch's first `GROUND_HIT` event (the ground-hit
  point at altitude 0; when no sample sits at the event time, the last
  sample before it that is still above the ground). That is usually the
  branch's last sample, but not always: OpenRocket keeps simulating a branch
  that lands while its motor still burns, and its later samples are at rest.
  Do not interpolate again. Both are `null` when the branch did not land.
* Recovery, per branch. Every recovery device that opened on the branch counts
  (a drogue and a main both count). `deployments` lists each opening in time
  order: `{"device", "time_s", "speed_ms", "during_burn"}`, where `speed_ms` is
  the total speed at that moment (interpolated between samples) and
  `during_burn` is true when a motor of the branch had ignited and not yet
  burnt out. `deploy_speed_ms` is the largest `speed_ms` (the fastest opening,
  usually the main of a dual-deploy rocket). `deploy_during_burn` is true when
  any opening happened during a burn (`null` when nothing opened).
  `deployed` and `deploy_time_s` refer to the first opening.
* `abort`: the reason text when OpenRocket aborted the flight, else `null`,
  as plain text (OpenRocket's HTML markup is removed; the same for warnings).
  An aborted or capped flight is a normal result: `"ok": true` with numbers.
* A flight without numbers has `"ok": false`, an `"error"` text and an
  `"error_kind"`: `"load"` or `"build"` (the file reloaded for this flight
  failed, or the rocket never started flying, for example a motor that
  ignites only after `max_sim_time_s`) or `"crash"` (OpenRocket threw an error
  during the flight; its partial numbers are artefacts and are not reported).
  `sim.py` retries a design with a crashed flight once on a fresh helper after
  the self-test rocket has flown; if the flight crashes again the reply is
  returned and the caller gives the design the build floor.
* `hit_step_cap` / `hit_time_cap`: the flight was stopped by `max_steps` or
  `max_sim_time_s`. These caps make "this design takes forever" a repeatable
  result that does not depend on how busy the machine is.

Reply when the design itself is at fault:

```json
{"id": "r1", "ok": false, "error_kind": "load", "message": "what OpenRocket said"}
```

`error_kind` is `"load"` (OpenRocket could not read the file) or `"build"`
(it read it but could not build or configure the rocket). Build faults
include: no motor in the flown configuration; a motor OpenRocket does not
have at all, or has only under the same name with another thrust curve (see
`motor_lookup`); a value OpenRocket skipped while reading the file (its load
warning starts "Invalid parameter encountered", for example `NaN`, after
which OpenRocket would keep a default and fly a different rocket); a rocket
whose mass, balance point or centre of pressure is not a finite number. A
build fault reply also carries `load_warnings` and `motor_lookup` when known.

`"request"` means the helper could not read the request (unknown field, a
value out of range, bad JSON). `sim.py` checks its arguments before sending,
so this should not happen; if it does, sim.py treats it as machine or helper
trouble (retry after the self-test rocket, then a design fault). `"internal"`
means the helper itself hit a bug; Python treats that as a machine problem
first, like a crash.

## Repeatability

The same request must give byte-identical flight numbers every time, in a
fresh process or a long-running one, alone or beside other helpers:

* a fixed seed for the random IDs OpenRocket gives parts on load
* the wind model rebuilt from each flight's `seed`
* the file reloaded before each flight, so no state carries over
* no wall-clock values in any reply

## Optional request fields

Added by the helper; leaving them out gives the behaviour described above.

* `config_id` (run): the flight configuration to fly, written exactly as the
  file writes it (a UUID, or a short id such as `"cfg0"`, which OpenRocket maps
  the same way on both sides). Without it the rocket's selected configuration
  flies. `allow_motor_substitution` (run, default false): see "How each motor
  was found". A design that declares its configuration without `default="true"`
  loads with a new, empty configuration selected, so the reward passes the
  declared id (`ork.flight_config_id`). An id the rocket does not have is a
  `build` fault.
* In `launch`:
  * `wind_direction_deg` (default 90, OpenRocket's own default),
  * `launch_into_wind` (default `false`),
  * `geodetic`: `"spherical"` (default), `"flat"` or `"wgs84"`,
  * `base_temperature_k` and `base_pressure_pa`: give either to fly OpenRocket's
    extended ISA atmosphere from that ground temperature and pressure; leave both
    out for the standard ISA atmosphere.

  The reward fixes these and never takes them from the design: sim.py sends
  `launch_into_wind`, `geodetic` and `wind_direction_deg` in every request
  (`sim.FIXED_LAUNCH`: false, spherical, 90) unless the caller gives its own,
  so nothing comes from a default or saved preference. They exist so
  that the parity check (`tools/sim_parity.py`) can repeat flights stored with
  other settings. Note that OpenRocket's own default for a simulation that does
  not name a geodetic method is flat earth, not the helper's spherical.

## Extra reply fields

`ping` adds `motor_database_size` (1,452 for OpenRocket 24.12: the entries of its
motor list, which hold 1,389 distinct thrust curves; sim.py refuses
a helper with fewer than 1,000). `run` adds per part `active`, `stage`,
`instances`, `radial_offset_m`, `mass_overridden_by`; in `rocket`
`structure_mass_kg` and `reference_length_m`; per flight `ground_hit_ms`
(OpenRocket's own ground-hit speed of the main branch, equal to its
`landing_total_ms` on all 147 parity designs), per flight `ignition_time_s`
(the time of the first motor IGNITION event of branch 0: 0 for a motor lit at
launch, later when the first motor is lit only after a delay while the rocket
waits on the pad; `targets.py` measures flight time and time to apogee from
it) and per branch `last_time_s`. When a branch keeps being simulated after it
touched down (seen on a rocket that lands while its motor still burns: model
answer row-023 hits the ground at 2.1 s and is simulated to 3.7 s), its last
sample is at rest, so the landing speeds are read at the touchdown sample, not
the last one (row-023: 8.4 m/s, equal to `ground_hit_ms`; before 2026-11-19
the helper read the last sample and reported 0). The reward still counts a
landed branch's vertical speed that is not above 0 as unknown. Components list every part
except the Rocket root, so stages are included (a top stage has parent -1).

### How each motor was found (helper version 3)

OpenRocket looks a motor up by the thrust-curve digest written in the file
first, then by maker and designation. `run` replies (and build faults) carry
`motor_lookup`: one entry per motor mount that the file gives a motor in the
flown configuration, in OpenRocket's tree order, or `null` when the file's
motor elements could not be matched to the mounts:

```json
{"mount": "Inner Tube",
 "requested_manufacturer": "AeroTech", "requested_designation": "G75J",
 "requested_digest": "8cc88c1180b7ded51fd377cec51cde52",
 "found_by": "name", "substituted": true,
 "flown_manufacturer": "AeroTech", "flown_designation": "G75M",
 "flown_digest": "a489d74510a23cfb4b882f14afed6aa5"}
```

* `found_by`: `"digest"` (the curve the file names), `"name"` (no curve with
  that digest, or the file names none, so OpenRocket took a motor with the same
  maker and designation) or `"none"` (no such motor; the mount would fly empty).
* `substituted`: the file names a digest and a different curve would fly.

The motor object of each mount repeats `found_by`, `substituted`,
`requested_manufacturer`, `requested_designation` and `requested_digest`, and
`rocket` has `motor_substituted` (any motor substituted). A `"none"` or a
substituted motor is a `build` fault unless the request sets
`"allow_motor_substitution": true` (parity checks only, never the reward); a
`"none"` motor then still fails when its mount was the only one.

## motors

```json
{"op": "motors", "id": "m1"}
```
```json
{"id": "m1", "ok": true, "motors": [{"digest": "...", "manufacturer": "AeroTech",
  "designation": "H170M", "common_name": "H170", "diameter_m": 0.038,
  "length_m": 0.191, "total_impulse_ns": 300.0}]}
```

Every thrust curve in OpenRocket's built-in motor list, sorted by digest.
`sim.Simulator.motor_list()` returns the list.

## quit

```json
{"op": "quit"}
```
The helper exits with code 0. Closing its standard input does the same, at
once, even in the middle of a request (standard input is read on its own
thread), so a helper never outlives a Python parent that was killed.
