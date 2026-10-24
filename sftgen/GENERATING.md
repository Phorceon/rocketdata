# Writing traces with `sftgen.session`

You are the generator. For each prompt you write the reasoning a careful rocket designer would
write, call the real tools through the harness, and finish with a design. The harness records
every tool output verbatim; you never type a tool number by hand. The rules come from
`sftgen/DATA_SPEC.md` sections 5 and 6. Read those first.

Run everything from the repo root (`_repos/Phorceon_rocketdata`) with `.venv/bin/python`.

## What you may and may not look at

You only get what the deployed model gets: the system prompt, the user prompt and the tools.

- **Allowed:** `DATA_SPEC.md`, this file, `sftgen/schema.py` (the design format), `sftgen/contract.py`
  (tool schemas, gates), `sftgen/examples/alpha_c6.json`, `sftgen/out/pilot.jsonl` (a finished
  trace, as a format example only), your own scratch files and your own sessions.
- **Never open:** `sftgen/out/prompts_v1.jsonl` or anything else holding targets or reference
  answers (`groups.json`, `converted_designs.jsonl`, `prompts_v1_report.md`, `ork/`,
  `new_results/`, other generators' sessions, `drops.jsonl`). Don't run `checker` or
  `assemble`. Don't reuse a reference rocket's design. The point is to design, not recall.

## Loop for one prompt

```bash
P=.venv/bin/python
$P -m sftgen.session start PROMPT_ID --generator NAME          # prints system + user prompt
$P -m sftgen.session step  SID --reasoning r1.txt --call motor_lookup '{"designation": "H128W"}'
$P -m sftgen.session step  SID --reasoning r2.txt --call simulate @call2.json
$P -m sftgen.session final SID --reasoning r3.txt --content c3.txt --dry-run   # lint only, nothing saved
$P -m sftgen.session final SID --reasoning r3.txt --content c3.txt
```

`SID` is `PROMPT_ID__d1`. Several `--call` flags in one `step` run in parallel and appear as one
assistant turn with several tool calls. Each `step`'s reasoning must be written before you see
that step's output, because it is the text the model writes before calling the tool.

**Never edit a session file.** If a session goes wrong (a must-level lint issue in a committed
turn, or a call with a typo you can't explain naturally), abandon it and restart under a new
draft number. Should-level warnings are not a reason to restart. To restart:
`session abandon SID --reason "..."`, then `session start PROMPT_ID --draft 2`. The new draft
gets a different wind seed, so earlier tool numbers won't carry over. Don't paste reasoning
from the old draft.

## The trace

Every reasoning block continues the six steps, with headings exactly as `N. Heading:` at the
start of a line:

`1. Understand:` `2. Feasibility:` `3. Size:` `4. Draft:` / `4. Check:` `5. Fix:` `6. Uncertainty:`

- **1. Understand.** Restate the request in SI units and label each item min / max / about /
  fixed. State the assumptions for anything missing: rail 1.5 m, wind 2 m/s, landing limit 6 m/s
  unless the prompt says otherwise. Read "about X" as within ±5%.
- **2. Feasibility.** Look up the motors you're considering (`motor_lookup`) and do rough impulse,
  thrust-to-weight and consistency math. If it can't be done, say which constraint fails and
  why, and offer the closest feasible version.
- **3. Size.** Estimate mass, thrust-to-weight, rail exit, chute size and delay, to 2–3
  significant figures. Show the arithmetic; a script rechecks it, so it must be right.
- **4. Draft / Check.** Describe the draft, then `simulate` it (and `stability` if useful). After
  the output, compare every number that matters against its target or gate:
  pass or fail, with the margin.
- **5. Fix.** Only when a check really failed. Name the failing value and limit, make one change
  aimed at the cause, re-simulate, and re-check. At most 3 rounds; after that, say what still
  fails. If everything passed, write one line saying no fix was needed.
- **6. Uncertainty.** What the model can't know: drag and Cd are model values, the build mass
  will differ, how sensitive the result is to those.

Give your honest best first draft. Don't plant a mistake to create a fix, and don't over-tune
before the first simulation to dodge one. Real first drafts miss about half the time, and both
outcomes are useful.

### Rules the linter enforces

- **No leakage.** No simulator-precision number before a tool returned it. Estimates are rounded
  (2–3 significant figures). A long number you computed from tool outputs (a sum of two motors'
  impulse, say) is only a warning, so don't restart over it; rounding it is still better.
- **Every section lands.** Simulations run for up to 3600 s; a section still in the air at the
  end fails, as does one whose recovery never deployed.
- **Provenance words.** "simulated", "the simulator gives", "verified", "confirmed" and
  "OpenRocket gives" appear only after the tool turn that produced the number. Never
  "measured" or "flight data".
- **Math.** Every `a op b = c` you write is recomputed. Use `*`, `/`, `+`, `-`, `sqrt(...)`, `^`.
- **Design matches trace.** The final `<design>` must be exactly the last design you simulated,
  and every number in it must appear in or follow from the trace.
- **Final turn.** `content` holds a 2–4 line plain summary, then one `<design>{...}</design>`
  block with nothing after it. For an infeasible request, the summary must say it's infeasible
  and name the constraint. A closest-version design is optional; if you include one, it must
  be safe.

### Conditions

Tools run at the site defaults (1.5 m rail, 0° launch angle, 2 m/s wind, sea level). When the
prompt states wind, rail length, launch angle or site altitude, pass them yourself in every
`simulate` call: `{"design": {...}, "conditions": {"wind_ms": 3.6, "rail_length_m": 2.4}}`.
Convert units first (5 mph = 2.2 m/s, 8 ft = 2.4 m).

`sections[].landing_ms` is the vertical descent rate at touchdown. Wind drift is reported
separately as `drift_m`, so a landing limit is met with a big enough chute whatever the wind.

### Design format

`sftgen/schema.py` is the contract: SI units, metres not millimetres, integer counts, materials
from `BULK_MATERIALS` / `SURFACE_MATERIALS`, and motors by designation, with the manufacturer
optional. Stages are listed top first. Each stage needs a body tube and a motor mount, and
every section that separates needs a parachute or streamer. A `simulate` error such as
"invalid design: ..." is a real tool result. Fix it in the next step and say what you changed.

## Working through a batch

Your batch is a file of prompt ids, one per line (`sftgen/out/batches/batch_NN.txt`). Work them
in order. After each prompt, append one line to `sftgen/out/batches/batch_NN.log`:
`PROMPT_ID<TAB>SESSION_ID<TAB>final|abandoned<TAB>simulate calls<TAB>fix rounds<TAB>note`.
If you are restarted, read the log first and continue from the first prompt without a `final`
line. A prompt with an `open` session in `sftgen/out/sessions/` belongs to you: abandon it
("interrupted") and start the next draft number.

## When you finish a batch

Report back: for each prompt the session id, status (`final` or abandoned with the reason),
number of fix rounds, and any harness or tool problem you hit. A tool that errors or returns
something physically odd is worth reporting: copy the exact call.
