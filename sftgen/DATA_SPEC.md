# Rocket Design SFT Data: How to Build the JSONL

For fine-tuning Qwen3.5-4B · Oct 22, 2026 · Adi Rehman

## 1. Goal

Every row in the JSONL teaches the model one design loop:

1. Understand the requirements.
2. Check whether the request is feasible.
3. Size the rocket.
4. Draft, then check it.
5. Fix it only when a check really fails.
6. Give the final design with honest uncertainty instead of "verified" numbers.

The reasoning must only use what the model could know at that point: the request, its own estimates, and simulator results it actually got back from a tool call. The current file breaks this rule, and the prompts make it worse. This sheet covers what to change, in the order you build a row: prompt, record, trace, checks, then the whole file.

Must = a row that breaks it is dropped or fixed. Should = default; break it only with a reason.

## 2. What is wrong with the current file

Counted over all 477 rows of sft_all.jsonl.

- The prompts are generated backward from finished designs. Each .ork file was simulated, and its outputs were turned into a prompt: "reaches about 1410 m in about 17.0 s … fly for about 287 s, touch down under 5.1 m/s." Every number is a simulator output with a fake "about" in front. Only 19 sentence templates cover all 477 prompts, and every one starts with "Design a rocket".
- The prompts pin outputs nobody asks for. 304 prompts set total flight time to a tenth of a second, 91 set time to apogee, and touchdown limits like "under 2.6 m/s" are just the simulated value rounded up. With five outputs pinned, there is basically one allowed answer, so the model learns to recall a design instead of designing one.
- Each design appears as three nested prompts. For 156 of the 159 files, the three rows ask for the same apogee, each with fewer extra fields than the last, and all three have the same answer.
- Some prompts have no goal at all. 11 prompts never give an altitude or speed, for example "Design a rocket on I300T motors." 158 say "motors" when there is only one.
- The reasoning already knows the answer. There are no tool calls, yet "Verified" appears in 381 traces and "measured in the flight data" in 150. 375 traces quote targets at full simulator precision. Estimates that disagree with the result get explained away: in 97 rows the installed impulse is below the trace's own estimate, and the trace still says it "comfortably covers" the need.
- Unsafe designs are kept as good answers. 9 rows have a static margin of 0 or below (unstable). 22 are under 3:1 thrust-to-weight, and 3 of those read "0.0:1" because of a broken motor parse.
- No feasibility step, no real fix step, no infeasible prompts. Every trace is one forward pass.
- Format: reasoning is in `<thought>`, but Qwen3.5 uses `<think>`. The system prompt asks for a "final verified" design. Counts are floats (`"fin_count":4.0`).

What is worth keeping: the 159 real designs, the design JSON format (every row parses), and the simulator setup. The fix is how prompts and traces get made, not the source designs.

## 3. Prompts

### 3.1 Where prompts come from

Write the prompt the way a rocketeer would ask, and treat the .ork design as a reference that proves the request can be met, not as the answer to copy. Take one or two of its outputs as goals, round them the way a person would, and add constraints people actually have. The answer in the row is then whatever design the generator builds and the simulator passes, which will usually differ from the .ork.

### 3.2 Rules

- **Ask for goals, not outputs (must).** Apogee, a touchdown limit, a motor or certification limit, a size limit, recovery type. Time to apogee and flight time only when there is a reason, such as a competition time window or "land within 90 s so it doesn't drift off the field".
- **Round like a person (must).** "About 600 m", "2,000 ft", "under 6 m/s". Never "96.1 s" or "under 2.6 m/s" copied from a simulation.
- **Every prompt has a goal (must).** "Design a rocket on I300T motors" becomes "I have an I300T. Build something that goes as high as it sensibly can and lands under 6 m/s."
- **One design, one prompt family (must).** Don't make three nested copies of the same request. If you want more rows per design, vary the constraint (different motor limit, different landing limit), and keep them all in one group so they go to the same split.
- **Give the limits real rockets have (should).** Motor class or certification level (Level 1 = H and I, Level 2 = J to L), body diameter or motor size (29 mm, 38 mm, 54 mm), payload mass, rail length, wind, recovery type (single chute, streamer, dual deploy).
- **Vary the wording (should).** Different openings, short and long requests, metric and imperial (US hobbyists say feet), casual and formal. No template should cover more than about 5% of prompts.
- **Leave some things out on purpose (should).** About 10% of prompts should be missing something important (no wind, no rail length), so the model learns to state an assumption.
- **Grammar (must).** "an I300T motor", not "I300T motors".

