"""Fixed constants shared by every stage of the SFT data pipeline.

Anything here is part of the data contract (DATA_SPEC.md): changing a value
means bumping CONTRACT_VERSION and regenerating every row.
"""

from __future__ import annotations

CONTRACT_VERSION = "sft-v2.1"
OPENROCKET_VERSION = "24.12"
MOTOR_DB_VERSION = "OpenRocket 24.12 bundled thrustcurve.org database"

SYSTEM_PROMPT = (
    "You design amateur rockets that fly on certified commercial motors. Work through "
    "the design, check it with the tools, and give the final design as JSON inside "
    "<design> tags. Only report results the tools returned."
)

# Step headings. Each assistant reasoning block opens its sections with
# "<n>. <Heading>:" at the start of a line. Step 4 is written "4. Draft:" when a
# design is proposed and "4. Check:" when a simulate/stability result is read.
STEP_HEADINGS = {
    1: ("Understand",),
    2: ("Feasibility",),
    3: ("Size",),
    4: ("Draft", "Check"),
    5: ("Fix",),
    6: ("Uncertainty",),
}
STEP_HEADING_REGEX = r"(?m)^([1-6])\. (Understand|Feasibility|Size|Draft|Check|Fix|Uncertainty):"

# Words that claim a number came from a tool. Allowed only in an assistant turn
# that directly follows the tool turn which returned the number being claimed.
PROVENANCE_WORDS = ("verified", "simulated", "confirmed", "openrocket gives", "the simulator gives", "simulation shows")
BANNED_PHRASES = ("measured in the flight data", "flight data shows", "measured at ignition")

# Safety gates (section 7.2).
GATES = {
    "min_thrust_to_weight": 3.0,
    "min_rail_exit_ms": 15.0,
    "min_launch_margin_cal": 1.0,
    "min_burn_margin_cal": 0.0,
    "default_max_landing_ms": 6.0,
    "max_total_impulse_ns": 40960.0,
    "max_wind_ms": 8.94,  # 20 mph
}

# Target tolerances (section 7.3), fixed before generation.
TOLERANCES = {
    "about_rel": 0.05,       # "about X": within +-5 %
    "about_rel_time": 0.10,  # "about X s" for time windows: +-10 %
}

TARGET_KINDS = ("about", "min", "max", "exact", "range")

# Allowed keys in a row's "targets". Each value is {"value": ..., "kind": ...};
# "range" values are [lo, hi]. Only keys the prompt actually asks for appear.
TARGET_KEYS = {
    "apogee_m": "number; about/min/max/range",
    "ground_hit_ms": "number; max; optional \"applies_to\": \"every section\"",
    "flight_time_s": "number; max/range (only when the prompt gives a reason)",
    "time_to_apogee_s": "number; about/range (competition prompts only)",
    "motor": "list of designations; exact (normalised: case, spaces, delay suffix stripped)",
    "motor_class": "letter A-O; max (e.g. Level 1 => \"I\")",
    "motor_diameter_m": "number; max",
    "body_diameter_m": "number; max (largest external diameter)",
    "total_impulse_ns": "number; max",
    "stages": "int; exact",
    "motor_count": "int; exact (clusters / multi-stage)",
    "payload_kg": "number; min (a mass item named like 'payload' of at least this mass)",
    "recovery": "\"single_chute\" | \"streamer\" | \"dual_deploy\"; exact",
    "drift_m": "number; max (landing distance from pad, every section)",
    "feasible": "false; exact (infeasible prompts only: the answer must say infeasible)",
}

