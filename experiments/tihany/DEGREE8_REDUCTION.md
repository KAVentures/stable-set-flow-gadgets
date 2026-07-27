# An order-independent reduction from a degree-eight vertex

This note records a structural consequence that is independent of the order-17 computation.
It does not eliminate degree eight by itself.

## Proposition

Let `G` be a hypothetical noncomplete double-critical 6-chromatic graph and let `x` be a vertex of degree eight. Then there is a maximal independent set `I` and a 5-vertex-critical graph

```text
H = G-I
```

such that

```text
d_H(x)=5,
```

and the induced graph on `N_H(x)` is one of the following two five-vertex graphs:

1. `P5`;
2. a `C4` with one pendant vertex.

## Proof

The standard local results give

```text
chi(G[N(x)]) <= 3,
alpha(G[N(x)]) <= d_G(x)-5 = 3.
```

Since `|N(x)|=8` and a 3-colouring has a colour class of size at least three,

```text
alpha(G[N(x)])=3.
```

Choose an independent triple `A` in `N(x)` and extend it to a maximal independent set `I` of `G`. No further neighbor of `x` can lie in `I`, because `A` is already a maximum independent set in `G[N(x)]`. Therefore

```text
|I cap N(x)|=3
```

and hence

```text
d_{G-I}(x)=8-3=5.
```

The complement of every maximal independent set in a double-critical 6-chromatic graph is 5-vertex-critical, so `H=G-I` has the required criticality.

The exact degree-eight neighbourhood classification leaves two graphs, with graph6 strings

```text
GEnfbW
GEjfrw
```

respectively. Each has exactly two independent triples. Direct inspection gives:

- in `GEnfbW`, deleting either independent triple leaves `P5`;
- in `GEjfrw`, deleting either independent triple leaves a `C4` with a pendant vertex.

Thus `H[N_H(x)]` has one of the two displayed forms. `QED`

## Why this matters

A full proof can now split cleanly:

1. prove that neither five-vertex configuration can occur as the neighbourhood of a degree-five vertex in a 5-critical complement carrying the double-critical attachment colourings; this would establish `delta(G)>=9`;
2. deal with the remaining minimum-degree-at-least-nine case.

The first step is an ambient precolouring-extension problem, not a classification of the isolated seven-vertex local escape object. If `F=G[N(x)]` and `R=G-N[x]`, then for every `y in N(x)` the graph `G-x-y` has a four-colouring whose restriction to `F-y` is constrained by the common-rainbow theorem. The obstruction lies in whether all eight boundary precolourings can be extended through the same ambient graph `R`.

This is the order-independent theorem-mining target used by the ablation experiments.