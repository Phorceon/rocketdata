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
FIN_ROOT_CHORD_MIN_M = 0.002  # trapezoid and elliptical fins; smallest reference root chord is 3 mm (V4-0002 and V4-0172, both broken elsewhere), smallest sound one 27.9 mm; a root of 0 is a fin attached to nothing
FIN_HEIGHT_MIN_M = 0.002       # trapezoid and elliptical fins; smallest reference span is 8.9 mm (V4-0172), smallest sound one 15.9 mm
FIN_TIP_PER_ROOT_MAX = 3.0     # trapezoid tip chord over root chord; references at most 1.14, so a wide fin hanging from a short root is about 2.6 times past any of them
FIN_SWEEP_MAX_M = FIN_CHORD_MAX_M  # fin sweep length, either way; references 0 to 0.356 m
FIN_TAB_HEIGHT_MAX_M = 0.15    # fin tab height; references at most 68.8 mm; about twice (tab length is bounded by FIN_CHORD_MAX_M; references at most 0.47 m)
FILLET_RADIUS_MAX_M = 0.05     # fin fillet radius; references at most 25.4 mm; about twice

# ---------------------------------------------------------------- outer shell
TUBE_RADIUS_MIN_M = 0.0025     # catalog: the narrowest body tube is 5 mm wide (narrowest real reference tube: 13.7 mm)
TUBE_RADIUS_MAX_M = 0.15       # catalog: the widest body tube is 300 mm (widest reference: 203 mm)
TUBE_LENGTH_MAX_M = 3.66       # catalog: two of the longest tube (1.83 m); longest reference tube is 1.9 m
WALL_MIN_M = 0.00013           # catalog: thinnest real tube wall; thinnest real reference wall is 0.14 mm. The word "filled" is a solid part; a 0 mm wall passes only on a part of length 0
NOSE_LENGTH_MAX_M = 2.0        # longest reference nose cone is 0.93 m; about twice that
TRANSITION_LENGTH_MAX_M = 1.5  # longest reference transition is 0.61 m; about twice that
SHELL_RADIUS_MAX_M = TUBE_RADIUS_MAX_M  # nose cones and transitions match the widest catalog tube (widest reference: 203 mm)
SHELL_RADIUS_MIN_M = 0.001    # nose cone base radius; smallest reference 2.4 mm (a pod nose), smallest sound one 6.9 mm. A radius of 0 is a rocket with no width: only the word "auto" takes the size of the next part
SHOULDER_LENGTH_MAX_M = 0.5    # nose cone and transition shoulders; longest reference 0.152 m; about three times (one calibre of the widest catalog tube is 0.3 m)
SHAPE_PARAMETER_MAX = 1.0      # top of OpenRocket's range for a nose cone or transition shape parameter (a negative one is a negative size); references use 0 to 1
WALL_AREAL_DENSITY_MIN_KG_M2 = 0.045  # wall thickness x table density of a body tube, nose cone, transition or tube fin; lightest sound reference is 0.095 kg/m2 (0.14 mm cardboard); about half. Blocks foam-film shells (0.13 mm EPS is 0.0026)

# ---------------------------------------------------------------- recovery
CHUTE_DIAMETER_MIN_M = 0.15    # catalog: smallest parachute 0.15 m (smallest reference: 0.20 m)
CHUTE_DIAMETER_MAX_M = 6.1     # catalog: largest parachute 6.1 m (largest reference: 4.57 m)
CHUTE_CD_MIN = 0.6             # catalog: lowest parachute drag coefficient 0.61 (reference: 0.61)
CHUTE_CD_MAX = 2.9             # catalog: highest 2.92 (reference: 2.2); Cd 50 was the soft-landing cheat
STREAMER_LENGTH_MAX_M = 6.0    # longest reference streamer is 3.66 m; about 1.6x that
STREAMER_WIDTH_MAX_M = 0.30    # widest reference streamer is 0.15 m; twice that
STREAMER_CD_MAX = 0.6          # earlier reward's judgment; references use 0.1 or "auto"
PACKED_LENGTH_MAX_M = 1.5      # packed length of a parachute, streamer, shock cord or mass component; references at most 0.70 m (a mass component; shock cord 0.67, parachute 0.61); about twice
PACKED_RADIUS_MAX_M = TUBE_RADIUS_MAX_M  # packed radius; references at most 95 mm; the widest catalog tube's radius
LINE_LENGTH_MAX_M = 8.0        # parachute shroud lines; references at most 3.66 m; about twice
CORD_LENGTH_MAX_M = 25.0       # shock cord length; references at most 12.8 m; about twice
LINE_COUNT_MIN = 1             # shroud lines, a whole number; references use 3 to 24
LINE_COUNT_MAX = 48            # about twice the most a reference uses (24)
DEPLOY_DELAY_MAX_S = 20.0      # recovery deployment and stage separation delay; references at most 1.5 s (separation 0.5 s); the longest motor ejection delay a reference uses is 19 s
DEPLOY_ALTITUDE_MAX_M = 3000.0 # recovery deployment and separation altitude; references at most 600 m; five times

