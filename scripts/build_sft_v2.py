#!/usr/bin/env python3
import json
import os
import sys
import hashlib
import re
import random

REPO = '/Users/dev/rocketdata'
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'scripts'))
sys.path.insert(0, os.path.join(REPO, 'sft'))

from sft_v1_lib import sims_of, targets_of, render_thought, SYSTEM_MSG, PROMPT_TEMPLATES, pick_prompt, motor_label, render_design_ir, n_stages
from ork_design import build_design
from scripts.or_headless import simulate
from sft_v1_readable import count_requirements_with_spans

V1 = os.path.join(REPO, 'new_results', 'sft_v1.jsonl')
V1T = os.path.join(REPO, 'data', 'sft_test.jsonl')
V2 = os.path.join(REPO, 'new_results', 'sft_v2.jsonl')
V2T = os.path.join(REPO, 'new_results', 'sft_test_v2.jsonl')
REPORT = os.path.join(REPO, 'new_results', 'SFT_V2_REPORT.md')

MISMATCH = {'U-197', 'U-199', 'U-441', 'U-443', 'U-444', 'U-452'}


def get_motors(path, simname):
    for s in sims_of(path):
        if s['name'] == simname:
            return s.get('active_motors') or []
    return []


def motor_label_from_list(ms):
    if not ms:
        return '?'
    return ms[0] if len(ms) == 1 else ', '.join(ms)


def sim_from_res_full(res, r):
    ms = get_motors(r['file'], r['sim'])
    max_mach = res.get('max_mach')
    if max_mach is None or (isinstance(max_mach, float) and (max_mach != max_mach)):
        max_mach = 0.0
    depv = res.get('deployment_velocity_ms')
    if depv is None or (isinstance(depv, float) and (depv != depv)):
        depv = 0.0
    wind_ms = res.get('wind_ms', 0.0)
    max_acc = res.get('max_accel_ms2', res.get('max_acceleration_ms2', 0.0))
    return {
        "name": r['sim'],
        "active_motors": ms,
        "apogee_m": float(res['apogee_m']),
        "max_velocity_ms": float(res['max_velocity_ms']),
        "max_acceleration_ms2": float(max_acc),
        "max_mach": float(max_mach),
        "time_to_apogee_s": float(res['time_to_apogee_s']),
        "flight_time_s": float(res['flight_time_s']),
        "ground_hit_ms": float(res['ground_hit_ms']),
        "deployment_velocity_ms": float(depv),
        "wind_ms": float(wind_ms),
    }


def replace_by_spans(prompt, spans):
    s = prompt
    items = sorted(spans, key=lambda x: x[0], reverse=True)
    for start, end, new_str, qty in items:
        s = s[:start] + new_str + s[end:]
    return s


def apply_touchdown_filter(kept, kept_t, v1_by_id, v1t_by_id):
    dropped_extra = []
    kept_new = []
    for r in kept:
        o = v1_by_id.get(r['id'])
        if not o:
            kept_new.append(r)
            continue
        ov = abs(o['targets'].get('ground_hit_ms') or 0)
        nv = abs(r['targets'].get('ground_hit_ms') or 0)
        cond = False
        if ov < 10 and nv > 15:
            cond = True
        if ov > 0 and abs(nv - ov) / ov > 1.0:
            cond = True
        if cond:
            dropped_extra.append((r['id'], 'touchdown_filter'))
            continue
        kept_new.append(r)
    kept_t_new = []
    for r in kept_t:
        if r['id'] not in v1t_by_id:
            kept_t_new.append(r)
            continue
        o = v1t_by_id[r['id']]
        ov = abs(o['targets'].get('ground_hit_ms') or 0)
        nv = abs(r['targets'].get('ground_hit_ms') or 0)
        cond = False
        if ov < 10 and nv > 15:
            cond = True
        if ov > 0 and abs(nv - ov) / ov > 1.0:
            cond = True
        if cond:
            dropped_extra.append((r['id'], 'touchdown_filter'))
            continue
        kept_t_new.append(r)
    return kept_new, kept_t_new, dropped_extra


def design_has_recovery(design):
    def walk(cs):
        for c in cs:
            if c.get('type') in ('parachute', 'streamer'):
                return True
            if walk(c.get('contains', []) or []):
                return True
        return False
    try:
        return walk(design.get('components', []) or [])
    except Exception:
        return False


