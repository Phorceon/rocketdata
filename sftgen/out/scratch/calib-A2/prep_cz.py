import json
import re
from pathlib import Path

from sftgen.lint import _check_math

root = Path("sftgen/out/scratch/calib-A2")
for name in ("tri_r4.txt", "cz_rfinal.txt"):
    text = (root / name).read_text()
    result = _check_math(text)
    print(name, "checked", result.checked, "skipped", result.skipped, "bad", result.bad)
    match = re.search(r"(?m)^5\. Fix:", text)
    if match:
        rest = text[match.end():]
        nxt = re.search(r"(?m)^6\. ", rest)
        body = rest[: nxt.start()] if nxt else rest
        lines = [ln for ln in body.splitlines() if ln.strip()]
        print(" step5 chars", len(body.strip()), "lines", len(lines))

design = json.loads((root / "cz_sim1.json").read_text())["design"]
summary = (
    "Infeasible: the 10 second flight time cannot be met with an apogee of about 650 m "
    "and a landing under 4.57 m/s.\n"
    "The simulated flight still takes 182.5 s, so the time limit fails. Closest safe rocket: "
    "F67W-9, 38 mm cardboard tube, 0.50 m chute, 652.5 m apogee, 4.2 m/s landing.\n"
)
content = summary + "<design>" + json.dumps(design, ensure_ascii=False) + "</design>\n"
(root / "cz_content.txt").write_text(content)
print("summary lines", len([ln for ln in summary.splitlines() if ln.strip()]))
