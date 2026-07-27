# Symbolic elimination of the residual degree-eight/degree-nine rook interfaces

## Scope and dependency

This note concerns the order-17 case.  It uses the preceding finite local reduction as
input:

1. a degree-eight vertex `0` adjacent to a degree-nine vertex `1` has the unique
   exceptional 13-vertex rooted interface;
2. after the exact cross-edge and four-outside-vertex multicover reductions, only
   interface patterns `0, 2, 3, 4, 6` remain.

The argument below is symbolic.  It does not rely on the SAT/CEGAR completion jobs.
Its conclusion is therefore only as strong as the independently certified local census
and multicover reduction that produce those five patterns.

We use the standard necessary properties of a hypothetical noncomplete double-critical
6-chromatic graph:

- `alpha(G)=4` in the order-17 reduction;
- `G` has no `K5`;
- `chi(G[N(v)]) <= 3` for every vertex `v`;
- every edge has at least four common neighbours;
- degree-eight vertices form an independent set.

Let `O={13,14,15,16}` be the four vertices outside the fixed 13-vertex interface.
The centres `0` and `1` have exact degrees eight and nine, so neither is adjacent to
`O`.

## Pattern 0

In pattern 0, vertices `4,6,8` form a triangle and each has interface degree five.
All three are adjacent to the degree-eight centre `0`.  Since degree-eight vertices are
independent, each of `4,6,8` has global degree at least nine.  There are only four
outside vertices, so every member of `O` is adjacent to all three of `4,6,8`.

If two vertices of `O` were adjacent, those two vertices together with the triangle
`{4,6,8}` would induce a `K5`.  Hence `O` is independent.  But `0` is anticomplete to
`O`, so `O union {0}` is an independent set of size five, contradicting `alpha(G)=4`.
Thus pattern 0 is impossible.

## Patterns 2, 3, 4 and 6

The same short colouring contradiction eliminates all four remaining patterns.
The fixed interface has the following properties in each of them:

- `8` has interface degree five;
- `4` has interface degree at most six;
- both `4` and `8` are adjacent to the degree-eight centre `0`;
- `5-12` is an edge and its common neighbours inside the 13-vertex interface are
  exactly `{1,2}`;
- the neighbourhood of `5` contains the three triangles

  ```text
  {0,4,8},  {0,1,2},  {1,2,12}.
  ```

Degree-eight independence implies `d_G(8)>=9` and `d_G(4)>=9`.  Consequently `8` is
adjacent to all four vertices of `O`, while `4` is adjacent to at least three of them.

The edge `5-12` must have at least four common neighbours.  Only `1` and `2` are
common neighbours inside the interface, so there are at least two outside common
neighbours of `5` and `12`.  Since `4` misses at most one member of `O`, one of these
outside common neighbours, say `z`, is adjacent to `4`.  It is also adjacent to `8`.

Now take a proper three-colouring of `G[N(5)]`.  The triangle `{0,4,8}` uses all three
colours, so a vertex adjacent to both `4` and `8` must receive the colour of `0`.
Thus `z` has the colour of `0`.  The triangles `{0,1,2}` and `{1,2,12}` force `12`
to receive that same colour.  But `z` is adjacent to `12`, a contradiction.

Therefore patterns `2,3,4,6` are impossible.

## Consequence

Subject to the finite local reduction stated at the beginning, an order-17
counterexample cannot contain an edge joining a degree-eight vertex to a degree-nine
vertex.  Together with degree-eight independence, this gives:

> In an order-17 counterexample, every neighbour of a degree-eight vertex has degree
> at least ten.

The immediate next target is to combine this high-neighbour condition with the two
certified degree-eight neighbourhood types and eliminate degree eight altogether in
order 17.

## Verification boundary

`verify_rook_pattern_elimination.cpp` independently reconstructs the five hard-coded
interface patterns and checks every finite fact used above: centre degrees, the relevant
interface degrees, the triangle incidences, and the exact fixed common neighbourhood
of the edge `5-12`.  The colouring and counting argument itself is given above and is
not replaced by a solver call.
