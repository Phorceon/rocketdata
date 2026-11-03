"""Pure, flight-free tests for the v4 COMPLETE source recovery generator.

No JVM anywhere: XML trees and catalog records are synthetic but shaped
exactly like the real ones (xml_tree node convention, rockets_full.jsonl
simulation records with @-prefixed flightdata attrs, fill_info dicts).  The
end-to-end test builds a tiny synthetic workspace on disk and runs the
generator with ``jvm=False`` (engineering/load checks recorded as
unavailable, never fabricated).
"""
import base64
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import sft_v4_sources as sv
from scripts.sft_compact_design import CompactError
from scripts.sft_full_fidelity_support.ork_archive import write_ork_archive
from scripts.sft_full_fidelity_support.xml_tree import parse_openrocket_xml


# --------------------------------------------------------------------------
# builders (xml_tree node convention; catalog record convention)
# --------------------------------------------------------------------------

def node(tag, text=None, attrs=None, children=None):
    return {"tag": tag, "attrs": attrs or {}, "text": text,
            "children": children or []}


def catalog_sim(name, status="uptodate", configid="cfg-A", fd=None, wind="2.0"):
    sim = {"@status": status, "name": name,
           "conditions": {"configid": configid, "windaverage": wind}}
    if fd is not None:
        sim["flightdata"] = {f"@{k}": v for k, v in fd.items()}
    return sim


def full_fd(apogee=120.0, ground=5.0, flight=30.0, tap=4.0, vel=70.0, mach=0.2):
    return {"maxaltitude": apogee, "groundhitvelocity": ground,
            "flighttime": flight, "timetoapogee": tap, "maxvelocity": vel,
            "maxmach": mach}


def motor_block(configid, digest=None, designation="C6",
                manufacturer="Estes", delay=None, diameter=None, length=None):
    kids = [node("manufacturer", manufacturer)]
    if digest is not None:
        kids.append(node("digest", digest))
    kids.append(node("designation", designation))
    if diameter is not None:
        kids.append(node("diameter", diameter))
    if length is not None:
        kids.append(node("length", length))
    if delay is not None:
        kids.append(node("delay", delay))
    return node("motor", attrs={"configid": configid}, children=kids)


def make_tree(sim_specs, motor_configs=("cfg-A",), default_config="cfg-A",
              digest_suffix="1"):
    """Tree with sims and one motormount populating the given configs."""
    mount_kids = [motor_block(c, digest=f"dg{c[-1]}{digest_suffix}")
                  for c in motor_configs]
    mount = node("motormount", children=mount_kids)
    rocket = node("rocket", children=[
        *[node("motorconfiguration",
               attrs={"configid": c, **({"default": "true"}
                                        if c == default_config else {})})
          for c in dict.fromkeys(list(motor_configs) + [default_config])],
        node("subcomponents", children=[
            node("stage", children=[
                node("subcomponents", children=[
                    node("bodytube", children=[mount])])])])])
    sim_nodes = []
    for spec in sim_specs:
        children = [node("name", spec["name"]),
                    node("conditions", children=[
                        node("configid", spec.get("configid", "cfg-A")),
                        node("windaverage", spec.get("wind", "2.0"))])]
        sim_nodes.append(node("simulation", attrs={"status": spec["status"]},
                              children=children))
    kids = [node("simulations", children=sim_nodes)] if sim_nodes else []
    return node("openrocket", attrs={"version": "230"},
                children=kids + [rocket])


# --------------------------------------------------------------------------
# finite / targets
# --------------------------------------------------------------------------

def test_finite_rejects_bools_and_nonfinite():
    assert sv.finite("123.4") == 123.4
    assert sv.finite(42) == 42.0
    assert sv.finite(True) is None
    assert sv.finite(False) is None
    assert sv.finite(float("nan")) is None
    assert sv.finite(float("inf")) is None
    assert sv.finite(None) is None
    assert sv.finite("abc") is None


def test_sim_targets_drop_bool_and_nonfinite_leaves():
    sim = catalog_sim("S", fd={"maxaltitude": "120.0",
                              "groundhitvelocity": True,
                              "flighttime": float("nan"),
                              "maxvelocity": "70"})
    targets = sv.sim_targets(sim)
    assert targets == {"apogee_m": 120.0, "max_velocity_ms": 70.0,
                       "wind_ms": 2.0}


