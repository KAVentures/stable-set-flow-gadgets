# Degree-five vertices in critical complements are independent

## Status and assumptions

Let `G` be a hypothetical noncomplete double-critical `6`-chromatic graph, let
`I` be a maximal independent set, and put `H=G-I`.  We use:

1. `H` is `5`-vertex-critical;
2. `delta(G)>=8`;
3. `delta(H)>=5`;
4. `chi(G[N(v)])<=3` for every vertex;
5. for every edge `uv` and every proper `4`-colouring of `G-u-v`, the common
   neighbourhood `N(u) cap N(v)` meets all four colour classes;
6. the independently reproduced classification of an eight-vertex neighbourhood:
   if `d_G(v)=8`, then `G[N(v)]` is one of `GEnfbW` and `GEjfrw`.

The symbolic argument below handles every case except one finite local gluing.
That last case is checked by `verify_adjacent_degree5_independent.cpp`, which
reconstructs the two graph6 neighbourhoods, derives their admissible defect
decompositions, enumerates all gluings, and performs exact colouring searches.

## 1. The degree-five defect system

Fix `h in V(H)` with `d_H(h)=5`.  Write

- `U=N_H(h)`, so `|U|=5`;
- `A=N_I(h)`, so `|A|>=3` because `d_G(h)>=8`;
- `C_i=N_H(i) cap U` for `i in A`.

For each `i in A`, every `4`-colouring of `G-i-h` makes `C_i` rainbow.  The
family `{C_i:i in A}` is an antichain: if `C_i subseteq C_j`, then in a
`4`-colouring of `G-i-h`, the surviving vertex `j` is adjacent to a set
containing all four colours.

Every `C_i` therefore has size exactly four.  Thus there are distinct defects
`x_i in U` such that

```
C_i = U - {x_i}.
```

The fifth vertex `x_i` repeats a colour in a private colouring for `ih`.  It
cannot repeat the colour of another defect `x_j`, because the surviving vertex
`j` has that colour and is adjacent to `x_i`.  Hence it repeats the colour of a
nondefect in

```
Z = U - {x_i : i in A}.
```

Consequently `Z` is nonempty and `|A|` is either three or four.  Moreover
`H[U]` is bipartite: in a proper `3`-colouring of `G[N(h)]`, every
`U-{x_i}` uses at most two colours.  If `U` used three colours, each of at
least three distinct defects would have to be the unique representative of a
different colour, leaving no colour for the two remaining vertices without
destroying one of those uniqueness statements.

When `|A|=4`, write `U={x_1,x_2,x_3,x_4,z}`.  Then `z` is nonadjacent to all
four defects.  The four-defect regime has the further property that in every
`4`-colouring of `G-h-z`, the four vertices of `A` have distinct colours and
`x_i` has the colour of `i`.

## 2. The theorem

> **Theorem.** The vertices of degree five in `H` form an independent set.

Assume that `hq` is an edge of `H` with

```
d_H(h)=d_H(q)=5.
```

Put `A=N_I(h)` and `B=N_I(q)`.  Each has size three or four.  Since `q` is a
member of the five-vertex defect system at `h`, it is nonadjacent to at most
one member of `A`; equivalently `|A-B|<=1`.  Symmetrically `|B-A|<=1`.

### Case 1: `|A|=3`, `|B|=4`

Then `A subset B`; write `B=A union {s}`.  At `h`, the vertex `q` is a
nondefect.  At `q`, the vertex `h` is the defect corresponding to `s`.  Let
`w` be the unique nondefect at `q`, and let `z` be the nondefect at `h`
distinct from `q`.

First, `w != z`.  Indeed, the unique nondefect in a four-defect system is
nonadjacent to every defect.  Since `h` is a defect at `q`, `w` is nonadjacent
to `h`, whereas `z in N_H(h)`.

Now take a `4`-colouring of `G-q-w`.  The four vertices of `B` receive four
distinct colours and `h` receives the colour of `s`.  The surviving vertex
`z` is adjacent to `h` and to every member of `A`, so it sees all four
colours, a contradiction.  The case `(4,3)` is symmetric.

### Case 2: `|A|=|B|=4` and `|A cap B|=3`

Write `A=R union {s}` and `B=R union {t}`.  Then `q` is the defect
corresponding to `s` at `h`, and `h` is the defect corresponding to `t` at
`q`.  Let `z_h,z_q` be the respective unique nondefects.

These vertices are distinct.  The nondefect `z_h` is nonadjacent to every
defect at `h`, including `q`, while `z_q` is adjacent to `q` by definition.

In a `4`-colouring of `G-h-z_h`, the set `A` receives four distinct colours
and `q` receives the colour of `s`.  The surviving vertex `z_q` is adjacent
to `q` and to all three members of `R`; it therefore sees all four colours,
a contradiction.

### Case 3: `A=B` and `|A|=4`

Here `q` and `h` are nondefects in the respective systems.  Fix `i in A` and
take a `4`-colouring of `G-h-i`.  If `x_j` is the defect of `j` at `h`, then

```
{q} union {x_j : j in A-{i}}
```

contains all four colours, and each surviving `j in A-{i}` has the colour of
`x_j`.  Let `y_i` be the defect of `i` at `q`.  The vertex `y_i` is adjacent
to `q` and to every member of `A-{i}`, so it sees all four colours, again a
contradiction.

### Case 4: `|A|=|B|=3`

Now `d_G(h)=d_G(q)=8`.  Each completed neighbourhood is one of the two
classified graphs.  There are two intersection regimes:

- `|A cap B|=3`, where each centre is a nondefect in the other neighbourhood;
- `|A cap B|=2`, where each centre is a defect in the other neighbourhood.

The independent C++ verifier does not hardcode the four decompositions.  It:

1. decodes `GEnfbW` and `GEjfrw` from graph6;
2. finds every independent triple with three distinct one-vertex defects and
   a bipartite five-vertex `H`-neighbourhood;
3. obtains exactly four labelled local decompositions;
4. glues every possible common `I`-vertex and every possible common
   `H`-neighbour, preserving all forced adjacencies;
5. retains the necessary four-common-neighbour condition on `hq`;
6. deletes every unspecified cross-edge, thereby relaxing the actual graph;
7. for every edge from `h` or `q` to its `I`-neighbours, searches exactly for
   a proper `4`-colouring after endpoint deletion whose common neighbourhood
   contains all four colours.

Its exact census is

```
local_decompositions 4
compatible_gluings 160
intersection_2 80
intersection_3 80
survivors 0
status PASS
```

Deleting unspecified edges only makes proper colourings easier.  Hence failure
of the required colouring in every relaxed gluing excludes every completion.
This completes the final case.

## 3. Consequence and next target

If `d_H(h)=5`, then every vertex of `N_H(h)` has `H`-degree at least six.
Thus the first low-degree defect systems cannot touch one another; any global
contradiction must propagate through vertices of degree at least six.

The next precise target is to eliminate an **isolated degree-five defect
system**.  A proof would establish `delta(H)>=6` for every critical complement.
The most promising interfaces are:

- the private colouring classes attached to the three or four vertices of
  `N_I(h)`;
- the edge-deletion colourings on the five edges from `h` into `H`;
- the fact that all five neighbours of `h` have `H`-degree at least six;
- maximum-independent-set replacement, which forces Hall inequalities between
  independent subsets of `H` and their neighbours in `I`.

This theorem is structural progress, not a resolution of the double-critical
conjecture.
