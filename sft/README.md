# SFT: Agents-A1-4B on the rocketdata designs (Unsloth)

Fine-tunes [InternScience/Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B) on
`data/sft_v0.jsonl` (174 examples) and tests on `data/sft_test.jsonl` (43 examples, different rockets).
Runs on one 16 GB GPU. Tested on Windows 11 with an RTX 5080 and the Python that ships with Unsloth Studio.

> **Read this first: the model mostly reproduces one rocket.**
> - **The cause:** 92 of the 174 training rows are the same Raketa design (`czech-rocket-challenge-2025__Raketa.ork`,
>   motor GragasMAY24). Only `wind_ms` differs between them.
> - **The effect:** in testing, 96 of 129 answers used GragasMAY24. No test prompt or reference answer uses that motor.
> - **What's working:** the model learned the answer format well (see Results).
> - **What isn't:** it hasn't learned to design a rocket that fits the request.
> - **Next step:** keep only a few Raketa rows (for example 5 of the 92) and retrain.

## Files

| File | What it does |
|---|---|
| `train_sft.py` | 16-bit LoRA training, then saves the LoRA adapter, a merged 16-bit model and a Q4_K_M GGUF |
| `eval_test.py` | Runs a GGUF on the 43 test prompts (or the 105 RL prompts) with llama-server and checks the answer format |

## How to run

Use Unsloth Studio's Python, which already has every dependency
(`%USERPROFILE%\.unsloth\studio\unsloth_studio\Scripts\python.exe`, called `python` below).
Before training or exporting, unload any model in Studio's chat and stop any running llama-server.
That frees the GPU, and an open GGUF can't be replaced.

```bat
python sft\train_sft.py --smoke 3      &REM 3-step check: loads, trains, prints VRAM
python sft\train_sft.py                &REM full run: 3 epochs, then LoRA + merged + GGUF export (~7 min)
python sft\train_sft.py --export-only  &REM redo the merged/GGUF export from the saved adapter
python sft\eval_test.py --gguf C:\ft\agents-a1-rocket\gguf\Agents-A1-4B-rocketdata.Q4_K_M.gguf --label test
python sft\eval_test.py --gguf C:\ft\agents-a1-rocket\gguf\Agents-A1-4B-rocketdata.Q4_K_M.gguf --label rl --test data\splits\rl_heldout.jsonl
python sft\eval_test.py --rescore C:\ft\agents-a1-rocket\eval\results_test.json   &REM re-score saved answers, no GPU
```

Two training runs with identical settings can still differ. GPU kernels aren't bit-for-bit deterministic, so
retrain into a new `--out` folder and compare before replacing a model you like.

To get the "Original" columns of the results table, run the same test on InternScience's own Q4_K_M quant of
the untuned model:

```bat
hf download InternScience/Agents-A1-4B-Q4_K_M-GGUF Agents-A1-4B-Q4_K_M.gguf --local-dir C:\ft\base-gguf
python sft\eval_test.py --gguf C:\ft\base-gguf\Agents-A1-4B-Q4_K_M.gguf --label base
python sft\eval_test.py --gguf C:\ft\base-gguf\Agents-A1-4B-Q4_K_M.gguf --label base_nothink --no-think
```