# Tool output shapes (JSON objects serialised into the tool turn's content).
MOTOR_LOOKUP_OUTPUT = {
    "ok": True, "manufacturer": "Estes", "designation": "C6", "class": "C",
    "total_impulse_ns": 8.8, "average_thrust_n": 4.8, "max_thrust_n": 14.1, "burn_time_s": 1.83,
    "diameter_m": 0.018, "length_m": 0.07, "loaded_mass_kg": 0.0231, "propellant_mass_kg": 0.0108,
    "delays_s": [0, 3, 5, 7], "type": "single-use",
}
STABILITY_OUTPUT = {
    "ok": True, "liftoff_mass_kg": 0.061, "cg_m": 0.322, "cp_m": 0.371, "length_m": 0.56,
    "reference_diameter_m": 0.0249, "static_margin_cal": 1.97,
}
SIMULATE_OUTPUT = {
    "ok": True,
    "apogee_m": 245.3, "time_to_apogee_s": 6.12, "max_velocity_ms": 92.4, "max_mach": 0.27,
    "rail_exit_ms": 14.2, "liftoff_mass_kg": 0.061, "thrust_to_weight": 8.0,
    "stability_rail_exit_cal": 2.31, "min_stability_burn_cal": 2.05, "flight_time_s": 38.4,
    "total_impulse_ns": 8.8,
    "sections": [
        {"name": "Sustainer", "landing_ms": 4.1, "drift_m": 55.0, "recovery_deployed": True,
         "deploy_time_s": 7.9, "deploy_velocity_ms": 12.0, "flight_time_s": 38.4},
    ],
    "warnings": [],
    "conditions": {"wind_ms": 2.0, "rail_length_m": 1.5, "launch_angle_deg": 0.0, "site_altitude_m": 0.0},
}
TOOL_ERROR_OUTPUT = {"ok": False, "error": "unknown motor 'C7'", "suggestions": ["C6", "C5"]}

DEFAULT_SIM_CONDITIONS = {
    "rail_length_m": 1.5,
    "launch_angle_deg": 0.0,
    "wind_ms": 2.0,
    "wind_turbulence": 0.1,
    "site_altitude_m": 0.0,
    "time_step_s": 0.05,
    "seed": 0,  # always overwritten per row
}

FIX_ROUND_CAP = 3

# Message shapes (OpenAI / Qwen chat-template style):
#   {"role": "assistant", "reasoning_content": str, "content": "",
#    "tool_calls": [{"id": "call_1", "type": "function",
#                    "function": {"name": "simulate", "arguments": {...}}}]}
#   {"role": "tool", "tool_call_id": "call_1", "name": "simulate", "content": "<json>"}
# Tool messages follow their assistant turn in tool_calls order. The final
# assistant turn has reasoning_content and content (summary + one <design> block)
# and no tool_calls. Tool content is json.dumps(output, ensure_ascii=False).
FINAL_SUMMARY_MAX_LINES = 4
TOOL_NAMES = ("motor_lookup", "stability", "simulate")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "motor_lookup",
            "description": (
                "Look up a certified motor in the pinned motor database. Returns total impulse, "
                "average and peak thrust, burn time, diameter, length, loaded and propellant "
                "mass, and available ejection delays. Returns an error for unknown motors."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "designation": {"type": "string", "description": "Motor designation, e.g. \"C6\", \"H128W\", \"I300T\"."},
                    "manufacturer": {"type": "string", "description": "Optional manufacturer, e.g. \"Estes\", \"AeroTech\"."},
                },
                "required": ["designation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stability",
            "description": (
                "Static stability of a design at launch with motors loaded: liftoff mass, CG and CP "
                "from the nose tip, reference diameter and static margin in calibers. No flight is simulated."
            ),
            "parameters": {
                "type": "object",
                "properties": {"design": {"type": "object", "description": "Design JSON in the <design> schema."}},
                "required": ["design"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simulate",
            "description": (
                "Fly the design in OpenRocket from rail to ground. Returns apogee, time to apogee, max "
                "velocity and Mach, rail-exit speed, thrust-to-weight, stability at rail exit and minimum "
                "during the burn, flight time, landing speed (vertical descent rate at touchdown) and "
                "drift per section, and warnings."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "design": {"type": "object", "description": "Design JSON in the <design> schema."},
                    "conditions": {
                        "type": "object",
                        "description": "Optional launch conditions; omitted fields use the site defaults.",
                        "properties": {
                            "wind_ms": {"type": "number"},
                            "rail_length_m": {"type": "number"},
                            "launch_angle_deg": {"type": "number"},
                            "site_altitude_m": {"type": "number"},
                        },
                    },
                },
                "required": ["design"],
            },
        },
    },
]
