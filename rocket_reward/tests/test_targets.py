"""Stage 7 (targets.py): the credit t for how well a flown rocket meets the
prompt's targets. Runs without Java on recorded simulator replies."""
from __future__ import annotations

import math

import pytest

from rocket_reward import ladder
from rocket_reward.limits import NOMINAL_FLIGHT
from rocket_reward.motors import MotorTable, _motor_fields, flown_motors
from rocket_reward.records import Requirements, Target
from rocket_reward.targets import check_targets, landing_credit

from answers import design_of
from replies import load_reply, parts_of


@pytest.fixture(scope="module")
def table() -> MotorTable:
    return MotorTable.load()


def nominal(reply: dict) -> dict:
    return reply["flights"][NOMINAL_FLIGHT]


def req(**fields) -> Requirements:
    fields.setdefault("apogee_m", Target(1000.0, "about"))
    return Requirements(id="t", **fields)


def row_of(chk, name: str) -> dict:
    return next(r for r in chk.info["targets"] if r["target"] == name)


# ------------------------------------------------------------------ basics

def test_apogee_alone_is_the_apogee_credit(table):
    reply = load_reply()
    apogee = nominal(reply)["apogee_m"]
    for asked in (apogee, apogee * 1.04, apogee * 1.5, apogee / 3):
        chk = check_targets(reply, req(apogee_m=Target(asked, "about")), {}, table)
        assert chk.stage == "targets" and chk.passed and chk.defects == []
        assert chk.credit == pytest.approx(ladder.closeness(apogee, asked, "about"))
        assert len(chk.info["targets"]) == 1
    exact = check_targets(reply, req(apogee_m=Target(apogee, "about")), {}, table)
    assert exact.credit == 1.0 and exact.reasons == []


FLIGHT_FIELDS = ("flight_time_s", "time_to_apogee_s", "max_velocity_ms", "max_accel_ms2")


@pytest.mark.parametrize("field", FLIGHT_FIELDS)
@pytest.mark.parametrize("kind,factor,tol", [("about", 1.3, None), ("about", 0.8, 0.1), ("max", 0.7, None),
                                             ("max", 0.95, 0.1), ("min", 1.4, None), ("min", 0.9, None)])
def test_every_flight_field_and_kind_uses_closeness(table, field, kind, factor, tol):
    reply = load_reply()
    measured = nominal(reply)[field]
    apogee = nominal(reply)["apogee_m"]
    target = Target(measured * factor, kind, tol)
    chk = check_targets(reply, req(apogee_m=Target(apogee, "about"), **{field: target}), {}, table)
    expected = ladder.closeness(measured, target.value, kind, tol)
    r = row_of(chk, field)
    assert r["measured"] == measured and r["credit"] == pytest.approx(expected) and r["weight"] == 1.0
    assert chk.credit == pytest.approx((3 * 1.0 + expected) / 4)


@pytest.mark.parametrize("kind", ["about", "max", "min"])
def test_body_diameter_is_the_widest_body_tube(table, kind):
    reply = load_reply()
    widest = 2 * max(c["outer_radius_fore_m"] for c in parts_of(reply, "BodyTube"))
    target = Target(0.15, kind)
    chk = check_targets(reply, req(body_diameter_m=target), {}, table)
    r = row_of(chk, "body_diameter_m")
    assert r["measured"] == pytest.approx(widest)
    assert r["credit"] == pytest.approx(ladder.closeness(widest, 0.15, kind))
    if r["credit"] < 1:
        assert any("body diameter 195 mm" in x and "150 mm" in x for x in chk.reasons), chk.reasons


def test_body_diameter_ignores_a_wider_nose_and_falls_back_to_the_rocket(table):
    reply = load_reply("two_stage")
    widest_tube = 2 * max(c["outer_radius_fore_m"] for c in parts_of(reply, "BodyTube"))
    parts_of(reply, "NoseCone")[0]["outer_radius_aft_m"] = 0.2
    chk = check_targets(reply, req(body_diameter_m=Target(0.05, "about")), {}, table)
    assert row_of(chk, "body_diameter_m")["measured"] == pytest.approx(widest_tube)
    reply["components"] = [c for c in reply["components"] if c["type"] != "BodyTube"]
    chk = check_targets(reply, req(body_diameter_m=Target(0.05, "about")), {}, table)
    assert row_of(chk, "body_diameter_m")["measured"] == pytest.approx(reply["rocket"]["max_diameter_m"])


@pytest.mark.parametrize("kind", ["about", "max", "min"])
def test_mass_is_the_liftoff_mass(table, kind):
    reply = load_reply()
    mass = reply["rocket"]["mass_kg"]
    chk = check_targets(reply, req(mass_kg=Target(10.0, kind, 0.1)), {}, table)
    r = row_of(chk, "mass_kg")
    assert r["measured"] == mass
    assert r["credit"] == pytest.approx(ladder.closeness(mass, 10.0, kind, 0.1))