Outputs go to `C:\ft\agents-a1-rocket\` (short path on purpose; Windows has a 260-character path limit):

| Path | What |
|---|---|
| `gguf\Agents-A1-4B-rocketdata.Q4_K_M.gguf` + `...BF16-mmproj.gguf` | the model to chat with (2.7 GB + 0.7 GB image encoder) |
| `lora\` | the LoRA adapter only (130 MB); needs the base model to load |
| `merged_16bit\` | base model with the adapter merged in (9 GB, Hugging Face format) |
| `checkpoints\`, `train_log.json` | every epoch's checkpoint and the loss history |
| `eval\` | `eval_test.py` results, including every generated answer |
| `unsloth_compiled_cache\` | Unsloth's generated kernels; safe to delete, rebuilt on the next run |

**To chat with it in Unsloth Studio:** copy the two GGUF files into a folder under
`%USERPROFILE%\.unsloth\studio\exports\` (for example `exports\Agents-A1-4B-rocketdata-gguf\`). Studio lists it
under exported models. Copy them again after every re-export. Leave thinking on, and use the training
system prompt from the data:
`You are an autonomous aerospace design engineer. When given flight requirements, you must first calculate the required propulsion, stability, and descent parameters, then output the final verified hardware blueprint in JSON format inside <design> tags.`

**Running `llama-server` yourself:** the prebuilt one from Studio needs PyTorch's CUDA DLLs on `PATH`
(`...\unsloth_studio\Lib\site-packages\torch\lib`). Without them it silently runs on the CPU, measured at
about 1/12 the speed. `eval_test.py` handles this for you.

## Choices made

- **The model:** Agents-A1-4B has the same config as Qwen3.5-4B, a vision-language model whose text layers mix
  Gated DeltaNet linear attention with full attention every 4th layer. Unsloth 2026.10 supports it.
- **16-bit LoRA, not 4-bit QLoRA:** Unsloth's Qwen3.5 guide advises against QLoRA for these models.
- **LoRA:** rank 16, alpha 16, on every text projection (attention, Gated DeltaNet and MLP); the vision tower
  stays frozen.
- **Training:** learning rate 2e-4, batch 1 × gradient accumulation 8, 3 epochs.
  - The test loss is logged after each epoch, but the saved adapter is always the last epoch. The test set
    isn't used to pick an epoch, so the scores below aren't biased toward it.
  - Every epoch's checkpoint is kept.
- **Loss on the answer only:** the system prompt and user prompt are masked out.
- **`<thought>` becomes `<think>`:**
  - The data writes its reasoning in `<thought>…</thought>`. The script moves that text into the model's own
    `<think>…</think>` slot.
  - Reason: Studio, llama.cpp and vLLM all turn thinking on by default for this model.
  - The `<design>{json}</design>` part is unchanged.
  - Use `--keep-thought` to train on the data verbatim, then chat with thinking off.
- **Stop tokens:** the exported `generation_config.json` stops on `<|im_end|>` (the end of a chat turn) as
  well as `<|endoftext|>`. The base model's config only lists `<|endoftext|>`.

## Results (2026-10-19)

**Training** (the shipped model, `--seed 42`):
- 4.3 minutes on an RTX 5080: 66 steps of 8 examples, including GPU kernel compilation.
- PyTorch's peak allocation was 9.6 GiB; with its cache it reserved 11.8 GiB. Leave about 12 GB of VRAM free.
- Unsloth's bundled Gated DeltaNet kernels worked on Windows.
  - When they can't be enabled, Unsloth prints "transformers will use a slower pure PyTorch path"; that didn't happen.
  - transformers' own "fast path is not available … causal-conv1d" warning at load time is expected and harmless.

| Epoch | 1 | 2 | 3 (saved) |
|---|---|---|---|
| Test loss | 0.553 | 0.468 | 0.454 |

**Answer format on the 43 test prompts** (Q4_K_M GGUF, temperature 0.3, thinking on unless noted):
- **Fine-tuned column:** the range over 3 runs. Answers vary a little between runs because llama-server batches 4
  prompts at a time.
- **"Original" columns:** InternScience's published Q4_K_M quant of the untuned model.

| Check | Fine-tuned | Original, thinking on | Original, thinking off |
|---|---|---|---|
| Has `<design>…</design>` in the answer | 43/43 | 0/43 | 43/43 |
| Design JSON parses | 42–43 | 0 | 42 |
| Uses this project's schema (motor, components, nose cone, body tube, known part types) | 34–41 | 0 | 0 |
| Has a parachute or streamer | 42–43 | 0 | 0 |
| Motor exists in `catalog.sqlite` or the data | 41–42 | 0 | 0 |
| Uses the motor the prompt asked for (10 prompts name one) | 10/10 | 0/10 | 0/10 |
| Got stuck repeating itself (ran out of tokens at 4,096) | 0 | 43 | 0 |

How the original model did:
- **Thinking on:** it never finished. Every answer was still reasoning at 4,096 tokens.
- **Thinking off:** it wrote valid JSON, but in a format of its own (`mission_profile`, `propulsion_analysis`, …),
  not this project's component tree.

Of the fine-tuned model's 18 schema misses over the 3 runs, 17 are invented part types and 1 is a JSON error.
The invented types are `enginebay` 9 times, `finset` 7, `retainingring` 2, and `engine` and `freeformfin` once each.
For prompt U-128, all 3 runs copied the prompt's motor label (`APEX | Cesaroni I216-CL(I)-14`) verbatim instead
of the catalog name `I216-CL(I)`.

**Why `--seed 42`:** a retrain with the original seed (3407) sometimes got stuck in loops, repeating the same
`masscomponent` entry until it ran out of tokens. So two models were trained and compared on the 105 RL
prompts, which share no rockets with the test set, so the test numbers above stay unbiased:

| On the 105 RL prompts | seed 3407 | seed 42 (shipped) |
|---|---|---|
| Got stuck in a loop | 12 | 0 |
| JSON parses | 82 | 103 |
| Uses the schema | 78 | 90 |
| Uses the motor the prompt asked for | 17/29 | 28/29 |

A repetition penalty (presence penalty 1.1, as the model card suggests) cut the loops on the seed-3407 model, but
it broke more of the JSON. Presence penalty applies to every repeated token, and JSON repeats keys constantly.
So keep it at 0 for this model.

**Caveats:**
- **The apogee isn't simulated:** the "Simulated apogee" the model writes in its reasoning is the prompt's number
  repeated back. It isn't a simulation result.
- **No physics check yet:** only running the generated design through OpenRocket would show whether it flies.
  That needs a `<design>` → `.ork` converter, which the repo doesn't have yet.

## Things to know about the data

- **Unsafe landings:** 73 of the 174 training answers land faster than 6 m/s, the limit the RL stage uses
  (`data/splits/rl_heldout.jsonl`). SFT teaches those landing speeds as correct.
- **One rocket dominates:** 92 of the 174 training rows are the Raketa design, which is why the model keeps
  reproducing it (see the note at the top). It also has the training data's longest runs of mass components:
  6 in one body tube, where the original seed's loops started.
- **No physics check:** the test script checks only the format. The repo has no simulator, so it can't tell
  whether a generated rocket would really fly.
