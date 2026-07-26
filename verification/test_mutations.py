#!/usr/bin/env python3
"""Adversarial mutations that the exact verifier must reject."""
import copy, json, subprocess, tempfile
from pathlib import Path
base=json.loads(Path('instances/C5.json').read_text())
mut=[]
# Remove the one-epsilon pair overload on one resource.
m=copy.deepcopy(base)
for a in m['arcs']:
    if a['id']=='rsecond_0': a['x']='17/20'
mut.append(('remove a cycle-edge incompatibility',m))
# Create a bypass path to an edge auxiliary that avoids both incidence resources.
m=copy.deepcopy(base); m['arcs'].append({'id':'forbidden_bypass','tail':'s','head':'e0','x':'0','cost':'0','kind':'mutation','owner':None})
mut.append(('add an unpriced bypass path',m))
# Make a hybrid primary path zero-cost.
m=copy.deepcopy(base)
for a in m['arcs']:
    if a['id']=='approach_0': a['cost']='0'
mut.append(('make a hybrid primary route cheap',m))
# Destroy the odd-cycle violation while preserving most topology.
m=copy.deepcopy(base); m['parameters']['q']='2/5'; m['parameters']['odd_cycle_violation=nq-k']='0'
mut.append(('erase the odd-cycle violation metadata',m))

for name,obj in mut:
    with tempfile.NamedTemporaryFile('w',suffix='.json',delete=False) as f:
        json.dump(obj,f); path=f.name
    r=subprocess.run(['python3','verification/verify_c5.py',path,'--quiet'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    assert r.returncode!=0, (name,r.stdout,r.stderr)
    print('REJECTED:',name)
print('PASS: mutation suite')
