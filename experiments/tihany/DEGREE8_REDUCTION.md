# An order-independent reduction from a degree-eight vertex

## Status and dependency

The first part of this note is unconditional. The final `P5` / `C4`-with-leaf split is conditional on the exact two-type degree-eight neighbourhood audit supplied with the project. It is theorem-discovery input and is **not** used in the direct order-17 core certificate unless that audit is independently reproduced and its local-colouring quantifiers are checked against the stated theorem.

## Unconditional proposition

Let `G` be a hypothetical noncomplete double-critical 6-chromatic graph and let `x` be a vertex of degree eight. Then there is a maximal independent set `I` such that

```text
H = G-I
```

is 5-vertex-critical and

```text
d_H(x)=5.
```

### Proof

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

The complement of every maximal independent set in a double-critical 6-chromatic graph is 5-vertex-critical, so `H=G-I` has the required criticality. `QED`

## Conditional refinement from the supplied audit

The supplied exact degree-eight neighbourhood audit reports two surviving graph6 strings,

```text
GEnfbW
GEjfrw
```

and each has exactly two independent triples. Direct graph6 inspection gives:

- in `GEnfbW`, deleting either independent triple leaves `P5`;
- in `GEjfrw`, deleting either independent triple leaves a `C4` with one pendant vertex.

Consequently, **once the audit's exhaustiveness and extension quantifiers have been independently validated**, the proposition refines to

```text
H[N_H(x)] is P5 or C4 with one pendant vertex.
```

## Why this matters

A possible proof can then split into:

1. prove that neither five-vertex configuration can occur as the neighbourhood of a degree-five vertex in a 5-critical complement carrying the ambient double-critical deletion colourings; this would establish `delta(G)>=9`;
2. deal with the remaining minimum-degree-at-least-nine case.

The first step is an ambient precolouring-extension problem, not a classification of the isolated local escape object. If `F=G[N(x)]` and `R=G-N[x]`, then for every `y in N(x)` the graph `G-x-y` has a four-colouring whose restriction to `F-y` is constrained by the common-rainbow theorem. The obstruction lies in whether all boundary precolourings can be extended through the same ambient graph `R`.

This conditional refinement is not part of the core SAT correctness path.