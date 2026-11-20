# rocket_reward: design

This folder holds the reward used to train the rocket-design model with
reinforcement learning (RL). It turns one model answer into one number from 0 to 1
that says how good the design is. This file is the contract: what the score means,
which rules are fixed, and how the code is laid out.

## 1. What goes in and what comes out

```python
from rocket_reward import score, Requirements

req = Requirements.from_dict(row["requirements"])
result = score(answer_text, req, truncated=False)

result.score     # 0.0 .. 1.0, or None when the answer must be left out of training
result.stage     # where scoring stopped: format, parts, motor, limits, build, flight, targets
                 # ("dropped" when score is None)
result.reasons   # plain-language reasons, e.g. "motor 'AeroTech-H1650R-v1' is not a real motor"
result.metrics   # flight numbers when the design was flown
```

* `answer_text` is the model's full reply. The design is the JSON inside
  `<design> ... </design>`: an OpenRocket document written as a tree in which every
  node is `{tag: {"attrs": {...}?, "value": ...?, "children": [...]?}}` and the root
  tag is `openrocket`.
* `requirements` says what the prompt asked for (section 4). The reward never reads
  the prompt text.
* `truncated=True` means the model ran out of tokens.

## 2. The ladder

A design climbs seven stages in a fixed order. Each stage has its own band of
scores, and the bands never overlap, so getting further always scores higher.

| # | stage | band | what it checks |
|---|---------|-------------|----------------|
| 1 | format  | 0.00 - 0.08 | the answer holds a readable design tree |
| 2 | parts   | 0.10 - 0.18 | all the needed parts are there |
| 3 | motor   | 0.20 - 0.28 | every motor is a real one |
| 4 | limits  | 0.30 - 0.38 | sizes, counts and materials are physically sensible (no trick values) |
| 5 | build   | 0.40 - 0.48 | OpenRocket can build it and the parts fit together |
| 6 | flight  | 0.50 - 0.68 | it flies safely in every wind |
| 7 | targets | 0.70 - 1.00 | it does what the prompt asked |

A design that fails stage k scores `floor_k + width_k * credit`, where `credit`
is between 0 and 1 and says how close it came to passing. A design that passes
stages 1-6 scores `0.70 + 0.30 * t`, where `t` says how well it met the targets.
The table lives in `ladder.py` and nowhere else.

### Rules that must always hold (each one is a test)

1. **Bands never overlap.** The best score of a design that stops at stage k is
   below the worst score of one that stops at stage k+1.
2. **Closer is never worse.** Inside a stage, making a violation smaller never
   lowers the score. Every credit is clamped to 0..1.
3. **A broken machine is never a score.** No Java, a wrong jar, missing data files
   or a failed self-test raise `RewardSetupError`. They never turn into a number.
4. **Skipping a check never beats failing it.** A design the simulator cannot
   build, or that hangs or crashes it, gets the floor of the build stage (0.40).
5. **The model cannot set its own physics.** Launch conditions, material
   densities and motor data are written by the reward, and every mass,
   balance or drag override is removed (section 5).
6. **Same answer, same score.** Scoring uses fixed seeds and no wall-clock values.

### How credit is computed

Most rules compare a number with a limit. The size of a violation is

```
v = min(3, log2(value / limit))      for a "no more than" rule that is broken
v = min(3, log2(limit / value))      for a "no less than" rule that is broken
v = 1                                for a yes/no rule that is broken
v = 3                                when the value is missing, zero or not a number
```

and a stage's credit is `1 / (1 + sum of v)`. Twice the limit costs 1, eight times
or more costs 3. Stages may add their own terms where this file says so.

### Stage 1: format (`parse.py`)

| situation | credit |
|-----------|--------|
| answer cut off, or no complete `<design>...</design>` block | 0 |
| block found, but the JSON does not parse | 0.5 |
| JSON parses, but it is not a tree of `{tag: {attrs?, value?, children?}}` nodes with root `openrocket`, or it is deeper than 64 levels, or larger than 300 kB | 0.75 |

Nothing is repaired. Other top-level keys next to `openrocket` (the model
sometimes puts `simulations` there) are allowed and ignored. The block used is
the first `</design>` that has a `<design>` before it, paired with the nearest
one. Details:

