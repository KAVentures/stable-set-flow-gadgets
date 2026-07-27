# Correctness of the reduction-independent order-17 encoding

## Proposition

The completed ultra-core CEGAR formula is satisfiable if and only if there exists a noncomplete double-critical 6-chromatic graph on 17 vertices.

The only imported structural theorem is the established minimum-degree bound `delta(G)>=8`. No independence-number or critical-complement reduction is used.

## Forward direction

Suppose `G` is a noncomplete double-critical 6-chromatic graph on 17 vertices. Since `G` is noncomplete, choose a nonedge and relabel its endpoints `0,1`. Then:

- `e_01` is false;
- `delta(G)>=8`;
- every edge `uv` has a proper four-colouring of `G-u-v`;
- `G` has no proper five-colouring.

Assign the graph variables and one deletion-colouring witness for each edge. Every base clause and every valid five-colouring cut is satisfied.

## Reverse direction

Let a completed ultra-core model define a graph `G`.

- `01` is a nonedge, so `G` is noncomplete.
- `delta(G)>=8`; in particular, `G` has an edge and is connected at order 17. Indeed, every component would contain at least nine vertices, while two components would require at least eighteen vertices.
- The completed CEGAR cuts imply that `G` is not five-colourable, so `chi(G)>=6`.
- Choose any edge `uv`. Its activated block four-colours `G-u-v`. Give `u` and `v` two fresh colours. Hence `chi(G)<=6`, and therefore `chi(G)=6`.
- Every edge deletion is at most four-colourable by its activated block. Deleting two vertices lowers chromatic number by at most two, so each deletion is also at least four-chromatic. Hence

  ```text
  chi(G-u-v)=4
  ```

  for every edge `uv`.

Thus `G` is a noncomplete double-critical 6-chromatic graph.

## Consequence

A SAT model passing the independent verifiers is a genuine order-17 counterexample. A static ultra-core CNF with an independently checked UNSAT certificate proves the order-17 exclusion without relying on the 13-vertex-complement computation, the attachment upper bound, or any local auxiliary lemma.