def test_weights(table):
    reply = load_reply()
    f = nominal(reply)
    chk = check_targets(reply, req(apogee_m=Target(f["apogee_m"] * 2, "about"),
                                   flight_time_s=Target(f["flight_time_s"], "about"),
                                   mass_kg=Target(reply["rocket"]["mass_kg"] * 3, "max")), {}, table)
    a = ladder.closeness(f["apogee_m"], f["apogee_m"] * 2, "about")
    assert row_of(chk, "apogee_m")["weight"] == ladder.APOGEE_WEIGHT
    assert chk.credit == pytest.approx((ladder.APOGEE_WEIGHT * a + 2 * ladder.OTHER_TARGET_WEIGHT)
                                       / (ladder.APOGEE_WEIGHT + 2 * ladder.OTHER_TARGET_WEIGHT))
    assert chk.info["t"] == chk.credit
    assert len(chk.reasons) == 1 and chk.reasons[0].startswith("apogee 1,318 m, asked for about 2,635 m (5% allowed)")


# ------------------------------------------------------------------ missing and odd values

def every_target() -> Requirements:
    return req(landing_ms=Target(6.0, "max"), flight_time_s=Target(90.0, "about"),
               time_to_apogee_s=Target(15.0, "about"), max_velocity_ms=Target(190.0, "about"),
               max_accel_ms2=Target(120.0, "max"), body_diameter_m=Target(0.2, "about"),
               mass_kg=Target(12.0, "about"), motors=("K550W",), motor_class="K")


def test_missing_values_earn_nothing(table):
    reply = load_reply()
    for field in ("apogee_m", "flight_time_s", "time_to_apogee_s", "max_velocity_ms", "max_accel_ms2"):
        nominal(reply)[field] = None
    nominal(reply)["branches"][0]["landing_vertical_ms"] = None
    reply["rocket"]["mass_kg"] = float("nan")
    chk = check_targets(reply, every_target(), {}, table)
    credits = {r["target"]: r["credit"] for r in chk.info["targets"]}
    for field in ("apogee_m", "landing_ms", "flight_time_s", "time_to_apogee_s", "max_velocity_ms",
                  "max_accel_ms2", "mass_kg"):
        assert credits[field] == 0.0, field
    assert credits["body_diameter_m"] > 0 and credits["motors"] == 1.0 and credits["motor_class"] == 1.0
    assert "apogee: the flight gives no value, asked for about 1,000 m (5% allowed): credit 0" in chk.reasons


def test_a_failed_nominal_flight_gives_no_flight_numbers(table):
    reply = load_reply()
    reply["flights"][NOMINAL_FLIGHT] = {"ok": False, "error": "crash", "apogee_m": 1000.0}
    chk = check_targets(reply, req(), {}, table)
    assert chk.credit == 0.0 and chk.passed and "note" in chk.info


@pytest.mark.parametrize("junk", [None, 3, "text", [], {}, {"flights": "x"}, {"flights": [1, 2, 3]},
                                  {"flights": [{}, {"ok": True, "branches": [None, 5]}]},
                                  {"rocket": [], "components": [None, {"type": "BodyTube", "motor": 4,
                                                                       "outer_radius_fore_m": True}]},
                                  {"components": [{"motor": {"designation": 7, "total_impulse_ns": "x"}}]}])
def test_odd_replies_never_crash(table, junk):
    chk = check_targets(junk, every_target(), {"openrocket": 5}, table)
    assert chk.passed and 0.0 <= chk.credit <= 1.0 and chk.defects == []
    assert all(isinstance(x, str) for x in chk.reasons)


def test_odd_numbers_in_the_flight(table):
    reply = load_reply()
    for bad in (True, "500", float("inf"), -10.0, 0, 10 ** 400):
        nominal(reply)["apogee_m"] = bad
        chk = check_targets(reply, req(), {}, table)
        assert chk.credit == 0.0, bad


# ------------------------------------------------------------------ landing

def test_comfort_floor_is_the_lower_of_the_two_rules():
    low = Target(5.0, "max")                 # 60% of 5 m/s is 3.0 m/s, below 3.5 m/s
    assert landing_credit(3.0, low) == 1.0
    assert landing_credit(2.0, low) == pytest.approx(2.0 / 3.0)
    high = Target(8.0, "max")                # 60% of 8 m/s is 4.8 m/s: the 3.5 m/s floor counts
    assert landing_credit(3.5, high) == 1.0
    assert landing_credit(3.4, high) == pytest.approx(3.4 / 3.5)
    assert landing_credit(7.99, high) == 1.0


