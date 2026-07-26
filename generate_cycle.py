#!/usr/bin/env python3
"""Generate the exact C_{2k+1} robust flow gadget as JSON."""
from fractions import Fraction as F
from pathlib import Path
import argparse, json

def fs(x): return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"

def build(k, eps):
    n=2*k+1; T=F(k,2*(k+1)); t=T+eps; sload=F(1,2)+eps
    b=sload+t; q=t/b; tau=1-t; lam_test=(sload+tau)/2
    arcs=[]
    def add(id,tail,head,x,c,kind,owner=None):
        arcs.append(dict(id=id,tail=tail,head=head,x=fs(x),cost=fs(c),kind=kind,owner=owner))
    vertices=['s']; terms=[]
    for i in range(n):
        vertices += [f'a{i}',f'b{i}',f'c{i}',f'd{i}',f't{i}']
        add(f'start_{i}','s',f'a{i}',t+F(1,2),0,'chain',i)
        add(f'rfirst_{i}',f'a{i}',f'b{i}',t+F(1,2),0,'resource_first',i)
        add(f'connector_{i}',f'b{i}',f'c{i}',t,0,'connector',i)
        add(f'rsecond_{i}',f'c{i}',f'd{i}',t+F(1,2),0,'resource_second',i)
        add(f'final_{i}',f'd{i}',f't{i}',t,0,'chain',i)
        add(f'approach_{i}','s',f'c{i}',F(1,2),1/b,'approach',i)
        add(f'direct_{i}','s',f't{i}',sload,1/b,'direct',i)
        terms.append(dict(id=f't{i}',kind='primary',index=i,demand=fs(b)))
    for i in range(n):
        j=(i+1)%n; vertices.append(f'e{i}')
        add(f'exit_second_{i}',f'd{i}',f'e{i}',F(1,2),0,'exit_second',i)
        add(f'exit_first_{i}',f'b{j}',f'e{i}',F(1,2),1/b,'exit_first',i)
        terms.append(dict(id=f'e{i}',kind='auxiliary',edge=[i,j],demand='1'))
    return dict(name=f'C{n}_robust_flow_gadget',source='s',vertices=list(dict.fromkeys(vertices)),terminals=terms,arcs=arcs,
      parameters={'k':k,'n':n,'epsilon':fs(eps),'T':fs(T),'t=bq':fs(t),'s=b(1-q)':fs(sload),'b':fs(b),'q':fs(q),'D':'1','tau=1-t':fs(tau),'lambda_test':fs(lam_test),'odd_cycle_violation=nq-k':fs(n*q-k),'fractional_cost':fs(n*(1-q+1/b))})

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('k',type=int); ap.add_argument('--epsilon'); ap.add_argument('-o','--output',required=True)
    a=ap.parse_args();
    if a.k < 1: raise SystemExit('k must be >= 1')
    eps=F(a.epsilon) if a.epsilon else F(1,8*(a.k+1)*(2*a.k+1))
    upper=F(1,4*(a.k+1))
    if not (0 < eps < upper): raise SystemExit(f'epsilon must satisfy 0 < epsilon < {upper}')
    Path(a.output).write_text(json.dumps(build(a.k,eps),indent=2))
if __name__=='__main__': main()
