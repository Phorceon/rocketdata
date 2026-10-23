#!/usr/bin/env python3
import json, os, sys, random
REPO = '/Users/dev/rocketdata'
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO,'scripts'))
from sft_v1_lib import sims_of, targets_of, render_thought, SYSTEM_MSG, PROMPT_TEMPLATES, pick_prompt, motor_label, render_design_ir, n_stages, fmt_feet
from ork_design import build_design
import ork_design

# build_design returns (components, meta); also need all_components equivalent
def all_components(path):
    comps, _ = build_design(path)
    return comps

from scripts.or_headless import simulate

V1 = os.path.join(REPO, 'new_results', 'sft_v1.jsonl')
V1T = os.path.join(REPO, 'data', 'sft_test.jsonl')
V2 = os.path.join(REPO, 'new_results', 'sft_v2.jsonl')
V2T = os.path.join(REPO, 'new_results', 'sft_test_v2.jsonl')
REPORT = os.path.join(REPO, 'new_results', 'SFT_V2_REPORT.md')

v1_rows = []
for line in open(V1):
    if line.strip(): v1_rows.append(json.loads(line))
v1t_rows = []
for line in open(V1T):
    if line.strip(): v1t_rows.append(json.loads(line))

PROB = {'U-197','U-199','U-441','U-443','U-444','U-452'}

def get_motors(path, simname):
    for s in sims_of(path):
        if s['name']==simname:
            return s.get('active_motors') or []
    return []

def motor_label_from_list(ms):
    if not ms: return '?'
    return ms[0] if len(ms)==1 else ', '.join(ms)

def sim_from_res_full(res,r):
    ms = get_motors(r['file'],r['sim'])
    # get max_mach from original if possible
    max_mach = r['targets'].get('max_mach') or 0.0
    return {
        "name": r['sim'],
        "active_motors": ms,
        "apogee_m": res['apogee_m'],
        "max_velocity_ms": res['max_velocity_ms'],
        "max_acceleration_ms2": res.get('max_accel_ms2', res.get('max_acceleration_ms2', 0.0)),
        "max_mach": max_mach,
        "time_to_apogee_s": res['time_to_apogee_s'],
        "flight_time_s": res['flight_time_s'],
        "ground_hit_ms": res['ground_hit_ms'],
        "deployment_velocity_ms": 0.0,
        "wind_ms": 0.0,
    }

def rebuild_prompt(old_prompt, tnew, sim_new, design, motor, rid):
    r2 = random.Random((hash(old_prompt) * 131542391) ^ hash(rid))
    pt = pick_prompt(PROMPT_TEMPLATES, tnew, sim_new, motor, n_stages(design), r2)
    return pt, (rid in PROB)

kept = []
dropped = []
flagged10 = []
changed_counts = {k:[] for k in ['apogee_m','flight_time_s','ground_hit_ms','max_velocity_ms','time_to_apogee_s']}

for r in v1_rows:
    try:
        res = simulate(r['file'], r['sim'], seed=42)
    except Exception as e:
        dropped.append((r['id'], r['file'], r['sim'], str(e)[:60]))
        continue
    try:
        comps = all_components(r['file'])
        ms = get_motors(r['file'],r['sim'])
        motor = motor_label_from_list(ms)
        design = {"flight": {"motor": motor, "wind_ms": 0.0}, "components": comps}
        sim_new = sim_from_res_full(res,r)
        tnew = targets_of(sim_new)
        oldt = r['targets']
        for k in ['apogee_m','flight_time_s','ground_hit_ms','max_velocity_ms','time_to_apogee_s']:
            ov = oldt.get(k); nv = tnew.get(k)
            if ov is not None and nv is not None and abs(ov)>1e-12:
                pct = abs(nv-ov)/abs(ov)*100.0
                changed_counts[k].append(pct)
                if pct > 10.0:
                    flagged10.append((r['id'], k, ov, nv, pct))
        pt_new, flagged = rebuild_prompt(r['prompt_text'], tnew, sim_new, design, motor, r['id'])
        ir = render_design_ir(design)
        row = {
            "id": r['id'],
            "file": r['file'],
            "source_prompt": "SFT_V2_RESIM",
            "sim": r['sim'],
            "prompt_text": pt_new,
            "messages": [{"role": "system", "content": SYSTEM_MSG}, {"role": "user", "content": pt_new}, {"role": "assistant", "content": render_thought(pt_new, sim_new, design)}],
            "targets": tnew,
            "ir_chars": len(ir),
            "split": r['split']
        }
        kept.append(row)
    except Exception as e:
        dropped.append((r['id'], r['file'], r['sim'], 'err'))
        continue

kept_t = []
dropped_t = []
for r in v1t_rows:
    try:
        res = simulate(r['file'], r['sim'], seed=42)
    except Exception as e:
        dropped_t.append((r['id'], r['file'], r['sim'], str(e)[:60]))
        continue
    try:
        comps = all_components(r['file'])
        ms = get_motors(r['file'],r['sim'])
        motor = motor_label_from_list(ms)
        design = {"flight": {"motor": motor, "wind_ms": 0.0}, "components": comps}
        sim_new = sim_from_res_full(res,r)
        tnew = targets_of(sim_new)
        pt_new,_ = rebuild_prompt(r['prompt_text'], tnew, sim_new, design, motor, r['id'])
        ir = render_design_ir(design)
        row = {
            "id": r['id'],
            "file": r['file'],
            "source_prompt": "SFT_V2_RESIM",
            "sim": r['sim'],
            "prompt_text": pt_new,
            "messages": [{"role": "system", "content": SYSTEM_MSG}, {"role": "user", "content": pt_new}, {"role": "assistant", "content": render_thought(pt_new, sim_new, design)}],
            "targets": tnew,
            "ir_chars": len(ir),
            "split": r['split']
        }
        kept_t.append(row)
    except Exception as e:
        dropped_t.append((r['id'], r['file'], r['sim'], 'err'))
        continue

with open(V2,'w') as f:
    for x in kept: f.write(json.dumps(x, ensure_ascii=False)+'\n')
with open(V2T,'w') as f:
    for x in kept_t: f.write(json.dumps(x, ensure_ascii=False)+'\n')

# verify
# rebuild twice
import subprocess
# write quick verify
print(json.dumps({'kept':len(kept),'dropped':len(dropped),'kept_t':len(kept_t),'dropped_t':len(dropped_t),'flagged10':len(flagged10)}))
open('/tmp/v2_flags.json','w').write(json.dumps(flagged10))
open('/tmp/v2_dropped.json','w').write(json.dumps(dropped))
open('/tmp/v2_dropped_t.json','w').write(json.dumps(dropped_t))
open('/tmp/v2_changes.json','w').write(json.dumps({k:sum(changed_counts[k])/len(changed_counts[k]) if changed_counts[k] else 0 for k in changed_counts}))
