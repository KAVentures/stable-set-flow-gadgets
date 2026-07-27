#!/usr/bin/env python3
from __future__ import annotations
import argparse,itertools,json,os,shutil,tempfile

OUTER=[(a,b) for a in range(14) for b in range(a+1,14) if b!=(a^1)]
assert len(OUTER)==84
IDX={e:i for i,e in enumerate(OUTER)}
STARS=[[i for i,e in enumerate(OUTER) if p in e] for p in range(14)]
assert all(len(s)==12 for s in STARS)
F_REPS=[((0,3),(1,2)),((0,3),(2,4)),((0,4),(2,4)),((0,4),(2,5)),((0,4),(2,6))]

class CNF:
    def __init__(self,body):
        self.body=body;self.nvars=0;self.nclauses=0
    def var(self): self.nvars+=1;return self.nvars
    def clause(self,*lits):
        ls=[]
        for x in lits:
            if isinstance(x,(list,tuple)):ls.extend(x)
            else:ls.append(x)
        if any(x==0 for x in ls): raise ValueError('zero literal')
        self.body.write(' '.join(map(str,ls))+' 0\n');self.nclauses+=1
    def atmost(self,lits,k):
        lits=list(lits);n=len(lits)
        if k<0:self.clause();return
        if k>=n:return
        if k==0:
            for x in lits:self.clause(-x)
            return
        if n==1:
            if k<1:self.clause(-lits[0])
            return
        s=[[None]*(k+1) for _ in range(n)]
        for i in range(n-1):
            for j in range(1,k+1):s[i][j]=self.var()
        self.clause(-lits[0],s[0][1])
        for j in range(2,k+1):self.clause(-s[0][j])
        for i in range(1,n-1):
            self.clause(-lits[i],s[i][1])
            self.clause(-s[i-1][1],s[i][1])
            for j in range(2,k+1):
                self.clause(-lits[i],-s[i-1][j-1],s[i][j])
                self.clause(-s[i-1][j],s[i][j])
            self.clause(-lits[i],-s[i-1][k])
        self.clause(-lits[-1],-s[n-2][k])
    def exact(self,lits,k):
        lits=list(lits);n=len(lits)
        if not 0<=k<=n:
            self.clause();return
        self.atmost(lits,k)
        if k==0:return
        if k==1:
            self.clause(lits)
        elif k==2:
            self.clause(lits)
            for i,x in enumerate(lits):self.clause(-x,lits[:i],lits[i+1:])
        else:
            raise NotImplementedError(k)

def stabilizer_orbit_check():
    x=(0,2)
    shared=[e for e in OUTER if e!=x and set(e)&set(x)]
    assert len(shared)==22
    group=[]
    for swap01 in (False,True):
      for rest in itertools.permutations(range(2,7)):
       for bits in range(1<<5):
        pairmap={0:1 if swap01 else 0,1:0 if swap01 else 1}
        pairmap.update({old:new for old,new in zip(range(2,7),rest)})
        p=[0]*14
        for old in range(7):
            new=pairmap[old];flip=0 if old<2 else ((bits>>(old-2))&1)
            for b in (0,1):p[2*old+b]=2*new+(b^flip)
        assert {p[0],p[2]}=={0,2}
        group.append(p)
    def act(e,p):return tuple(sorted((p[e[0]],p[e[1]])))
    viable={tuple(sorted((a,b))) for a,b in itertools.combinations(shared,2)
            if (0 in a)+(0 in b)==1 and (2 in a)+(2 in b)==1}
    unseen=set(viable);orbits=[]
    while unseen:
        a=next(iter(unseen));orb={tuple(sorted((act(a[0],p),act(a[1],p)))) for p in group}
        orb &= viable;orbits.append(orb);unseen-=orb
    expected={tuple(sorted(z)) for z in F_REPS}
    assert len(orbits)==5
    assert all(sum(tuple(sorted(z)) in o for z in expected)==1 for o in orbits)
    return [len(o) for o in orbits]

def build(case:int,out:str,meta:str):
    assert 0<=case<5
    orbit_sizes=stabilizer_orbit_check()
    tmp=out+'.body'
    with open(tmp,'w',buffering=1024*1024) as body:
        c=CNF(body)
        h={}
        for i in range(84):
            for j in range(i+1,84):h[i,j]=c.var()
        def hv(i,j):
            if i>j:i,j=j,i
            return h[i,j]
        for x,e in enumerate(OUTER):
            es=set(e)
            for p in range(14):
                rhs=2-int(p in es)-int((p^1) in es)
                c.exact([hv(x,y) for y in STARS[p] if y!=x],rhs)
        for x,e in enumerate(OUTER):
            shared=[y for y,f in enumerate(OUTER) if y!=x and set(e)&set(f)]
            disjoint=[y for y,f in enumerate(OUTER) if y!=x and not(set(e)&set(f))]
            assert len(shared)==22 and len(disjoint)==61
            c.exact([hv(x,y) for y in shared],2)
        for i in range(84):
            ei=set(OUTER[i])
            for j in range(i+1,84):
                terms=[hv(i,j)]
                for k in range(84):
                    if k==i or k==j:continue
                    y=c.var();a=hv(i,k);b=hv(j,k)
                    c.clause(-y,a);c.clause(-y,b);c.clause(y,-a,-b)
                    terms.append(y)
                rhs=1 if ei&set(OUTER[j]) else 2
                c.exact(terms,rhs)
        x=IDX[(0,2)]
        chosen={IDX[tuple(sorted(e))] for e in F_REPS[case]}
        shared={y for y,e in enumerate(OUTER) if y!=x and set(e)&{0,2}}
        assert len(shared)==22 and len(chosen)==2 and chosen<=shared
        for y in sorted(shared):c.clause(hv(x,y) if y in chosen else -hv(x,y))
    with open(out,'w',buffering=1024*1024) as fo,open(tmp) as bi:
        fo.write(f'p cnf {c.nvars} {c.nclauses}\n');shutil.copyfileobj(bi,fo,1024*1024)
    os.unlink(tmp)
    data={'case':case,'F':F_REPS[case],'outer':OUTER,'h_variables':{f'{i},{j}':v for (i,j),v in h.items()},
          'nvars':c.nvars,'nclauses':c.nclauses,'orbit_sizes':orbit_sizes}
    with open(meta,'w') as f:json.dump(data,f,separators=(',',':'))
    print(json.dumps({k:data[k] for k in ('case','F','nvars','nclauses','orbit_sizes')}))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',type=int,required=True);ap.add_argument('--out',required=True);ap.add_argument('--meta',required=True)
    a=ap.parse_args();build(a.case,a.out,a.meta)
if __name__=='__main__':main()