### 3.3 Prompt mix

| Type | Share | Example |
|---|---|---|
| Altitude goal plus one or two constraints | 30% | "Single-stage, 38 mm motor max, around 900 m. Land under 6 m/s." |
| Fixed motor, open goal | 15% | "I'm Level 1 and have an H128W. What's the highest stable rocket I can build for it?" |
| Recovery-driven | 15% | "Needs to hit about 1,500 m and come down inside a small field in 4 m/s wind. Dual deploy is fine." |
| Two-stage or cluster | 10% | "Two-stage, I booster and G sustainer, 1,400 m, both stages under 6 m/s." |
| Fix a given design | 10% | "Here's my design [JSON]. OpenRocket says margin is 0.6 cal. Fix it without changing the motor." |
| Missing information | 10% | "Build me a rocket that goes about 3,000 ft." |
| Infeasible or conflicting | 5–10% | "3,000 m on a single C6." / "From 1,500 m, under 25 s total flight, landing under 5 m/s." |
| Timed target (competition style) | ≤5% | "Carry a 60 g payload to 250 m and stay up 40 to 45 s." |

### 3.4 Current prompts rewritten

| Current | Rewritten |
|---|---|
| Design a rocket on G80T + I300T motors that reaches about 1410 m in about 17.0 s. It should hit a max velocity of about 173 m/s, fly for about 287 s, and touch down under 5.1 m/s. | Two-stage rocket: I300T booster, G80T sustainer. I want it to clear 1,400 m. Both stages need to land under 6 m/s, and our rail is 1.5 m. |
| Design a rocket on I300T motors. | I'm Level 1 and have an AeroTech I300T. Build something stable in 4 m/s wind that lands under 6 m/s. Go as high as is sensible. |
| Design a rocket that reaches about 207 m. It should touch down under 2.6 m/s. | Beginner rocket on a C6-5 that gets to about 200 m (650 ft) and lands soft enough to fly again. |
| Design a rocket that reaches about 12410 m. | What would it take to get to 12 km? We can fly up to L3, 98 mm max body diameter. |
| Design a rocket that reaches about 1770 m. It should fly for about 96.1 s. | Around 1,750 m on a K motor or smaller. We need it on the ground in under 2 minutes. |

## 4. Record format

One JSON object per line, UTF-8. Every row has these fields:

| Field | Holds |
|---|---|
| id | Unique, never reused |
| group_id | The source design family. All rows built from one .ork file, plus renamed copies of it, share one group_id. |
| split | train, val or test. Assigned per group, never per row. |
| source | ork, synthesized or hand-written |
| targets | Only what the prompt asks for, each with a kind: about, max, min or exact |
| sim_conditions | Rail length, launch angle, wind, site altitude, time step, random seed |
| tools | The tool schemas. Identical in every row. |
| messages | system, user, then assistant and tool turns, ending with the final assistant turn |
| verification | Checker result per target and per safety gate, plus OpenRocket version, motor database version and seed |
| generator | Which model or person wrote the trace, and the prompt version |

Targets example, for "clear 1,400 m, both stages under 6 m/s":

```json
"targets": {
  "apogee_m":      {"value": 1400, "kind": "min"},
  "ground_hit_ms": {"value": 6.0,  "kind": "max", "applies_to": "every section"},
  "motor":         {"value": ["I300T", "G80T"], "kind": "exact"}
}
```

Set the random seed in the simulation options every time. OpenRocket gives each new simulation a random seed for its wind model, so without a fixed seed the same design can come back with slightly different numbers.

## 5. Messages and the trace

### 5.1 System prompt

One system prompt, the same in every row. It must not ask for anything the trace can't honestly do. Proposed:

> You design amateur rockets that fly on certified commercial motors. Work through the design, check it with the tools, and give the final design as JSON inside `<design>` tags. Only report results the tools returned.

