# SFT: Qwen3.5-4B on the rocketdata designs (Unsloth)

Fine-tunes [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) on `new_results/sft_v2.jsonl` (the team's
OpenRocket re-simulated set) and tests on `new_results/sft_test_v2.jsonl` (different rockets). Runs on one 16 GB GPU.
Tested on Windows 11 with an RTX 5080 and the Python that ships with Unsloth Studio (Unsloth 2026.10.7,
transformers 5.5.0, TRL 0.23.1, torch 2.13 + CUDA 13.0).

> **Summary (2026-10-28)**
> - **It beats the earlier Agents-A1-4B fine-tune on the 105 RL prompts:** valid design JSON 103 vs 103, uses this
>   project's schema 101 vs 90, uses the motor the prompt asked for 28/29 vs 28/29.
> - **It copies far less:** the most common motor is in 18% of its answers, across 37 different motors. The Agents
>   model put GragasMAY24 (the Raketa design's motor) in about 74%.
> - **How it has to be run:** the 8-bit GGUF, thinking off, temperature 0.7, and the output grammar
>   `sft/design.gbnf`. Without the grammar the same file scores 93 valid / 90 schema.
> - **On the 38 test prompts** (never used to choose anything): valid JSON 36–38, schema 36–37, asked-for motor
>   10–11 of 11, over 3 runs.
> - **Still weak:** it makes up motor names (H121W, F67T, ...) in about a third of its designs, a few answers still
>   loop (2 of 105 here, 14 for another training seed), and no design has been simulated.

## Files

| File | Purpose |
|---|---|
| `train_sft.py` | Trains the model and exports it |
| `eval_test.py` | Tests a trained model and scores its answers |
| `filter_data.py` | Writes the training copy without the very large designs (optional; `train_sft.py` filters the same way) |
| `design.gbnf` | llama.cpp grammar that keeps answers in the `<thought>…</thought><design>{json}</design>` format |
| `README.md` | This guide: how to run everything, the choices made, and the results |

### `train_sft.py`: trains the model

What it does, in order:

1. Loads Qwen/Qwen3.5-4B in 16-bit and adds LoRA adapters to its text layers. The image part of the model stays
   frozen, since the task is text only.
2. Reads the training data (`new_results/sft_v2.jsonl`) and skips every design with 60 or more parts (12 of 163
   rows; see Choices made). Reads the test data (`new_results/sft_test_v2.jsonl`) as is.
3. Trains for 3 epochs on each answer as written, `<thought>` reasoning included. Loss is computed on the answer
   only, so the model isn't trained to repeat the prompt. After each epoch it logs the loss on the test data.
4. Saves the LoRA adapter, then exports a merged 16-bit model and a Q8_0 GGUF (the file you chat with).

Writes everything to `--out` (default `C:\ft\qwen35-rocket\`).

| Option | What it changes |
|---|---|
| `--smoke 3` | Runs 3 training steps and stops: a quick check that loading, training and VRAM are fine |
| `--export-only` | Skips training; re-exports the merged model and GGUF from the saved adapter |
| `--no-export` | Saves only the LoRA adapter |
| `--model` | Base model (default `Qwen/Qwen3.5-4B`; any Qwen3.5-family model works) |
| `--train`, `--test` | Other data files |
| `--max-parts` | Skip training designs with this many parts or more (default 60; `0` keeps every row) |
| `--out` | Output folder; use a new one per run so you never overwrite a model |
| `--epochs`, `--lr`, `--rank`, `--seed` | Training settings (defaults: 3, 2e-4, 16, 42) |
| `--max-len` | Longest example in tokens (default 6400, enough for all of `sft_v2`; the longest kept example is 2,542) |
| `--move-thought` | Moves `<thought>` into the model's `<think>` slot (thinking-on training, as in the Agents-A1 run) |
| `--gguf`, `--name` | GGUF quantization (default `q8_0`) and file name (default `<model>-rocketdata`) |

### `eval_test.py`: tests a trained model

What it does, in order:

1. Starts llama-server (the one that ships with Unsloth Studio) on the GPU with the GGUF you give it.
2. Sends every prompt from the test file and saves every answer. The default is the 38 test prompts in
   `new_results/sft_test_v2.jsonl`; `--test data\splits\rl_heldout.jsonl` uses the 105 RL prompts instead.
   By default it prompts with thinking off, at temperature 0.7, with `sft/design.gbnf` as the output grammar.
3. Scores each answer:
   - **Design:** is there a `<design>` block, and does its JSON parse?
   - **Schema:** does it have a motor and components, a nose cone and a body tube, and only part types
     that appear in the data?
   - **Recovery:** is there a parachute or a streamer?
   - **Motor:** is the motor a real one (in `data/catalog.sqlite` or the SFT data)? When the prompt names a
     motor, did it use that one?
   - **Loops:** did it get stuck repeating itself until it hit the token limit?
4. Writes `results_<label>.json`, with the summary and every answer, and prints the summary.

It checks the format only. The `<design>` format records no part positions, so a design can't be simulated
faithfully; the team's newer `sftgen` format is the one built for simulation.

| Option | What it changes |
|---|---|
| `--gguf`, `--label` | The model to test, and the name for its results file (both required) |
| `--test` | Which prompts to use (default `new_results/sft_test_v2.jsonl`) |
| `--no-grammar` | Scores the raw model, with no output grammar |
| `--think` | Prompts with thinking on, for `--move-thought` models (also turns the grammar off) |
| `--temperature`, `--presence-penalty` | Sampling (defaults 0.7 and 0; 0.3 makes this model loop, and any presence penalty breaks the JSON) |
| `--rescore <results file>` | Re-scores saved answers without the GPU, for example after changing a check |
| `--out-dir`, `--port`, `--overwrite` | Where results go, which port the server uses, and whether to replace an old results file |

### `design.gbnf`: keeps the answer format valid

A [llama.cpp grammar](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md). It lets the model write
anything inside `<thought>…</thought>`, then forces `<design>`, a JSON object with balanced brackets, and
`</design>`, and ends the answer there. It doesn't know the design schema: part types, motor names and list
lengths are still up to the model. llama-server takes it as the `grammar` field of a request, llama.cpp's CLI as
`--grammar-file`, and vLLM (for RL) as a guided-decoding grammar.

## How to run

Use Unsloth Studio's Python, which already has every dependency
(`%USERPROFILE%\.unsloth\studio\unsloth_studio\Scripts\python.exe`, called `python` below).
Before training or exporting, unload any model in Studio's chat and stop any running llama-server.
That frees the GPU, and an open GGUF can't be replaced.

```bat
python sft\train_sft.py --smoke 3      &REM 3-step check: loads, trains, prints VRAM
python sft\train_sft.py                &REM full run: 3 epochs, then LoRA + merged + Q8_0 GGUF export (~7 min)
python sft\train_sft.py --export-only  &REM redo the merged/GGUF export from the saved adapter
python sft\eval_test.py --gguf C:\ft\qwen35-rocket\gguf\Qwen3.5-4B-rocketdata.Q8_0.gguf --label test
python sft\eval_test.py --gguf C:\ft\qwen35-rocket\gguf\Qwen3.5-4B-rocketdata.Q8_0.gguf --label rl --test data\splits\rl_heldout.jsonl
python sft\eval_test.py --rescore C:\ft\qwen35-rocket\eval\results_test.json   &REM re-score saved answers, no GPU
```

Two training runs with identical settings can still differ. GPU kernels aren't bit-for-bit deterministic, so
retrain into a new `--out` folder and compare on the RL prompts before replacing a model you like.

Outputs go to `C:\ft\qwen35-rocket\` (short path on purpose; Windows has a 260-character path limit):

| Path | What |
|---|---|
| `gguf\Qwen3.5-4B-rocketdata.Q8_0.gguf` + `...BF16-mmproj.gguf` | the model to chat with (4.6 GB + 0.7 GB image encoder) |
| `lora\` | the LoRA adapter only (130 MB); needs the base model to load |
| `merged_16bit\` | base model with the adapter merged in (9 GB, Hugging Face format) |
| `checkpoints\`, `train_log.json` | every epoch's checkpoint and the loss history |
| `eval\` | `eval_test.py` results, including every generated answer |
| `unsloth_compiled_cache\` | Unsloth's generated kernels; safe to delete, rebuilt on the next run |

## Using the model

- **Settings:** thinking off, temperature 0.7, top-p 0.95, top-k 20, no presence or repetition penalty, and
  `sft/design.gbnf` as the grammar where the app supports one (llama.cpp, LM Studio, vLLM).
- **System prompt** (the one in the data):
  `You are an autonomous aerospace design engineer. When given flight requirements, you must first calculate the required propulsion, stability, and descent parameters, then output the final verified hardware blueprint in JSON format inside <design> tags.`
- **Unsloth Studio:** copy the two GGUF files into a folder under `%USERPROFILE%\.unsloth\studio\exports\`
  (for example `exports\Qwen3.5-4B-rocketdata-gguf\`). Studio lists it under exported models. Turn thinking off in
  the chat settings. Studio's chat has no grammar option, so expect more broken JSON there than in the results below.
- **Running `llama-server` yourself:** the prebuilt one from Studio needs PyTorch's CUDA DLLs on `PATH`
  (`...\unsloth_studio\Lib\site-packages\torch\lib`). Without them it silently runs on the CPU, measured at
  about 1/12 the speed. `eval_test.py` handles this for you.

## Choices made

- **The model:** plain Qwen3.5-4B, the model Agents-A1-4B is built on. Same architecture (Gated DeltaNet linear
  attention with full attention every 4th layer), so the scripts needed no model-specific changes.
- **The data:** `new_results/sft_v2.jsonl`, the team's re-simulation of `sft_v1` with OpenRocket 24.12 (163 rows,
  79 rockets, at most 5 rows per rocket). It replaces `data/sft_v0.jsonl`, where 92 of 174 rows were one rocket.
- **Dropping the 12 largest designs:** 12 rows model every small part of a kit, with 71 to 133 parts each (67
  centering rings in the Estes Rubicon, 92 inner tubes in Nemesis 150). The median design has 14. Trained on
  them, the model learned that a part list can go on and on, and it got stuck repeating one part ("Centering
  ring" 209 times) until it ran out of tokens. 151 rows from 73 rockets remain.
- **Thinking off:** each answer is trained as written, `<thought>` text included, and the model is prompted with
  thinking off. Training it as thinking (`--move-thought`) did worse (26 valid of 105), with more loops.
- **Temperature 0.7:** Qwen's recommended setting for thinking-off use. At 0.3 the model looped on 13 of 105 RL
  prompts; at 0.7 on 0 without the grammar and 2 with it.
- **Q8_0, not Q4_K_M:** every design nests 7 to 13 brackets deep and ends in a run like `"C6"}]}]}`. The 4-bit file
  lost count of the brackets on 59 of 105 answers; the 8-bit file on 9. Q8_0 is 4.6 GB and still fits easily.
- **The grammar:** it removes the remaining bracket errors. The model's own answers are still scored, both with
  and without it (see Results).
- **Picked on the 105 RL prompts:** every comparison between runs used `data/splits/rl_heldout.jsonl`, which shares
  no rockets with training or testing. The test set was only used to confirm the final model.
- **Unchanged from the Agents-A1 run:** 16-bit LoRA, rank 16, alpha 16, on every text projection; learning rate
  2e-4, batch 1 × gradient accumulation 8, 3 epochs, last epoch saved; loss on the answer only.

## Results (2026-10-28)

**Training** (the shipped model, `--seed 42`):
- 3.8 minutes on an RTX 5080: 57 steps of 8 examples, then about 2 minutes of export.
- PyTorch's peak allocation was 9.6 GiB; with its cache it reserved 13.4 GiB. With `--max-parts 0` the longest
  example (6,275 tokens) peaked at 10.1 GiB allocated. Close games and other GPU apps first.

| Epoch | 1 | 2 | 3 (saved) |
|---|---|---|---|
| Test loss | 0.499 | 0.453 | 0.450 |

Test loss didn't show any of the problems below: every variant ended between 0.438 and 0.454.

**On the 105 RL prompts**, in the order things were tried (temperature 0.3 unless noted):

| Run | Valid JSON | Schema | Asked-for motor | Loops |
|---|---|---|---|---|
| Agents-A1-4B fine-tune, 2026-10-19 (Q4, thinking on) | 103 | 90 | 28/29 | 0 |
| Qwen, all 163 rows, seed 42 (Q4) | 69 | 69 | 18/29 | 24 |
| Qwen, all 163 rows, seed 3407 (Q4) | 49 | 49 | | 48 |
| Without the 12 largest designs (Q4) | 34 | 32 | 11/29 | 13 |
| … at temperature 0.7 | 46 | 42 | 16/29 | 0 |
| … trained as thinking, thinking on (Q4) | 26 | 25 | 8/29 | 36 |
| Without the 12 largest, grammar, temperature 0.7 (Q4) | 103 | 96 | 28/29 | 2 |
| **Same, Q8_0 (shipped)** | **103** | **101** | **28/29** | **2** |
| Same, Q8_0, no grammar | 93 | 90 | 26/29 | 3 |
| Same recipe, seed 3407 (Q4, grammar, 0.7) | 91 | 88 | 26/29 | 14 |
| Shipped model at temperature 1.0 | 104 | 99 | 28/29 | 1 |

The Agents-A1 row was scored on 2026-10-19 with the motor and part-type lists of `sft_v0`; the newer rows also
accept motors and part types from `sft_v1`, `sft_v2` and `sft_test_v2`.

**Loops still depend on the training run.** Seed 42 was picked because it scored best here; the same recipe with
seed 3407 looped on 14 of the 105 (every one a part list that never ends). Because seed 42 was chosen on these
prompts, its row above is a little optimistic. The test prompts below were never used to choose anything.

**On the 38 test prompts** (shipped settings, 3 runs; the range over the runs):

| Check | Q8_0 (shipped) | Q4_K_M |
|---|---|---|
| Has `<design>…</design>` in the answer | 36–38 | 35–38 |
| Design JSON parses | 36–38 | 35–38 |
| Uses this project's schema | 36–37 | 32–38 |
| Has a parachute or streamer | 36–38 | 31–34 |
| Motor exists in `catalog.sqlite` or the data | 21–25 | 21–26 |
| Uses the motor the prompt asked for (11 prompts name one) | 10–11 | 10–11 |
| Got stuck repeating itself (ran out of tokens at 4,096) | 0–2 | 0–3 |

These aren't directly comparable with the Agents-A1 test table further down: that model was tested on the older
`data/sft_test.jsonl` (43 prompts).

**Where the shipped model still fails** (RL prompts):
- **Loops:** U-055 lists "Rail Button" 352 times; U-008 never finishes its reasoning.
- **Schema:** of the 101, every miss is a made-up part type (`engine`, `payload`, `pod`, `freeformnosecone`) or a
  part with no type.
- **Motors:** 67 of 105 designs use only motors from the catalog or the data. The rest name motors that don't
  exist (H121W, F67T, F23T, ...). The training answers use only 66 different motors, so the model guesses names
  for anything else.
- **Physics:** untested. The "Simulated apogee" in its reasoning is its own claim, not a simulation result.

## Things to know about the data

- **Fast landings:** 85 of the 151 training answers land faster than 6 m/s (median 6.3 m/s), the limit the RL
  stage uses. SFT teaches those landing speeds as correct.
- **One rocket dominates the test set:** 21 of the 38 test rows are `OpenRocket-Design__Rocket_Model.ork`, so the
  test scores mostly measure that rocket. The RL prompts (105, from 8 rockets) are the better comparison.
- **The RL prompts don't always agree with their targets:** 14 of the 105 ask for an apogee more than 10% away
  from their own `requirements.target_apogee_m`, and 54 give no apogee at all.

## Earlier run: Agents-A1-4B on `sft_v0` (2026-10-19)

The first fine-tune used [InternScience/Agents-A1-4B](https://huggingface.co/InternScience/Agents-A1-4B) on
`data/sft_v0.jsonl` (174 rows), tested on `data/sft_test.jsonl` (43 rows), trained as thinking. To repeat it:

```bat
python sft\train_sft.py --model InternScience/Agents-A1-4B --train data\sft_v0.jsonl --test data\sft_test.jsonl --max-parts 0 --max-len 2048 --move-thought --gguf q4_k_m --out C:\ft\agents-a1-rocket
python sft\eval_test.py --gguf C:\ft\agents-a1-rocket\gguf\Agents-A1-4B-rocketdata.Q4_K_M.gguf --label test --think --temperature 0.3 --test data\sft_test.jsonl --out-dir C:\ft\agents-a1-rocket\eval
```

What it showed:
- **It learned the format, not design:** 92 of the 174 training rows were the same Raketa design
  (`czech-rocket-challenge-2025__Raketa.ork`, motor GragasMAY24), and 96 of its 129 test answers used GragasMAY24.
  No test prompt or reference answer uses that motor.
- **Test prompts (43, 3 runs):** `<design>` present 43/43, JSON parses 42–43, schema 34–41, asked-for motor 10/10,
  no loops. Test loss 0.553 → 0.468 → 0.454. The untuned model never produced this project's schema.
- **Seeds matter:** a retrain with seed 3407 looped on 12 of the 105 RL prompts; seed 42 on none, so seed 42 shipped.
- **Presence penalty breaks the JSON:** penalty 1.1 cut its loops but broke more of the JSON, since JSON repeats
  keys constantly.
