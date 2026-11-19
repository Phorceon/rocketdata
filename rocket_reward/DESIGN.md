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
   build, or that hangs or crashes it, gets the floor of the build stage (0.40),
   also when this happens to its natural twin (stage 5).
5. **The model cannot set its own physics.** Launch conditions, material
   densities and motor data are written by the reward (section 5).
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
finite numbers everywhere; 1 to 8 fins per set; parachute drag coefficient and
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
points to the list in `data/material_table.json`. On a part that overrides its own mass the
material changes nothing, so the name is only noted (`info["notes"]`).
First bounds on single values stay as a guard before anything is flown (stage 5
bounds what the overrides do to the whole rocket): mass and balance
overrides (never negative; at most 20 kg and 3.66 m), and the density of an
unknown name (never negative; bulk 10 to 25,000 kg/m3, surface up to 5 kg/m2,
line up to 1 kg/m; skipped on a part whose mass is overridden). A material is
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

Walls and fins must also weigh enough per area (thickness times the density
the part flies with: the table's for a known name): a body tube, nose cone,
transition or tube fin wall at least 0.045 kg/m2 (lightest sound reference:
0.095, a 0.14 mm cardboard wall), fins at least 0.12 kg/m2 (lightest sound
reference: 0.27, 1/16 inch balsa). A catalogue-thin wall of foam is not a
light rocket. Parts whose mass is overridden, solid ("filled") parts and a
0 mm wall on a part of length 0 are skipped, as for the wall rule.

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
| motor tube behind the airframe / ring, bulkhead or engine block outside it | 50 mm / 20 mm |
| motor diameter over its mount's inner diameter | 1.05 times |
| motor hanging out behind its mount | half its length |
| back end of a motor ahead of the back end of its stage's airframe (pods and side boosters excepted) | 0.15 m |
| pod or side-booster shell over the main body's widest radius | 1.0 times |
| a pod or side booster whose front shell is an open body tube (not a nose cone or transition) | yes/no |
| two fin sets on one part at the same angles (within 2 degrees) | not allowed |
| two rings, bulkheads or engine blocks pushed into each other | 3.5 mm |
| a motor of the flown configuration missing after loading | yes/no, per motor |
| liftoff mass with overrides over without | 0.6 to 1.8 times |
| each stage's own parts (no motors) with overrides over without | at least 0.6 times |
| balance point moved by overrides | 1.5 calibres either way |

The last three rules compare the rocket with its "natural" twin: when the cleaned
design has mass or balance overrides (any setting whose tag starts with
`override`), the same design without them (`clean.natural_copy`) is also built
by OpenRocket, with one flight cut short after 0.05 s (only its mass and
balance point are read; on all 158 reference designs with overrides they are
identical to a full flight's). Building the twin is part of this stage: when
OpenRocket rejects, cannot build, hangs or crashes on the twin, or its flight
cannot start, the design gets credit 0 (score 0.40), exactly as if that had
happened to the design itself, and the reason says what happened without the
overrides. The per-stage rule sums each stage's parts as OpenRocket reports
them (a part whose mass an enclosing override stands for is not counted
again); it stops a heavy booster and its motors from hiding a nearly
weightless sustainer.

Inside parts are judged against the inner radius of the nearest enclosing
nose cone, body tube or transition. When that frame has no room inside
(solid, or a wall as thick as its radius), the part is judged against the
frame's outer radius instead (nose weight cast into a solid nose cone), never
skipped. A violation smaller than 0.5
(`ladder.FIT_DEFECT_BELOW`, about 1.41 times the limit) is a defect; larger
ones fail the stage with the violation formula. On the references, 10 designs
fail here and 4 have defects only, all of them on the measurement's broken list
or within a few percent of a limit (REFERENCE_ROCKETS.md lists them).

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
  section always, lands at 9 m/s or slower (vertical); the main section also
  within the prompt's landing limit plus 15% slack (never above 9 m/s); a
  section without recovery (a spent booster) at 25 m/s or slower. The
  vertical landing speed is downward and positive: a landed section reported
  at 0 m/s or moving up is an odd reply and counts as unknown (3), never as a
  soft landing

Credit = `1 / (1 + pad violation + the worst flight's violations)`. Any number
a rule needs that the reply leaves out counts as 3, never as a pass.

### Stage 7: targets (`targets.py`)

`t` is the weighted mean of one credit per stated target, read from the
1x-wind flight. Each target has a kind:

* `about`: full credit within the tolerance, then `1 / (1 + d / 0.25)` where
  `d = |ln(value / target)| - ln(1 + tol)`. Credit never reaches zero, so twice
  off always beats four times off.
* `max` / `min`: full credit on the right side of the limit, the same falling
  curve past it. A `max` landing speed also earns less below a comfort floor
  (3.5 m/s or 60% of the limit, whichever is lower), in proportion: a
  needlessly large parachute drifts far.

Apogee, flight time, time to apogee, top speed and top acceleration come from
the flight; flight time and time to apogee are measured from the first motor
ignition (`ignition_time_s` in the reply; 0 for every reference), so a rocket
that waits on the pad gains nothing. Landing speed is the main section's
vertical speed (none when it is not above 0); body diameter is the widest
main-body tube OpenRocket built (tubes in pods and side boosters do not
count); mass is the liftoff mass. `motors`
earns the share of named motors the rocket really flies; `motor_class` earns 1
for the right class letter, 0.5 for one letter off. Apogee has weight 3, every
other stated target weight 1. A missing measured value earns 0. Every target
that loses credit gets a reason with both numbers and the credit.

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
| OpenRocket rejects (`load`), cannot build (`build`), hangs on (`hang`) or crashes on (`crash`) this design or its natural twin (stage 5), or a flight cannot start or crashes, also after a retry on a fresh helper that flew the self-test rocket | score 0.40, the floor of the build stage |
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
any number of threads: each run takes one free helper. With 4 helpers an answer
takes about 0.14-0.2 s (more when many answers need a shadow flight).

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
  digest). On the 72 reference designs that wrote another version, every
  flight number is identical either way.
* every drag override (`overridecd` and its `overridesubcomponentscd` switch)
  is removed: the drag is the one OpenRocket computes. Mass and balance
  overrides stay (155 of 183 sound references weigh their kit parts); stage 5
  compares the rocket with its natural twin and bounds what they do to the
  whole rocket (mass 0.6 to 1.8 times, balance point within 1.5 calibres).
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

Stage 4 still keeps its first bounds on single overrides (never negative; at
most 20 kg and 3.66 m), as a guard before anything is flown.

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