### 5.2 Tools

Only use tools the deployed model will actually have, and only call them for real while the trace is being generated. Proposed set:

- `motor_lookup(designation)`: impulse, thrust, burn time, diameter, mass. Returns an error for unknown motors.
- `stability(design)`: mass, CG, CP, static margin.
- `simulate(design)`: apogee, time to apogee, max velocity, rail-exit speed, flight time, landing speed per section, warnings.

### 5.3 Turn structure for Qwen3.5-4B

- Each assistant turn puts its reasoning in `reasoning_content` (rendered as `<think>…</think>`), not `<thought>`.
- Tool calls go in the `tool_calls` field. The chat template turns them into Qwen's XML format; don't hand-write it.
- Each tool result is its own message with role `tool`, holding the tool's output exactly. Tool turns are excluded from the training loss.
- The final assistant turn: reasoning, then content with a short plain summary and one `<design>…</design>` block. Nothing after the block.

Shape of one row (reasoning shortened; values in angle brackets come from the tool, never typed in):

```
{"role": "system", "content": "<system prompt>"}
{"role": "user", "content": "Two-stage rocket: I300T booster, G80T sustainer. Clear 1,400 m, both stages under 6 m/s, 1.5 m rail."}
{"role": "assistant",
 "reasoning_content": "1. Understand: apogee at least 1,400 m; each stage lands at most 6 m/s; motors fixed; rail 1.5 m. Wind not given, assuming 2 m/s.\n2. Feasibility: need motor data.",
 "tool_calls": [{"name": "motor_lookup", "arguments": {"designation": "I300T"}},
                {"name": "motor_lookup", "arguments": {"designation": "G80T"}}]}
{"role": "tool", "content": "<I300T data>"}
{"role": "tool", "content": "<G80T data>"}
{"role": "assistant",
 "reasoning_content": "2. Feasibility: total about 560 N*s. Ballistic speed for 1,400 m is sqrt(2*9.81*1400) = 166 m/s, so it looks reachable if the sustainer is light... 3. Size: ... chute for 1.5 kg at 5.5 m/s, Cd 0.8: D = 1.1 m ... 4. Draft: <design JSON>. Checking.",
 "tool_calls": [{"name": "simulate", "arguments": {"design": {...}}}]}
{"role": "tool", "content": "<simulate output>"}
{"role": "assistant",
 "reasoning_content": "4. Check: apogee <value> vs at least 1,400: pass/fail. Booster landing <value> vs 6.0: ... Margin <value> cal ...\n5. Fix: <only if something failed> 6. Uncertainty: drag and chute Cd are model values; ...",
 "content": "<2-4 line summary>\n<design>{...}</design>"}
```

### 5.4 Rules for the reasoning

- **No leakage (must).** Cover the targets and the final simulation results. Every line must still be something you could have written from the request, your own math, and tool output that came earlier. No target value at simulator precision before a tool returns it.
- **Provenance words (must).** "Verified", "simulated", "confirmed", "OpenRocket gives" only directly after a tool turn that returned that number. Never "measured in the flight data"; there is no flight.
- **Restate, don't paste (must).** Step 1 rewrites the request in SI units and labels each item as a minimum, maximum, approximate or fixed. Assumptions are stated.
- **Feasibility is real (must).** Step 2 compares rough required impulse with what's available, checks thrust-to-weight, and checks whether the targets agree with each other. If the request can't be met, say which part and offer the closest version.
- **Estimates may be wrong (must).** If the step 3 estimate disagrees with the simulator, say so and go with the simulator. Never bend an estimate to agree with a result.
- **Math recomputes (must).** Every shown calculation (thrust-to-weight, rail-exit speed, margin, descent rate) is rechecked by script.
- **Honest precision (must).** Estimates get 2 to 3 significant figures. Only tool output carries more.
- **Design matches reasoning (must).** Every number in the final design appears in, or follows from, the trace or a tool result.
- **Vary the sentences (should).** Keep the six step headings fixed, but don't reuse one sentence template with only numbers swapped.

## 6. Reflection and fixes

