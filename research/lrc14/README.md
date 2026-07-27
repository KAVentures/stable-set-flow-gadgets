# Lonely Runner 14: exact three-replacement search

This branch contains an isolated computer-assisted search toward the unresolved 14-runner case. It is not intended for merge into the main stable-set-flow-gadgets project.

## The finite family

Let

\[
C=\{1,2,\ldots,13\},\qquad
V=(C\setminus R)\cup\{x,y,z\},
\]

where `R` is a three-element subset of `C` and `14 <= x < y < z`. Sets with an added speed below 14 differ from `C` in at most two places and belong to the previously certified two-replacement theorem.

The program exhaustively determines whether any such `V` lacks a time `t` with

\[
\|vt\|\ge 1/14\quad(v\in V).
\]

## Exact interval representation

For a speed `v`, its bad set is

\[
B_v=\bigcup_{k\in\mathbb Z}
\left(\frac{k}{v}-\frac1{14v},\frac{k}{v}+\frac1{14v}\right).
\]

All bad intervals are open. Their complementary good intervals are closed, and every endpoint is rational. The implementation stores reduced integer fractions and compares them with 128-bit cross-products. No floating point is used for proof decisions.

Starting with the ten canonical speeds in `C \\ R`, the program intersects their exact good sets with the good sets of `x` and `y`. A final candidate `z` is a counterexample exactly when its open bad set covers every closed component remaining after the first twelve speeds.

A closed interval `[a,b]` is contained in one bad component of `z` exactly when an integer `k` satisfies

\[
zb-\frac1{14}<k<za+\frac1{14}.
\]

This is tested with exact floor arithmetic.

## Exhaustive bounds

Let `L0` be the length of any good interval for the ten canonical speeds. If three speeds `x<y<z` cover that interval, the standard interval-measure estimate

\[
|B_v\cap I|\le \frac{|I|}{7}+\frac{2}{7v}
\]

implies

\[
2L_0\le \frac1x+\frac1y+\frac1z<\frac3x.
\]

Therefore

\[
x<\frac3{2L_0}.
\]

After adding `x`, let `L1` be a longest remaining good interval. Covering it with `y,z` requires

\[
\frac52L_1\le\frac1y+\frac1z<\frac2y,
\]

so

\[
y<\frac4{5L_1}.
\]

After adding `x,y`, let `L2` be a longest remaining good interval. One open bad component of `z` has length `1/(7z)`, and to contain a closed interval of length `L2` it is necessary that

\[
z<\frac1{7L_2}.
\]

The program computes `L0`, `L1`, and `L2` separately for every branch, so the loops are finite without any externally chosen cutoff.

When `x`, `y`, and `z` are all nonzero modulo 14, `t=1/14` is an immediate witness. Such `z` values are skipped only under that exact criterion.

## Running

```bash
g++ -O3 -std=c++20 research/lrc14/three_replacement_exact.cpp -o lrc14_three
./lrc14_three 0 1 result.json
```

The GitHub Actions workflow divides the 286 deleted triples into eight exhaustive residue shards. Every shard must terminate with `NO_COUNTEREXAMPLE` for the three-replacement theorem to be certified.

## Claim boundary

Even a successful run proves only that no counterexample is obtained from `{1,...,13}` by exactly three replacements. It does not by itself prove the full 14-runner Lonely Runner Conjecture.