def build_row(r, v1_row, regen_log, regen_reasons):
    v1_assistant_content = v1_row['messages'][2]['content']
    m = re.search(r"<design>\n(.*)\n</design>", v1_assistant_content, re.S)
    if not m:
        raise ValueError("no design")
    design = json.loads(m.group(1))

    try:
        res = simulate(r['file'], r['sim'], seed=42)
    except Exception as e:
        raise

    # Check recovery/ground hit
    if design_has_recovery(design):
        gh = res.get('ground_hit_ms')
        if gh is None or (isinstance(gh, float) and (gh != gh)):
            raise ValueError('recovery: no ground hit / NaN')
        if abs(gh) < 1e-12 and res.get('flight_time_s') and res.get('flight_time_s') < 1e-6:
            raise ValueError('recovery: no deployment/flight')
    else:
        gh = res.get('ground_hit_ms')
        if gh is None or (isinstance(gh, float) and (gh != gh)):
            raise ValueError('no ground hit / NaN')

    sim_new = sim_from_res_full(res, r)
    tnew = targets_of(sim_new)
    tnew['max_mach'] = sim_new['max_mach']
    tnew['deployment_velocity_ms'] = sim_new['deployment_velocity_ms']
    tnew['wind_ms'] = sim_new['wind_ms']
    tnew['max_acceleration_ms2'] = sim_new['max_acceleration_ms2']
    # ensure exactly from fresh sim
    tnew['apogee_m'] = float(sim_new['apogee_m'])
    tnew['max_velocity_ms'] = float(sim_new['max_velocity_ms'])
    tnew['time_to_apogee_s'] = float(sim_new['time_to_apogee_s'])
    tnew['flight_time_s'] = float(sim_new['flight_time_s'])
    tnew['ground_hit_ms'] = float(sim_new['ground_hit_ms'])

    for k, v in tnew.items():
        if isinstance(v, float):
            if v != v or abs(v) == float('inf'):
                raise ValueError(f'bad {k}')
    for k in ['apogee_m', 'max_velocity_ms', 'time_to_apogee_s', 'flight_time_s', 'ground_hit_ms']:
        if k not in tnew or tnew[k] is None:
            raise ValueError(f'missing {k}')
        if float(tnew[k]) <= 0 and k != 'ground_hit_ms':  # ground hit can be signed? check
            pass

    motor = motor_label_from_list(get_motors(r['file'], r['sim']))
    sim_info = {"motor": motor, "max_acceleration_ms2": tnew.get('max_acceleration_ms2')}

    regen = False
    pt_new = None
    if r['id'] in MISMATCH:
        regen = True
        regen_reasons.append((r['id'], 'mismatch_known'))
    else:
        try:
            found, spans = count_requirements_with_spans(v1_row, max_accel={r['id']: tnew.get('max_acceleration_ms2')}, new_targets=tnew)
            if len(spans) == 0 and len(found) == 0:
                regen = True
                regen_reasons.append((r['id'], 'unmapped_no_spans'))
            elif len(spans) < max(1, len([x for x in v1_row['prompt_text'] if False])):  # try harder - if spans missing for mapped numbers, still try to be more aggressive
                # try again with more permissive mapping
                try:
                    # attempt replacement if we got any spans
                    if len(spans) == 0:
                        regen = True
                        regen_reasons.append((r['id'], 'unmapped'))
                    else:
                        pt_new = replace_by_spans(v1_row['prompt_text'], spans)
                        regen = False
                except Exception:
                    regen = True
                    regen_reasons.append((r['id'], 'map_error'))
            else:
                pt_new = replace_by_spans(v1_row['prompt_text'], spans)
                regen = False
        except Exception:
            regen = True
            regen_reasons.append((r['id'], 'map_exception'))

    if regen or pt_new is None:
        if not any(x[0] == r['id'] for x in regen_reasons):
            regen_reasons.append((r['id'], 'regen_forced'))
        h = hashlib.sha256(r['id'].encode()).hexdigest()
        seed = int(h[:16], 16)
        rng = random.Random(seed)
        pt_new = pick_prompt(PROMPT_TEMPLATES, tnew, sim_new, motor, n_stages(design), rng)

    thought_new = render_thought(pt_new, sim_new, design)
    if '<design>' in v1_assistant_content:
        idx = v1_assistant_content.index('<design>')
        assistant_content = thought_new + '\n' + v1_assistant_content[idx:]
    else:
        assistant_content = thought_new

    ir = render_design_ir(design)
    row = {
        "id": r['id'],
        "file": r['file'],
        "source_prompt": "SFT_V2_RESIM",
        "sim": r['sim'],
        "prompt_text": pt_new,
        "messages": [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": pt_new},
            {"role": "assistant", "content": assistant_content},
        ],
        "targets": tnew,
        "ir_chars": len(ir),
        "split": r['split']
    }
    return row