The "wait" only helps when it catches a real failure. A real fix has four parts, or it gets deleted:

1. the tool call that ran
2. the failing value against the target or limit it missed
3. the one change made to the design
4. the same tool run again, now passing

- **Must change something.** A "wait… yes, that's right" with nothing changed gets deleted.
- **Use real first drafts (should).** The best fixes come from the generator's first design actually failing the simulator.
- **Clean passes too (must).** At least about 30% of rows pass everything on the first draft and say so in one line under step 5. Without these, the model never learns when to stop.
- **Cap at 2 to 3 fix rounds (should).** After that, the answer says what's still failing.
- **Pick a fix that targets the cause (should):** apogee low → bigger motor or less mass; margin low → bigger fins or nose weight; landing fast → bigger chute; flight time long → dual deploy; slow off the rail → higher-thrust motor. Re-check what else the fix moves.

## 7. Checks before a row is kept

Generate several drafts per prompt with targets hidden from the generator, and keep only the ones that pass all four checks. Log a reason for every dropped draft. If every draft fails, log the prompt as unsolved; don't silently skip it.

1. **Parses.** One `<design>` block of valid JSON. Known component types, materials in OpenRocket's database, motors in the pinned motor database, SI units in key names, integer counts.
2. **Safety gates.** Thrust-to-weight at least 3:1 (NAR high power code). Rail-exit speed at least 15 m/s. Static margin at least 1.0 cal at launch and above 0 through the burn. Every section that separates has recovery. Each section lands under the limit (6 m/s by default). Total impulse at most 40,960 N·s. Wind under 20 mph.
3. **Targets.** Re-simulate the final design with the recorded seed. Use tolerances written before generation: apogee ±5% for "about", one-sided for "min"/"max", exact motor match after normalising names.
4. **Trace lint.** Leakage, provenance words, math recheck, design-matches-trace, repetition. Also re-run each tool call and confirm it matches its tool turn.

Before using the checker, test it on about 20 known cases, half that must pass and half that must fail. Include a design written in millimetres instead of metres, an unknown motor, an unstable design that still hits apogee, and a missing parachute.

Infeasible prompts pass only if the answer says infeasible and names the constraint that can't be met.

## 8. The whole file

- **Dedup (must).** Drop exact duplicate rows (3 now). Merge renamed copies of a design into one group (6 pairs now).
- **Cap rows per group (must).** Check the maximum, not the average.
- **Answer variety (must).** Count how often each motor, fin shape, body diameter and material appears in answers, and cap any one at a set share. An older set had 92 of 174 rows on one design, and the model learned to copy it.
- **Fill thin spots (should).** The file now has 433 single-stage designs, 38 two-stage and 6 three-stage, and 30 two-motor designs. Multi-stage and clusters need more rows.
- **Split by group (must).** All rows from one design go to one split. None of the current held-out files is clean: every prompt in rl_prompts_all.jsonl is in sft_all.jsonl, 249 of 252 in emh_prompts.jsonl, and all 43 in sft_test.jsonl. Match on names with folders and extensions stripped, and on target values, to catch renamed copies.
- **Token length (must).** Measure with the Qwen3.5-4B tokenizer and chat template, tool schemas and tool turns included. Shorten or drop overlong rows; never truncate.
- **Data card (must).** A short README per version: counts, sources, generator, checker and OpenRocket versions, tolerances, gate thresholds, drop counts by reason.

## 9. Row checklist

- Prompt asks for goals a person would set, rounded like a person, with at least one goal
- Prompt is not a nested copy of another row's prompt
- Targets hold only what the prompt asked, each with a kind
- Same system prompt and tool list as every other row
- Reasoning in reasoning_content (`<think>`), tool calls in tool_calls, tool output in tool turns
- All six steps present, in order
- No target or simulator value appears before a tool returned it
- "Verified", "simulated" etc. only right after the backing tool turn
- Every fix has a failing tool result, a change, and a passing re-run; or one line saying no fix was needed
- Final turn: short summary, one `<design>` block, nothing after
- Design parses, passes every safety gate, and meets every target on re-simulation
- Every tool turn matches a re-run with the recorded seed
- group_id and split set; under the group cap; fits the token limit