def test_fill_targets_map_only_real_keys():
    fi = {"apogee_m": 827.0, "ground_hit_mps": 8.04, "flight_time_s": 117.3,
          "max_velocity_mps": 158.0, "rail_exit_mps": 25.2}
    targets = sv.fill_targets(fi)
    assert targets == {"apogee_m": 827.0, "ground_hit_ms": 8.04,
                       "flight_time_s": 117.3, "max_velocity_ms": 158.0,
                       "rail_exit_ms": 25.2}
    # nothing invented: no time_to_apogee / max_mach / wind
    assert "time_to_apogee_s" not in targets
    assert "max_mach" not in targets
    assert "wind_ms" not in targets
    bad = dict(fi, apogee_m=True, flight_time_s=float("nan"))
    assert sv.fill_targets(bad) == {"ground_hit_ms": 8.04,
                                    "max_velocity_ms": 158.0,
                                    "rail_exit_ms": 25.2}


# --------------------------------------------------------------------------
# fill-pipeline result matching
# --------------------------------------------------------------------------

def test_parse_fill_parts_both_stored_shapes():
    assert sv.parse_fill_parts("G71R-10.5 + H225BL-0.0") == [
        ("G71R", 10.5), ("H225BL", 0.0)]
    assert sv.parse_fill_parts("J350-SF+I65W") == [("J350-SF", None),
                                                   ("I65W", None)]
    assert sv.parse_fill_parts("J615ST-20A+465I150-11A") == [
        ("J615ST-20A", None), ("465I150-11A", None)]
    assert sv.parse_fill_parts("I215") == [("I215", None)]


def test_match_single_motor_with_prefix_designation():
    design = [{"manufacturer": "AeroTech", "designation": "I215R",
               "delay": "10.5", "digest": "f49"}]
    fill = {"manufacturer": "AeroTech", "designation": "I215",
            "delay_s": 10.5}
    ok, detail = sv.match_fill_configuration(fill, design)
    assert ok, detail


def test_match_multi_motor_combined_designations():
    design = [{"manufacturer": "AeroTech", "designation": "I65W",
               "delay": "10.8", "digest": "d01"},
              {"manufacturer": "Loki Research", "designation": "J350-SF",
               "delay": "0.0", "digest": "cce"}]
    fill = {"manufacturer": "Loki Research", "designation": "J350-SF+I65W",
            "delay_s": 10.8}
    ok, detail = sv.match_fill_configuration(fill, design)
    assert ok, detail


def test_match_manufacturer_prefix_spelling():
    design = [{"manufacturer": "Cesaroni Technology",
               "designation": "716J280-16A", "delay": "14.5", "digest": "x"}]
    fill = {"manufacturer": "Cesaroni Technology Inc.",
            "designation": "1196J745-P+716J280-16A", "delay_s": 14.5}
    # wrong motor count: two fill parts, one design motor -> no match
    ok, _ = sv.match_fill_configuration(fill, design)
    assert not ok
    fill["designation"] = "716J280-16A"
    ok, detail = sv.match_fill_configuration(fill, design)
    assert ok, detail


@pytest.mark.parametrize("fill,reason_bit", [
    ({"designation": "F10", "manufacturer": "Estes", "delay_s": 3.0},
     "matches no design motor"),
    ({"designation": "C6", "manufacturer": "Estes", "delay_s": 9.0},
     "delay_s"),
    ({"designation": "C6", "manufacturer": "Kosdon", "delay_s": 3.0},
     "manufacturer"),
])
def test_mismatched_fill_provenance_is_not_used(fill, reason_bit):
    design = [{"manufacturer": "Estes", "designation": "C6",
               "delay": "3.0", "digest": "abc"}]
    ok, detail = sv.match_fill_configuration(fill, design)
    assert not ok
    assert reason_bit in detail


def test_fill_count_mismatch_never_substitutes_a_motor():
    two = [{"manufacturer": "Estes", "designation": "C6", "delay": "3.0"},
           {"manufacturer": "Estes", "designation": "D12", "delay": "5.0"}]
    ok, detail = sv.match_fill_configuration(
        {"designation": "C6", "manufacturer": "Estes", "delay_s": 3.0}, two)
    assert not ok and "motor(s)" in detail


