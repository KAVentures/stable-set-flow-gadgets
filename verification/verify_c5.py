#!/usr/bin/env python3
"""Exact all-path/all-routing verifier for the supplied C5 certificate.

No prescribed path list is trusted. Every simple source-terminal path is derived
from the JSON DAG, and all 3^10 = 59,049 unsplittable routings are enumerated.
All arithmetic uses fractions.Fraction.
"""
from fractions import Fraction as F
from collections import defaultdict, deque
from itertools import product
from pathlib import Path
import argparse, json, sys

def frac(x): return F(str(x))

def stable_sets_cycle(n):
    out=set()
    for bits in range(1<<n):
        S=tuple(i for i in range(n) if bits>>i & 1)
        if all(not ((bits>>i)&1 and (bits>>((i+1)%n))&1) for i in range(n)):
            out.add(S)
    return out

def topological(vertices, arcs):
    indeg={v:0 for v in vertices}; adj=defaultdict(list)
    for i,a in enumerate(arcs):
        adj[a['tail']].append((a['head'],i)); indeg[a['head']]+=1
    q=deque([v for v,d in indeg.items() if d==0]); order=[]
    while q:
        v=q.popleft(); order.append(v)
        for w,_ in adj[v]:
            indeg[w]-=1
            if indeg[w]==0:q.append(w)
    assert len(order)==len(vertices), 'graph is not acyclic'
    return adj,order

def all_paths(adj, source, target):
    out=[]
    def dfs(v,path,seen):
        if v==target:
            out.append(tuple(path)); return
        for w,ai in adj[v]:
            if w not in seen: dfs(w,path+(ai,),seen|{w})
    dfs(source,tuple(),{source})
    return out

def load_cost(choice, terms, paths, demands, arcs):
    loads=[F(0) for _ in arcs]; cost=F(0)
    for term,pi in zip(terms,choice):
        d=demands[term]
        for ai in paths[term][pi]:
            loads[ai]+=d; cost += d*arcs[ai]['cost']
    return loads,cost

def verify(path, quiet=False):
    data=json.loads(Path(path).read_text())
    arcs=[{**a,'x':frac(a['x']),'cost':frac(a['cost'])} for a in data['arcs']]
    adj,order=topological(data['vertices'],arcs)
    source=data['source']; terms=[t['id'] for t in data['terminals']]
    demands={t['id']:frac(t['demand']) for t in data['terminals']}
    primary=[t['id'] for t in data['terminals'] if t['kind']=='primary']
    aux=[t['id'] for t in data['terminals'] if t['kind']=='auxiliary']
    n=int(data['parameters']['n']); k=int(data['parameters']['k'])
    assert n==5 and k==2, 'this exhaustive verifier is intentionally specialized to C5'
    assert max(demands.values())==1

    # Fractional flow feasibility, from arc loads alone.
    bal=defaultdict(F)
    for a in arcs:
        bal[a['tail']]-=a['x']; bal[a['head']]+=a['x']
    assert bal[source]==-sum(demands.values())
    for t,d in demands.items(): assert bal[t]==d, (t,bal[t],d)
    for v in data['vertices']:
        if v!=source and v not in demands: assert bal[v]==0, (v,bal[v])

    paths={t:all_paths(adj,source,t) for t in terms}
    assert all(len(paths[t])==3 for t in terms), {t:len(paths[t]) for t in terms}
    cheap={}
    for t in primary:
        z=[j for j,p in enumerate(paths[t]) if sum(arcs[a]['cost'] for a in p)==0]
        assert len(z)==1, (t,z)
        cheap[t]=z[0]

    frac_cost=sum(a['x']*a['cost'] for a in arcs)
    assert frac_cost==frac(data['parameters']['fractional_cost'])
    stable=stable_sets_cycle(n)

    def enumerate_at(lam):
        good=0; masks=set(); mincost=None; witness=None
        for choice in product(*[range(len(paths[t])) for t in terms]):
            loads,cost=load_cost(choice,terms,paths,demands,arcs)
            if all(loads[i] <= a['x']+lam for i,a in enumerate(arcs)):
                good+=1
                mask=tuple(i for i,t in enumerate(primary) if choice[i]==cheap[t])
                masks.add(mask)
                if mincost is None or cost<mincost:
                    mincost=cost; witness=choice
        return good,masks,mincost,witness

    good1,masks1,min1,w1=enumerate_at(F(1))
    assert masks1==stable, (masks1^stable)
    assert good1==724

    lam=frac(data['parameters']['lambda_test'])
    tau=frac(data['parameters']['tau=1-t'])
    gap=frac(data['parameters']['odd_cycle_violation=nq-k'])
    assert lam<tau
    goodL,masksL,minL,wL=enumerate_at(lam)
    assert masksL==stable
    assert minL-frac_cost==gap, (minL,frac_cost,gap)

    goodT,masksT,minT,wT=enumerate_at(tau)
    assert minT <= frac_cost
    assert minT==n

    # Direct odd-cycle arithmetic.
    q=frac(data['parameters']['q'])
    assert n*q-k==gap and gap>0

    if not quiet:
        print('PASS: exact C5 certificate')
        print('topological vertices:',len(order),'arcs:',len(arcs))
        print('path counts:',{t:len(paths[t]) for t in terms})
        print('all routings:',3**len(terms))
        print('lambda=1 good routings:',good1,'selection masks:',len(masks1))
        print('lambda_test:',lam,'good routings:',goodL)
        print('fractional cost:',frac_cost,'minimum cost:',minL,'gap:',minL-frac_cost)
        print('threshold tau:',tau,'minimum cost at tau:',minT)
    return True

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('instance',nargs='?',default='instances/C5.json'); ap.add_argument('--quiet',action='store_true')
    a=ap.parse_args()
    try: verify(a.instance,a.quiet)
    except Exception as e:
        if not a.quiet: print('FAIL:',repr(e),file=sys.stderr)
        raise
