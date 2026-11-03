"""Tests for scripts/sft_compact_design.py (Stage 1, flight-free).

Every test here is purely static: no JVM, no simulation, no flights.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.sft_compact_design import (  # noqa: E402
    CONFIGID_PLACEHOLDER,
    CompactError,
    diff_trees,
    dump_compact_json,
    from_compact,
    normalize_tree,
    static_check,
    to_compact,
    type_text,
    untype_value,
)

FCID_SEL = "e51fe740-c1b8-49ea-9632-b44d1efb712d"
FCID_OTHER = "7cc89a91-ada2-4bbe-b59b-b5981f6c9bdd"
ROCKET_ID = "6c60211d-46f9-482a-814e-a27ddef36f3b"
COMPONENT_ID = "091032e6-23e5-4e9e-8b41-68435ead56d0"


def _node(tag, attrs=None, text=None, children=None):
    return {"tag": tag, "attrs": attrs or {}, "text": text, "children": children or []}


def make_full_design() -> dict:
    """A small but representative full-fidelity design (no JVM needed).

    Covers: two simulations, two motor configurations, component ids/names,
    appearance subtree, fin points, per-config motor / deployment / ignition /
    separation configurations, a preset, an engineering thrustcurve attachment
    and a cosmetic texture attachment.
    """
    motor_sel = _node(
        "motor", attrs={"configid": FCID_SEL},
        children=[
            _node("type", text="single"),
            _node("manufacturer", text="Estes"),
            _node("digest", text="c8743ef3fa99e14a89885cbe0ead47b2"),
            _node("designation", text="C6"),
            _node("diameter", text="0.018"),
            _node("length", text="0.07"),
            _node("delay", text="0.0"),
        ],
    )
    motor_other = _node(
        "motor", attrs={"configid": FCID_OTHER},
        children=[
            _node("type", text="single"),
            _node("manufacturer", text="Estes"),
            _node("digest", text="4f0059c416964ba2528c83551e6a6839"),
            _node("designation", text="C11"),
            _node("diameter", text="0.024"),
            _node("length", text="0.07"),
            _node("delay", text="0.0"),
        ],
    )
    innertube = _node(
        "innertube",
        children=[
            _node("name", text="Inner Tube"),
            _node("id", text=COMPONENT_ID),
            _node("position", attrs={"type": "bottom"}, text="0.0"),
            _node("material", attrs={"density": "680.0", "type": "bulk"}, text="Cardboard"),
            _node("length", text="0.07"),
            _node("outerradius", text="0.0095"),
            _node("thickness", text="5.333999999999998E-4"),
            _node("clusterconfiguration", text="single"),
            _node("clusterscale", text="1.0"),
            _node("clusterrotation", text="0.0"),
            _node(
                "motormount",
                children=[
                    _node("ignitionevent", text="automatic"),
                    _node("ignitiondelay", text="0.0"),
                    _node("overhang", text="0.0"),
                    motor_sel,
                    motor_other,
                    _node(
                        "ignitionconfiguration", attrs={"configid": FCID_SEL},
                        children=[
                            _node("ignitionevent", text="automatic"),
                            _node("ignitiondelay", text="0.0"),
                        ],
                    ),
                ],
            ),
        ],
    )
    parachute = _node(
        "parachute",
        children=[
            _node("name", text="Parachute"),
            _node("position", attrs={"type": "top"}, text="0.0"),
            _node("cd", text="auto"),
            _node("material", attrs={"density": "0.0", "type": "surface"}, text="Polyethylene LDPE"),
            _node("deployevent", text="altitude"),
            _node("deployaltitude", text="200.0"),
            _node("deploydelay", text="0.0"),
            _node("diameter", text="0.4572"),
            _node("linecount", text="6"),
            _node("linelength", text="0.4572"),
            _node(
                "deploymentconfiguration", attrs={"configid": FCID_SEL},
                children=[
                    _node("deployevent", text="altitude"),
                    _node("deployaltitude", text="152.4"),
                    _node("deploydelay", text="0.0"),
                ],
            ),
            _node(
                "deploymentconfiguration", attrs={"configid": FCID_OTHER},
                children=[_node("deployevent", text="ejection")],
            ),
        ],
    )
    finset = _node(
        "trapezoidfinset",
        children=[
            _node("name", text="Trapezoidal Fin Set"),
            _node("position", attrs={"type": "bottom"}, text="0.0"),
            _node("material", attrs={"density": "680.0", "type": "bulk"}, text="Cardboard"),
            _node("fincount", text="3"),
            _node("rotation", text="0.0"),
            _node("thickness", text="0.003"),
            _node("crosssection", text="square"),
            _node("cant", text="0.0"),
            _node("rootchord", text="0.09"),
            _node("tipchord", text="0.035"),
            _node("sweeplength", text="0.025"),
            _node("height", text="0.05"),
        ],
    )
    bodytube = _node(
        "bodytube",
        children=[
            _node("name", text="Body tube"),
            _node("id", text=COMPONENT_ID),
            _node(
                "appearance",
                children=[
                    _node("paint", attrs={"alpha": "255", "blue": "0", "green": "0", "red": "102"}),
                    _node("shine", text="0.0"),
                ],
            ),
            _node("finish", text="normal"),
            _node("material", attrs={"density": "608.7016092000001", "type": "bulk"}, text="Paper"),
            _node("length", text="0.4572"),
            _node("thickness", text="0.0005333999999999998"),
            _node("radius", text="0.0168275"),
            _node(
                "subcomponents",
                children=[
                    innertube,
                    parachute,
                    finset,
                    _node("masscomponent",
                          children=[_node("masscomponenttype", text="ballast"),
                                    _node("mass", text="0.010")]),
                ],
            ),
        ],
    )
    nosecone = _node(
        "nosecone",
        children=[
            _node("name", text="Nose cone"),
            _node("appearance", children=[_node("shine", text="0.0")]),
            _node("finish", text="normal"),
            _node("material", attrs={"density": "601.8664426919009", "type": "bulk"}, text="Polystyrene PS"),
            _node("length", text="0.1016"),
            _node("thickness", text="0.003175"),
            _node("shape", text="ogive"),
            _node("shapeparameter", text="1.0"),
            _node("aftradius", text="0.0168275"),
        ],
    )
    stage = _node(
        "stage",
        children=[
            _node("name", text="Sustainer"),
            _node(
                "subcomponents",
                children=[nosecone, bodytube],
            ),
        ],
    )
    sim_sel = _node(
        "simulation", attrs={"status": "outdated"},
        children=[
            _node("name", text="Simulation 1"),
            _node("simulator", text="RK4Simulator"),
            _node("calculator", text="BarrowmanCalculator"),
            _node(
                "conditions",
                children=[
                    _node("configid", text=FCID_SEL),
                    _node("launchrodlength", text="1.0"),
                    _node("launchrodangle", text="0.0"),
                    _node("windaverage", text="2.0"),
                    _node("windturbulence", text="0.1"),
                    _node("launchaltitude", text="0.0"),
                    _node("atmosphere", attrs={"model": "isa"}),
                    _node("timestep", text="0.05"),
                ],
            ),
        ],
    )
    sim_other = _node(
        "simulation",
        children=[
            _node("name", text="Simulation 2"),
            _node("simulator", text="RK4Simulator"),
            _node("calculator", text="BarrowmanCalculator"),
            _node("conditions", children=[_node("configid", text=FCID_OTHER)]),
        ],
    )
    freeform = _node(
        "freeformfinset",
        children=[
            _node("finpoints", children=[
                _node("point", attrs={"x": "0.0", "y": "0.0"}),
                _node("point", attrs={"x": "0.05", "y": "0.038"}),
            ]),
        ],
    )
    return {
        "schema_version": "full-fidelity-1.0",
        "openrocket_version": "1.6",
        "creator": "OpenRocket 15.03",
        "ork_container": {"format": "zip"},
        "parameter_tree": _node(
            "openrocket", attrs={"creator": "OpenRocket 15.03", "version": "1.6"},
            children=[
                _node(
                    "rocket",
                    children=[
                        _node("name", text="Rocket"),
                        _node("id", text=ROCKET_ID),
                        _node("comment", text="a comment"),
                        _node("designer", text="someone"),
                        _node("revision", text="rev 2"),
                        _node("referencetype", text="maximum"),
                        _node("motorconfiguration", attrs={"configid": FCID_SEL, "default": "true"},
                              children=[_node("stage", attrs={"active": "true", "number": "0"})]),
                        _node("motorconfiguration", attrs={"configid": FCID_OTHER},
                              children=[_node("stage", attrs={"active": "true", "number": "0"})]),
                        _node("subcomponents", children=[stage, freeform]),
                    ],
                ),
                _node("simulations", children=[sim_sel, sim_other]),
                _node("docprefs", children=[_node("docmaterials")]),
                _node("photostudio", children=[_node("sky", text="Meadow")]),
            ],
        ),
        "bundle_entries": {
            "thrustcurves/c8743ef3fa99e14a89885cbe0ead47b2.rse": {
                "encoding": "base64", "sha256": "0" * 64,
                "data": "PHJzZT4xMjM8L3JzZT4=",
            },
            "/datafiles/textures/balsa.jpg": {
                "encoding": "base64", "sha256": "1" * 64,
                "data": "cG5nZGF0YQ==",
            },
        },
        "selected_simulation": {
            "name": "Simulation 1",
            "index": 0,
            "flight_configuration_id": FCID_SEL,
            "simulator": "RK4Simulator",
            "calculator": "BarrowmanCalculator",
        },
    }


def walk_keys(obj, path=""):
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_keys(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_keys(v, f"{path}[{i}]")


def _find_in_compact(node, tag):
    for item in node.get("children") or []:
        (child_tag, payload), = item.items()
        if child_tag == tag:
            return payload
    raise AssertionError(f"no compact child <{tag}>")


def find_child(node, tag):
    """First child element with the given tag (compact node or tree node)."""
    if "children" in node and node.get("children") and isinstance(node["children"][0], dict) \
            and "tag" in node["children"][0]:
        for c in node["children"]:
            if c["tag"] == tag:
                return c
        raise AssertionError(f"no child <{tag}>")
    return _find_in_compact(node, tag)


def find_descendants(node, tag):
    """All descendants with the given tag in a generic tree node."""
    out = []
    def rec(n):
        for c in n.get("children") or []:
            if c["tag"] == tag:
                out.append(c)
            rec(c)
    rec(node)
    return out


UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
GETTER_RE = re.compile(r"^(?:get|is|set)[A-Z]")


# --------------------------------------------------------------------------
# typing rules
# --------------------------------------------------------------------------

def test_type_text_canonical_only():
    assert type_text("true") is True and type_text("false") is False
    assert type_text("0.1016") == 0.1016
    assert type_text("3") == 3
    assert type_text("-2") == -2
    assert type_text("0.0") == 0.0
    # non-canonical spellings must stay strings (exactness over prettiness)
    assert type_text("5.333999999999998E-4") == "5.333999999999998E-4"
    assert type_text("0624") == "0624"
    assert type_text("1e6") == "1e6"
    assert type_text("auto") == "auto"
    assert type_text("bottom") == "bottom"


def test_type_text_roundtrip_via_untype():
    for s in ["0.1016", "3", "5.333999999999998E-4", "0624", "auto", "true",
              "false", "1.0", "0.0", "-45.00000000000001", "Cardboard"]:
        assert untype_value(type_text(s)) == s


# --------------------------------------------------------------------------
# core round trip on the synthetic design
# --------------------------------------------------------------------------

def test_roundtrip_matches_normalized_tree():
    design = make_full_design()
    result = static_check(design)
    assert result["pass"], result["differences"]


def test_diff_trees_detects_value_changes():
    design = make_full_design()
    rebuilt = from_compact(to_compact(design))
    expected = normalize_tree(design["parameter_tree"], "Simulation 1")
    diffs = diff_trees(expected, rebuilt["parameter_tree"])
    assert diffs == []
    # perturb one physics value in the rebuilt tree: the nose cone length
    def find(node, tag, out):
        if node["tag"] == tag:
            out.append(node)
        for c in node.get("children") or []:
            find(c, tag, out)
        return out
    nosecones = find(rebuilt["parameter_tree"], "nosecone", [])
    length = next(c for c in nosecones[0]["children"] if c["tag"] == "length")
    length["text"] = "0.2"
    diffs = diff_trees(expected, rebuilt["parameter_tree"])
    assert any("#text" in d and "0.1016" in d and "0.2" in d for d in diffs)


def test_deterministic_output():
    design = make_full_design()
    a = dump_compact_json(to_compact(design))
    b = dump_compact_json(to_compact(design))
    assert a == b
    assert json.loads(a) == to_compact(design)


def test_compact_is_smaller():
    design = make_full_design()
    original_chars = len(json.dumps(design["parameter_tree"]))
    compact_chars = len(dump_compact_json(to_compact(design)))
    assert compact_chars < original_chars


# --------------------------------------------------------------------------
# removal rules
# --------------------------------------------------------------------------

def test_no_hash_uuid_source_filename_or_getter_keys():
    """The compact output must not carry hashes, uuids, source filenames or
    loader getter keys.

    Documented exceptions (needed to resolve the same physics on rebuild):
    * motor/preset `digest` values (content identity inside OpenRocket's
      databases, not source-file hashes);
    * the single deterministic config-id placeholder `cfg0`.
    """
    design = make_full_design()
    compact_text = dump_compact_json(to_compact(design))
    compact = json.loads(compact_text)
    forbidden_keys = {"component_index", "simulation_options_snapshot",
                      "reconstruction_contract", "source_path", "source_file",
                      "sha256", "provenance"}
    for path, value in walk_keys(compact):
        key = path.rsplit("/", 1)[-1].split("[", 1)[0]
        assert key not in forbidden_keys, f"forbidden key {key!r} at {path}"
        assert not re.search(r"(?i)sha ?256|md5|hash", key), f"hash-like key {key!r} at {path}"
        assert not GETTER_RE.match(key), f"getter-style key {key!r} at {path}"
        if isinstance(value, str):
            assert not UUID_RE.match(value) or value == CONFIGID_PLACEHOLDER or \
                key == "digest", f"uuid-like value {value!r} at {path}"
            assert ".ork" not in value and not value.startswith("ork/"), \
                f"source filename {value!r} at {path}"
            assert "uuid" not in key.lower(), f"uuid key at {path}"


def test_non_selected_configs_dropped():
    design = make_full_design()
    compact = to_compact(design)
    text = dump_compact_json(compact)
    assert FCID_SEL not in text and FCID_OTHER not in text
    assert ROCKET_ID not in text and COMPONENT_ID not in text
    openrocket = compact["openrocket"]
    simulations = _find_in_compact(_find_in_compact(openrocket, "simulations"), "simulation")
    assert isinstance(simulations, dict), "exactly one (selected) simulation must remain"
    assert _find_in_compact(simulations, "name") == {"value": "Simulation 1"}
    top_tags = [next(iter(c)) for c in openrocket.get("children") or []]
    assert "photostudio" not in top_tags and "docprefs" not in top_tags
    rocket = _find_in_compact(openrocket, "rocket")
    rocket_tags = [next(iter(c)) for c in rocket.get("children") or []]
    assert "comment" not in rocket_tags and "id" not in rocket_tags and "name" not in rocket_tags
    mc = _find_in_compact(rocket, "motorconfiguration")
    assert mc["attrs"]["configid"] == CONFIGID_PLACEHOLDER
    # non-selected motor (C11) and its config are gone; selected motor (C6) remains
    text_without_attachments = text.split('"attachments"')[0]
    assert '"C11"' not in text_without_attachments
    assert '"C6"' in text_without_attachments


def test_selected_config_placeholder_is_deterministic():
    design = make_full_design()
    compact = to_compact(design)
    openrocket = compact["openrocket"]
    rocket = _find_in_compact(openrocket, "rocket")
    mc = _find_in_compact(rocket, "motorconfiguration")
    assert mc["attrs"]["configid"] == CONFIGID_PLACEHOLDER
    sim = _find_in_compact(_find_in_compact(openrocket, "simulations"), "simulation")
    conditions = _find_in_compact(sim, "conditions")
    assert _find_in_compact(conditions, "configid") == {"value": CONFIGID_PLACEHOLDER}
    bodytube = _find_compact_descendant(rocket, "bodytube")
    mount = _find_compact_descendant(bodytube, "motormount")
    assert _find_in_compact(mount, "motor")["attrs"]["configid"] == CONFIGID_PLACEHOLDER
    assert _find_in_compact(mount, "ignitionconfiguration")["attrs"]["configid"] == CONFIGID_PLACEHOLDER
    chute = _find_compact_descendant(bodytube, "parachute")
    assert _find_in_compact(chute, "deploymentconfiguration")["attrs"]["configid"] == CONFIGID_PLACEHOLDER


def _find_compact_descendant(node, tag):
    for item in node.get("children") or []:
        (child_tag, payload), = item.items()
        if child_tag == tag:
            return payload
        found = _find_compact_descendant(payload, tag)
        if found is not None:
            return found
    return None


def test_physics_values_preserved_exactly():
    design = make_full_design()
    compact = to_compact(design)
    openrocket = compact["openrocket"]
    rocket = _find_in_compact(openrocket, "rocket")
    bodytube = _find_compact_descendant(rocket, "bodytube")
    assert _find_in_compact(bodytube, "length") == {"value": 0.4572}
    assert _find_in_compact(bodytube, "material") == {
        "attrs": {"density": 608.7016092000001, "type": "bulk"}, "value": "Paper"}
    chute = _find_compact_descendant(bodytube, "parachute")
    assert _find_in_compact(chute, "position") == {"attrs": {"type": "top"}, "value": 0.0}
    assert _find_in_compact(chute, "cd") == {"value": "auto"}
    assert _find_in_compact(chute, "diameter") == {"value": 0.4572}
    finset = _find_compact_descendant(bodytube, "trapezoidfinset")
    assert _find_in_compact(finset, "fincount") == {"value": 3}
    assert _find_in_compact(finset, "thickness") == {"value": 0.003}
    mount = _find_compact_descendant(bodytube, "motormount")
    motor = _find_in_compact(mount, "motor")
    assert _find_in_compact(motor, "designation") == {"value": "C6"}
    assert _find_in_compact(motor, "delay") == {"value": 0.0}
    assert _find_in_compact(motor, "digest") == {"value": "c8743ef3fa99e14a89885cbe0ead47b2"}
    assert _find_in_compact(mount, "overhang") == {"value": 0.0}


def test_sibling_order_preserved():
    """Sibling order is physics (AFTER/TOP placement resolves against it)."""
    design = make_full_design()
    rebuilt = from_compact(to_compact(design))
    expected = normalize_tree(design["parameter_tree"], "Simulation 1")

    def tags(node):
        return [c["tag"] for c in node.get("children") or []]

    assert tags(rebuilt["parameter_tree"]) == tags(expected)
    # bodytube subcomponents must keep [innertube, parachute, trapezoidfinset,
    # masscomponent] order exactly
    tubes = find_descendants(rebuilt["parameter_tree"], "bodytube")
    subs = find_child(tubes[0], "subcomponents")
    assert tags(subs) == ["innertube", "parachute", "trapezoidfinset", "masscomponent"]


def test_scientific_notation_text_round_trips_exactly():
    """Thickness text uses E-notation in the source; it must survive verbatim."""
    design = make_full_design()
    compact = to_compact(design)
    openrocket = compact["openrocket"]
    rocket = _find_in_compact(openrocket, "rocket")
    innertube = _find_compact_descendant(rocket, "innertube")
    assert _find_in_compact(innertube, "thickness") == {"value": "5.333999999999998E-4"}
    rebuilt = from_compact(compact)
    tubes = find_descendants(rebuilt["parameter_tree"], "innertube")
    assert tubes[0]["text"] is None
    thick = next(c for c in tubes[0]["children"] if c["tag"] == "thickness")
    assert thick["text"] == "5.333999999999998E-4"


# --------------------------------------------------------------------------
# attachments
# --------------------------------------------------------------------------

def test_engineering_attachment_kept_and_cosmetic_dropped():
    design = make_full_design()
    result = static_check(design)
    assert result["pass"], result["differences"]
    assert result["dropped_attachments"] == ["/datafiles/textures/balsa.jpg"]
    compact = to_compact(design)
    assert set(compact["attachments"]) == {"thrustcurves/c8743ef3fa99e14a89885cbe0ead47b2.rse"}
    rebuilt = from_compact(compact)
    entry = rebuilt["bundle_entries"]["thrustcurves/c8743ef3fa99e14a89885cbe0ead47b2.rse"]
    import base64
    assert base64.b64decode(entry["data"]) == b"<rse>123</rse>"
    assert entry["sha256"] is not None  # recomputed for the rebuild pipeline


# --------------------------------------------------------------------------
# rebuild shape
# --------------------------------------------------------------------------

def test_from_compact_produces_rebuildable_design_shape():
    design = make_full_design()
    rebuilt = from_compact(to_compact(design))
    assert rebuilt["schema_version"] == "full-fidelity-1.0"
    assert rebuilt["openrocket_version"] == "1.6"
    assert rebuilt["ork_container"] == {"format": "zip"}
    assert rebuilt["parameter_tree"]["tag"] == "openrocket"
    # no audit/provenance keys
    for forbidden in ("component_index", "simulation_options_snapshot",
                      "reconstruction_contract", "creator"):
        assert forbidden not in rebuilt
    # tree text/attrs are strings again (XML-ready)
    def leaves(node):
        yield node
        for c in node["children"]:
            yield from leaves(c)
    for n in leaves(rebuilt["parameter_tree"]):
        assert n["tag"] and isinstance(n["attrs"], dict)
        assert n["text"] is None or isinstance(n["text"], str)
        for v in n["attrs"].values():
            assert isinstance(v, str)


def test_missing_selected_simulation_raises():
    design = make_full_design()
    design["selected_simulation"]["name"] = "Nope"
    with pytest.raises((KeyError, CompactError)):
        to_compact(design)