# --------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------

def test_select_prefers_uptodate_over_outdated():
    sims = [catalog_sim("S1", "outdated", fd=full_fd()),
            catalog_sim("S2", "uptodate", fd=full_fd(apogee=200))]
    tree = make_tree([{"name": "S1", "status": "outdated", "configid": "cfg-A"},
                      {"name": "S2", "status": "uptodate", "configid": "cfg-A"}])
    pick = sv.select_simulation(sims, tree, "original", None)
    assert pick["label_mode"] == "flight_grounded"
    assert pick["name"] == "S2"
    assert pick["provenance"]["source"] == "catalog_simulation"
    assert pick["targets"]["apogee_m"] == 200
    assert "outdated_saved_results_reference_only" not in pick["flags"]


def test_select_outdated_is_explicit_reference_with_warning():
    sims = [catalog_sim("S1", "outdated", fd=full_fd())]
    tree = make_tree([{"name": "S1", "status": "outdated", "configid": "cfg-A"}])
    pick = sv.select_simulation(sims, tree, "original", None)
    assert pick["label_mode"] == "flight_grounded"
    assert "outdated_saved_results_reference_only" in pick["flags"]
    assert "saved_simulation_not_uptodate" in pick["flags"]


def test_select_requires_positive_apogee_and_landing_speed():
    sims = [catalog_sim("S1", "uptodate", fd=full_fd(apogee=0)),
            catalog_sim("S2", "uptodate", fd=full_fd(ground=-1)),
            catalog_sim("S3", "uptodate", fd=full_fd(apogee=float("nan")))]
    specs = [{"name": f"S{i}", "status": "uptodate", "configid": "cfg-A"}
             for i in (1, 2, 3)]
    pick = sv.select_simulation(sims, make_tree(specs), "original", None)
    assert pick["label_mode"] == "hardware_only"
    assert pick["targets"] == {}
    assert "hardware_only_no_flight_labels" not in pick["flags"]  # phase E adds it


def test_select_requires_motors_populated_for_that_config():
    sims = [catalog_sim("S1", "uptodate", configid="cfg-empty", fd=full_fd())]
    tree = make_tree([{"name": "S1", "status": "uptodate",
                       "configid": "cfg-empty"}],
                      motor_configs=("cfg-empty",), default_config="cfg-empty")
    # motor blocks without digest/designation children do not count as populated
    pick = sv.select_simulation(sims, tree, "original", None)
    assert pick["label_mode"] == "hardware_only"


def test_select_hardware_only_prefers_populated_default_config():
    sims = [catalog_sim("S-empty", "notsimulated", configid="cfg-B"),
            catalog_sim("S-motor", "cantrun", configid="cfg-A")]
    tree = make_tree([{"name": "S-empty", "status": "notsimulated",
                        "configid": "cfg-B"},
                       {"name": "S-motor", "status": "cantrun",
                        "configid": "cfg-A"}])
    pick = sv.select_simulation(sims, tree, "original", None)
    assert pick["label_mode"] == "hardware_only"
    assert pick["name"] == "S-motor"
    assert pick["status"] == "cantrun"
    assert pick["configid"] == "cfg-A"


def test_select_duplicate_names_uses_catalog_index():
    # two sims share a name; the uptodate one is the SECOND XML instance
    sims = [catalog_sim("Atlas", "outdated", configid="cfg-A", fd=full_fd(999)),
            catalog_sim("B", "notsimulated", configid="cfg-B"),
            catalog_sim("Atlas", "uptodate", configid="cfg-A", fd=full_fd(55))]
    tree = make_tree([{"name": "Atlas", "status": "outdated", "configid": "cfg-A"},
                      {"name": "B", "status": "notsimulated", "configid": "cfg-B"},
                      {"name": "Atlas", "status": "uptodate", "configid": "cfg-A"}])
    pick = sv.select_simulation(sims, tree, "original", None)
    assert pick["name"] == "Atlas"
    assert pick["sim_index"] == 2
    assert pick["targets"]["apogee_m"] == 55  # the uptodate instance's data


