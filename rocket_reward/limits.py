"""Every physical limit and constant: used by stages 2-7 (parts.py, motors.py,
limit_checks.py, fit.py, flight.py), clean.py, records.py and the material-table tool.

These are bounds no sound hobby rocket crosses. They exist to block trick
values (paper-thin fins, a 50x drag parachute, fins used as air brakes), not
to grade style. Each number says where it came from:

  catalog    the parts library inside OpenRocket 24.12 (1,496 body tubes,
             422 parachutes), as measured by the team's earlier reward
  reference  the 582 reference ("gold") answers in the sft_v5 train, val and
             test files; tools/calibrate_preflight.py re-checks that they pass
  contract   the project's design contract
  OpenRocket a limit OpenRocket itself applies

A limit may fail a reference design only when that design is truly broken.
The reference designs that fail, and why, are listed at the end of this file.
Lengths are in metres, masses in kilograms, angles in degrees, impulse in
newton-seconds.
"""
from __future__ import annotations

# ---------------------------------------------------------------- fins
FIN_COUNT_MIN = 1          # OpenRocket: a fin set has at least one fin
FIN_COUNT_MAX = 8          # OpenRocket's fin count menu stops at 8; references use 1-8
FIN_COUNT_WHOLE_TOLERANCE = 1e-6  # a fin count this close to a whole number is that number (3.0000001 fins is 3)
FIN_CANT_MAX_DEG = 15.0    # OpenRocket allows +-15 deg; references use at most 4.0 deg
FIN_THICKNESS_MIN_M = 0.0005   # thinnest real reference fin is 1.0 mm; 0.5 mm blocks razor-fin tricks
FIN_SPAN_PER_DIAMETER_MAX = 4.0  # references: p95 1.84, max 3.43 (fin height / diameter of the tube it sits on); fins 5-10x the body were an air-brake cheat
FIN_CHORD_MAX_M = 1.0      # longest reference root chord is 0.495 m; twice that
FIN_POINTS_MAX = 100       # most points in a reference freeform fin is 45; about twice that
FIN_POINT_COORD_MAX_M = 1.0    # reference fin points lie within x -0.019..0.47 m, y -0.019..0.20 m
FIN_AREAL_DENSITY_MIN_KG_M2 = 0.12  # fin thickness x table density; lightest sound reference fin is 0.27 kg/m2 (1/16 inch balsa); 1/32 inch balsa is 0.135; blocks foam-film fins (0.5 mm EPS is 0.01)
TUBE_FIN_RADIUS_PER_BODY_MAX = 1.0  # tube fin radius over the radius of the body it sits on; the one sound reference uses "auto" (the body's own size); 3-5 times was an air-brake trick

# ---------------------------------------------------------------- outer shell
TUBE_RADIUS_MIN_M = 0.0025     # catalog: the narrowest body tube is 5 mm wide (narrowest real reference tube: 13.7 mm)
TUBE_RADIUS_MAX_M = 0.15       # catalog: the widest body tube is 300 mm (widest reference: 203 mm)
TUBE_LENGTH_MAX_M = 3.66       # catalog: two of the longest tube (1.83 m); longest reference tube is 1.9 m
WALL_MIN_M = 0.00013           # catalog: thinnest real tube wall; thinnest real reference wall is 0.14 mm. The word "filled" is a solid part; a 0 mm wall passes only on a part whose mass is overridden
NOSE_LENGTH_MAX_M = 2.0        # longest reference nose cone is 0.93 m; about twice that
TRANSITION_LENGTH_MAX_M = 1.5  # longest reference transition is 0.61 m; about twice that
SHELL_RADIUS_MAX_M = TUBE_RADIUS_MAX_M  # nose cones and transitions match the widest catalog tube (widest reference: 203 mm)
WALL_AREAL_DENSITY_MIN_KG_M2 = 0.045  # wall thickness x table density of a body tube, nose cone, transition or tube fin; lightest sound reference is 0.095 kg/m2 (0.14 mm cardboard); about half. Blocks foam-film shells (0.13 mm EPS is 0.0026)

