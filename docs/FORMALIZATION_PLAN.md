# Formalisation plan

A complete Lean formalisation is realistic in four layers.

1. **Finite independence systems.** Define a finite ground type, a downward-closed
   family, and its antichain of minimal forbidden sets. Prove that a set belongs
   to the family iff it contains no minimal forbidden set.
2. **Abstract incidence gadget.** Avoid graph implementation initially. Define
   resource incidences, primary choices, auxiliary choices, and the load formula.
   Formalise the two directions of the realisation theorem as finite-sum
   inequalities.
3. **Odd-cycle arithmetic.** Formalise the bound `card S <= k` for stable subsets
   of `Fin (2*k+1)`, the parameter identities, the connector separator, and the
   exact threshold witness. These are suitable for `omega`, `linarith`, and
   `norm_num` after rational coercions are controlled.
4. **Graph-path refinement.** Build the explicit DAG, prove a dominator lemma:
   every source-to-auxiliary path contains the incidence resource immediately
   preceding its final exit, and prove uniqueness of the zero-cost primary path.

Suggested theorem dependency order:

```
minimalForbidden_iff
incidence_exit_dominator
unique_zero_primary_path
realisation_forward
realisation_backward
oddCycle_card_le
oddCycle_fractional_violation
connector_separator
potential_shift_nonnegative
threshold_lower_bound
threshold_witness
symmetric_supremum
```

Lean was not installed in the execution environment, so no uncompiled Lean file
is represented as machine-checked. The exact Python verifier covers the finite C5
certificate; the general proof remains a conventional mathematical proof ready
for formalisation.
