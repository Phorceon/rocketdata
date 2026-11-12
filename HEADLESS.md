# Headless OpenRocket simulation (no GUI)

Run OpenRocket simulations from Python with no window, for automated pipeline
and RL use. This drives OpenRocket 24.12's own Java engine through
[orhelper](https://github.com/openrocket/orhelper) (a thin JPype wrapper), so the
numbers come from OpenRocket itself.

`scripts/or_headless.py` exposes one function:

```python
from scripts.or_headless import simulate

simulate("meta/ork/ESTES Alpha 3.ork")             # first simulation in the file
simulate("meta/ork/Skyshot.ork", "Simulation 5")   # by name
```

It returns `apogee_m`, `max_velocity_ms`, `time_to_apogee_s`, `flight_time_s`,
`ground_hit_ms`, `max_accel_ms2`, `stability_cal`, and `runtime_ms`. Simulation
summary values come straight from OpenRocket's `SimulatedData`; `stability_cal`
is computed as `(CP − CG) / max diameter` at the first step where CP is valid.

## Setup

Do this once. macOS (Apple Silicon) is what this was tested on.

> **Do not use Apple's built-in Python.** The system Python at
> `/usr/bin/python3` lacks the hardened-runtime JIT entitlement the JDK needs, so
> the JVM aborts in `CodeHeap::allocate` the moment JPype starts it. Use a
> uv-managed Python instead.

```bash
# 1. Install uv (if you don't have it): https://docs.astral.sh/uv/
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. A standalone Python 3.11 (arm64 on Apple Silicon; do not use system Python)
uv python install 3.11

# 3. Create the venv and install the pinned dependencies
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements-headless.txt

# 4. Temurin JDK 17 into ~/.jdks (no sudo, no system-wide changes)
mkdir -p ~/.jdks && cd ~/.jdks
curl -sL -o temurin17.tar.gz \
  "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20.1%2B1/OpenJDK17U-jdk_aarch64_mac_hotspot_17.0.20.1_1.tar.gz"
tar -xzf temurin17.tar.gz && rm temurin17.tar.gz && cd -

# 5. Download the OpenRocket 24.12 JAR into lib/ (gitignored)
bash scripts/fetch_openrocket.sh

# 6. Smoke test: one simulation, checks the numbers are sane
.venv/bin/python -m pytest tests/test_openrocket_smoke.py -v
```

`scripts/or_headless.py` looks for the JDK at
`~/.jdks/jdk-17.0.20.1+1/Contents/Home` and the JAR at `lib/OpenRocket.jar`.
Override with `OPENROCKET_JAVA_HOME` and `OPENROCKET_JAR` (only these variables
are read — nothing system-wide is changed).

Run one simulation from the command line:

```bash
.venv/bin/python -m scripts.or_headless "meta/ork/ESTES Alpha 3.ork"
```

## Performance and known issues

- **Speed:** about **400 ms per simulation** on an M-series Mac (40 ms for the
  smallest rockets, up to ~1.6 s for a 16 km flight). The target for RL is
  **< 50 ms per sim**, so this is roughly 8× too slow. The cost is JVM startup
  and OpenRocket's own solver; a long-lived JVM (already done here) removes the
  restart cost, but per-sim solver time remains. Speeding this up is open work.
- **`falconHeavey.ork` / `Simulation 5`:** our headless flight time differs from
  the value stored in the `.ork` by **42%** (apogee differs 7.8%). The stored
  simulation likely used a different configuration or wind than the one we run.
  Still to investigate.
- Validation against 10 rockets re-simulated from `new_results/sft_v1.jsonl`
  (small, mid and high power): apogee within ~2.6% for 9 of 10, flight time
  within ~2% for 8 of 10. Small differences from the stored values are expected —
  they were produced by different OpenRocket versions and random wind.

## Determinism

Out of the box OpenRocket 24.12 does not give the same numbers twice for the same file
and seed. `simulate()` fixes the three causes, using helpers in
`scripts/or_batch/OrBatch.java` (compiled automatically into `lib/or_batch_classes/`
with the JDK's `javac` on first use):

1. **Wind.** `SimulationOptions` builds its pink-noise wind models from a random seed when
   it is constructed, and `setRandomSeed()` does not reseed them. They are rebuilt from
   `seed`.
2. **Component UUIDs.** Older `.ork` files store no component ids, so every load assigns
   `UUID.randomUUID()`. Those UUIDs key OpenRocket's motor map, so the motor iteration
   order, and with it the result of multi-motor and multi-stage sims (up to about 6% here),
   changes from load to load. A seeded `SecureRandom` provider is installed before
   OpenRocket boots, and every call loads the file fresh with UUID seed 42.
3. **First-run caches.** The first run of a design in a JVM differs from later runs at
   about 1e-14. One discarded warm-up run per (file, sim) is done.

With these fixes the same inputs give bit-identical outputs, and the numbers match
`scripts/resim_v2.py` and `new_results/sft_v2_sims.jsonl`. `simulate()` also returns
`events`, the flight events per branch (`RECOVERY_DEVICE_DEPLOYMENT`, `GROUND_HIT`, …).
