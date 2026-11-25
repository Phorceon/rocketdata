# rl/ — everything needed for RL

Copy this one folder to the GPU box. Nothing outside it is used.

## Quick start (GPU box)

```bash
bash rl/setup.sh                                          # JDK 17, pip deps, OpenRocket jar, checks, dry run
cd rl
python train_grpo.py --smoke 15 --wandb-project rocket-ai # 15-step smoke test
python train_grpo.py --max-steps 300 --wandb-project rocket-ai
```

Add `--load-in-4bit` for 4-bit QLoRA on a 24–40 GB GPU. Run `python train_grpo.py -h` for all flags.

## Layout

| Path | What it is |
|---|---|
| `train_grpo.py` | Unsloth + TRL `GRPOTrainer` launch script (`--dry-run`, `--smoke N`) |
| `setup.sh` | Fresh-box setup: Java, pip deps, jar fetch, checks |
| `requirements.txt` | Training deps (Unsloth, TRL, datasets, W&B, pytest) |
| `rocket_reward/` | The reward: parse → fit → 7-stage ladder → OpenRocket 24.12 flight (stdlib only) |
| `rocket_reward/adapters/trl.py` | `make_reward`, `make_diagnostics` for TRL / Unsloth |
| `rocket_reward/prompts/synthetic/rl_prompts_v2.jsonl` | 2,100 synthetic RL prompts (train/val/test) — default |
| `rocket_reward/prompts/rl_prompts_v1.jsonl` | Real-kit prompts (val/test benchmark) |
| `rocket_reward/data/` | Motor + material tables, canary rocket |
| `rocket_reward/java/` | OpenRocket helper source (compiled on first run) |
| `rocket_reward/lib/` | OpenRocket-24.12.jar lands here (`fetch-jar`, git-ignored) |
| `rocket_reward/tests/` | Tests + gold/model answer fixtures |
| `environments/rocket_design/` | `verifiers` env for `prime-rl` (alternative trainer) |
| `check_rocket_env.py` | No-GPU check of the `verifiers` env |
| `outputs/` | Checkpoints (git-ignored) |

## Env vars

- `ROCKET_REWARD_JAVA_HOME` — JDK folder, if Java is not on `PATH`.
- `ROCKET_REWARD_JAR` — jar path, if not in `rocket_reward/lib/`.

## Tests

```bash
cd rl && python -m pytest rocket_reward/tests -q
```

More detail: `rocket_reward/README.md`, `rocket_reward/DESIGN.md`, `rocket_reward/adapters/README.md`.
