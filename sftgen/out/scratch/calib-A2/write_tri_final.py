import json
from pathlib import Path

from sftgen.lint import _check_math

root = Path("sftgen/out/scratch/calib-A2")
text = (root / "tri_rfinal.txt").read_text()
result = _check_math(text)
print("checked", result.checked, "skipped", result.skipped, "bad", result.bad)
design = json.loads((root / "tri_sim4.json").read_text())["design"]
summary = (
    "Three Estes C11 motors in a 58 mm cardboard cluster, with enlarged balsa fins and 40 g of nose clay.\n"
    "Stable on the 0.914 m rod at 1.12 cal, landing 5.5 m/s on the stated limit. Apogee is still 230.9 m, short of about 305 m, after three design changes.\n"
)
content = summary + "<design>" + json.dumps(design, ensure_ascii=False) + "</design>\n"
(root / "tri_content.txt").write_text(content)
print("summary lines", len([ln for ln in summary.splitlines() if ln.strip()]))