def main():
    os.environ['OR_NO_CACHE']='1'
    v1_rows = [json.loads(l) for l in open(V1) if l.strip()]
    v1t_rows = [json.loads(l) for l in open(V1T) if l.strip()]
    v1_by_id = {r['id']: r for r in v1_rows}
    v1t_by_id = {r['id']: r for r in v1t_rows}

    kept = []
    dropped = []
    regen_log = []
    regen_reasons = []

    for r in v1_rows:
        v1r = v1_by_id[r['id']]
        try:
            row = build_row(r, v1r, regen_log, regen_reasons)
            kept.append(row)
        except Exception as e:
            dropped.append((r['id'], r['file'], r['sim'], str(e)))
            continue

    kept_t = []
    dropped_t = []
    for r in v1t_rows:
        v1r = v1t_by_id[r['id']]
        try:
            row = build_row(r, v1r, regen_log, regen_reasons)
            kept_t.append(row)
        except Exception as e:
            dropped_t.append((r['id'], r['file'], r['sim'], str(e)))
            continue

    kept, kept_t, dropped_extra = apply_touchdown_filter(kept, kept_t, v1_by_id, v1t_by_id)
    dropped.extend([(x[0], None, None, x[1]) for x in dropped_extra])

    os.makedirs(os.path.dirname(V2), exist_ok=True)
    with open(V2, 'w') as f:
        for x in kept:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')
    with open(V2T, 'w') as f:
        for x in kept_t:
            f.write(json.dumps(x, ensure_ascii=False) + '\n')

    # determinism check
    try:
        import scripts.or_headless as oh
        oh._DOC_CACHE.clear()
        if hasattr(oh, '_SIM_CACHE'): oh._SIM_CACHE.clear()
    except Exception:
        pass
    kept2, dropped2, regen_log2, regen_reasons2 = [], [], [], []
    for r in v1_rows:
        v1r = v1_by_id[r['id']]
        try:
            row = build_row(r, v1r, regen_log2, regen_reasons2)
            kept2.append(row)
        except Exception as e:
            dropped2.append((r['id'], r['file'], r['sim'], str(e)))
            continue
    kept_t2, dropped_t2 = [], []
    for r in v1t_rows:
        v1r = v1t_by_id[r['id']]
        try:
            row = build_row(r, v1r, regen_log2, regen_reasons2)
            kept_t2.append(row)
        except Exception as e:
            dropped_t2.append((r['id'], r['file'], r['sim'], str(e)))
            continue
    kept2, kept_t2, dropped_extra2 = apply_touchdown_filter(kept2, kept_t2, v1_by_id, v1t_by_id)
    dropped2.extend([(x[0], None, None, x[1]) for x in dropped_extra2])

    h1 = hashlib.sha256()
    for x in kept:
        h1.update((json.dumps(x, ensure_ascii=False) + '\n').encode())
    h2 = hashlib.sha256()
    for x in kept2:
        h2.update((json.dumps(x, ensure_ascii=False) + '\n').encode())
    h1t = hashlib.sha256()
    for x in kept_t:
        h1t.update((json.dumps(x, ensure_ascii=False) + '\n').encode())
    h2t = hashlib.sha256()
    for x in kept_t2:
        h2t.update((json.dumps(x, ensure_ascii=False) + '\n').encode())

    # schema check
    try:
        import eval_test
        types, motors = eval_test.reference_vocab()
        schema_ok = 0
        for r in kept + kept_t:
            ans = r["messages"][-1]["content"]
            s = eval_test.score(r, "", ans, "stop", types, motors)
            if s["design_found"] and s["json_ok"] and s["schema_ok"] and s["recovery"]:
                schema_ok += 1
        schema_total = len(kept) + len(kept_t)
    except Exception as e:
        schema_ok, schema_total = 0, len(kept) + len(kept_t)

    # stats
    changes_gh = []
    changes_ft = []
    details = []
    for r in kept:
        o = v1_by_id[r['id']]
        ov = o['targets'].get('ground_hit_ms')
        nv = r['targets'].get('ground_hit_ms')
        of = o['targets'].get('flight_time_s')
        nf = r['targets'].get('flight_time_s')
        if ov is not None and nv is not None and ov != 0 and nv == nv:
            pct = abs(nv - ov) / abs(ov) * 100.0
            changes_gh.append(pct)
            details.append((r['id'], ov, nv, pct, 'gh'))
        if of is not None and nf is not None and of != 0 and nf == nf:
            pct = abs(nf - of) / abs(of) * 100.0
            changes_ft.append(pct)
            details.append((r['id'], of, nf, pct, 'ft'))

    def med(a):
        if not a:
            return float('nan')
        b = sorted(a)
        n = len(b)
        if n % 2 == 1:
            return b[n // 2]
        return (b[n // 2 - 1] + b[n // 2]) / 2

    def p90(a):
        if not a:
            return float('nan')
        b = sorted(a)
        k = min(len(b) - 1, int(round(0.9 * (len(b) - 1))))
        return b[k]

    report = []
    report.append('# SFT_V2_REPORT')
    report.append('')
    report.append(f'- Rows kept (train): {len(kept)} / {len(v1_rows)}')
    report.append(f'- Rows kept (test): {len(kept_t)} / {len(v1t_rows)}')
    report.append(f'- Regenerated rows (with reasons): {regen_reasons}')
    report.append('')
    report.append(f'- Touchdown speed % change (train, after drops): median={med(changes_gh):.2f}%, p90={p90(changes_gh):.2f}%')
    report.append(f'- Flight time % change (train, after drops): median={med(changes_ft):.2f}%, p90={p90(changes_ft):.2f}%')
    report.append('')
    report.append('## Top 10 changes (old → new)')
    for x in sorted(details, key=lambda x: x[3], reverse=True)[:10]:
        report.append(f'- {x[0]} ({x[4]}): {x[1]:.3f} → {x[2]:.3f} ({x[3]:.1f}% change)')
    report.append('')
    report.append('## All dropped rows with reasons')
    all_dropped = []
    for x in dropped:
        all_dropped.append(('train_drop', x))
    for x in dropped_t:
        all_dropped.append(('test_drop', x))
    for tag, x in all_dropped:
        if len(x) == 4:
            report.append(f'- {tag} {x[0]} {x[1]} [{x[2]}]: {x[3]}')
        elif len(x) == 2:
            report.append(f'- {tag} {x[0]}: {x[1]}')
        else:
            report.append(f'- {tag} {x}')
    report.append('')
    report.append('## Verification')
    report.append(f'- eval_test.score style (types,motors from reference_vocab()): {schema_ok}/{schema_total}')
    report.append(f'- Deterministic (train): {h1.hexdigest() == h2.hexdigest()}')
    report.append(f'- Deterministic (test): {h1t.hexdigest() == h2t.hexdigest()}')
    report.append(f'- <design> blocks byte-identical to v1: verified by design copy')
    report.append(f'- Hashes train: {h1.hexdigest()} vs {h2.hexdigest()}')
    report.append(f'- Hashes test: {h1t.hexdigest()} vs {h2t.hexdigest()}')

    with open(REPORT, 'w') as f:
        f.write('\n'.join(report) + '\n')

    print(json.dumps({'kept_train': len(kept), 'kept_test': len(kept_t), 'schema_ok': schema_ok, 'schema_total': schema_total, 'det_train': h1.hexdigest() == h2.hexdigest(), 'det_test': h1t.hexdigest() == h2t.hexdigest(), 'hash_train1': h1.hexdigest(), 'hash_test1': h1t.hexdigest()}))


if __name__ == '__main__':
    main()
