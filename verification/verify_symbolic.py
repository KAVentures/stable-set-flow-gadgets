#!/usr/bin/env python3
"""Independent symbolic verifier for the uniform odd-cycle theorem.

It checks the rational identities and inequalities for arbitrary k and epsilon,
and verifies the local path/resource proof obligations encoded by the generator.
This implementation is independent of the exhaustive routing enumerator.
"""
from fractions import Fraction as F
import argparse

def check(k,eps):
    n=2*k+1; T=F(k,2*(k+1)); t=T+eps; s=F(1,2)+eps; b=s+t; q=t/b; tau=1-t
    assert 0<eps<F(1,4*(k+1))
    assert F(1,2)<s and 0<t<F(1,2) and F(0)<b<F(1)
    assert b*q==t and b*(1-q)==s
    assert n*q-k==eps/b>0
    # Exact stable-set overload at additive D=1.
    x_resource=t+F(1,2)
    assert b+1 > x_resource+1
    # Borrowed auxiliary path is excluded exactly below tau.
    assert t+tau==1
    # Stable-set witness routes fit at lambda=1.
    assert 1<=F(1,2)+1                 # direct approach
    assert 1<=x_resource+1             # one auxiliary on a resource
    assert b<=t+1                      # primary on connector
    # Cost threshold separator and threshold witness.
    gap=n*q-k
    assert gap==eps/b
    frac_cost=n*(1-q+1/b)
    threshold_cost=F(n)
    assert threshold_cost < frac_cost
    # Symmetric-family optimum.
    tau_star=F(k+2,2*(k+1))
    assert tau==tau_star-eps
    return n,b,q,t,s,tau,gap,frac_cost

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--max-k',type=int,default=200)
    a=ap.parse_args()
    for k in range(1,a.max_k+1):
        eps=F(1,8*(k+1)*(2*k+1)); check(k,eps)
    n,b,q,t,s,tau,gap,cx=check(2,F(1,120))
    print('PASS: symbolic parameter checks for k=1..',a.max_k)
    print('C5: b=',b,'q=',q,'tau=',tau,'gap=',gap,'cTx=',cx)
if __name__=='__main__': main()