# ---------------------------------------------------------------- mass and motors
MASS_COMPONENT_MAX_KG = 20.0   # heaviest reference mass component is 12.7 kg; 20 kg is the earlier reward's size bound
TOTAL_IMPULSE_MAX_NS = 40960.0 # contract: the top of the O class; largest reference total is 22,224 Ns
CLASS_A_MAX_NS = 2.5           # standard model-rocketry classes: A is up to 2.5 Ns and each next letter doubles it (B 5 Ns, C 10 Ns ...)
MOTOR_DIAMETER_MATCH_M = 0.0005  # stage 3: two motor diameters within 0.5 mm are the same size; real sizes are at least 2 mm apart (10.5, 13, 18, 24 mm ...)
MASS_COMPONENT_DENSITY_MAX_KG_M3 = 1.0e6  # mass over packed volume of a mass component with a size; sound references reach 462,025 (V4-0086: 5.67 kg written 25 mm long and 12.5 mm in radius; kit weights are written with a nominal size), so about twice; a 20 kg coin is 2e7. Point masses (length or radius 0, 346 reference parts) are not judged
MOTOR_DELAY_MAX_S = 30.0       # motor ejection delay; references at most 19 s
IGNITION_DELAY_MAX_S = 20.0    # motor ignition delay (the cleaning sets the bottom stage's to 0); references at most 9 s on an upper stage; about twice
CLUSTER_SCALE_MAX = 60.0       # spacing scale of a motor cluster; references at most 27.8; about twice

# ---------------------------------------------------------------- mass, balance and drag overrides
# 2026-11-19: until this date the model could override a part's mass and
# balance point, and stages 4 and 5 bounded what the overrides did (per part,
# and against the same rocket without them). A review showed a bounded override
# could still fake about 2 calibres of stability (a rocket at -0.42 cal read
# 1.07 cal and scored 1.0) and hide a too-fast landing behind a lighter stage.
# Every override setting (tag starting with "override") is now removed by the
# cleaning (clean.py) before anything judges or flies the design, so no limit
# here bounds one. Measured cost on the 161 reference designs in the prompt
# file, scored against an apogee-only requirement: 4 stop passing stages 1-6:
#   V4-0025  flight: stability leaving the rail -0.00 cal in the 6 m/s wind (needs above 0)
#   V4-0027  flight: a recovery device opens at 70.4 m/s (at most 60)
#   V4-0166  flight: 0.8 cal on the pad (at least 1.0)
#   V4-0225  limits: a transition wall of 0.000254 mm (at least 0.13 mm), which
#            its mass override used to stand in for
# Each flies as its parts and materials make it; the override was what made it pass.

# ---------------------------------------------------------------- material densities
# The cleaning gives every material the table knows its table density, so these
# bounds judge only names the table does not know (stage 4 also fails such a
# name).
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
# The same two rail button limits bound its base, flange and screw heights
# (references at most 7.7, 4.8 and 0 mm) and its inner diameter (at most 8 mm).
PART_INSTANCES_MIN = 1         # copies of one part ("instancecount"), a whole number; every reference writes at least 1

