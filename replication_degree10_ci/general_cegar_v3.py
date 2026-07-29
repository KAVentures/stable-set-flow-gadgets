#!/usr/bin/env python3
"""Support-aware CEGAR strengthened by the packing property itself.

Localization orthant lemma.  Let C=cuboid(S) have the packing property and let
w be a violating cuboid weight with w_i+w_bar_i=tau.  For every infeasible
x in {0,1}^d, ind(S triangle x) has the packing property.  When d<=10 the
certified Abdi--Schwarcz theorem for clutters on at most ten elements makes this
localization MFMC.  Give coordinate i weight w_i if x_i=0 and tau-w_i if
x_i=1.  Every localization cover maps to a w-weight cuboid cover, so its cover
value is at least tau.  Hence it has an integral packing of at least tau local
members.  Lifting any tau of them to S gives feasible p^1,...,p^tau satisfying

  x_i=0 => sum_k p^k_i <= w_i,
  x_i=1 => sum_k p^k_i >= w_i.

Theorem 16 supplies an infeasible point together with all d Hamming neighbours,
so we encode this lemma for all d+1 points of that star.
"""
from __future__ import annotations

import itertools

import general_cegar as base
import support


def infeasible_row(enc, row, flip=-1):
    """Force the point row (with optional one-coordinate flip) outside S."""
    for p in range(1 << enc.d):
        mismatch = []
        for j in range(enc.d):
            pbit = (p >> j) & 1
            if j == flip:
                # False exactly when row[j] xor 1 equals pbit.
                mismatch.append(-row[j] if pbit == 0 else row[j])
            else:
                mismatch.append(row[j] if pbit == 0 else -row[j])
        enc.add_clause([-enc.x[p]] + mismatch)


def add_hamming_star(enc):
    centre = [enc.new_var() for _ in range(enc.d)]
    infeasible_row(enc, centre)
    for i in range(enc.d):
        infeasible_row(enc, centre, i)
    return centre


def add_feasible_symbolic_row(enc, row):
    for p in range(1 << enc.d):
        enc.add_clause([enc.x[p]] + support.mismatch_row(row, p))


def add_orthant_packing(enc, centre, flip=-1):
    rows = [[enc.new_var() for _ in range(enc.d)] for _ in range(enc.tau)]
    for row in rows:
        add_feasible_symbolic_row(enc, row)

    for j in range(enc.d):
        column = [row[j] for row in rows]
        for centre_bit in (0, 1):
            xbit = centre_bit ^ (1 if j == flip else 0)
            for bits in itertools.product((0, 1), repeat=enc.tau):
                count = sum(bits)
                bad = ((xbit == 0 and count > enc.w[j]) or
                       (xbit == 1 and count < enc.w[j]))
                if bad:
                    support.forbid(enc, [centre[j]] + column,
                                   (centre_bit,) + bits)
    for r in range(len(rows) - 1):
        enc.add_lex_geq(rows[r], rows[r + 1])
    return rows


def add_star_localization_packings(enc, centre):
    start_v, start_c = enc.var_count, enc.clause_count
    witnesses = [add_orthant_packing(enc, centre)]
    for i in range(enc.d):
        witnesses.append(add_orthant_packing(enc, centre, i))
    return {
        "witnesses": len(witnesses),
        "rows": len(witnesses) * enc.tau,
        "variables": enc.var_count - start_v,
        "clauses": enc.clause_count - start_c,
    }


def build_master(module, branch):
    d = branch["d"]
    tau = branch["tau"]
    w = branch["w"]
    tight = branch["tight"]
    enc = module.MFMCInstanceEncoder(d, tau, w, tight, False, "memory")
    enc.add_mates()
    enc.add_zero_infeasible()
    enc.add_no_small_covers(tau if tight else tau - 1)
    enc.add_weight_symmetry_breaking()

    centre = add_hamming_star(enc)
    residual = support.add_single_decrement_residual_holes(enc)
    residual["pair_decrement_hierarchy"] = support.add_pair_decrement_hierarchy(enc)
    residual["star_localization_packings"] = add_star_localization_packings(enc, centre)
    basis = support.add_support(enc, branch["support_size"])
    return enc, centre, residual, basis


def solve_without_unsupported_interrupt(solver, seconds):
    del seconds
    return solver.solve()


if __name__ == "__main__":
    base.build_master = build_master
    base.solve_with_timeout = solve_without_unsupported_interrupt
    base.main()