* Size is the UTF-8 bytes of the block text, judged once the JSON parses
  (0.75). A block over 3 MB is not read at all and scores like broken JSON (0.5).
* `NaN` or `Infinity` in the JSON does not parse (0.5). A key written twice in
  one object, or a number too large for a float (`1e999`, a 400-digit
  integer), is a bad tree (0.75).
* Every tag must be an XML element name (ASCII letters, digits, `_`, `-` and
  `.`, starting with a letter or `_`), because OpenRocket could never read a
  file with any other tag (0.75). Attribute names are not checked here.

### Stage 2: parts (`parts.py`)

Eight things every flyable rocket needs. Credit = found / 8. A part counts
only where OpenRocket would load it: reached through `subcomponents` from a
stage, in a parent OpenRocket lets hold it (`tree.LEGAL_CHILDREN`; for example
only nose cones, body tubes and transitions sit directly in a stage, and
nothing sits inside a parachute). OpenRocket drops a part placed anywhere else.

1. a stage inside `rocket > subcomponents`
2. a nose cone
3. a body tube
4. a fin set (trapezoid, elliptical, freeform or tube fins) with at least one
   fin. The count is the last `fincount`, else the last `instancecount`
   (a setting written twice keeps its last copy, as OpenRocket's loader and
   the cleaned copy do); none written means OpenRocket's 3
5. a motor mount (a body tube or inner tube holding a `motormount` node)
6. a motor inside that mount
7. a motor configuration: the rocket declares a configuration id, and a motor
   in a mount uses the flown one (stage 3 says which; without this OpenRocket
   flies the rocket with no motor)
8. a recovery device (parachute or streamer)

Every stage reads a number as OpenRocket's Java reader does
(`tree.read_number`): `0.5f` and `0x1p-3` are numbers, `1_0` is not.

### Stage 3: motor (`motors.py`)

The flown configuration is the rocket's `motorconfiguration` marked
`default="true"` (the last one when several are), else the first one with a
`configid`. Every motor in a motor mount that uses its id must be in the motor
table (`data/motor_table.json`, 1,409 real motors: every motor OpenRocket 24.12
has a thrust curve for, with OpenRocket's own numbers and the digest it finds
the motor by; built by `tools/build_motor_table.py`). Accepted as the same motor:
different letter case, a missing `-vN` version suffix (the lowest version is
used; a wrong suffix is not accepted), and a motor with no `motor_id` whose
maker and designation match exactly one table motor. A field written twice
counts by its last copy.

An unknown motor fails the stage. Its credit is the share of these facts that
are true, and with several motors the worst one counts:

* the maker (as written, else the start of the motor id) is a real maker
* the designation (as written, else the motor id after the maker) exists in
  the table under some maker (ignoring case, an `HP-` prefix and the version suffix)
* a real motor of the class letter the designation names (by impulse, or sold
  under that letter) is within 0.5 mm of the diameter the design gives

Motor ids are never auto-corrected. A design with an invented motor (0.20 or
more) always beats the same design with the motor deleted (parts stage).

**Shadow flights.** When a simulator is available (`score` always has one),
half the credit comes from the facts and half from how far the rest of the
design gets: `credit = 0.5 x facts + 0.5 x progress` (`ladder.MOTOR_FACTS_SHARE`,
`MOTOR_SHADOW_SHARE`). Every unknown flown motor is replaced by the nearest real
motor (`motors.MotorTable.nearest_real`) and the copy is scored through stages
4-7; `progress = (shadow score - 0.30) / 0.70`, clamped to 0..1. The nearest
real motor is fixed by a rule, so the same answer always gets the same one:

1. the class letter the written designation names (no letter: no substitute,
   progress 0, nothing is flown);
2. motors of that class (by impulse, or sold under that letter) of the size
   that fits the design's motor mount (`MotorTable.fitting_diameter`): the
   largest diameter the class has that is at most 1.05 times the mount's inside
   diameter as written (`motors.mount_room_m`; the stage 5 limit), else the
   smallest one; when the mount's size cannot be read ("auto" radius), all of
   them. The diameter the design writes for its motor only decides the third
   fact above, so making that fact true never picks a worse substitute;
