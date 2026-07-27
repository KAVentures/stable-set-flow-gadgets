#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
import numpy as np
OUTER=[(a,b) for a in range(14) for b in range(a+1,14) if b!=(a^1)]
assert len(OUTER)==84

def parse_model(path):
    vals={}
    for line in open(path,errors='ignore'):
        if not line.startswith('v '):continue
        for z in line.split()[1:]:
            v=int(z)
            if v:vals[abs(v)]=v>0
    return vals

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--solver-log',required=True);ap.add_argument('--meta',required=True);ap.add_argument('--output',default='adjacency.txt')
    a=ap.parse_args();meta=json.load(open(a.meta));vals=parse_model(a.solver_log)
    if not vals:raise SystemExit('No SAT witness literals found')
    H=np.zeros((84,84),dtype=np.int64)
    for key,var in meta['h_variables'].items():
        i,j=map(int,key.split(','));H[i,j]=H[j,i]=int(vals.get(var,False))
    A=np.zeros((99,99),dtype=np.int64)
    for p in range(14):A[0,1+p]=A[1+p,0]=1
    for p in range(0,14,2):A[1+p,1+p+1]=A[1+p+1,1+p]=1
    for x,e in enumerate(OUTER):
        ox=15+x
        for p in e:A[ox,1+p]=A[1+p,ox]=1
    A[15:,15:]=H
    assert np.array_equal(A,A.T)
    assert np.all(np.diag(A)==0)
    assert set(np.unique(A))<={0,1}
    assert np.all(A.sum(axis=1)==14),A.sum(axis=1)
    target=12*np.eye(99,dtype=np.int64)-A+2*np.ones((99,99),dtype=np.int64)
    assert np.array_equal(A@A,target),np.max(np.abs(A@A-target))
    idx={e:i for i,e in enumerate(OUTER)};x=idx[(0,2)]
    selected={OUTER[y] for y in range(84) if H[x,y] and set(OUTER[y])&{0,2}}
    expected={tuple(z) for z in meta['F']}
    assert selected==expected,(selected,expected)
    np.savetxt(a.output,A,fmt='%d')
    json.dump({'parameters':[99,14,1,2],'adjacency':A.tolist()},open(a.output+'.json','w'))
    print('PASS: exact SRG(99,14,1,2) adjacency matrix')
if __name__=='__main__':main()