def test_select_catalog_xml_mismatch_is_hardware_only():
    sims = [catalog_sim("S1", "uptodate", fd=full_fd())]
    # XML disagrees with the catalog entry (different status)
    tree = make_tree([{"name": "S1", "status": "notsimulated",
                       "configid": "cfg-A"}])
    pick = sv.select_simulation(sims, tree, "original", None)
    assert pick["label_mode"] == "hardware_only"


def test_select_no_sims_is_config_only_hardware_record():
    tree = make_tree([], motor_configs=("cfg-A", "cfg-B"),
                     default_config="cfg-A")
    pick = sv.select_simulation([], tree, "original", None)
    assert pick["sim_index"] is None
    assert pick["name"] is None
    assert pick["label_mode"] == "hardware_only"
    assert "no_simulations_in_design" in pick["flags"]
    assert pick["configid"] == "cfg-A"


def test_select_fill_pipeline_result_used_despite_notsimulated():
    sims = [catalog_sim("filled", "notsimulated", configid="cfg-F")]
    tree = make_tree([{"name": "filled", "status": "notsimulated",
                       "configid": "cfg-F"}],
                      motor_configs=("cfg-F",), default_config="cfg-F")
    fill = {"manufacturer": "Estes", "designation": "C6", "delay_s": 3.0,
            "apogee_m": 250.0, "ground_hit_mps": 4.4, "flight_time_s": 40.0}
    pick = sv.select_simulation(sims, tree, "motor_filled", fill)
    assert pick["label_mode"] == "flight_grounded"
    assert pick["provenance"]["source"] == "fill_pipeline"
    assert pick["targets"]["apogee_m"] == 250.0
    assert pick["targets"]["ground_hit_ms"] == 4.4
    assert "fill_pipeline_metrics_not_resimulated" in pick["flags"]


def test_select_fill_mismatch_keeps_hardware_only():
    sims = [catalog_sim("filled", "notsimulated", configid="cfg-F")]
    tree = make_tree([{"name": "filled", "status": "notsimulated",
                       "configid": "cfg-F"}],
                      motor_configs=("cfg-F",), default_config="cfg-F")
    fill = {"manufacturer": "Estes", "designation": "D12", "delay_s": 5.0,
            "apogee_m": 250.0}
    pick = sv.select_simulation(sims, tree, "motor_filled", fill)
    assert pick["label_mode"] == "hardware_only"
    assert pick["targets"] == {}
    assert "fill_result_configuration_mismatch" in pick["flags"]
    assert "not used" in pick["provenance"]["notes"]


def test_select_partial_trusted_metrics_stay_honest():
    # trusted sim with apogee but no landing speed: not promptable as grounded
    sims = [catalog_sim("S1", "outdated", fd={"maxaltitude": 1251.0,
                                              "flighttime": 6.198})]
    tree = make_tree([{"name": "S1", "status": "outdated", "configid": "cfg-A"}])
    pick = sv.select_simulation(sims, tree, "original", None)
    assert pick["label_mode"] == "hardware_only"
    assert pick["targets"]["apogee_m"] == 1251.0  # real saved metrics kept
    assert "ground_hit_ms" not in pick["targets"]
    assert "saved_metrics_partial_no_landing_speed" in pick["flags"]


# --------------------------------------------------------------------------
# no-simulation compact round trip (pure, flight-free)
# --------------------------------------------------------------------------

def _no_sim_full(digestless=False):
    motor = (motor_block("cfg-A", digest=None, designation="H128W",
                         manufacturer="AeroTech", delay="6.0",
                         diameter="0.029", length="0.194")
             if digestless else
             motor_block("cfg-A", digest="dg1", designation="C6",
                         manufacturer="Estes", delay="3.0"))
    tree = node("openrocket", attrs={"version": "230"}, children=[
        node("rocket", attrs={"creator": "junk"}, children=[
            node("motorconfiguration",
                 attrs={"configid": "cfg-A", "default": "true"}),
            node("motorconfiguration", attrs={"configid": "cfg-B"}),
            node("subcomponents", children=[
                node("stage", children=[
                    node("subcomponents", children=[
                        node("bodytube", attrs={"color": "#ff0000"},
                             children=[node("length", "0.4"),
                                       node("motormount", children=[motor])])])])]),
        ]),
    ])
    return {"parameter_tree": tree, "bundle_entries": {}}