# ---------------------------------------------------------------- recovery
CHUTE_DIAMETER_MIN_M = 0.15    # catalog: smallest parachute 0.15 m (smallest reference: 0.20 m)
CHUTE_DIAMETER_MAX_M = 6.1     # catalog: largest parachute 6.1 m (largest reference: 4.57 m)
CHUTE_CD_MIN = 0.6             # catalog: lowest parachute drag coefficient 0.61 (reference: 0.61)
CHUTE_CD_MAX = 2.9             # catalog: highest 2.92 (reference: 2.2); Cd 50 was the soft-landing cheat
STREAMER_LENGTH_MAX_M = 6.0    # longest reference streamer is 3.66 m; about 1.6x that
STREAMER_WIDTH_MAX_M = 0.30    # widest reference streamer is 0.15 m; twice that
STREAMER_CD_MAX = 0.6          # earlier reward's judgment; references use 0.1 or "auto"

# ---------------------------------------------------------------- mass and motors
MASS_COMPONENT_MAX_KG = 20.0   # heaviest reference mass component is 12.7 kg; 20 kg is the earlier reward's size bound
TOTAL_IMPULSE_MAX_NS = 40960.0 # contract: the top of the O class; largest reference total is 22,224 Ns
CLASS_A_MAX_NS = 2.5           # standard model-rocketry classes: A is up to 2.5 Ns and each next letter doubles it (B 5 Ns, C 10 Ns ...)
MOTOR_DIAMETER_MATCH_M = 0.0005  # stage 3: two motor diameters within 0.5 mm are the same size; real sizes are at least 2 mm apart (10.5, 13, 18, 24 mm ...)

# ---------------------------------------------------------------- mass, balance and drag overrides
# The model may override a part's mass and balance point (CG). These keep the
# overrides physical; stage 5 bounds their effect on the whole rocket (section
# "fit (stage 5)"). A negative value is always broken. 0 is allowed: references
# write overridemass 0 on 225 parts. Drag overrides are removed by the cleaning
# (clean.py), so OVERRIDE_CD_MAX only judges a tree checked without cleaning.
OVERRIDE_MASS_MAX_KG = 20.0    # reference: heaviest single part 4.85 kg, heaviest whole stage 14.0 kg; same bound as a mass component
OVERRIDE_CD_MAX = 1.0          # reference: largest drag override 0.422 (a whole stage); about twice that
OVERRIDE_CG_MAX_M = TUBE_LENGTH_MAX_M  # reference: largest CG override 0.889 m from the part's front; never more than the longest tube

# ---------------------------------------------------------------- material densities
# The cleaning gives every material the table knows its table density, so these
# bounds judge only names the table does not know (stage 4 also fails such a
# name). A part whose own mass is overridden does not use its material's density.
BULK_DENSITY_MIN_KG_M3 = 10.0      # earlier reward's bound (light foam is ~15 kg/m3); lowest sound reference 40.8 kg/m3
BULK_DENSITY_MAX_KG_M3 = 25000.0   # earlier reward's bound; densest element is 22,600 kg/m3, densest reference 8,906 kg/m3
SURFACE_DENSITY_MAX_KG_M2 = 5.0    # earlier reward's bound; heaviest reference canopy 0.18 kg/m2 (0 is used 42 times)
LINE_DENSITY_MAX_KG_M = 1.0        # earlier reward's bound; heaviest reference line 0.116 kg/m (0 is used 285 times)
# Lowest physical surface and line densities, used when the material table is
# built (tools/build_material_table.py). Stage 4 does not use them yet.
SURFACE_MIN_KG_M2 = 0.001          # OpenRocket's lists: lightest real cloth is 0.30 mil HDPE film at 0.00705 kg/m2; about seven times below it, so only unit slips fail (references write cloth at 1e-7 kg/m2)
LINE_MIN_KG_M = 0.00001            # OpenRocket's lists: lightest real line is size 23 Kevlar thread (0.15 mm) at 0.0000198 kg/m; half of it, so only unit slips fail