# ---------------------------------------------------------------- positions and angles
# Where a part sits and how it is turned. Stage 5 judges the fit on OpenRocket's
# own placement; these first bounds stop absurd numbers before anything is flown.
POSITION_MAX_M = 5.0           # "position", "axialoffset", "tabposition", "instanceseparation" and a mount's "overhang", either way; references at most 2.59 m (a centering ring's offset); about twice
ANGLE_MAX_DEG = 360.0          # "angleoffset", "rotation", "radialdirection", "clusterrotation"; references -157.5 to 180 degrees; one full turn either way
RADIAL_OFFSET_MAX_M = 0.3      # "radialposition" and "radiusoffset", either way; references at most 55 mm; the widest catalog tube is 300 mm across

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
# The evidence counts in these notes were measured on 2026-11-19 with the
# references' mass overrides applied, before overrides were removed.
# Measured by flying the 183 reference designs that pass stages 1-5 under the
# launch conditions above (calibration report: flight statistics). A limit is
# set so that sound references pass and only truly unsafe ones fail.
RAIL_EXIT_MIN_MS = 11.0            # 15 m/s (contract) fails 14 references, 12 of them otherwise sound and most of them small (an A8 rocket leaves at 11.6); one reference is below 11 (9.0, and it weathercocks)
STATIC_STABILITY_MIN_CAL = 1.0     # contract. Flown as the reward flies them (table densities), every reference that reaches this stage has at least 1.0 cal except one (V4-0171: 0.973 cal; it had 1.02 with the densities its file wrote), which is left failing rather than loosening the contract. With overrides removed V4-0171 measures 0.86 cal, and V4-0162 (0.52) and V4-0166 (0.82) also fail here (REFERENCE_ROCKETS.md)
RAIL_STABILITY_MIN_CAL = 0.0       # leaving the rail in the worst wind: the margin moves by a median 0.48 cal across the three winds, so 1.0 here fails 31 references, 29 of them sound; the other two are below 0 and truly unstable
BURN_STABILITY_MIN_CAL = 0.0       # contract: stable from the rail to the last burnout; four references fail (two air-start a second stage after a 9 s coast)
THRUST_TO_WEIGHT_MIN = 3.0         # contract; lowest reference is 3.08
DEPLOY_SPEED_MAX_MS = 60.0         # references open recovery at a median 7.7 m/s, 95% under 36; the two above 60 use a 0 s ejection delay (68 and 99 m/s). OpenRocket itself warns from 20 m/s
LANDING_HARD_MAX_MS = 9.0          # vertical speed of any section that has a recovery device; fastest reference is 8.93 m/s
LANDING_SLACK_DEFAULT = 0.15       # tolerance of a "max" landing target when the requirements give none (stage 7, targets.py; stage 6 no longer judges the prompt's landing): prompts were written from one flight with no margin (worst reference 1.117x with overrides applied; with overrides removed one row is over 1.15x, V4-0233 original at 1.186x, landing credit 0.89). The RL prompt file writes tol 0.0 on every max target, so this is not used there
RECOVERY_OPEN_BEFORE_LANDING_MIN_S = 3.0  # time from the last opening of a recovered section's recovery devices to its landing, in every flight. OpenRocket fills a parachute the instant it opens, so without this a main parachute set to open 4 m above the ground lands "softly" (a 23 kg rocket falling at 34 m/s, 0.4 s before touchdown, scored 1.0); the 159 references that pass open at least 5.7 s before landing (V4-0073), so 3 s fails none; V4-0189, which fails this stage anyway, opens 0.1 s before it lands
DEPLOY_ALTITUDE_MIN_M = 50.0       # lowest altitude a recovery device may be set to open at when it opens at a fixed altitude (as OpenRocket read the setting); 55 references open a device at a fixed altitude, the lowest at 100 m (V4-0173), the rest at 152 m or more; half of the lowest
UNRECOVERED_LANDING_MAX_MS = 25.0  # a spent booster with no recovery device tumbles down at up to 20.6 m/s in sound references; nine references drop theirs nose-first at 52-64 m/s (1.3-3.6 kJ)

