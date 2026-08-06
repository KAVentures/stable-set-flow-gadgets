# Correctness of the direct core encoding

## Proposition

After the established order-17 reduction, the completed core CEGAR formula is satisfiable if and only if there exists a noncomplete double-critical 6-chromatic graph on 17 vertices.

Here “completed” means that every proper colouring with at most five colours has been excluded by its corresponding permanent colouring cut.

## Forward direction

Let `G` be an order-17 counterexample. The established reduction gives a maximum independent set of size four. Relabel it as

```text
I = {0,1,2,3}.
```

Then:

1. the six edges inside `I` are absent;
2. no five-set is independent, because `alpha(G)=4`;
3. every vertex has degree at least eight;
4. each `x in I` has all its neighbours in `H=G-I`, and the proved attachment bound gives `8 <= |N(x)| <= 11`;
5. for every edge `uv`, double-criticality provides a proper four-colouring of `G-u-v`;
6. `G` has no proper five-colouring.

Assign the graph variables and one selected deletion colouring for every edge. Every core clause is satisfied. Every five-colouring cut is also satisfied, since otherwise its five classes would be independent sets giving a proper five-colouring of `G`.

## Reverse direction

Suppose a completed core formula has a model and let `G` be its graph.

- The fixed set `I` is independent.
- The independent-five-set clauses imply `alpha(G) <= 4`; hence `alpha(G)=4`.
- The degree clauses give `delta(G) >= 8`.
- At order 17 this already implies connectivity: every component has at least nine vertices, so two components would require at least 18 vertices.
- The completed CEGAR cuts imply that `G` is not five-colourable, so `chi(G) >= 6`.
- The degree bound guarantees an edge `uv`. Its activated block four-colours `G-u-v`; assigning two fresh colours to `u` and `v` gives a six-colouring of `G`. Thus `chi(G) <= 6` and therefore `chi(G)=6`.
- For every edge `uv`, the activated block gives `chi(G-u-v) <= 4`. Deleting two vertices can lower chromatic number by at most two, so

  ```text
  chi(G-u-v) >= chi(G)-2 = 4.
  ```

  Hence `chi(G-u-v)=4` for every edge.

Thus `G` is connected, 6-chromatic and double-critical. It is noncomplete because it contains the independent four-set `I`.

## Consequence

A decoded SAT model is a genuine counterexample after independent verification. A checked UNSAT certificate for the completed static core CNF proves that no order-17 counterexample exists, and therefore raises the lower bound to 18.

The accelerated formula is not used in this equivalence proof.