# ---------------------------------------------------------------- launch conditions
DEFAULT_WIND_MS = 2.0          # contract: the wind used when the requirements state none (DESIGN.md, stage 6)

# ---------------------------------------------------------------- component types
# Every component type the 582 reference designs place inside a "subcomponents"
# list. Anything else is an invented type and fails stage 4.
KNOWN_COMPONENT_TYPES = frozenset({
    "stage", "parallelstage", "podset",
    "nosecone", "bodytube", "transition", "tubecoupler", "innertube",
    "centeringring", "bulkhead", "engineblock", "launchlug", "railbutton",
    "trapezoidfinset", "ellipticalfinset", "freeformfinset", "tubefinset",
    "parachute", "streamer", "shockcord", "masscomponent",
})

# ---------------------------------------------------------------- part counts and small outside parts
# OpenRocket's time per design grows faster than the number of parts, and small
# outside parts (launch lugs, rail buttons) have no other bound, so many or
# large ones were a way to add drag or to make one answer take a minute.
COMPONENTS_MAX = 100           # parts in one design (every component inside the rocket); reference: at most 73 in the 582 SFT rows, but the 594-row meta file also has V4-0172 (134), V4-0167 (124), V4-0165 (88) and V4-0168 (78), so V4-0167 and V4-0172 fail this cap (lowered from 150 on 2026-11-19 to bound slow answers; the owner should confirm). Simulation time grows with the part count, so the cap also bounds how long one answer can take
PART_INSTANCES_MAX = 8         # copies of one part ("instancecount", fin sets excepted: they have FIN_COUNT_MAX); reference: at most 2 (rail buttons, pods, side boosters)
LAUNCH_LUG_COUNT_MAX = 8       # launch lugs in one design, copies counted; reference: at most 4
RAIL_BUTTON_COUNT_MAX = 8      # rail buttons in one design, copies counted; reference: at most 3 parts of up to 2 copies
LAUNCH_LUG_RADIUS_MAX_M = 0.02     # reference: widest lug 9.6 mm in radius; about twice
LAUNCH_LUG_LENGTH_MAX_M = 0.3      # reference: longest lug 0.152 m; about twice
RAIL_BUTTON_DIAMETER_MAX_M = 0.04  # reference: widest rail button 20 mm across; twice
RAIL_BUTTON_HEIGHT_MAX_M = 0.03    # reference: tallest rail button 14.2 mm; about twice

# ---------------------------------------------------------------- launch conditions (stage 6)
# The reward sets every launch condition itself. Each design is flown three
# times, in WIND_FACTORS times the wind the requirements state.
WIND_FACTORS = (0.5, 1.0, 1.5)     # a design must be safe in half and in one and a half times the stated wind
WIND_MAX_MS = 8.94                 # contract: 20 mph, the highest wind anyone should launch in
FLIGHT_SEEDS = (1, 2, 3)           # fixed, so every answer to a prompt meets the same gusts
NOMINAL_FLIGHT = 1                 # index of the 1x-wind flight; targets are read from it
# Launch rail length by the impulse class of the largest single motor, as launch
# sites do. One 1.5 m rail for every rocket made 44 of 163 real rockets leave it
# too slowly (earlier reward's measurement); larger rockets need more rail.
RAIL_LENGTH_BY_CLASS_M = (("F", 1.5), ("G", 1.8), ("I", 2.4), ("K", 3.0))  # up to this class letter -> metres
RAIL_LENGTH_LARGEST_M = 3.7        # class L and above
MAX_SIM_TIME_S = 1200.0            # a flight still in the air after 20 simulated minutes is stopped
MAX_SIM_STEPS = 400000             # backstop so a runaway simulation ends the same way on any machine

