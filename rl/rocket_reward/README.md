# rocket_reward

The reward for training the rocket-design model with reinforcement learning (RL).

## What the reward is

The model answers a rocket request ("a rocket that reaches about 900 m on an
H motor and lands under 6 m/s") with a design: an OpenRocket document written
as JSON inside `<design> ... </design>`. The reward turns that answer into one
number from 0 to 1. It climbs a ladder of seven checks in a fixed order, from
"is there a readable design at all" to "did it reach the asked-for height". The
design gets a score inside the band of the first check it fails, so getting
further always scores more, and how close it came decides where in the band it
lands. To judge the later checks the reward builds and flies the design in
OpenRocket 24.12 itself, under launch conditions the model cannot change, in
three winds. The rules are the contract in [DESIGN.md](DESIGN.md).

## The ladder

| # | stage | score band | passes when |
|---|---------|-------------|----------------|
| 1 | format  | 0.00 - 0.08 | the answer holds a readable design tree |
| 2 | parts   | 0.10 - 0.18 | the eight parts every rocket needs are there |
| 3 | motor   | 0.20 - 0.28 | every motor is a real one (from OpenRocket's list) |
| 4 | limits  | 0.30 - 0.38 | sizes, counts and materials are physically sensible |
| 5 | build   | 0.40 - 0.48 | OpenRocket builds it and the parts fit together |
| 6 | flight  | 0.50 - 0.68 | it flies safely in every wind |
| 7 | targets | 0.70 - 1.00 | it does what the prompt asked |

Stages 1-4 are plain Python and need no Java. Stages 5-7 need Java and the
OpenRocket jar.

## Set-up

You need Python 3.10 or newer (the reward uses only the standard library;
the tests also need pytest: `python -m pip install pytest`), a Java 17 JDK (a
development kit with `javac`, not only a runtime) and the OpenRocket 24.12 jar.
Run every command from the folder that holds `rocket_reward` (the repository
root). A Python script of your own that imports `rocket_reward` must also run
from there (`python my_script.py` with the script in that folder), or set
`PYTHONPATH` to that folder; otherwise Python says
`No module named 'rocket_reward'`.

**Windows**

1. Install Python 3.10+ from https://www.python.org (tick "Add to PATH").
2. Install a JDK 17, for example Eclipse Temurin 17 from https://adoptium.net.
3. Get the jar: `python -m rocket_reward fetch-jar`. It downloads
   `OpenRocket-24.12.jar` from the official OpenRocket GitHub release into
   `rocket_reward\lib\`, checks its SHA-256 and refuses any other file.
4. Tell the reward where Java is (PowerShell; use the JDK folder that holds
   `bin`, usually a `jdk-17...` folder under `Program Files\Eclipse Adoptium`):
   `$env:ROCKET_REWARD_JAVA_HOME = "<that folder>"`. To keep it, set it under
   "Edit environment variables for your account" instead.
   If the jar is somewhere else than `rocket_reward\lib\`, also set
   `$env:ROCKET_REWARD_JAR` to the full path of the jar.
5. `python -m rocket_reward check`

**macOS**

1. Install Python 3.10+ (https://www.python.org or `brew install python`).
2. Install a JDK 17 (`brew install --cask temurin@17`, or the installer from adoptium.net).
3. `python3 -m rocket_reward fetch-jar`
4. `export ROCKET_REWARD_JAVA_HOME=$(/usr/libexec/java_home -v 17)`, and
   `export ROCKET_REWARD_JAR=/path/to/OpenRocket-24.12.jar` if the jar is not in `rocket_reward/lib/`.
5. `python3 -m rocket_reward check`

**Linux**

1. Install Python 3.10+ (`sudo apt install python3` or your distribution's package).
2. Install a JDK 17 (`sudo apt install openjdk-17-jdk`, or Temurin 17).
3. `python3 -m rocket_reward fetch-jar`
4. `export ROCKET_REWARD_JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64` (the
   folder that holds `bin/java`), and `ROCKET_REWARD_JAR` as on macOS if needed.
5. `python3 -m rocket_reward check`

Without `ROCKET_REWARD_JAVA_HOME` the reward also tries `JAVA_HOME`, then
`java` on the PATH; without `ROCKET_REWARD_JAR` it looks in `rocket_reward/lib/`.
`check` prints the Java and jar it found, starts the simulator helper, flies a
built-in self-test rocket and ends with `READY`, or prints `NOT READY:` and what
to fix. The jar folder `rocket_reward/lib/` is in `.gitignore`: never commit
the jar. The first run compiles a small Java helper into your user cache folder
(set `ROCKET_REWARD_CACHE` to put it elsewhere).

## Scoring one answer in Python

```python
import gzip, json
from rocket_reward import Requirements, score

# a sample answer and its requirements, from the files the tests use
row = json.loads(gzip.open("rocket_reward/tests/data/gold_val.jsonl.gz", "rt", encoding="utf-8").readline())
records = json.load(open("rocket_reward/tests/data/model_val_requirements.json", encoding="utf-8"))
result = score(row["answer"], Requirements.from_dict(records[row["id"]]))
print(result.score, result.stage, result.reasons)        # 1.0 targets []

# your own request: answer_text is the model's whole reply
req = Requirements.from_dict({"id": "my-1", "apogee_m": {"value": 900, "kind": "about"},
                              "landing_ms": {"value": 6, "kind": "max"}, "motors": ["H128W"]})
result = score(answer_text, req)
```

`tests/data/model_val.jsonl.gz` holds 48 model answers (in `"content"`) for
the same ids, if you want answers that fail.

The first call starts a shared pool of simulator helpers (a few seconds). For
many answers use one pool and `score_many`, which keeps the input order:

```python
from rocket_reward.scoring import score_many
from rocket_reward.sim import SimPool

with SimPool(4) as pool:                  # 4 helpers: about 0.15-0.3 s per answer once warm
    results = score_many(answers, requirements_list, simulator=pool)
```

`preflight(answer_text)` runs stages 1-4 only and needs no Java. The fields a
requirements record may hold are in DESIGN.md section 4 and `records.py`.

## Scoring a file from the command line

```
python -m rocket_reward score answers.jsonl requirements.json [--json] [--workers 4]
```

`answers.jsonl` (or `.jsonl.gz`) has one answer per line with an `"id"` and
the answer in `"content"`, `"answer"` or the last assistant message of
`"messages"`; `"truncated": true` marks an answer that ran out of tokens.
Each answer is matched with its requirements by id: the requirements file is
a `.json` holding `{id: record}`, a list of records or one record for every
answer, or a `.jsonl` of rows with `"id"` and `"requirements"` (like
`prompts/rl_prompts_v1.jsonl`). The table shows each answer's stage, score and
first reason, then the count per stage; `--json` prints every answer's stage,
score, reasons, defects, flight numbers and shadow flight as JSON. Example
with the files the tests use (about 25 s with Java, starting the helpers
included; without Java it stops with
a setup error once an answer reaches stage 5):

```
python -m rocket_reward score rocket_reward/tests/data/model_val.jsonl.gz rocket_reward/tests/data/model_val_requirements.json
```

`python -m rocket_reward preflight FILE.jsonl` runs stages 1-4 on a file with no Java.

## Using it in training

* The trainer adapter (TRL / Unsloth GRPO) and
  the settings to use are in [adapters/README.md](adapters/README.md).
* The prompts to train on, with their requirements, are
  `prompts/rl_prompts_v1.jsonl`; [prompts/README.md](prompts/README.md) says how
  they were made and which split and family flags to respect.

## Reading a result

`score` returns a `Result` (`records.py`):

* `score`: 0 to 1. `None` means the reward itself hit an unexpected error on
  this answer: it was saved to the quarantine folder and must be left out of
  training (the adapters do this for you).
* `stage`: where scoring stopped (`format` ... `targets`; `targets` means every
  gate passed). `stages_passed` counts the passed stages, 0 to 7.
* `reasons`: plain sentences saying what failed and by how much, for example
  "motor 'A8' is 18 mm wide but the inside of its mount ... is 4.9 mm".
  For an answer that reached `targets`, a reason for every target that lost credit.
* `defects`: small problems that did not stop the ladder; each costs 5% of the
  credit (at most 50%).
* `metrics`: the numbers of the 1x-wind flight when the design was flown.
* `flags`: extra facts: `truncated`, `shadow` (for an unknown motor: the real
  motor it was flown with instead and how far that got), `clean_notes` (what the
  cleaning changed), `overrides_removed` (how many override settings the
  cleaning removed, when there were any), `stage_info` (the stopping stage's
  own numbers), `quarantined`.

## When it stops with a setup error

`RewardSetupError` means the machine is not ready, never that the answer is
bad, so it is raised instead of returning a score. The message says what to
fix: Java missing or older than 17, a runtime without `javac`, the jar missing
or not the pinned file, a data file missing, the self-test rocket flying
wrongly, `ROCKET_REWARD_WORKERS` not a whole number, or too many answers
crashing the reward (more than 1% of the last 500, or 5 in a row). Fix it, run
`python -m rocket_reward check` until it says `READY`, then start again.
Command-line exit codes: 0 done, 1 `fetch-jar` could not get the right file, 2
a usage or file problem, 3 a setup error.

## Running the tests

From the repository root:

```
python -m pytest rocket_reward/tests -q -p no:cacheprovider
```

Without Java the 97 tests marked `needs_java` are skipped, and the other
2,277 run in a little over a minute. With `ROCKET_REWARD_JAVA_HOME` and
`ROCKET_REWARD_JAR` set (or the jar in `rocket_reward/lib/`) all 2,374 run, in
about three minutes (times measured on 2026-11-19 on a PC shared with other
jobs). Four tests of the prompt data and the reference designs also need
`ROCKET_REWARD_PROMPT_META` set to the reference meta file
(`sft_v5_meta_c94ffa5.jsonl`); they are skipped without it.

## Adding a rule

1. The number goes in `limits.py` (a physical limit, with a one-line note on
   where it comes from: which reference value it clears and by how much) or in
   `ladder.py` (only if it shapes the score itself, such as a band or a credit).
   No other file holds a tuning number.
2. The check goes in the stage's own file: `limit_checks.py` (stage 4, the
   design tree), `fit.py` (stage 5, the positions OpenRocket reports), `flight.py`
   (stage 6) or `targets.py` (stage 7). Use the violation helpers already there
   (`over_limit` / `under_limit` in `ladder.py`), and write a reason that says
   what is wrong, by how much, and what to change. If the rule needs a number
   OpenRocket does not report yet, add the field in `java/RocketSim.java`,
   raise its `HELPER_VERSION` and describe the field in `java/PROTOCOL.md`
   (the pod rules added `axis_offset_m` this way, helper version 4).
3. Copy a test next to a similar rule: in `tests/test_limits.py` (for example
   `test_launch_lug_and_rail_button_counts` and `test_more_lugs_never_score_better`),
   `tests/test_fit.py` (`test_tube_fins_past_the_back_of_their_part`) or
   `tests/test_flight.py`. Test just under the limit, a little over and far
   over, and that a smaller violation never scores lower. A rule judges the
   cleaned design, which never holds an override setting, so it needs no
   exception for one.
4. If it blocks a cheat, add an operator to `tools/mutate.py` that says what
   the reward must do with it (stop at a given stage, score the same, or stay
   in the targets stage and score lower) and re-make
   `tests/data/mutation_expected.json` (the command is in `tests/test_mutations.py`).
5. Re-run the calibration and check that no sound reference moved:
   `python -X utf8 -m rocket_reward.tools.calibrate --meta sft_v5_meta_c94ffa5.jsonl --prompts parsed_prompts.jsonl --out calib.md --json calib.json`
   (Java needed). The two input files are the reference rows and what each
   prompt states; they are not in this package (ask the data owners), so give
   their full paths.
   If the model answers move, regenerate `tests/data/model_val_scored.json` on
   purpose and say why in `tests/test_model_scores.py`. If a reference changes
   stage, rebuild the RL prompts (below) and update REFERENCE_ROCKETS.md.
   Update DESIGN.md.

## Rebuilding the data files

* Motor table (`data/motor_table.json`), whenever the OpenRocket jar changes:
  `python -X utf8 -m rocket_reward.tools.build_motor_table --out NEW.json --rescue-by-curve`,
  then check it and copy it over the packaged one (the tool's docstring has the details).
* Material table (`data/material_table.json`):
  `python -m rocket_reward.tools.build_material_table --java-home JDK_FOLDER --jar OpenRocket-24.12.jar --gold train.jsonl val.jsonl test.jsonl --model-answers rocket_reward/tests/data/model_val.jsonl.gz --out rocket_reward/data/material_table.json --report material_report.md`
  (`--gold` takes the `sft_v5` training files).
* RL prompts (`prompts/`), after any change to a limit or the ladder (Java
  needed; about 2 minutes):
  `python -X utf8 -m rocket_reward.tools.build_rl_prompts --meta sft_v5_meta_c94ffa5.jsonl --out-dir rocket_reward/prompts`.
  It also rewrites `prompts/README.md`. The requirements it starts from come
  from `tools/build_requirements.py`.

Every tool prints its arguments with `--help`.

## Known limits and things not done

* Cost is not scored: a design that uses an expensive motor or many parts is not penalised for it.
* Wind is one speed at every height (three flights at 0.5, 1 and 1.5 times the
  prompt's wind); wind that changes with height is not modelled.
* One answer with many parts and a long descent (huge parachutes) can take
  far longer than the usual fraction of a second. A run that takes longer
  than the helper's wall-clock limit (30 s plus 10 s per flight, `sim.py`) is
  tried once more on a fresh helper, and if it is still stuck it scores 0.40,
  the floor of the build stage. Set trainer timeouts with that in mind.
* 38 of the 197 reference designs (114 of the 594 rows) do not pass, and 1 more
  (3 rows) passes with a defect; [REFERENCE_ROCKETS.md](REFERENCE_ROCKETS.md)
  lists them for the data owners. The RL prompt file leaves them out.
* The stage 6 limits were measured on the references with their own written
  densities and their mass overrides, while the reward flies the material
  table's densities and no overrides (see the V4-0171 note in
  REFERENCE_ROCKETS.md).
* Override settings (`overridemass`, `overridecg`, `overridecd` and their
  `overridesubcomponents` switches) are removed, so a design is scored without
  the overrides it writes. To add mass, add a mass component. Six reference
  designs pass only with their overrides and now fail (REFERENCE_ROCKETS.md,
  "Sound only with their overrides").
* A mass component written as a point (length or radius 0) is not
  density-checked, so heavy nose ballast is accepted as real mass. Moving
  V4-0205's 12.69 kg point mass to the nose tip raises its stability from
  2.18 to 5.12 calibres and still scores 0.835.
* Inner tubes, tube couplers and centering rings may have zero wall thickness
  and then weigh nothing. A minimum would fail sound references (33 inner
  tubes and 15 couplers in the references have a 0 wall once their overrides
  are removed).
* A wrong named motor only halves the targets credit (`ladder.MOTORS_CREDIT_MIN`),
  so flying another real motor can pay when the named one would miss an
  `about` apogee target by more than about 1.35 times (`ladder.closeness`
  gives 0.4987 there, under the swap's 0.5). With both `motors` and
  `motor_class` stated and the class two or more letters away, the swap earns
  0.25 and pays only past about 2.2 times (0.2503 there).
* A landing faster than the prompt asks but under 9 m/s now stays in the
  targets stage with a lower score, where it used to stop at flight: 1% over
  a limit given with tolerance 0 scores 0.9885, twice the limit 0.7795, and a
  rocket asked for at most 3 m/s (tolerance 0) that lands at 8.9 m/s 0.756.
* Any rocket that flies safely in every wind still scores at least 0.70,
  however far it misses the targets: on the 400 designs of the review's
  attack search, the
  57 that miss the apogee by more than 50% score 0.702-0.806.
* A pod or side booster may stand up to 100 mm clear of the body beside it
  (`limits.POD_GAP_MAX_M`; V4-0112's pods stand 50.8 mm off), and up to about
  1.41 times that with only a defect. Nothing checks that a strut joins it to
  the body.
* A pod or side booster may reach past the ends of the main body of its stage
  by up to a third of its own length (`limits.POD_OVERHANG_MAX_FRACTION`), and
  with only a defect up to a share of about 0.47, so strap-on boosters that
  end a little below the core pass: V4-0107's boosters (0.1715 m long) moved
  0.08 m aft score 0.9837 with a defect.
* The 50 m floor for an opening reads only the altitude a device is set to,
  not where it really opens. A device timed by a delay (an ALTITUDE setting of
  183-457 m plus a deploy delay, or APOGEE plus a delay) can really open 20-40 m
  up while falling at 25-46 m/s and still pass, as long as it opens 3 s
  before landing. V4-0086 (25.9 kg) with its main at ALTITUDE 213 m plus a
  7.31 s delay opens at 24.9 m/s, 3.35 s before landing, about 30-40 m up, and
  scores 1.0; it ties the honest version with the main set to 50 m (1.0) and
  never beats it. 28 reference designs can do this (measured on the second
  round's code; the third round changed no stage 6 rule). Closing it needs the
  helper to report the height of every opening (a new field and a new helper
  version), so that the floor can be applied to the real height of each
  section's last opening.
* A weight of the top stage placed far down in the booster is impossible (it
  sits inside the booster's airframe but stays with the top stage at
  separation) but is not caught,
  because reaching back into the stage behind is judged only against the
  whole airframe. It gains nothing: V4-0139 scores 0.9998 against 0.9991 for
  the honest weight in the nose, and on four other designs it fails flight.
* Pods beside a nose cone or transition were not tried in the attacks. By
  reading the code only: `pod_inside_body` and `pod_detached` use the largest
  radius the main body has along the pod's own length, and read a nose cone
  or transition along a straight line between its two end radii, so beside a
  curved nose the gap is judged a little generously.

Holes found by the 2026-11-19 attacks on the fixed version and left open
(DESIGN.md section 7 has the ones that were closed; the numbers below were
measured before the second round's rules were added):

* A nose cone or transition shoulder wider than the rocket is not checked.
  It is a solid disk outside the airframe with no drag: V4-0049 (0.594,
  flight) scores 1.0 with a solid nose shoulder 1.5 times the body radius, and
  a transition shoulder does the same (V4-0057 0.971 to 1.0). Left because it
  gains nothing over honest nose ballast of the same mass (V4-0049 with a
  3-times shoulder 0.8825, with the same mass as a point weight in the nose
  0.8835), and because a rule would fail three references whose 76 mm
  shoulders sit on 25 mm noses (V4-0086, V4-0087, V4-0109).
* Adding one massless part of no size can change the simulated flight on a
  few designs: V4-0050's apogee goes from 5,832 to 5,547 m and its score from
  0.9747 to 1.0 with one such mass component (five of them give 0.9746). Apogee
  moved by more than 1% on 3 of 80 designs and on none of the next 40;
  re-scoring the unchanged designs gave no difference. This is the
  simulator's own behaviour: its result depends on the number of parts (it
  may come from the random part ids OpenRocket gives on load, which the
  helper seeds; not proven). A policy could gain about 0.025 by trying such
  parts.
* An unreadable wall value such as `"auto 0.00001"` is not judged by stage 4,
  so a design that fails limits can fail build instead and score more:
  V4-0062 goes from 0.3204 (limits) to 0.40 (build). Left because it only moves
  a failing design up one failing band, far below 0.70.
* The `motors` target gives full credit when the one named motor is flown
  twice in a cluster. With the apogee target set to what the doubled rocket
  reaches, it beats the single motor: V4-0006 (M2000R) 0.8318 against 0.797.
  Left because twice the impulse really flies (real physics); whether naming
  one motor means flying exactly one is a question for the prompts.
* A fin fillet may be up to 50 mm in radius whatever the fin height
  (`limits.FILLET_RADIUS_MAX_M`). A 50 mm fillet on every fin set lifted 11 of
  30 designs (V4-0066 0.9153 to 1.0) by adding real tail mass, which a builder
  could do; the one case where the fillet is taller than the fin (V4-0016,
  30 mm fins) failed anyway (0.559), so no absurd fillet design was found
  scoring 0.70 or more.

## Files

The code layout is in DESIGN.md section 6.
