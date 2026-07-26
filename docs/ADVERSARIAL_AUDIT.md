# Adversarial audit report

## Result under audit

The report proves two claims:

1. Every finite loopless independence system is strongly realised by an acyclic
   single-source flow gadget when selection refers to the unique zero-cost path
   of each primary terminal.
2. The uniform C_(2k+1) subfamily has an exact cost-preserving additive
   congestion threshold tau=1-bq, and the best threshold obtainable by its
   symmetric parameterisation has supremum (k+2)/(2(k+1)).

## Failure modes and eliminations

### Omitted actual paths
The proof never assumes that the displayed paths are exhaustive. For the general
construction, every path to an auxiliary terminal must enter through an incidence
exit situated after its incidence resource. A hybrid may traverse extra resources,
but cannot avoid the resource immediately preceding its exit. The C5 verifier
independently derives all paths from the arc list.

### Borrowed prefixes
Borrowed prefixes are allowed. At additive D they do not invalidate the
realisation theorem because any route to a forbidden-set auxiliary still uses an
incidence resource. In the cost-threshold theorem, a borrowed path to a second
incidence uses a connector of fractional load t and is infeasible for every
lambda<1-t.

### Hybrid primary paths
Every approach arc that enters a primary chain downstream has positive reduced
cost 1/b. Hence the full chain is the unique zero-cost path of its primary
terminal.

### Changes of quantifiers
The realisation theorem states an if-and-only-if for every subset S and every
actual routing. The lower bound states that for every unsplittable routing y and
every lambda<tau, the conjunction of the load inequalities implies a strict cost
increase.

### Negative separator coefficients
The signed connector vector is not presented as an admissible cost. Explicit DAG
potentials convert it to a nonnegative arc-cost vector, and equal divergence makes
the cost difference invariant.

### Floating-point or solver tolerance
All certificate arithmetic is rational. The exhaustive verifier uses Python
Fraction and enumerates 3^10=59,049 routings.

### Symmetry assumptions
The exact threshold optimisation is explicitly scoped to the uniform symmetric
odd-cycle family. No claim is made that no unrelated gadget can have a stronger
asymptotic threshold.

### Perturbation resistance
The mutation suite adds a bypass path, removes a critical overload, makes a hybrid
path cheap, and erases the odd-cycle violation. Each mutated certificate is
rejected.

## Remaining epistemic qualification

The mathematical theorem is self-contained. The novelty review is necessarily
non-exhaustive: the targeted search found adjacent EPT/EPG and externally imposed
conflict-flow literatures, but no equivalent theorem. Priority should not be
claimed without expert bibliographic review.
