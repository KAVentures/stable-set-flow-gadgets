# Exact order-17 search for the double-critical 6-chromatic case

## Status

This directory is a fresh, direct encoding of the defining graph problem. It does **not** treat any earlier exploratory SAT/SMT output as a theorem. In particular, an UNSAT result is accepted only after a deterministic static DIMACS formula is emitted and an independently checked proof certificate is produced.

The mathematical reduction used by the core search is:

- `n = 17`;
- a fixed maximum independent set `I = {0,1,2,3}`;
- `alpha(G) = 4`;
- `delta(G) >= 8`;
- for `x in I`, `8 <= |N(x)| <= 11`;
- for every edge `uv`, `G-u-v` is 4-colourable;
- `G` is not 5-colourable.

The attachment upper bound follows because `H=G-I` is 5-vertex-critical: `N(x)=V(H)` would induce `H`, while a 12-vertex attachment would induce `H-w`; these have chromatic number 5 and 4 respectively, contradicting `chi(G[N(x)]) <= 3`.

## Two encodings

### Core

The core formula contains only:

1. graph variables on 17 vertices;
2. the fixed independent four-set;
3. clauses forbidding independent five-sets;
4. minimum degree eight;
5. attachment degrees between eight and eleven;
6. one guarded four-colouring block for every possible edge.

Non-5-colourability is enforced by CEGAR. Every independently found 5-colouring with classes `C_1,...,C_5` adds the permanent clause

```
OR_{i=1}^5 OR_{a<b in C_i} e_ab.
```

A SAT model with no 5-colouring is decoded and independently checked. An UNSAT result causes the current base clauses and all preserved cuts to be written as one static DIMACS file.

### Accelerated

The accelerated formula adds only proved necessary conditions:

- `H` is 5-vertex-critical;
- `delta(H) >= 5`;
- each completed vertex neighbourhood is 3-colourable;
- every edge has at least four common neighbours;
- the four attachment neighbourhoods form an antichain and cover `H`;
- the local capacity inequalities.

The accelerated search is for speed and theorem discovery. The core search is the primary protection against a false UNSAT caused by an auxiliary encoding error.

## Validation

The workflow performs the following before accepting a result:

- tests the generic deletion-colouring module on fixed `K6`;
- checks that fixed `K6-e` is eliminated by a valid 5-colouring cut;
- checks all connected graph-atlas graphs through order seven;
- validates every generated cut against the graph that produced it;
- uses two separately written exact colouring algorithms before declaring a candidate non-5-colourable;
- independently verifies every edge deletion in a candidate;
- compiles a separate C++ graph verifier;
- emits a static DIMACS formula after CEGAR convergence;
- reruns a proof-producing SAT solver on the static formula;
- checks the resulting DRAT proof with `drat-trim`.

## Files

- `core_search.py`: deterministic CNF construction, CEGAR loop, checkpointing, and static DIMACS output.
- `verify_graph.py`: independent Python verification and graph-atlas regression tests.
- `verify_graph.cpp`: separately written C++ verifier for a decoded candidate.
- `tests.py`: unit and regression tests.
- `run_certified.sh`: proof-producing static solve and DRAT verification.

## Success conditions

- A decoded graph passing both independent verifiers is an order-17 counterexample.
- A static core CNF together with an independently accepted DRAT/LRAT certificate proves that no order-17 counterexample exists, hence `n >= 18`.
- Neither outcome by itself resolves all orders. The UNSAT-core and ablation outputs are retained to extract an order-independent structural lemma.