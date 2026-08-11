#!/usr/bin/env python3
"""Exact rooted-84 search for an SRG(99,14,1,2).

Outside vertices are the 84 edges of K_14 minus a perfect matching.
The model enforces all degree, root-label common-neighbor (NL), and
outside-pair common-neighbor equations. Any feasible solution is therefore
a full Conway 99 graph; the script reconstructs and independently verifies A.

Usage: python root84_cp_sat.py --branch 0 --seconds 20000
branch 0 fixes {0,2}~{0,3}; branch 1 fixes {0,2}~{0,4}.
These are the two stabilizer orbits for the unique F-neighbor through label 0.
"""
from __future__ import annotations
import argparse, json, os, time
from itertools import combinations
from ortools.sat.python import cp_model

PAIRS=[(2*i,2*i+1) for i in range(7)]
MATE={}
for a,b in PAIRS: MATE[a]=b; MATE[b]=a
TYPES=[(a,b) for a in range(14) for b in range(a+1,14) if MATE[a]!=b]
IDX={t:i for i,t in enumerate(TYPES)}
assert len(TYPES)==84

def build(branch:int):
    m=cp_model.CpModel()
    E={(i,j):m.NewBoolVar(f'e_{i}_{j}') for i in range(84) for j in range(i+1,84)}
    def e(i,j):
        if i==j: return 0
        return E[(i,j)] if i<j else E[(j,i)]

    # L 1 = 12 1 and exact NL=2J-N-KN.
    for i,t in enumerate(TYPES):
        st=set(t)
        m.Add(sum(e(i,j) for j in range(84) if j!=i)==12)
        for u in range(14):
            target=2-int(u in st)-int(MATE[u] in st)
            ys=[j for j,s in enumerate(TYPES) if j!=i and u in s]
            m.Add(sum(e(i,j) for j in ys)==target)

    # N^T N + L^2 = 12I-L+2J, off diagonal.
    # For each pair, common outside neighbors + shared root labels + adjacency = 2.
    for i in range(84):
        si=set(TYPES[i])
        for j in range(i+1,84):
            shared=len(si.intersection(TYPES[j]))
            zs=[]
            for k in range(84):
                if k==i or k==j: continue
                z=m.NewBoolVar(f'z_{i}_{j}_{k}')
                a=e(i,k); b=e(j,k)
                m.Add(z<=a); m.Add(z<=b); m.Add(z>=a+b-1)
                zs.append(z)
            m.Add(sum(zs)+shared+e(i,j)==2)

    x=IDX[(0,2)]
    y=IDX[(0,3)] if branch==0 else IDX[(0,4)]
    m.Add(e(x,y)==1)
    return m,E

def reconstruct(solver,E):
    L=[[0]*84 for _ in range(84)]
    for (i,j),v in E.items():
        if solver.Value(v): L[i][j]=L[j][i]=1
    A=[[0]*99 for _ in range(99)]
    for u in range(14): A[0][1+u]=A[1+u][0]=1
    for a,b in PAIRS: A[1+a][1+b]=A[1+b][1+a]=1
    for i,(a,b) in enumerate(TYPES):
        v=15+i
        for u in (a,b): A[v][1+u]=A[1+u][v]=1
    for i in range(84):
        for j in range(i+1,84):
            if L[i][j]: A[15+i][15+j]=A[15+j][15+i]=1
    return A,L

def verify(A):
    assert len(A)==99 and all(len(r)==99 for r in A)
    for i in range(99):
        assert A[i][i]==0
        assert sum(A[i])==14
        for j in range(99): assert A[i][j] in (0,1) and A[i][j]==A[j][i]
    for i in range(99):
        for j in range(99):
            lhs=sum(A[i][k]*A[k][j] for k in range(99))
            rhs=(12 if i==j else 0)-A[i][j]+2
            assert lhs==rhs,(i,j,lhs,rhs)
    return True

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--branch',type=int,choices=[0,1],required=True)
    ap.add_argument('--seconds',type=float,default=20000); ap.add_argument('--workers',type=int,default=4)
    ap.add_argument('--out',default='result.json'); args=ap.parse_args()
    t0=time.time(); model,E=build(args.branch); build_sec=time.time()-t0
    solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=args.seconds
    solver.parameters.num_search_workers=args.workers; solver.parameters.log_search_progress=True
    status=solver.Solve(model)
    result={'branch':args.branch,'status':solver.StatusName(status),'build_seconds':build_sec,
            'wall_seconds':solver.WallTime(),'conflicts':solver.NumConflicts(),'branches':solver.NumBranches()}
    if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        A,L=reconstruct(solver,E); result['verified']=verify(A); result['adjacency_rows']=[''.join(map(str,r)) for r in A]
    with open(args.out,'w') as f: json.dump(result,f,indent=2)
    print('RESULT_JSON',json.dumps(result if 'adjacency_rows' not in result else {k:v for k,v in result.items() if k!='adjacency_rows'}))

if __name__=='__main__': main()