# ---------------------------------------------------------------- flight safety (stage 6)
# Measured by flying the 183 reference designs that pass stages 1-5 under the
# launch conditions above (calibration report: flight statistics). A limit is
# set so that sound references pass and only truly unsafe ones fail.
RAIL_EXIT_MIN_MS = 11.0            # 15 m/s (contract) fails 14 references, 12 of them otherwise sound and most of them small (an A8 rocket leaves at 11.6); one reference is below 11 (9.0, and it weathercocks)
STATIC_STABILITY_MIN_CAL = 1.0     # contract. Flown as the reward flies them (table densities), every reference that reaches this stage has at least 1.0 cal except one (V4-0171: 0.973 cal; it had 1.02 with the densities its file wrote), which is left failing rather than loosening the contract
RAIL_STABILITY_MIN_CAL = 0.0       # leaving the rail in the worst wind: the margin moves by a median 0.48 cal across the three winds, so 1.0 here fails 31 references, 29 of them sound; the other two are below 0 and truly unstable
BURN_STABILITY_MIN_CAL = 0.0       # contract: stable from the rail to the last burnout; four references fail (two air-start a second stage after a 9 s coast)
THRUST_TO_WEIGHT_MIN = 3.0         # contract; lowest reference is 3.08
DEPLOY_SPEED_MAX_MS = 60.0         # references open recovery at a median 7.7 m/s, 95% under 36; the two above 60 use a 0 s ejection delay (68 and 99 m/s). OpenRocket itself warns from 20 m/s
LANDING_HARD_MAX_MS = 9.0          # vertical speed of any section that has a recovery device; fastest reference is 8.93 m/s
LANDING_SLACK_DEFAULT = 0.15       # slack on a prompt's landing limit when the requirements give none: prompts were written from one flight with no margin (worst reference: 1.117x)
UNRECOVERED_LANDING_MAX_MS = 25.0  # a spent booster with no recovery device tumbles down at up to 20.6 m/s in sound references; nine references drop theirs nose-first at 52-64 m/s (1.3-3.6 kJ)

# ---------------------------------------------------------------- fit (stage 5)
# Measured on OpenRocket's own placement of every part in the reference designs.
SHELL_STEP_MAX_FRACTION = 0.10         # change in outer radius between neighbouring shell parts of one stage, as a share of the larger; 98% of references are under 3.4%, the three above 10% are broken (one is the base-drag trick)
SHELL_STEP_BETWEEN_STAGES_MAX_FRACTION = 0.15  # between stages; largest reference step is 14.3%
FIN_PAST_BACK_MAX_CHORDS = 0.5         # how far a fin root may run past the back end of its parent, in root chords; the four references beyond this have fins on nothing
FIN_PAST_FRONT_MAX_CHORDS = 1.0        # past the front end; 0.5 would fail two sound references
RIGID_INSIDE_RADIUS_MAX_RATIO = 1.08   # rings, bulkheads, engine blocks, inner tubes, couplers: outer radius over the inner radius of the airframe around them; the two references above are 15% and 23% too wide
SOFT_INSIDE_RADIUS_MAX_RATIO = 1.30    # parachutes, streamers, shock cords, mass parts (packed size is approximate); one reference is at 1.64
MOTOR_TUBE_BEHIND_TAIL_MAX_M = 0.05    # how far a motor tube may stick out behind the airframe; one reference: 0.25 m
RING_OUTSIDE_AIRFRAME_MAX_M = 0.02     # rings, bulkheads, engine blocks outside the airframe; one reference: 0.034 m
MOTOR_DIAMETER_MAX_RATIO = 1.05        # motor diameter over its mount's inner diameter; largest reference 1.044
MOTOR_OVERHANG_MAX_FRACTION = 0.5      # share of the motor's length hanging out behind its mount; one reference: 0.88
FIN_SETS_SAME_ANGLE_DEG = 2.0          # two fin sets on one part overlapping within this angle are the same fins twice; 15 references interleave sets at other angles, which is fine
RING_OVERLAP_MAX_M = 0.0035            # two rings, bulkheads or engine blocks pushed into each other; references touch by up to 3.2 mm, one overlaps 10.5 mm
# What mass and balance overrides may do to the whole rocket, compared with the
# same rocket without them. 155 of 183 references use overrides (kit parts are
# weighed), and removing them changes 31 references a lot, so they stay; but an
# override must adjust the rocket, not replace its physics.
OVERRIDE_MASS_RATIO_MIN = 0.6          # liftoff mass with overrides over without; references span 0.66-1.77
OVERRIDE_MASS_RATIO_MAX = 1.8
OVERRIDE_CG_SHIFT_MAX_CAL = 1.5        # how far overrides may move the balance point, in calibres, either way; sound references span -1.45 to +1.5, two use an override as nose ballast (+2.9, +3.4)
# Added 2026-11-19 after the stage 5-7 review (each one measured on OpenRocket's
# placement of the reference parts, gold_flights.jsonl, as-written variant):
MOTOR_AHEAD_OF_TAIL_MAX_M = 0.15       # how far the back end of a motor may sit ahead of the back end of its stage's airframe; sound references: at most 0.12 m (one), the rest under 0.05 m; the two beyond 0.2 m are broken (0.24, 0.60)
POD_RADIUS_PER_BODY_MAX = 1.0          # outer radius of a pod or side-booster shell over the main body's widest radius; sound references at most 0.59; the one at 0.99 is broken (shell step)
# The same OVERRIDE_MASS_RATIO_MIN is also applied to each stage's structure
# (its parts without motors): sound references span 0.603-1.84 (lowest
# 0.603), and a sustainer overridden to 23% of its mass hid behind a heavy booster.

