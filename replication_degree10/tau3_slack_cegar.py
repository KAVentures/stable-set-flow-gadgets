#!/usr/bin/env python3
"""Run the tau=3 CEGAR with residual-hole constraints from minimality.

For every single-element decrement of an entrywise-minimal violating weight,
there is a packing of tau-1 members.  Its unused capacities select exactly one
member of the ambient cuboid.  That residual member must be infeasible, since
otherwise it completes the packing to size tau.  This is strictly stronger
than merely asserting the decrement packing witnesses.

The exact packing and cube-idealness separators are reused from tau3_cegar.py.
UNSAT remains exploratory until the final deterministic formula has a checked
DRAT/LRAT certificate.
"""
from __future__ import annotations

import itertools
import tau3_cegar as base


def add_single_decrement_residual_holes(enc) -> dict:
    k = enc.tau - 1
    start_v, start_c = enc.var_count, enc.clause_count
    witnesses = row_symmetries = 0
    for target in range(enc.d):
        # Decrement the positive element: residual target bit is 1.
        # Decrement the negative element: residual target bit is 0.
        for target_bit in (1, 0):
            witnesses += 1
            rows = [[enc.new_var() for _ in range(enc.d)] for _ in range(k)]
            residual = [enc.new_var() for _ in range(enc.d)]
            enc.add_clause([residual[target] if target_bit else -residual[target]])

            # Every row is a feasible point of S.
            for row in rows:
                for p in range(1 << enc.d):
                    mismatch = [row[j] if ((p >> j) & 1) == 0 else -row[j]
                                for j in range(enc.d)]
                    enc.add_clause([enc.x[p]] + mismatch)

            # Column load plus the residual bit is exactly w_j.
            for j in range(enc.d):
                column = [rows[r][j] for r in range(k)]
                for bits in itertools.product((0, 1), repeat=k):
                    for residual_bit in (0, 1):
                        if sum(bits) + residual_bit != enc.w[j]:
                            base.forbid(enc, column + [residual[j]], bits + (residual_bit,))

            # The residual cuboid member cannot be feasible, or it completes
            # these tau-1 rows to an exact tau-packing under w.
            for p in range(1 << enc.d):
                mismatch = [residual[j] if ((p >> j) & 1) == 0 else -residual[j]
                            for j in range(enc.d)]
                enc.add_clause([-enc.x[p]] + mismatch)

            # Label symmetry among the packing rows.
            for r in range(k - 1):
                enc.add_lex_geq(rows[r], rows[r + 1])
                row_symmetries += 1

    return {
        "witnesses": witnesses,
        "packing_size": k,
        "row_symmetries": row_symmetries,
        "added_variables": enc.var_count - start_v,
        "added_clauses": enc.clause_count - start_c,
    }


def build_master(mod, centre_weight: int):
    d, tau, w, tight = 10, 3, (1,) * 10, False
    centre = (1 << centre_weight) - 1
    enc = mod.MFMCInstanceEncoder(d, tau, w, tight, False, None)
    enc.add_strictly_polar()
    # Cube-idealness is separated lazily by the exact published clauses.
    enc.add_mates()
    enc.add_zero_infeasible()
    enc.add_no_small_covers(tau - 1)
    base.add_fixed_star(enc, centre)
    stabilizer = base.add_stabilizer_symmetry(enc, centre)
    residual_holes = add_single_decrement_residual_holes(enc)
    return enc, centre, stabilizer, residual_holes


if __name__ == "__main__":
    base.build_master = build_master
    base.main()
