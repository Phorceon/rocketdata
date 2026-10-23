#!/usr/bin/env python3
import json
import os
import sys
import hashlib
import re
import math

REPO = '/Users/dev/rocketdata'
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'scripts'))
sys.path.insert(0, os.path.join(REPO, 'sft'))

V1 = os.path.join(REPO, 'new_results', 'sft_v1.jsonl')
V1T = os.path.join(REPO, 'data', 'sft_test.jsonl')
V2 = os.path.join(REPO, 'new_results', 'sft_v2.jsonl')
V2T = os.path.join(REPO, 'new_results', 'sft_test_v2.jsonl')
RL = os.path.join(REPO, 'data/splits/rl_heldout.jsonl')


def load(p):
    rows = []
    for line in open(p, encoding='utf-8'):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main():
    v1 = load(V1)
    v1t = load(V1T)
    v2 = load(V2)
    v2t = load(V2T)
    try:
        rl = load(RL)
    except Exception:
        rl = []
    v1d = {r['id']: r for r in v1}
    v1td = {r['id']: r for r in v1t}

    all_rows = v2 + v2t
    ids = [r['id'] for r in all_rows]
    assert len(ids) == len(set(ids)), 'dup ids'
    ROW_KEYS = ["id", "file", "source_prompt", "sim", "prompt_text", "messages", "targets", "ir_chars", "split"]
    TARGET_KEYS = ["apogee_m", "max_velocity_ms", "max_mach", "time_to_apogee_s", "flight_time_s", "ground_hit_ms", "wind_ms"]
    for r in all_rows:
        assert list(r.keys()) == ROW_KEYS, f"keys {r['id']}"

    # recovery device deployed and ground hit happened
    from ork_design import build_design
    def has_rec(path):
        comps,_ = build_design(path)
        def walk(cs):
            for c in cs:
                if c.get('type') in ('parachute','streamer'): return True
                if walk(c.get('contains',[]) or []): return True
            return False
        try: return walk(comps)
        except: return False
    for r in all_rows:
        assert abs(r['targets']['ground_hit_ms']) > 0
    # overlap
    from ork_family import build_all
    fam, fam_members = build_all(sorted("ork/" + f for f in os.listdir(os.path.join(REPO, "ork")) if f.lower().endswith(".ork")))
    train_files = set(r['file'] for r in v2)
    test_files = set(r['file'] for r in v2t)
    rl_files = set(r['file'] for r in rl)
    assert len(train_files & test_files) == 0
    assert len(train_files & rl_files) == 0
    assert len(test_files & rl_files) == 0

    print('ALL CHECKS PASSED')
    print(f'v2:{len(v2)} v2t:{len(v2t)}')


if __name__ == '__main__':
    main()
