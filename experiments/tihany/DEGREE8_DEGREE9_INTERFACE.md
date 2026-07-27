# The unique degree-eight/degree-nine interface at order 17

## Statement

> **Computer-assisted classification.** In an order-17 hypothetical noncomplete
> double-critical 6-chromatic graph, suppose a degree-eight vertex is adjacent to a
> degree-nine vertex. Subject to the standard local neighbourhood restrictions, the
> two completed neighbourhoods have one rooted 13-vertex amalgam, up to isomorphism
> fixing the two centres.

The degree-eight neighbourhood is `GEnfbW`. The degree-nine neighbourhood is the
4-regular nine-vertex graph

```text
HqolhhX
```

in graph6 notation. It is **not** the `3 x 3` rook graph: it has seven triangles,
whereas the rook graph has six. Earlier exploratory wording calling this graph a rook
graph was incorrect and is withdrawn.

The unique rooted amalgam has 13 vertices and 39 edges. Its complete edge list is the
base interface used by `verify_rook_pattern_elimination.cpp` and the historically named
`rook_order17_cegar.py`.

## Necessary degree-nine neighbourhood conditions

Let `Q=G[N(q)]` for a degree-nine vertex `q`. The verifier generates every unlabeled
graph on nine vertices and retains exactly those satisfying the local conditions used
in the manuscript:

- minimum degree at least four;
- no vertex of degree seven;
- for every vertex, its non-neighbours induce no isolated vertex;
- no `K4`;
- independence number at most four;
- three-colourability.

The exact census is

```text
unlabeled graphs on 8 vertices       12346
labelled one-vertex extensions     3160576
raw admissible extensions               492
nonisomorphic admissible 9-graphs        67
```

The generator performs exact colour refinement followed by complete permutation within
every stable refinement class. The count `12346` is also the full known unlabeled
8-vertex graph count and serves as an internal completeness check.

## Exact amalgamation scan

For each of the two certified degree-eight neighbourhoods, every possible position of
the degree-nine centre is considered. For each of the 67 degree-nine neighbourhoods,
every possible position of the degree-eight centre is considered.

If the two centre positions have the same local degree, the verifier enumerates every
bijection between their common-neighbour sets and retains exactly the
adjacency-preserving bijections. For each resulting amalgam it deletes all unspecified
edges between the exclusive local pieces. This is a safe relaxation for the following
test, because both centres have their complete neighbourhoods already present.

The verifier then requires, separately for every edge incident with either centre, a
proper four-colouring after deleting the edge endpoints in which the common
neighbourhood contains all four colours.

The exact census is

```text
compatible labelled amalgams       4656
amalgams passing every rainbow test    8
surviving degree-eight types            1
surviving degree-nine types             1
rooted isomorphism types                 1
```

All eight labelled survivors use `GEnfbW` and `HqolhhX`, and all are isomorphic while
fixing the degree-eight and degree-nine centres. The rooted interface has 13 vertices
and 39 edges.

## Consequence with the residual-interface theorem

`ROOK_INTERFACE_ELIMINATION.md` starts from this unique rooted interface, enumerates
all 4096 choices of its twelve unspecified cross edges, reduces the sixteen local
survivors to five possibilities compatible with four outside vertices, and eliminates
those five by short symbolic arguments.

Combining the two independently checkable finite stages gives:

> **Order-17 degree restriction.** A degree-eight vertex cannot be adjacent to a
> degree-nine vertex in an order-17 counterexample.

Together with the separate theorem that degree-eight vertices are independent, every
neighbour of a degree-eight vertex in an order-17 counterexample has degree at least
ten.

## Verification boundary

`verify_degree8_degree9_interface.cpp` is self-contained. It:

- generates all unlabeled graphs through order eight;
- generates and canonically deduplicates all admissible nine-vertex neighbourhoods;
- decodes the two degree-eight neighbourhoods from fixed edge masks;
- enumerates every common-neighbour bijection directly;
- constructs each relaxed amalgam as bitsets;
- performs exact DSATUR-style deletion-rainbow searches;
- canonically identifies the surviving degree-nine graph as graph6 `HqolhhX`;
- canonically identifies one rooted surviving amalgam.

The remaining broader trust boundary is the previously certified two-type
classification of degree-eight neighbourhoods itself. No SAT/CEGAR completion result is
used in this interface theorem.