def test_landing_above_the_limit_uses_closeness():
    t = Target(5.0, "max", 0.1)
    assert landing_credit(5.49, t) == 1.0
    assert landing_credit(6.5, t) == pytest.approx(ladder.closeness(6.5, 5.0, "max", 0.1))
    assert landing_credit(6.5, t) < 1.0
    assert landing_credit(None, t) == 0.0 and landing_credit(0.0, t) == 0.0


def test_landing_is_read_from_the_main_section(table):
    reply = load_reply("two_stage")         # the booster falls at 11.8 m/s with no recovery
    main = nominal(reply)["branches"][0]["landing_vertical_ms"]
    chk = check_targets(reply, req(apogee_m=Target(nominal(reply)["apogee_m"], "about"),
                                   landing_ms=Target(6.0, "max")), {}, table)
    assert row_of(chk, "landing_ms")["measured"] == main and chk.credit == 1.0


def test_landing_reasons_on_both_sides(table):
    reply = load_reply()
    apogee = Target(nominal(reply)["apogee_m"], "about")
    nominal(reply)["branches"][0]["landing_vertical_ms"] = 1.5
    slow = check_targets(reply, req(apogee_m=apogee, landing_ms=Target(5.0, "max")), {}, table)
    assert slow.reasons == ["landing speed 1.50 m/s, 1.50 m/s slower than needed (full credit from 3.00 m/s "
                            "up to the limit, at most 5.00 m/s), so the parachute is larger than it needs "
                            "to be: credit 0.50"]
    nominal(reply)["branches"][0]["landing_vertical_ms"] = 7.0
    fast = check_targets(reply, req(apogee_m=apogee, landing_ms=Target(5.0, "max")), {}, table)
    assert fast.reasons[0].startswith("landing speed 7.00 m/s, asked for at most 5.00 m/s: credit 0.")


# ------------------------------------------------------------------ motors

def test_motor_share_and_normalising(table):
    reply = load_reply()                     # flies one K550W and three I211W
    for named, share in ((("K550W",), 1.0), (("K550W", "I211W"), 1.0), (("k550w", "HP-I211W-v1"), 1.0),
                         (("K550W", "M2000R"), 0.5), (("M2000R",), 0.0), (("K550W", "k550w"), 1.0),
                         (("K550",), 1.0)):    # K550 is the designation the file asked for
        chk = check_targets(reply, req(apogee_m=Target(nominal(reply)["apogee_m"], "about"), motors=named),
                            {}, table)
        assert row_of(chk, "motors")["credit"] == pytest.approx(share), named
        assert chk.credit == pytest.approx((3 + share) / 4)
        if share < 1:
            assert "missing M2000R" in chk.reasons[0] and "I211W" in chk.reasons[0]


def test_motors_fall_back_to_the_design_when_the_reply_lists_none(table, gold_rows):
    root = design_of(gold_rows[0]["answer"], root_only=True)
    key = table.resolve(*_motor_fields(flown_motors(root)[0])[:3])
    assert key is not None
    reply = load_reply()
    for c in reply["components"]:
        c["motor"] = None
    named = (table.get(key)["designation"],)
    chk = check_targets(reply, req(motors=named), root, table)
    assert row_of(chk, "motors")["credit"] == 1.0
    chk = check_targets(reply, req(motors=named), {}, table)
    assert row_of(chk, "motors")["credit"] == 0.0
    assert "flown: no motor" in chk.reasons[-1]


def test_motor_class_credit(table):
    reply = load_reply()                     # largest motor: K550W, 1,625 Ns, class K
    for letter, credit in (("K", 1.0), ("J", 0.5), ("L", 0.5), ("I", 0.0), ("M", 0.0), ("A", 0.0)):
        chk = check_targets(reply, req(apogee_m=Target(nominal(reply)["apogee_m"], "about"),
                                       motor_class=letter), {}, table)
        assert row_of(chk, "motor_class")["credit"] == credit, letter
        if credit < 1:
            assert "largest motor K550W (1,625 Ns) is class K, asked for class " + letter in chk.reasons[0]


def test_motor_class_sold_under_a_letter_counts(table):
    reply = load_reply("two_stage")
    m = next(c["motor"] for c in reply["components"] if c.get("motor") and c["motor"]["designation"] == "I115W")
    m["designation"], m["total_impulse_ns"] = "H128W", 150.0    # measures as a G, sold as an H
    for letter, credit in (("H", 1.0), ("G", 1.0), ("I", 0.5), ("F", 0.5), ("J", 0.0)):
        chk = check_targets(reply, req(motor_class=letter), {}, table)
        assert row_of(chk, "motor_class")["credit"] == credit, letter


def test_motor_class_without_motors_earns_nothing(table):
    reply = load_reply()
    for c in reply["components"]:
        c["motor"] = None
    chk = check_targets(reply, req(motor_class="K"), {}, table)
    assert row_of(chk, "motor_class")["credit"] == 0.0