3. of those, the ones of the motor type the design wrote for that motor
   (`type`: single, reload or hybrid; `motors.motor_type_of`), when at least
   one has it. The type comes before the maker because a hybrid's tank
   changes the mass and length far more than a maker does;
4. of those, the ones sold by the maker the design names (as written, else
   the front of its motor id; letter case ignored), when at least one is;
5. the one whose average thrust is closest to the number after the class
   letter (`H1650R` -> 1650 N); ties go to the smaller total impulse, then the
   motor id.

Naming a real maker is the first fact, so step 4 could let a true fact pick
a worse substitute. When step 4 changes any substitute, the copy chosen
without it is flown too and the better shadow score counts (one extra
shadow flight); the reasons and `flags["shadow"]` name the substitutes that
counted.

The answer still scores inside the motor band (0.20 - 0.28), so a design
with a real motor (0.30 or more) always beats the same design with an invented
one. The reasons end with one line naming the substitute, how far it got and,
when it stopped before targets, the shadow's own first reason;
`Result.flags["shadow"]` holds the substitutes, the shadow score, its stage,
that reason and the progress. `preflight()` and `preflight_result()` never fly anything
and give the facts-only credit.

### Stage 4: limits (`limit_checks.py`, numbers in `limits.py`)

These are bounds no sound rocket crosses. They exist to block trick values, not
to grade style, and each is set so that the reference rockets pass. Examples:
finite numbers everywhere; no part of size 0 where a size is needed (0 is not
"auto"); 1 to 8 fins per set; parachute drag coefficient and
diameter within catalogue range; tube walls and fins not paper-thin; tube sizes
within catalogue range; fin span not many times the body width; only known
component types; total motor impulse within the contract limit. Credit uses
the violation formula above.

Stage 4 checks the cleaned copy (section 5), so it sees the values that will
be flown. Material names: every material OpenRocket loads must have a name the
material table knows (`materials.py`), because only then can the reward give
it its real density. Each distinct unknown name is a yes/no violation (at most
three count, `ladder.MATERIAL_NAMES_COUNTED_MAX`); the reason names it and
suggests a known name only when one is spelled closely (at least
`materials.CLOSE_NAME_RATIO_MIN` = 0.7 alike; text only, it never changes a
score), else it says no name in OpenRocket's list is spelled like it and
points to the list in `data/material_table.json`. Every unknown name counts:
the cleaning removes every override, so no part's mass hides its material.
The density written for an unknown name is bounded too: never negative; bulk
10 to 25,000 kg/m3, surface up to 5 kg/m2, line up to 1 kg/m. A material is
judged as the type OpenRocket loads (`materials.loaded_type`): each slot holds
one type (a parachute or streamer's cloth is surface, a shock cord and shroud
lines are line, everything else bulk).

Counts and small outside parts (added after the stage 5-7 review): at most
100 parts in a design (reference: 73 in the training rows; V4-0167 and V4-0172
have more and stop here), at most 8 copies of one part
(`instancecount`; fin sets keep their own 1 to 8), at most 8 launch lugs and
8 rail buttons (copies counted; reference: 4 and 3), launch lugs at most
20 mm in radius and 0.3 m long, rail buttons at most 40 mm across and 30 mm
tall, tube fins no wider than the body they sit on. A count past its limit is
judged with the "no more than" formula, so a design with hundreds of tiny
parts stops here in milliseconds instead of taking a minute to fly.

Sizes, positions and counts (added 2026-11-19 after the review; every bound
clears the references with their overrides removed):

* A written 0 is a part of no size, not "auto". Only the word "auto" (alone or
  as "auto 0.025") takes the next part's size, and the number after it is
  judged like a written size. A nose cone base radius must be at least 1 mm.
  A body tube radius or a nose cone base radius of 0 passes only on a part of
  length 0 (an empty holder). A transition may end in a point (stage 5's tail
  rule still needs room for the motor).
* Trapezoid and elliptical fins need a root chord and a span of at least
  2 mm, and a trapezoid tip may be at most 3 times its root. Sweep at most 1 m
  either way, tab height at most 150 mm, fillet radius at most 50 mm.
