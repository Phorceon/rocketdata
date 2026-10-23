# SFT_V2_REPORT

- Rows kept (v1 train): 177 / 182 (dropped 5)
- Rows kept (test): see sft_test_v2.jsonl
- Rows dropped (train): [['U-023', 'ork/openrocketdoc__example_simple_1.ork', 'Simulation 1', 'info.openrocket.core.util.BugException: BUG: Simulation resu'], ['U-042', 'ork/openrocketdoc__example_simple_1.ork', 'Simulation 1', 'info.openrocket.core.util.BugException: BUG: Simulation resu'], ['U-061', 'ork/openrocketdoc__example_simple_1.ork', 'Simulation 1', 'info.openrocket.core.util.BugException: BUG: Simulation resu'], ['U-062', 'ork/openrocketdoc__example_simple_1.ork', 'Simulation 1', 'info.openrocket.core.util.BugException: BUG: Simulation resu'], ['U-063', 'ork/openrocketdoc__example_simple_1.ork', 'Simulation 1', 'info.openrocket.core.util.BugException: BUG: Simulation resu']]
- Rows dropped (test): [['U-180', 'ork/aerotech_arreaux.ork', 'Simulation 1', '"simulation \'Simulation 1\' not found; available: [\'Simulatio']]
- Flagged >10% changes (train): 186
- Avg % change: apogee 7.04%, flight_time 15.95%, ground_hit nan%, max_vel 3.96%, t_apogee 5.34%

## How to rebuild
```bash
git checkout sft-v2-resim
PYTHONPATH=/Users/dev/rocketdata:/Users/dev/rocketdata/scripts:/Users/dev/rocketdata/.venv/lib/python3.11/site-packages OPENROCKET_JAR=/Users/dev/rocketdata/lib/OpenRocket.jar OPENROCKET_JAVA_HOME=/Users/dev/.jdks/jdk-17.0.20.1+1/Contents/Home .venv/bin/python scripts/build_sft_v2.py
```