def test_to_compact_config_round_trip_static_pass():
    full = _no_sim_full()
    compact = sv.to_compact_config(full, "cfg-A")
    # only the default config's elements survive, placeholdered
    rocket = compact["openrocket"]["children"][0]["rocket"]
    configs = [w["motorconfiguration"] for w in
               next(c["rocket"] for c in compact["openrocket"]["children"]
                    if "rocket" in c)["children"]
               if "motorconfiguration" in w]
    assert [c["attrs"]["configid"] for c in configs] == ["cfg0"]
    check = sv.static_check_config(full, "cfg-A")
    assert check["pass"], check["differences"]


def test_static_check_config_detects_lost_geometry():
    full = _no_sim_full()
    # sabotage: expect the second config too -> round trip keeps only cfg-A
    check = sv.static_check_config(full, "cfg-B")
    assert not check["pass"]
    assert any("motorconfiguration" in d for d in check["differences"])


def test_read_full_design_no_sims_has_no_simulation_block():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "nosim.ork"
        write_ork_archive(src, _no_sim_full()["parameter_tree"],
                          container={"format": "plain_xml"})
        full = sv.read_full_design(src, None)
        assert full["selected_simulation"] is None
        tags = [c["tag"] for c in full["parameter_tree"]["children"]]
        assert "simulations" not in tags


# --------------------------------------------------------------------------
# design-side motors, lookup pairing, digestless identities
# --------------------------------------------------------------------------

def _mini_compact(digests=("dg1", None, "dg3")):
    """Compact with three mounts: the middle motor block has no digest."""
    mount_kids = []
    for i, d in enumerate(digests):
        if d is None:
            mount_kids.append(
                node("motormount", children=[motor_block(
                    "cfg0", digest=None, designation=f"M{i}",
                    manufacturer="Estes", delay="4.0")]))
        else:
            mount_kids.append(
                node("motormount", children=[motor_block(
                    "cfg0", digest=d, designation=f"M{i}",
                    manufacturer="Estes", delay="4.0")]))
    body = node("bodytube", children=mount_kids)
    rocket = node("rocket", children=[
        node("subcomponents", children=[
            node("stage", children=[
                node("subcomponents", children=[body])])])])
    compact = {"openrocket": {"children": [{"rocket": rocket}]}}
    return compact


def test_dataset_motor_entries_pair_mounts_by_index_no_shift():
    # mount 0 resolves, mount 1 is unresolved (motor None), mount 2 resolves:
    # the old zip(design blocks, resolved motors) lost/shifted entries here.
    compact = _mini_compact()
    eng = {"motors": [
        {"motor": {"total_impulse_ns": 10.0, "burn_time_s": 1.0,
                   "average_thrust_n": 10.0}},
        {"motor": None},
        {"motor": {"total_impulse_ns": 30.0, "burn_time_s": 2.0,
                   "average_thrust_n": 15.0}}]}
    entries = sv.collect_dataset_motor_entries(
        [{"catalog_id": "x", "compact": compact, "engineering": eng}])
    by_digest = {e["digest"]: e for e in entries}
    assert set(by_digest) == {"dg1", "dg3"}  # digest-less block not here
    assert by_digest["dg1"]["total_impulse_ns"] == 10.0
    assert by_digest["dg3"]["total_impulse_ns"] == 30.0  # no shift


def test_dataset_motor_entries_keep_unresolved_digests():
    compact = _mini_compact(digests=("dgX",))
    eng = {"motors": [{"motor": None}]}  # database cannot resolve it
    entries = sv.collect_dataset_motor_entries(
        [{"catalog_id": "x", "compact": compact, "engineering": eng}])
    assert [e["digest"] for e in entries] == ["dgX"]
    assert entries[0]["total_impulse_ns"] is None
    assert entries[0]["manufacturer"] == "Estes"


def test_digestless_identities_readable_deterministic_not_hashes():
    compact = _mini_compact(digests=(None, None))
    registry = sv.digestless_identities(
        [{"catalog_id": "r1", "compact": compact,
          "engineering": {"motors": [
              {"motor": {"digest": "resolved-1"}},
              {"motor": {"digest": "resolved-2"}}]}}])
    assert set(registry) == {"Estes-M0", "Estes-M1"}
    entry = registry["Estes-M0"]
    assert entry["resolved_digest"] == "resolved-1"
    assert entry["used_by"] == ["r1"]
    for identity in registry:
        assert not re.fullmatch(r"[0-9a-f]{8,}", identity.split("-")[-1])