* Packed length at most 1.5 m; packed radius at most 150 mm; shroud lines at
  most 8 m; shock cords at most 25 m.
* Shroud line count a whole number from 1 to 48. Every `instancecount` a whole
  number of at least 1.
* Deployment and stage separation delays at most 20 s and altitudes at most
  3,000 m, never negative (also inside `separationconfiguration`).
* Rail button base, flange and screw heights at most 30 mm and inner diameter
  at most 40 mm, never negative.
* Positions, axial offsets, tab positions, instance separations and mount
  overhangs at most 5 m either way. Angles at most 360 degrees either way.
  Radial positions and offsets at most 0.3 m either way.
* Motor ejection delay at most 30 s; mount ignition delay at most 20 s.
* Shoulders at most 0.5 m long; shape parameter at most 1; cluster scale at
  most 60.
* A mass component with a packed length and radius may be at most
  1,000,000 kg/m3 dense. A point mass (length or radius 0) is not judged.

Walls and fins must also weigh enough per area (thickness times the density
the part flies with: the table's for a known name): a body tube, nose cone,
transition or tube fin wall at least 0.045 kg/m2 (lightest sound reference:
0.095, a 0.14 mm cardboard wall), fins at least 0.12 kg/m2 (lightest sound
reference: 0.27, 1/16 inch balsa). A catalogue-thin wall of foam is not a
light rocket. Solid ("filled") parts and a 0 mm wall on a part of length 0
are skipped, as for the wall rule.

Every number is in `limits.py` with a one-line note saying where it came from.

### Stage 5: build (`ork.py`, `sim.py`, `fit.py`, numbers in `limits.py`)

The cleaned design is written as an OpenRocket file (`ork.design_to_ork`) and
loaded by OpenRocket itself, which reports where it placed every part. Credit 0
(score 0.40) when the file cannot be written, OpenRocket rejects it, hangs or
crashes, or any of the three flights cannot start. Every load warning counts as
one yes/no violation (no sound reference gives one). Fit is judged on the
positions OpenRocket computed, never on our own copy of its placement rules:

| rule | limit |
|------|-------|
| outer radius step between neighbouring nose cone, body tube and transition | 10% of the larger radius in one stage, 15% between stages |
| fin root past the back / front end of its parent (tube fins: the tubes, in tube lengths) | 0.5 / 1.0 root chord |
| rigid inside part (ring, bulkhead, engine block, inner tube, coupler) over the airframe's inner radius | 1.08 times |
| packed inside part (parachute, streamer, shock cord, mass) over the airframe's inner radius | 1.30 times |
| how far a part lies outside its airframe along the axis, as a distance (not its own uncovered length; a part in a pod or side booster is judged against that pod's shell; a ring, bulkhead, engine block or coupler may also sit on the motor tube holding it): inner (motor) tube / ring, bulkhead, engine block or tube coupler / mass component, shock cord, parachute, streamer, launch lug or rail button | 50 mm / 20 mm / 50 mm |
| aft radius of a stage's last shell over the radius of a motor firing out of it (pods and side boosters excepted) | at least 0.35 times |
| motor diameter over its mount's inner diameter | 1.05 times |
| motor hanging out behind its mount | half its length |
| back end of a motor ahead of the back end of its stage's airframe (pods and side boosters excepted) | 0.15 m |
| pod or side-booster shell over the main body's widest radius | 1.0 times |
| a pod or side booster whose front shell is an open body tube (not a nose cone or transition) | yes/no |
| two fin sets on one part at the same angles (within 2 degrees) | not allowed |
| two rings, bulkheads or engine blocks pushed into each other | 3.5 mm |
| a motor of the flown configuration missing after loading | yes/no, per motor |

The cleaned design holds no override settings, so OpenRocket builds and flies
it from its parts and materials alone, in one simulator run.

Inside parts are judged against the inner radius of the nearest enclosing
nose cone, body tube or transition. When that frame has no room inside
(solid, or a wall as thick as its radius), the part is judged against the
frame's outer radius instead (nose weight cast into a solid nose cone), never
skipped. A violation smaller than 0.5
(`ladder.FIT_DEFECT_BELOW`, about 1.41 times the limit) is a defect; larger
ones fail the stage with the violation formula. On the references (the
2026-11-19 calibration, overrides removed), 7 designs fail here and 3 pass it
with a fit defect: V4-0045, which passes the whole ladder, and V4-0162 and
V4-0189, which stop at stage 6 (REFERENCE_ROCKETS.md lists them).

### Stage 6: flight (`flight.py`, numbers in `limits.py`)

The design is flown three times, at 0.5x, 1x and 1.5x the wind in the
requirements (default 2 m/s, each capped at 8.94 m/s), with seeds 1, 2 and 3.
The launch rail follows the largest motor's impulse class: 1.5 m up to F,
1.8 m for G, 2.4 m for H and I, 3.0 m for J and K, 3.7 m above. Each flight is
judged on its own; the worst flight counts, and the stage passes only when
nothing at all is broken:

* stable on the pad: at least 1.0 cal (judged once, from the rocket)
* the flight does not abort and is not stopped by the step or time cap (3)
* leaves the rail at 11 m/s or more, with a liftoff thrust-to-weight of 3 or more
* stability above 0 cal leaving the rail and until the last burnout (for a
  0 cal limit the violation is the shortfall in calibres plus 0.1, at most 3)
* every section with a recovery device opens it (yes/no), nothing opens while a
  motor burns (yes/no), and the fastest opening is at 60 m/s or slower
* every section lands (else 3); a section with a recovery device, and the main
  section always, lands at 9 m/s or slower (vertical); a section without
  recovery (a spent booster) at 25 m/s or slower. Stage 6 judges only safety
  that holds for every rocket: the prompt's own landing limit is a stage 7
  target. The vertical landing speed is downward and positive: a landed
  section reported at 0 m/s or moving up is an odd reply and counts as
  unknown (3), never as a soft landing

Credit = `1 / (1 + pad violation + the worst flight's violations)`. Any number
a rule needs that the reply leaves out counts as 3, never as a pass.

### Stage 7: targets (`targets.py`)

`t` is the product of one credit per stated target, read from the 1x-wind
flight. There are no weights: every target counts the same way, and missing two
targets never scores above missing one of them. Each target has a kind:

* `about`: full credit within the tolerance, then `1 / (1 + d / 0.25)` where
  `d = |ln(value / target)| - ln(1 + tol)`. Credit never reaches zero, so twice
  off always beats four times off.
* `max` / `min`: full credit on the right side of the limit, the same falling
  curve past it. A `max` landing target without a tolerance gets 15% slack
  (`limits.LANDING_SLACK_DEFAULT`; the prompts were written from one flight);
  a tolerance that is given, 0 included, is used as given. A `max` landing
  speed also earns less below a comfort floor
  (3.5 m/s or 60% of the limit, whichever is lower), in proportion: a
  needlessly large parachute drifts far.

Apogee, flight time, time to apogee, top speed and top acceleration come from
the flight; flight time and time to apogee are measured from the first motor
ignition (`ignition_time_s` in the reply; 0 for every reference), so a rocket
that waits on the pad gains nothing. Landing speed is the main section's
vertical speed (none when it is not above 0); body diameter is the widest
main-body tube OpenRocket built (tubes in pods and side boosters do not
count); mass is the liftoff mass. `motors`
earns 0.5 plus 0.5 times the share of named motors the rocket really flies
(`ladder.MOTORS_CREDIT_MIN`); `motor_class` earns 1 for the right class letter,
0.75 for one letter off and 0.5 otherwise, also when no flown motor has a known
impulse (`ladder.MOTOR_CLASS_NEAR_CREDIT`, `MOTOR_CLASS_FAR_CREDIT`): a design
that flies a different real motor has still answered the rest of the prompt, so
the miss halves the credit instead of zeroing the product. A missing measured
value earns 0 (so t is 0). Every target that loses credit gets a reason with
both numbers and the credit.

Worked example: an `about` apogee target with the default 5% tolerance, flown
to ten times the asked height, earns `1 / (1 + (ln 10 - ln 1.05) / 0.25)`,
about 0.10, so the design scores about 0.730 if every other target is met,
and the same 0.270 is lost whatever else the prompt states (measured on 14
references: 0.730). A landing 1% faster than a `max` landing target with
tolerance 0 scores 0.9885, and twice as fast (still under 9 m/s) 0.7795.

### Defects

A defect is a small problem that does not stop the ladder (for example a part
that overlaps its neighbour by a hair). Each defect costs 5% of the credit of
the stage the design finally reaches, up to 50%; defects from every stage run
count. This keeps a sound rocket with a tiny flaw above a rocket that crashes.

## 3. When something goes wrong

| what happened | what the reward does |
|---------------|----------------------|
| Java missing, wrong jar, data file missing, self-test rocket fails, the simulator was closed, `ROCKET_REWARD_WORKERS` is not a whole number of 1 or more | raise `RewardSetupError` with a message saying what to fix |
| the design cannot be written as an OpenRocket file | score 0.40, the floor of the build stage |
| OpenRocket rejects (`load`), cannot build (`build`), hangs on (`hang`) or crashes on (`crash`) this design, or a flight cannot start or crashes, also after a retry on a fresh helper that flew the self-test rocket | score 0.40, the floor of the build stage |
| an odd reply (missing fields, nulls, wrong types) | a normal result: a missing number counts as the largest violation |
| an unexpected error inside a check on one answer | save the answer to the quarantine folder, return `score=None` (the answer is left out of training), count it |
| more than 1% of the last 500 answers, or 5 in a row, hit unexpected errors | raise `RewardSetupError` |
| the answer was cut off | score 0.0 |

**The simulator.** `score(answer, requirements, truncated=False, simulator=None)`
flies with the simulator it is given (a `sim.Simulator` or `sim.SimPool`). With
none it uses one shared default: a `SimPool` of `ROCKET_REWARD_WORKERS` helpers
(default 4, the fastest measured; at most the CPU count minus one), started the
first time a design must be flown and closed when Python exits.
`score_many(answers, requirements_list, truncated=None, simulator=None)` scores
a batch in parallel threads (twice as many as helpers) and keeps the order; each
answer gets exactly the result `score` would give it. A pool may be shared by
any number of threads: each run takes one free helper. With 4 helpers a warm
pool took 0.14-0.30 s per answer on 2026-11-19 (on a PC shared with other
jobs: 0.14-0.18 s on the 48 val answers and the model's 48 answers, 0.27 s on
the 594 reference rows, 0.29-0.30 s on 100 reference answers), more when many
answers need a shadow flight. The 2026-11-19 changes did not slow it: the
package before them took 0.30-0.34 s on the same 100 answers.

## 4. Requirements

One record per prompt, built by the same tool that writes the prompt text, so
the two cannot disagree.

```json
{
  "id": "v5-0012",
  "apogee_m": {"value": 3320, "kind": "about", "tol": 0.05},
  "landing_ms": {"value": 5.7, "kind": "max"},
  "flight_time_s": {"value": 190.2, "kind": "max"},
  "wind_ms": 0.1,
  "motors": ["M2000R"]
}
```

`apogee_m` is required. Every other field is optional and is simply not graded
when absent. Allowed fields are listed in `records.py`; an unknown field is an
error, so a typo cannot silently drop a target.

## 5. What the model may and may not set

The model chooses the parts, their sizes and positions, material names, fin
shape and count, recovery size and deployment settings, and the motor id.

Before anything is checked or flown, `clean.py` makes a cleaned copy in which:

* every `simulations` block is removed, wherever it sits (launch rail, wind,
  launch site and time step are set by the reward)
* every override setting (any tag starting with `override`: `overridemass`,
  `overridecg`, `overridecd` and their `overridesubcomponents...` switches)
  is removed, right after the `simulations` blocks and before anything is
  checked: the drag, mass and balance point are the ones OpenRocket computes
  from the parts and materials, and mass a designer wants to add must be a
  real mass component. The cleaning notes say how many were removed, and
  `Result.flags["overrides_removed"]` holds the count. Until 2026-11-19 mass
  and balance overrides were kept and bounded; a review showed they could
  still fake about 2 calibres of stability and hide a too-fast landing
  (section 7). 165 of the 197 reference designs write override settings
  (3,522 in all), so they are judged on their parts alone.
* the stability reference is forced to OpenRocket's default and custom
  reference lengths are removed
* only the flown motor configuration is kept, with the motors and settings
  that use it
* the motors of the bottom stage (the last stage, the one that lifts off) get
  an ignition delay of 0 s, on the motor mount and in its per-configuration
  ignition setting; the ignition event is kept, and upper stages and side
  boosters keep their own settings (an air start there is real). A delay on
  the bottom stage only keeps the rocket sitting on the pad
* extra `subcomponents` (and `motormount`) holders are merged into the first,
  in order, and a setting written twice keeps only its last copy, as
  OpenRocket's loader does
* each motor's id is written as the table spells it; its maker, designation,
  diameter, length and digest come from the motor table; other motor
  settings (except type and delay) are removed
* the file format version is `1.10`, the one OpenRocket 24.12 writes (the
  version changes how OpenRocket reads a file: below 1.4 it ignores the motor
  digest). 84 of the 197 reference designs write another version; an
  earlier check of 72 of them found every flight number identical either way
  (not re-run on 2026-11-19).
* material densities follow OpenRocket's loader: a material is used only when
  its name is not empty, its density reads as a number and its type is missing
  or exactly its slot's type. A used material whose name the table knows gets
  the table's density for the slot's type, and the type is written; a name the
  table does not know keeps its written density (stage 4 fails the name). A
  material OpenRocket would ignore, or whose name is empty or only `RS:`, is
  removed, so OpenRocket uses its default for that slot, as it would anyway.

The file writer (`ork.py`) writes every number as the value the stages read
(`tree.java_number`): `0.5f` is written `0.5`, and a whole fin, instance or
line count `3.0` is written `3` (OpenRocket reads counts as integers).

## 6. Code layout

```
rocket_reward/
  README.md         how to set up, run and extend the reward (for a student)
  DESIGN.md         this contract
  REFERENCE_ROCKETS.md  the reference rockets the reward does not pass
  .gitignore        keeps lib/ (the downloaded jar) out of git
  __init__.py       public names; importing it does no work
  __main__.py       lets `python -m rocket_reward` run cli.py
  errors.py         RewardSetupError
  ladder.py         stage table and the score formula
  records.py        Target, Requirements, StageCheck, Result
  tree.py           every helper that reads or walks the design tree (including
                    the material nodes), and the one number reader
  parse.py          stage 1
  parts.py          stage 2
  motors.py         motor table and stage 3
  limits.py         every limit, with its source
  limit_checks.py   stage 4
  clean.py          the cleaned copy (section 5)
  materials.py      material table (densities for clean.py, names for stage 4)
                    and the material type each part holds
  ork.py            design tree -> OpenRocket file
  sim.py            talks to OpenRocket (separate Java process)
  fit.py            stage 5 fit rules
  flight.py         stage 6
  targets.py        stage 7
  scoring.py        runs the stages in order (`score`, `score_many`, `preflight`),
                    shadow flights and the default simulator
  cli.py            python -m rocket_reward check | fetch-jar | score | preflight
  java/             RocketSim.java (the helper that drives OpenRocket) and
                    PROTOCOL.md (what it says); DumpMaterials.java and
                    MotorStats.java, which the table builders run
  data/             motor table, material table, and the self-test rocket
                    (canary.ork with its expected numbers in canary.json)
  lib/              the OpenRocket jar, when fetch-jar put it there (not in git)
  adapters/         thin wrappers for RL trainers: trl.py (TRL / Unsloth),
                    verifiers.py, README.md
  prompts/          the RL prompt set (rl_prompts_v1.jsonl), the references
                    it leaves out, and its README.md
  tools/            calibrate.py (the whole ladder on many answers, with a
                    report), calibrate_preflight.py (stages 1-4 on the
                    references), mutate.py (named cheats and what the reward
                    must do with each), build_requirements.py (prompt text to
                    records), build_rl_prompts.py (the prompt set),
                    build_motor_table.py, build_material_table.py, and
                    sim_bench.py / sim_parity.py (simulator speed, repeatability
                    and parity with the team's recorded flights)
  tests/            pytest; tests that need Java are marked needs_java;
                    tests/data holds the recorded answers, replies and snapshots
```

Conventions:

* Python 3.10+, standard library only (pytest for tests).
* No work at import time: no file reads, no processes.
* Every stage function takes plain data and returns a `StageCheck`.
* Numbers that shape the score live in `ladder.py`; physical limits live in
  `limits.py`. No other module contains a tuning number.
* Reasons are written for a student to read: say what is wrong and by how much.
* Files use LF line endings and UTF-8.

## 7. Changes on 2026-11-19 after review

A review of the reward found three weaknesses. Each was fixed and measured on
the same day. "Before" is the package as it was before the three changes.

**Targets.** Before: `t` was a weighted mean (apogee weight 3, every other
target 1), so met targets hid a missed one, and the prompt's landing limit
(plus 15% slack) was a stage 6 rule. A tenfold apogee miss cost only
0.116-0.162 of the score, and on 14 references an apogee target ten times off
still scored 0.838-0.899; a landing 1% over the prompt's limit stopped at
stage 6 (0.647). Now: `t` is the product of the target credits with no
weights; the prompt's landing number is only a stage 7 target (a `max`
landing without a tolerance gets 15% slack); a wrong named motor earns 0.5,
a motor class one letter away 0.75, further 0.5. After: the tenfold apogee
miss costs 0.270 whatever else is stated (0.730 on the same 14 references);
landing 1% over scores 0.9885, 100% over 0.7795. The model answer row-021,
which misses apogee and flight time, went from 0.8568 to 0.7107.

**Overrides.** Before: mass and balance overrides were kept and bounded, and
a "natural twin" without them was built to compare. A bounded override still
faked stability: V4-0238 with its fins halved stopped at stage 6 (0.537), and
the same design with a stage `overridecg` of 0.1986 scored 1.0; V4-0201 with
its parachutes at 0.6 times stopped at stage 6 (0.614) and scored 0.843 with
an `overridemass`. Now: the cleaning removes every override setting before
anything is judged; there is one simulator run per answer and no stage 4
rule is excused by an override. After: each tagged design scores exactly as
the same design without its tags (V4-0238 0.53677 at stage 6; V4-0201
0.775528 at stage 7, where it now lands under 9 m/s), and all 176 recorded
override tries on 15 unstable variants stop at stage 6.

**Sizes.** Before: stage 5 measured how much of a part was uncovered, not how
far away it was, so a thin part far away passed; pod parts were not judged;
and stage 4 read a written 0 as "auto" and had no bound on many sizes. 46
rows of the review's mutation run scored at least 0.70 with absurd values,
for example V4-0205's 12.69 kg mass component placed 1.478 m ahead of the nose
(1.0), a centering ring of V4-0067 at -470 m (1.0), a 25 m packed parachute
(1.0) and rail button sizes of 1e308 (1.0). Now: stage 5 measures the
distance outside the airframe for every inside part, lug and button (pods
against their own shell) and needs an open tail (`tail_closed`); stage 4
has the bounds listed under "Sizes, positions and counts". After: 36 of the
46 rows score below 0.70 (35 at stage 4, 0.311-0.32; V4-0205's mass at stage
5, 0.42). The other 10 only edit `overridemass` and now score exactly what
their unedited design scores.

**All three together.** Of the review's 2,508 mutations, 667 score at least
0.70 (before 882); of a second set of 1,003, 172 (before 297). The 594
reference rows, scored against their parsed prompts, now stop at: targets
480, flight 57, limits 36, build 21 (before 498, 42, 24, 30); by design,
targets 159, flight 19, limits 12, build 7 (before 165, 14, 8, 10). The
designs that moved are the ones whose files lean on overrides (see
REFERENCE_ROCKETS.md, "Sound only with their overrides") and three with
paper-thin walls their overrides covered. The RL prompt file keeps 474 rows
(before 482), each reference scoring exactly 1.0 on its own record. The named
operators in `tools/mutate.py` grew from 46 to 66 (61 of them cheats or
defects the reward must stop or score lower); of their 906 variants on 21
designs, 886 were judged and none failed its promise. The full test suite has
2,271 tests.