# ---------------------------------------------------------------- fit (stage 5)
# The evidence counts in these notes were measured on 2026-11-19 with the
# references' mass overrides applied, before overrides were removed.
# Measured on OpenRocket's own placement of every part in the reference designs.
SHELL_STEP_MAX_FRACTION = 0.10         # change in outer radius between neighbouring shell parts of one stage, as a share of the larger; 98% of references are under 3.4%, the three above 10% are broken (one is the base-drag trick)
SHELL_STEP_BETWEEN_STAGES_MAX_FRACTION = 0.15  # between stages; largest reference step is 14.3%
FIN_PAST_BACK_MAX_CHORDS = 0.5         # how far a fin root may run past the back end of its parent, in root chords; the four references beyond this have fins on nothing
FIN_PAST_FRONT_MAX_CHORDS = 1.0        # past the front end; 0.5 would fail two sound references
RIGID_INSIDE_RADIUS_MAX_RATIO = 1.08   # rings, bulkheads, engine blocks, inner tubes, couplers: outer radius over the inner radius of the airframe around them; the two references above are 15% and 23% too wide
SOFT_INSIDE_RADIUS_MAX_RATIO = 1.30    # parachutes, streamers, shock cords, mass parts (packed size is approximate); one reference is at 1.64
MOTOR_TUBE_BEHIND_TAIL_MAX_M = 0.05    # how far a motor tube may lie outside the airframe (behind the tail or ahead of the nose); one reference: 0.25 m; sound references at most 38 mm (V4-0201)
RING_OUTSIDE_AIRFRAME_MAX_M = 0.02     # how far a ring, bulkhead, engine block or tube coupler lies outside the airframe or the motor tube it sits on; sound references at most 10.2 mm (V4-0183; its motor retainer rings sit on a motor tube that sticks out 22 mm behind the tail, which counts as inside); V4-0210's engine block at 38 mm is broken
PACKED_OUTSIDE_AIRFRAME_MAX_M = 0.05   # the same for a mass component, shock cord, parachute, streamer, launch lug or rail button; sound references at most 28.6 mm (V4-0179's tail weight), recovery parts, lugs and buttons 0; about 1.75 times
MOTOR_DIAMETER_MAX_RATIO = 1.05        # motor diameter over its mount's inner diameter; largest reference 1.044
MOTOR_OVERHANG_MAX_FRACTION = 0.5      # share of the motor's length hanging out behind its mount; one reference: 0.88
FIN_SETS_SAME_ANGLE_DEG = 2.0          # two fin sets on one part overlapping within this angle are the same fins twice; 15 references interleave sets at other angles, which is fine
RING_OVERLAP_MAX_M = 0.0035            # two rings, bulkheads or engine blocks pushed into each other; references touch by up to 3.2 mm, one overlaps 10.5 mm
# Mass and balance overrides are no longer bounded here: the cleaning removes
# them (2026-11-19, see "mass, balance and drag overrides" above).
# Added 2026-11-19 after the stage 5-7 review (each one measured on OpenRocket's
# placement of the reference parts, gold_flights.jsonl, as-written variant):
MOTOR_AHEAD_OF_TAIL_MAX_M = 0.15       # how far the back end of a motor may sit ahead of the back end of its stage's airframe (for a motor in a pod or side booster, that pod's own shells); sound references: at most 0.12 m (one), the rest under 0.05 m; the two beyond 0.2 m are broken (0.24, 0.60)
POD_RADIUS_PER_BODY_MAX = 1.0          # outer radius of a pod or side-booster shell over the main body's widest radius; sound references at most 0.59; the one at 0.99 is broken (shell step)
STAGE_JOINT_REACH_MAX_M = 0.20         # how far a motor tube or tube coupler of a lower stage may reach ahead of the front of its own stage's shells, into the stage above (the joint between stages); the references that pass reach at most 0.102 m (V4-0063's coupler), V4-0003's motor tubes 0.19 m; other inside parts (weights, rings, bulkheads, recovery parts) never lie ahead of their own stage in any reference and keep their outside-the-airframe limit (a ring, bulkhead or engine block counted from the front of the motor tube or tube coupler that holds it, when that reaches further forward). A booster's weight inside the sustainer's nose steadies the rocket on the way up and then drops away
POD_OVERHANG_MAX_FRACTION = 0.33       # share of a pod's or side booster's own length (its shells) that may reach ahead of the front or behind the back of the main-body shells of the stage that holds it (of the whole main body when that stage has no shells); up to about 0.47 this is a defect, beyond it the stage fails (ladder.FIT_DEFECT_BELOW); 0 on every reference with pods (V4-0107, V4-0112, V4-0168, V4-0227, V4-0230). A strap-on that ends a little below the core is sound, so the limit is a share, not a distance; a small weighted pod held 3 m ahead of the nose (nose weight on a stick) measures far more than 1
POD_SUNK_MAX_FRACTION = 0.5            # share of a pod's radius that may lie inside the body beside it, which is the largest radius the main body has along the pod's own length (0 = the pod sits flush on the outside, 1 = its axis is on the body's surface, more = its axis is inside the body); the sound references sit flush (0), or stand off the body (below 0: V4-0112); V4-0227, already broken, has its pods on the centre line. A motor in a pod inside the body fires into the airframe
POD_GAP_MAX_M = 0.10                   # clear gap between a pod or side booster and the body beside it; the sound references sit against the body (0) except V4-0112, whose pods stand 50.8 mm off it; about twice that (V4-0227, already broken, has its pods inside the body)
SLENDERNESS_WIDTH_SHARE = 0.10         # the width used for slenderness is the largest diameter that at least this share of the main body's length has (each nose cone, body tube and transition counted with its larger end; pods do not count; with no usable shell, the reply's rocket max_diameter_m), so a thin flared disk at the tail does not count (judged on the largest diameter, a 100:1 rocket with a 2 mm disk 2.5 times its width measured 40)
SLENDERNESS_MAX = 60.0                 # rocket length over that width; the references reach at most 56.1 (V4-0050). Up to about 85 this is a defect, beyond it the stage fails (ladder.FIT_DEFECT_BELOW). A 25 mm tube 3.7 m long (151 times) would buckle, which the simulator does not model
TAIL_RADIUS_PER_MOTOR_MIN = 0.35       # aft outer radius of the last shell of a stage over the radius of a motor that fires out of it (for a motor in a pod or side booster, the last shell of that pod); sound references at least 0.71 (V4-0010, a boat tail around a 54 mm motor); half of that. A tail closed to a point leaves the motor no way out

