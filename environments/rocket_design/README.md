# rocket-design

A `verifiers` environment for RL on rocket design. It's built for verifiers 0.4+, the v1 API (taskset / task / `@vf.reward`). It runs self-hosted, so there's no Prime sandbox and no API key.

- **Prompt:** a mission, e.g. "Design a rocket that reaches about 900 m and lands under 6 m/s". It's sent with the system prompt the v5 model was fine-tuned with.
- **Answer:** `<thought>...</thought>`, then the OpenRocket tree as JSON inside `<design>...</design>`.
- **Reward:** `rocket_reward`, from `scripts/reward.py`, the reward ladder. It runs six gates: format, structure, motors, cad, flight, targets. The reward is gates passed / 6.
- **Metrics:** `passed_<gate>` for each gate, plus `slop`. They're logged only (weight 0) and show which gate the model gets stuck on.
- **Harness:** plain chat with no tools (verifiers' null harness). The model answers once and the answer is scored.

## Setup

Run these from the repo root, using the repo's `.venv`. The venv already has cadquery and JPype. The flight gate also needs the JDK and `lib/OpenRocket.jar`.

```
uv pip install --python .venv/bin/python verifiers
uv pip install --python .venv/bin/python -e environments/rocket_design
.venv/bin/python scripts/check_rocket_env.py model_out/results_val.json
```

`check_rocket_env.py` needs no GPU and no model. It does three things:

1. Loads the environment the way verifiers does, by its id.
2. Scores the saved answers through verifiers' own scoring code.
3. Checks that every score matches `scripts/reward.py` run directly.

In training, use the id `rocket-design` (prime-rl: `--env.taskset.id rocket-design`).

## Options

| option | default | notes |
|---|---|---|
| `taskset.prompts_file` | `data/splits/rl_heldout.jsonl` | JSONL with `prompt` (a string or chat messages) or `messages`. Only the user text is used. |
| `taskset.task.motor_lookup` | `new_results/sft_v4_motor_lookup.json` | The real motor files. If it's missing, the env falls back to a weaker check against catalog names. |
| `taskset.task.workers` | 4 | Number of scoring processes. Each one runs its own OpenRocket JVM. |
| `taskset.task.flight`, `taskset.task.cad` | true | Turn off the slow gates. Scores are then only comparable to runs with the same setting. |
| `taskset.task.timeout_s` | 300 | An answer whose scoring takes longer than this gets 0. |
