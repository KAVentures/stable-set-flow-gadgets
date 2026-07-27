# Degree-eight vertices are independent

## Statement

> **Computer-assisted theorem.** Let `G` be a noncomplete double-critical
> `6`-chromatic graph. Then no two vertices of degree eight are adjacent.
> Equivalently, the vertices of minimum possible degree form an independent set.

The finite part uses the independently reproduced classification that the
neighbourhood of a degree-eight vertex is one of the two graph6 graphs

```
GEnfbW
GEjfrw
```

and the KPT common-rainbow property: for every edge `uv`, every proper
`4`-colouring of `G-u-v` uses all four colours on `N(u) cap N(v)`.

The theorem has not yet been checked against the full historical literature for
novelty.  The Rolek--Song degree theorem excludes edges from a degree-seven
vertex to vertices of degrees seven, eight, or nine; the present statement is a
different, next-degree restriction.

## Exact reduction

Assume adjacent degree-eight vertices `h,q` exist.  Fix the labelled local graphs

```
L_h = G[N(h)],   L_q = G[N(q)].
```

Both belong to the two-element list above.  In `L_h`, the vertex representing
`q` has neighbourhood exactly

```
C = N_G(h) cap N_G(q).
```

Likewise, the vertex representing `h` in `L_q` has neighbourhood `C`.  Hence the
two local degrees are equal, and the induced graphs on these two copies of `C`
must be isomorphic.

The verifier enumerates:

1. both choices of `L_h`;
2. every possible position of `q` in `L_h`;
3. both choices of `L_q`;
4. every possible position of `h` in `L_q`;
5. every adjacency-preserving bijection between the two labelled copies of `C`.

There are exactly 184 compatible labelled amalgams:

```
GEjfrw  degree 4  / GEjfrw  degree 4 : 40
GEjfrw  degree 4  / GEnfbW  degree 4 : 32
GEjfrw  degree 5  / GEjfrw  degree 5 :  8
GEnfbW  degree 4  / GEjfrw  degree 4 : 32
GEnfbW  degree 4  / GEnfbW  degree 4 : 72
```

For each amalgam `R`, all edges within `N(h)` and within `N(q)` are fixed by the
two local graphs.  Every other edge between the two exclusive local pieces is
deleted.  This is a safe relaxation for the test below:

- deleting those edges can only make a proper colouring easier;
- `h` and `q` have degree exactly eight, so all their neighbours are already in
  the amalgam;
- for an edge `hx`, every possible common neighbour is in `N(h)`, and its
  adjacency to `x` is already fixed by `G[N(h)]`; therefore deleting unspecified
  cross-edges neither removes nor adds a common neighbour of `hx`;
- the same holds for every edge incident with `q`.

If the amalgam came from an actual graph `G`, then for every edge `hx` incident
with `h`, a `4`-colouring of `G-h-x` would restrict to a proper `4`-colouring of
`R-h-x` in which the fixed set `N_R(h) cap N_R(x)` contains all four colours.
The analogous statement holds at `q`.

The exact verifier searches for these colourings separately for every incident
edge.  No compatible amalgam supports all of them:

```
compatible_gluings 184
survivors 0
status PASS
```

Thus adjacent degree-eight vertices cannot exist.

## Verification boundary

`verify_adjacent_degree8.cpp` is self-contained.  It:

- decodes both graph6 strings itself;
- enumerates all common-neighbour bijections by raw permutations;
- checks adjacency compatibility without a graph-isomorphism package;
- constructs the relaxed amalgam directly as bitsets;
- performs an exact DSATUR-style backtracking search for each required proper
  four-colouring and common-rainbow condition;
- asserts the complete census `184` and survivor count `0`.

A separately written Python prototype, using NetworkX for the common-neighbour
isomorphisms and a different colouring routine, independently produced the same
five subtotals and zero survivors before this C++ verifier was committed.

## Consequences

Let

```
D = {v in V(G) : d_G(v)=8}.
```

Then `D` is independent.  Hence it may be included in a maximal independent set
`I`; the critical complement `H=G-I` contains no global degree-eight vertex.
Every vertex of `H` therefore has global degree at least nine, although its
`H`-degree may still be five.

Combining this with the degree-five defect theorem gives an especially clean
remaining low-degree configuration.  If `h in H` has `d_H(h)=5`, then

```
d_G(h)=9,  |N_I(h)|=4,
```

so only the four-defect regime can occur.  Its five `H`-neighbours have
`H`-degree at least six, because degree-five vertices in `H` are independent.

The next target is therefore narrower than before:

> Eliminate an isolated four-defect degree-five vertex in a critical complement
> chosen to contain all global degree-eight vertices.

A proof of that target would give `delta(H)>=6` for this canonical choice of
maximal independent set and materially sharpen both the order-17 search and the
order-independent structural program.
