# rocket-design

A `verifiers` environment for RL on rocket design. It uses verifiers 0.4.1 (`<0.5`, the v1 API: taskset / task / `@vf.reward`) and runs self-hosted with no Prime sandbox or API key.

- **Prompt:** a mission from `rocket_reward/prompts/synthetic/rl_prompts_v2.jsonl` (`2,000` OpenRocket-verified synthetic `train` prompts + `50` synthetic `val` + `50` synthetic `test`, zero SFT prompts, with ~10% of motor designations held out exclusively for `val`/`test`). Real reference prompts remain in `rocket_reward/prompts/rl_prompts_v1.jsonl` (`36` val / `53` test) if you want an extra real-kit eval source.
- **Answer:** `<thought>...</thought>`, then the OpenRocket tree as JSON inside `<design>...</design>`.
- **Reward:** `rocket_reward` (7-stage ladder in `0..1`: `format`, `parts`, `motor`, `limits`, `build`, `flight`, `targets`, flown in OpenRocket 24.12). Quarantined answers call `trace.drop(...)` and return `None`. Setup errors log at CRITICAL and raise `RewardSetupError` (verifiers wraps it as `TaskError`; configure `prime-rl` to abort on high task-error rate).
- **Metrics:** `rocket_stages_passed` (`0..7`) plus `passed_<stage>` for each of the seven stages (weight 0, logged only).
- **Harness:** plain chat with no tools (verifiers' null harness). The model answers once and the answer is scored.

## Setup

Run these from the repo root. You need Python 3.10+, a JDK 17+, and `OpenRocket-24.12.jar` (see `rocket_reward/README.md`). Install with `-e` (editable) or set `ROCKETDATA_REPO` to the repo root so `rocket_reward` can be imported.

```
python -m rocket_reward fetch-jar
python -m rocket_reward check
uv pip install --python .venv/bin/python "verifiers>=0.4.1,<0.5"
uv pip install --python .venv/bin/python -e environments/rocket_design
.venv/bin/python scripts/check_rocket_env.py
```

`check_rocket_env.py` needs no GPU and no model. It verifies:

1. `verifiers` loads `rocket-design` (`train`, `val`, `test`) and resolves `RocketHarness`.
2. Truncation (`calls[-1].finish_reason == "length"`), quarantine `trace.drop(...)`, single-flight caching, and `Task.rescore` cache invalidation all behave as expected.
3. Saved answers scored through `verifiers`' `Task.score` match `rocket_reward.scoring.score_many` on every score and stage.

In training, use the id `rocket-design` (`env.taskset.id = "rocket-design"`).

## Options

| option | default | notes |
|---|---|---|
| `taskset.prompts_file` | `rocket_reward/prompts/synthetic/rl_prompts_v2.jsonl` | JSONL (or `.jsonl.gz`) with `prompt` and `requirements` (`2,000` train / `50` val / `50` test). |
| `taskset.split` | `"train"` | Filter rows by `split` (`train`, `val`, `test`), or `""` / `null` for all rows. |
| `taskset.task.workers` | `4` | Number of OpenRocket helper processes in `SimPool` (`0` uses `ROCKET_REWARD_WORKERS`). |
