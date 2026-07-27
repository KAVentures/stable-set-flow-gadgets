#!/usr/bin/env python3
"""Independent exact audit of Dmitry Rybin's triangle counterexample."""
from fractions import Fraction as F
from collections import defaultdict, deque
from itertools import combinations, product
from pathlib import Path
import json, argparse

def paths(adj,s,t):
    out=[]
    def dfs(v,p,seen):
        if v==t: out.append(tuple(p)); return
        for w,a in adj[v]:
            if w not in seen: dfs(w,p+(a,),seen|{w})
    dfs(s,tuple(),{s}); return out

def main(path):
    d=json.loads(Path(path).read_text()); arcs=[]; adj=defaultdict(list)
    for i,a in enumerate(d['arcs']):
        a={**a,'x':F(a['x']),'cost':F(a['cost'])}; arcs.append(a); adj[a['tail']].append((a['head'],i))
    dem={t['id']:F(t['demand']) for t in d['terminals']}; terms=list(dem); D=max(dem.values())
    ps={t:paths(adj,d['source'],t) for t in terms}
    assert {t:len(ps[t]) for t in terms}=={'t1':2,'t2':2,'t3':2}
    # The underlying graph is a subdivision of K4.  Suppressing each
    # degree-two terminal yields all six edges on the four core vertices.
    undirected={frozenset((a['tail'],a['head'])) for a in arcs}
    assert len(undirected)==len(arcs)==9
    core={'s','u','v','w'}
    direct={e for e in undirected if e<=core}
    terminal_pairs=set()
    expected_neighbors={'t1':{'s','v'},'t2':{'s','w'},'t3':{'u','w'}}
    for t, expected in expected_neighbors.items():
        neighbors={next(iter(e-{t})) for e in undirected if t in e}
        assert neighbors==expected
        terminal_pairs.add(frozenset(neighbors))
    suppressed=direct|terminal_pairs
    assert suppressed=={frozenset(pair) for pair in combinations(core,2)}
    bal=defaultdict(F)
    for a in arcs: bal[a['tail']]-=a['x']; bal[a['head']]+=a['x']
    assert bal['s']==-sum(dem.values())
    for t in terms: assert bal[t]==dem[t]
    fx=sum(a['x']*a['cost'] for a in arcs); assert fx==58
    zero={t:[j for j,p in enumerate(ps[t]) if sum(arcs[a]['cost'] for a in p)==0] for t in terms}
    assert all(len(zero[t])==1 for t in terms)
    masks=set(); good=[]; two_sided_D=[]; two_sided_2D=[]
    for choice in product(range(2),repeat=3):
        load=[F(0)]*len(arcs); cost=F(0)
        for t,j in zip(terms,choice):
            for a in ps[t][j]: load[a]+=dem[t]; cost+=dem[t]*arcs[a]['cost']
        if all(load[i]<=a['x']+D for i,a in enumerate(arcs)):
            mask=tuple(i for i,t in enumerate(terms) if choice[i]==zero[t][0]); masks.add(mask); good.append(cost)
        if all(a['x']-D<=load[i]<=a['x']+D for i,a in enumerate(arcs)):
            two_sided_D.append(cost)
        if all(a['x']-2*D<=load[i]<=a['x']+2*D for i,a in enumerate(arcs)):
            two_sided_2D.append(cost)
    assert masks=={(),(0,),(1,),(2,)}
    assert min(good)==60
    assert two_sided_D and min(two_sided_D)==60
    assert two_sided_2D and min(two_sided_2D)<=fx
    print("PASS: triangle independently audited; planar K4 subdivision, paths=6, routings=8")
    print("additive-D: feasible without costs, but minimum cost=60 > fractional cost=58")
    print("additive-2D: cost-preserving routing exists")
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('instance',nargs='?',default='instances/Rybin_triangle.json'); a=ap.parse_args(); main(a.instance)