# ------------------------------------------------------------------ closer is never worse

def t_for(field: str, value: float, target: Target, table: MotorTable) -> float:
    reply = load_reply()
    apogee = Target(nominal(reply)["apogee_m"], "about")
    if field == "landing_ms":
        nominal(reply)["branches"][0]["landing_vertical_ms"] = value
    elif field == "mass_kg":
        reply["rocket"]["mass_kg"] = value
    else:
        nominal(reply)[field] = value
    fields = {field: target} if field != "apogee_m" else {"apogee_m": target}
    if field != "apogee_m":
        fields["apogee_m"] = apogee
    return check_targets(reply, req(**fields), {}, table).credit


@pytest.mark.parametrize("field,target", [
    ("apogee_m", Target(500.0, "about")), ("apogee_m", Target(500.0, "about", 0.2)),
    ("flight_time_s", Target(60.0, "max")), ("max_velocity_ms", Target(100.0, "min")),
    ("mass_kg", Target(2.0, "about")), ("landing_ms", Target(5.0, "max")),
    ("landing_ms", Target(8.0, "max", 0.15)), ("landing_ms", Target(5.0, "about")),
])
def test_closer_is_never_worse(table, field, target):
    """Step the measured value away from the target on both sides: t never rises."""
    best = target.value if not (field == "landing_ms" and target.kind == "max") else target.value * 0.8
    ends = []
    for direction in (1.02, 1 / 1.02):
        value, last = best, t_for(field, best, target, table)
        assert last == pytest.approx(1.0)
        for _ in range(150):
            value *= direction
            t = t_for(field, value, target, table)
            assert t <= last + 1e-12, (field, value)
            last = t
        ends.append(last)
    # an "about" target (and a landing limit) loses credit on both sides, "max" and "min" on one
    both = target.kind == "about" or field == "landing_ms"
    # (apogee, met exactly, keeps 3/4 of t when another target is stepped)
    floor = 0.0 if field == "apogee_m" else 0.75
    assert (max(ends) if both else min(ends)) < floor + 0.1


def test_landing_credit_is_monotone_on_a_fine_grid():
    t = Target(6.0, "max")
    speeds = [i * 0.01 for i in range(1, 2000)]
    credits = [landing_credit(s, t) for s in speeds]
    peak = credits.index(1.0)
    assert all(a <= b for a, b in zip(credits[:peak], credits[1:peak + 1]))
    assert all(a >= b for a, b in zip(credits[peak:], credits[peak + 1:]))
    assert all(0.0 < c <= 1.0 and math.isfinite(c) for c in credits)


# ------------------------------------------------------------------ review fixes

def test_landing_that_is_not_downward_earns_nothing(table):
    for bad in (-4.0, 0.0):
        reply = load_reply()
        for b in nominal(reply)["branches"]:
            b["landing_vertical_ms"] = bad
        chk = check_targets(reply, req(landing_ms=Target(6.0, "max")), {}, table)
        assert row_of(chk, "landing_ms")["measured"] is None and row_of(chk, "landing_ms")["credit"] == 0.0


def test_body_diameter_ignores_tubes_in_pods_and_side_boosters(table):
    from rocket_reward.fit import _Parts
    reply = load_reply("two_stage")
    parts = _Parts(reply["components"])
    main = 2 * max(c["outer_radius_fore_m"] for c in parts.all if c["type"] == "BodyTube" and not parts.in_pod(c))
    booster = next(c for c in parts.all if c["type"] == "BodyTube" and parts.in_pod(c))
    booster.update(outer_radius_fore_m=0.2, outer_radius_aft_m=0.2, length_m=0.002)    # a wide stub
    chk = check_targets(reply, req(body_diameter_m=Target(0.4, "about")), {}, table)
    assert row_of(chk, "body_diameter_m")["measured"] == pytest.approx(main)


@pytest.mark.parametrize("field", ["flight_time_s", "time_to_apogee_s"])
def test_times_are_measured_from_the_first_ignition(table, field):
    """A rocket that waits on the pad before its motor lights gains no flight time."""
    reply = load_reply()
    flown = nominal(reply)[field]
    target = Target(flown + 16.0, "about")
    plain = check_targets(reply, req(**{field: target}), {}, table)
    nominal(reply)[field] = flown + 16.0
    nominal(reply)["ignition_time_s"] = 16.0
    waited = check_targets(reply, req(**{field: target}), {}, table)
    assert row_of(waited, field)["measured"] == pytest.approx(flown)
    assert waited.credit == pytest.approx(plain.credit) and waited.credit < 1.0
    for odd in (None, -5.0, "16", True, float("nan")):
        nominal(reply)["ignition_time_s"] = odd
        chk = check_targets(reply, req(**{field: target}), {}, table)
        assert row_of(chk, field)["measured"] == pytest.approx(flown + 16.0), odd