def test_json_line_rejects_nan():
    with pytest.raises(ValueError):
        sv.json_line({"a": float("nan")})


# --------------------------------------------------------------------------
# end to end on a synthetic workspace (jvm=False, no fabricated checks)
# --------------------------------------------------------------------------

def _build_workspace(tmp_path: Path):
    ws = tmp_path / "ws"
    (ws / "ork").mkdir(parents=True)
    (ws / "ork_filled").mkdir(parents=True)
    (ws / "data").mkdir()

    good_xml = """<openrocket version="230">
 <rocket>
  <motorconfiguration configid="cfg-A" default="true"/>
  <subcomponents><stage><subcomponents>
   <bodytube><length>0.30</length>
    <motormount><motor configid="cfg-A">
     <manufacturer>Estes</manufacturer><digest>dg-good-1</digest>
     <designation>C6</designation><diameter>0.018</diameter>
     <length>0.07</length><delay>3.0</delay></motor></motormount>
   </bodytube></subcomponents></stage></subcomponents>
 </rocket>
 <simulations><simulation status="uptodate"><name>Sim 1</name>
  <conditions><configid>cfg-A</configid><windaverage>2.0</windaverage>
  </conditions></simulation></simulations>
</openrocket>"""
    (ws / "ork" / "A.ork").write_text(good_xml)

    nosim_xml = """<openrocket version="230">
 <rocket>
  <motorconfiguration configid="cfg-A" default="true"/>
  <motorconfiguration configid="cfg-B"/>
  <subcomponents><stage><subcomponents>
   <bodytube><length>0.25</length>
    <motormount><motor configid="cfg-A">
     <manufacturer>AeroTech</manufacturer><designation>H128W</designation>
     <diameter>0.029</diameter><length>0.194</length><delay>6.0</delay>
    </motor></motormount></bodytube>
  </subcomponents></stage></subcomponents>
 </rocket>
</openrocket>"""
    (ws / "ork" / "B.ork").write_text(nosim_xml)

    filled_xml = """<openrocket version="230">
 <rocket>
  <motorconfiguration configid="cfg-F" default="true"/>
  <subcomponents><stage><subcomponents>
   <bodytube><length>0.60</length>
    <motormount><motor configid="cfg-F">
     <manufacturer>Estes</manufacturer><digest>dg-fill-1</digest>
     <designation>C6</designation><diameter>0.018</diameter>
     <length>0.07</length><delay>3.0</delay></motor></motormount>
   </bodytube></subcomponents></stage></subcomponents>
 </rocket>
 <simulations><simulation status="notsimulated"><name>filled</name>
  <conditions><configid>cfg-F</configid></conditions></simulation>
 </simulations>
</openrocket>"""
    (ws / "ork_filled" / "C_filled.ork").write_text(filled_xml)

    # custom-curve rocket: zip container with a thrustcurves/ attachment
    curve = b"<rse>fake curve bytes</rse>"
    custom_tree = parse_openrocket_xml(good_xml.replace(
        "dg-good-1", "e5b53def203dd437ebf0d67846f6cd3b").encode())
    write_ork_archive(ws / "ork" / "D.ork", custom_tree,
                      container={"format": "zip"},
                      bundle_entries={
                          "thrustcurves/e5b53def203dd437ebf0d67846f6cd3b.rse":
                          curve})

    sim_fd = {"@maxaltitude": "120.0", "@groundhitvelocity": "5.0",
              "@flighttime": "30.0"}
    catalog = [
        {"id": "original:A.ork", "source_file": "A.ork", "origin": "original",
         "simulations": [{"@status": "uptodate", "name": "Sim 1",
                          "conditions": {"configid": "cfg-A",
                                         "windaverage": "2.0"},
                          "flightdata": sim_fd}],
         "source_repo": "t", "looks_machine_generated": False,
         "motor_chosen_by_pipeline": False, "openrocket_version": "230"},
        {"id": "original:B.ork", "source_file": "B.ork", "origin": "original",
         "simulations": [], "source_repo": "t",
         "looks_machine_generated": False,
         "motor_chosen_by_pipeline": False, "openrocket_version": "230"},
        {"id": "motor_filled:C.ork", "source_file": "C.ork",
         "origin": "motor_filled",
         "simulations": [{"@status": "notsimulated", "name": "filled",
                          "conditions": {"configid": "cfg-F"}}],
         "fill_info": {"manufacturer": "Estes", "designation": "C6",
                       "delay_s": 3.0, "apogee_m": 250.0,
                       "ground_hit_mps": 4.4, "flight_time_s": 40.0,
                       "max_velocity_mps": 60.0, "rail_exit_mps": 12.0},
         "source_repo": "t", "looks_machine_generated": False,
         "motor_chosen_by_pipeline": True, "openrocket_version": "230"},
        {"id": "original:D.ork", "source_file": "D.ork", "origin": "original",
         "simulations": [{"@status": "uptodate", "name": "Sim 1",
                          "conditions": {"configid": "cfg-A",
                                         "windaverage": "2.0"},
                          "flightdata": sim_fd}],
         "source_repo": "t", "looks_machine_generated": False,
         "motor_chosen_by_pipeline": False, "openrocket_version": "230"},
    ]
    catalog_path = ws / "data" / "rockets_full.jsonl"
    catalog_path.write_text("".join(json.dumps(r) + "\n"
                                    for r in catalog))

    db_path = tmp_path / "motor_db.json"
    db_path.write_text(json.dumps([
        {"manufacturer": "Estes", "designation": "C6",
         "digest": "dg-good-1", "diameter_m": 0.018, "length_m": 0.07,
         "total_impulse_ns": 8.8, "burn_time_s": 1.8,
         "average_thrust_n": 4.7},
        {"manufacturer": "Estes", "designation": "A8",
         "digest": "e5b53def203dd437ebf0d67846f6cd3b", "diameter_m": 0.018,
         "length_m": 0.07, "total_impulse_ns": 2.5, "burn_time_s": 0.7,
         "average_thrust_n": 3.5}]))
    v3_train = tmp_path / "v3_train.jsonl"
    v3_test = tmp_path / "v3_test.jsonl"
    v3_train.write_text("")
    v3_test.write_text("")
    v3_lookup = tmp_path / "v3_lookup.json"
    v3_lookup.write_text(json.dumps({
        "Old-Motor": {"manufacturer": "Estes", "designation": "C6",
                      "digest": "dg-good-1", "diameter_m": 0.018,
                      "length_m": 0.07, "total_impulse_ns": 8.8,
                      "burn_time_s": 1.8, "average_thrust_n": 4.7}}))
    return ws, catalog_path, db_path, [v3_train, v3_test, v3_lookup]