# ---------------------------------------------------------------- reference designs that fail
# Measured on all 582 sft_v5 gold answers (train-N, val-N and test-N are line
# numbers, from 0, in the sft_v5 train, val and test files; each rocket appears
# in three rows, asked three ways). 567 of 582 pass (2026-11-19, with table
# densities and material names checked). The 15 failures are five rockets,
# each with a part that would fly far thinner than any real one:
#   train-111..113  freeform fins 0.0003 mm thick (a unit slip in the source file)
#   train-207..209  freeform fins 0.08 mm thick
#   test-9..11      trapezoid fins 0.1 mm thick
#   train-288..290  a body tube 0.025 mm wide
#   train-18..20    a 0.64 m fiberglass body tube with a 0 mm wall and no mass override (weightless)
# Two rockets that failed only on a slipped density now pass, because the
# cleaning gives every known material its table density: train-81..83 (an
# engine block of "Paper, bulk" written 0.0011 kg/m3, now 820) and test-33..35
# (fins of "RS: G10 (PML 0.093)" written 0.0071 kg/m3, now 1,905).
# No name in the 582 sft_v5 answers is unknown to the material table; the nine
# "RS:" shroud lines (three rockets) name no material and are removed by the
# cleaning, so OpenRocket uses its default line there. (The 594-row prompt
# file has one more rocket, V4-0172, which names the material "Custom" and
# stops here; it is broken at stage 5 too.)
# Three rockets with paper-thin transition walls (train-60, -276, -282) pass:
# those transitions override their mass, so the wall changes nothing.
# All 48 val rows (tests/data/gold_val.jsonl.gz) pass.
# The model's 48 saved answers: 2 now stop here on unknown material names
# (row-009, row-027); see tests/test_model_answers.py.
# Re-check with: python -m rocket_reward.tools.calibrate_preflight train.jsonl val.jsonl test.jsonl
# The whole ladder (stages 1-7, with Java): python -m rocket_reward.tools.calibrate --meta ... --prompts ...
# Passing the five would reopen the razor-fin (0.1 mm), paper-tube and
# zero-wall tricks the limits exist to block.
