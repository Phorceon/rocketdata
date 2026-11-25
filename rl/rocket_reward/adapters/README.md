# Trainer adapters

Thin wrappers so an RL trainer can call the one scoring core
(`scoring.score_many`, DESIGN.md). Importing them imports no trainer library.

* `trl.py`: Hugging Face TRL `GRPOTrainer` (also Unsloth, which wraps it).
  Checked against the TRL 0.23.1 source.

## The one rule that matters

**A setup error stops training.** `RewardSetupError` (no Java, wrong jar,
failed self-test, too many crashes, a dataset row without valid requirements)
is raised and never turned into a number. If you catch it, stop the run: the
machine is broken, not the model. A score of 0 for every answer would train
the model on noise.

## The dataset

The examples read `rocket_reward/prompts/rl_prompts_v1.jsonl`, one prompt per
line:

```json
{"id": "V4-0006:original", "split": "train", "system": "...", "prompt": "...",
 "requirements": {"id": "V4-0006:original", "apogee_m": {"value": 3320, "kind": "about"}}, "...": "..."}
```

(one line in the file; the other fields are listed in
[../prompts/README.md](../prompts/README.md)). `requirements` is the record
from DESIGN.md section 4. Either adapter accepts it as a dict or as a JSON
string of one. The TRL example writes it as a string, so the `datasets`
library does not merge the rows' different keys. **Train only on the rows
with `"split": "train"`**; the file also holds the val and test prompts, which
the examples below leave out.

## TRL / Unsloth GRPO

```python
import json
from datasets import load_dataset
from trl import GRPOConfig, GRPOTrainer
from rocket_reward.adapters.trl import make_reward, make_diagnostics
from rocket_reward.sim import SimPool

ds = load_dataset("json", data_files="rocket_reward/prompts/rl_prompts_v1.jsonl", split="train")
ds = ds.filter(lambda r: r["split"] == "train")           # 385 of the 474 prompts
ds = ds.map(lambda r: {"prompt": [{"role": "system", "content": r["system"]},
                                  {"role": "user", "content": r["prompt"]}],
                       "requirements": json.dumps(r["requirements"])}, remove_columns=["system"])
with SimPool(4) as pool:                                  # one pool for the whole run
    reward = make_reward(simulator=pool, max_completion_tokens=4096)
    stages = make_diagnostics(reward)                     # 7 functions, logged only
    args = GRPOConfig(output_dir="grpo-out", max_completion_length=4096, num_generations=8,
                      scale_rewards="batch", reward_weights=[1.0] + [0.0] * len(stages))
    GRPOTrainer(model="path/to/sft-model", reward_funcs=[reward, *stages.values()],
                args=args, train_dataset=ds).train()
```

* `max_completion_tokens` must equal `max_completion_length`. TRL passes the
  token ids of each completion, and an answer that used every token was cut
  off, so it scores 0.0. Pass `eos_token_id=` too if you want an answer whose
  very last allowed token was the end token to count as finished.
* The diagnostics return 1.0 or 0.0 per answer for "reached this stage or a
  later one". With weight 0 they change nothing, but TRL logs
  `rewards/rocket_reached_<stage>/mean`, which shows where the model is stuck.
  They reuse the batch the reward already scored (a small cache keyed by the
  batch), so nothing is flown twice. `rocket_reached_format` is always 1.0.
  It is there so the seven lines read as one ladder.

### What a quarantined answer returns, and why

When a check crashes on one answer, `Result.score` is None and the answer
should be left out. TRL 0.23.1 (`trl/trainer/grpo_trainer.py`) turns None
into NaN:

```python
output_reward_func = [reward if reward is not None else torch.nan for reward in output_reward_func]
```

Then it sums the reward functions with NaN treated as 0:

```python
rewards = (rewards_per_func * self.reward_weights.to(device).unsqueeze(0)).nansum(dim=1)
```

Unsloth 2026.10.7 says the same in `unsloth/models/rl_replacements.py`:
"older TRL scores it 0 (nansum), so its group has variance and real
advantages there". So a plain None would score the answer 0.0, the worst score
there is, and push the model away from whatever it wrote.

The adapter therefore returns, for a quarantined answer, **the mean score of
the other answers to the same prompt in that call**. The group mean does not
change, so the answer's advantage is zero and it pushes the model neither way.
When every answer to a prompt was quarantined, all of them get None: they all
sum to 0, so the advantages are still zero. The diagnostics return None for a
quarantined answer, so it is left out of their logged means (TRL uses
`torch.nanmean` there).

### How rewards are normalised inside a group, and the setting to use

TRL 0.23.1 compares each answer only with the other answers to the same
prompt:

```python
mean_grouped_rewards = rewards.view(-1, self.num_generations).mean(dim=1)
...
advantages = rewards - mean_grouped_rewards

if self.scale_rewards in ["group", "none"]:
    # If self.scale_rewards = "none", we'll still log group level std
    std_rewards = rewards.view(-1, self.num_generations).std(dim=1)
...
elif self.scale_rewards == "batch":
    # Compute global std
    std_rewards = rewards.std().expand_as(rewards)
...
if self.scale_rewards != "none":
    advantages = advantages / (std_rewards + 1e-4)
```

The default is `scale_rewards="group"` (`grpo_config.py`: "`True` or
`"group"` (default): rewards are scaled by the standard deviation within each
group").

What this means for the 0..1 ladder: only differences inside a group count,
so the bands work through ranking. An answer that climbs one stage higher than
its siblings gets a large positive advantage. But with `"group"`, a group
whose answers all stop at the same stage (for example eight answers in the
motor band, 0.22 to 0.24) is divided by a tiny standard deviation. A 0.01
nudge inside the band then gets as much push as climbing from the motor stage
to the targets stage. Groups with equal scores (all cut off at 0.0, or all at
1.0) give zero advantage either way; TRL logs their share as
`frac_reward_zero_std`.

**I recommend `scale_rewards="batch"`.** It divides by one standard deviation
for the whole batch, so a stage climb stays worth more than a small move
inside a band, as the ladder intends. `"none"` (the Dr. GRPO choice) also keeps
the ladder's own scale, but it makes the step size depend on the spread of the
scores. Leave `mask_truncated_completions=False` (the default) so the 0.0 for
a cut-off answer still teaches the model to finish.

## Speed

About 0.15-0.3 s per answer with 4 warm simulator helpers (`SimPool(4)`,
measured on 2026-11-19 on a PC shared with other jobs: 0.27 s on the 594
reference rows, 0.14-0.18 s on 48 val answers and on the model's 48 answers).
Starting a helper takes a few seconds (`python -m rocket_reward check` started
one and flew the self-test rocket in 5.2 s), and the first batch is slower
while the helpers warm up. Each helper is one Java process, so make one pool
per trainer process and share it. With no pool given, both adapters use the
shared default pool, `ROCKET_REWARD_WORKERS` helpers (default 4, at most the
CPU count minus one). A rare slow design can take far longer: a run past the
helper's wall-clock limit (30 s plus 10 s per flight, `sim.py`) is tried once
more on a fresh helper and, if still stuck, scores 0.40. Set the trainer's
reward timeout with that in mind.