def test_run_emits_every_catalog_row_in_order_with_contract(tmp_path):
    ws, catalog_path, db_path, v3 = _build_workspace(tmp_path)
    out = tmp_path / "out"
    summary = sv.run(out, ws, catalog_path, jvm=False,
                     motor_db_path=db_path, v3_paths=v3)
    assert summary["catalog_rows"] == 4
    assert summary["records_emitted"] == 4
    assert summary["catalog_id_order_match"] is True
    assert summary["catalog_id_set_equal"] is True
    assert summary["flight_simulations_run"] == 0

    records = [json.loads(l) for l in
               (out / "sources.jsonl").read_text().splitlines() if l.strip()]
    assert [r["catalog_id"] for r in records] == [
        "original:A.ork", "original:B.ork", "motor_filled:C.ork",
        "original:D.ork"]
    for rec in records:
        assert list(rec.keys())[:5] == ["catalog_id", "source_id",
                                        "source_file", "origin", "file"]
        assert rec["source_id"] == rec["catalog_id"]
        assert Path(rec["file"]).is_absolute()
        assert "saved_flight_not_rerun" in rec["flags"]
        assert rec["compact"], rec["catalog_id"]
        assert rec["engineering"]["unavailable"].startswith("JVM disabled")
        assert rec["digest_entry"]["c_pass"] is False  # not verified, honestly
        assert "load_equivalence_not_verified" in rec["flags"]

    by = {r["catalog_id"]: r for r in records}
    a = by["original:A.ork"]
    assert a["label_mode"] == "flight_grounded"
    assert a["targets"]["apogee_m"] == 120.0
    assert a["metric_provenance"]["source"] == "catalog_simulation"
    assert a["model_compact"] is not None

    b = by["original:B.ork"]
    assert b["label_mode"] == "hardware_only"
    assert b["sim"] is None
    assert b["simulation_status"] == "unavailable"
    assert b["targets"] == {}
    assert "no_simulations_in_design" in b["flags"]
    assert "hardware_only_no_flight_labels" in b["flags"]
    assert "motor_block_without_digest" in b["flags"]
    assert b["source_preservation"]["digestless_motor_identities"] == \
        ["AeroTech-H128W"]
    # full hardware tree preserved: bodytube length and motor setup intact
    rocket = b["compact"]["openrocket"]["children"][0]["rocket"]
    body = rocket["children"][0]["subcomponents"]["children"][0][
        "stage"]["children"][0]["subcomponents"]["children"][0]["bodytube"]
    assert body["children"][0]["length"]["value"] == 0.25
    assert "simulations" not in [w for c in
                                 b["compact"]["openrocket"]["children"]
                                 for w in c.keys()]

    c = by["motor_filled:C.ork"]
    assert c["label_mode"] == "flight_grounded"
    assert c["metric_provenance"]["source"] == "fill_pipeline"
    assert c["targets"] == {"apogee_m": 250.0, "ground_hit_ms": 4.4,
                            "flight_time_s": 40.0, "max_velocity_ms": 60.0,
                            "rail_exit_ms": 12.0}
    assert c["simulation_status"] == "notsimulated"
    assert "fill_pipeline_metrics_not_resimulated" in c["flags"]

    d = by["original:D.ork"]
    assert "custom_thrust_curve_attachments" in d["flags"]
    assert list(d["compact"]["attachments"]) == [
        "thrustcurves/e5b53def203dd437ebf0d67846f6cd3b.rse"]
    assert "attachments" not in (d["model_compact"] or {})
    assert d["source_preservation"]["assets"]["entries"][0][
        "attachment_name"] == "thrustcurves/e5b53def203dd437ebf0d67846f6cd3b.rse"

    assets = json.loads((out / "assets.json").read_text())
    assert assets["schema"] == "sft_v4_assets-1"
    entry = assets["assets"]["Estes-A8"]
    assert entry["used_by"] == ["original:D.ork"]
    assert base64.b64decode(entry["data_base64"]) == b"<rse>fake curve bytes</rse>"
    assert "restore_path" in assets
    assert "digestless_identities" in assets

    lookup = json.loads((out / "motor_lookup.json").read_text())
    digests = {v["digest"] for v in lookup.values()}
    assert {"dg-good-1", "dg-fill-1",
            "e5b53def203dd437ebf0d67846f6cd3b"} <= digests
    assert summary["motor_lookup"]["all_design_digests_in_lookup"] is True
    # v3 identity preserved for shared digests
    assert "Old-Motor" in lookup


def test_run_limit_and_id_mismatch_guard(tmp_path):
    ws, catalog_path, db_path, v3 = _build_workspace(tmp_path)
    out = tmp_path / "out_limit"
    summary = sv.run(out, ws, catalog_path, limit=2, jvm=False,
                     motor_db_path=db_path, v3_paths=v3)
    assert summary["records_emitted"] == 2
    assert summary["limit_run"] is True


def test_run_missing_source_file_is_honest_not_silent(tmp_path):
    ws, catalog_path, db_path, v3 = _build_workspace(tmp_path)
    (ws / "ork" / "A.ork").unlink()
    out = tmp_path / "out_missing"
    summary = sv.run(out, ws, catalog_path, jvm=False,
                     motor_db_path=db_path, v3_paths=v3)
    assert summary["records_emitted"] == 4  # still one record per row
    records = [json.loads(l) for l in
               (out / "sources.jsonl").read_text().splitlines() if l.strip()]
    a = next(r for r in records if r["catalog_id"] == "original:A.ork")
    assert a["compact"] is None
    assert "source_file_missing" in a["flags"]
