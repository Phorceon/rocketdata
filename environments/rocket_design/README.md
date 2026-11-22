# rocket-design

A `verifiers` environment for RL on rocket design. It uses verifiers 0.4+ (the v1 API: taskset / task / `@vf.reward`) and runs self-hosted with no Prime sandbox or API key.

- **Prompt:** a mission from `rocket_reward/prompts/rl_prompts_v1.jsonl`, sent with the v5 system prompt and its structured `requirements` record.
- **Answer:** `<thought>...</thought>`, then the OpenRocket tree as JSON inside `<design>...</design>`.
- **Reward:** `rocket_reward` (7-stage ladder in `0..1`: `format`, `parts`, `motor`, `limits`, `build`, `flight`, `targets`, flown in OpenRocket 24.12). Quarantined answers call `trace.drop(...)` and return `None`. Setup errors raise `RewardSetupError`.
- **Metrics:** `rocket_stages_passed` (`0..7`) plus `passed_<stage>` for each of the seven stages (weight 0, logged only).
- **Harness:** plain chat with no tools (verifiers' null harness). The model answers once and the answer is scored.

## Setup

Run these from the repo root. You need Python 3.10+, a JDK 17+, and `OpenRocket-24.12.jar` (see `rocket_reward/README.md`).

```
python -m rocket_reward fetch-jar
python -m rocket_reward check
uv pip install --python .venv/bin/python verifiers
uv pip install --python .venv/bin/python -e environments/rocket_design
.venv/bin/python scripts/check_rocket_env.py
```

`check_rocket_env.py` needs no GPU and no model. It does three things:

1. Loads the `rocket-design` environment by its id through `verifiers`.
2. Scores saved answers through `verifiers`' own `Task.score` (`@vf.metric` and `@vf.reward`).
3. Checks that every score and stage matches `rocket_reward.scoring.score_many` directly.

In training, use the id `rocket-design` (prime-rl: `--env.taskset.id rocket-design`).

## Options

| option | default | notes |
|---|---|---|
| `taskset.prompts_file` | `rocket_reward/prompts/rl_prompts_v1.jsonl` | JSONL (or `.jsonl.gz`) with `prompt` and `requirements`. |
| `taskset.split` | `"train"` | Filter rows by `split` (`train`, `val`, `test`), or `""` / `null` for all rows. |
| `taskset.task.workers` | `4` | Number of OpenRocket helper processes in `SimPool` (`0` uses `ROCKET_REWARD_WORKERS`). |