# ---------------------------------------------------------------- reference designs that fail
# Measured on all 582 sft_v5 gold answers (train-N, val-N and test-N are line
# numbers, from 0, in the sft_v5 train, val and test files; each rocket appears
# in three rows, asked three ways). 567 of 582 pass (2026-11-19, with table
# densities and material names checked, before overrides were removed). The 15
# failures are five rockets, each with a part that would fly far thinner than any
# real one:
#   train-111..113  freeform fins 0.0003 mm thick (a unit slip in the source file)
#   train-207..209  freeform fins 0.08 mm thick
#   test-9..11      trapezoid fins 0.1 mm thick
#   train-288..290  a body tube 0.025 mm wide
#   train-18..20    a 0.64 m fiberglass body tube with a 0 mm wall (weightless)
# Two rockets that failed only on a slipped density now pass, because the
# cleaning gives every known material its table density: train-81..83 (an
# engine block of "Paper, bulk" written 0.0011 kg/m3, now 820) and test-33..35
# (fins of "RS: G10 (PML 0.093)" written 0.0071 kg/m3, now 1,905).
# No name in the 582 sft_v5 answers is unknown to the material table; the nine
# "RS:" shroud lines (three rockets) name no material and are removed by the
# cleaning, so OpenRocket uses its default line there. (The 594-row prompt
# file has one more rocket, V4-0172, which names the material "Custom" and
# stops here; it is broken at stage 5 too.)
# Since 2026-11-19 the cleaning removes every override, so four more rockets
# stop here: their mass overrides used to stand in for a wall that weighs
# nothing. Three have paper-thin transition walls (V4-0062 0.0254 mm,
# V4-0225 0.000254 mm, V4-0229 0.00254 mm) and V4-0222 has a
# 0 mm nose cone wall. On the 594-row prompt file stages 1-4 now pass 558 rows
# (570 before; its 12 rows beyond the 582 are V4-0165, V4-0167, V4-0168 and
# V4-0172, so 555 of the 582 pass).
# All 48 val rows (tests/data/gold_val.jsonl.gz) pass.
# The model's 48 saved answers: 3 now stop here on unknown material names
# (row-009, row-023, row-027); see tests/test_model_answers.py.
# Re-check with: python -m rocket_reward.tools.calibrate_preflight train.jsonl val.jsonl test.jsonl
# The whole ladder (stages 1-7, with Java): python -m rocket_reward.tools.calibrate --meta ... --prompts ...
# Passing the five would reopen the razor-fin (0.1 mm), paper-tube and
# zero-wall tricks the limits exist to block.
