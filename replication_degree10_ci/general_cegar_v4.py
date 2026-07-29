#!/usr/bin/env python3
"""Support-aware CEGAR with universal localization packings.

For every x outside S, contract in cuboid(S) the element selected by x in each
complementary pair.  The resulting clutter ind(S triangle x) has at most d
ordinary elements and inherits the packing property.  For d <= 10 it is MFMC
by the independently certified ten-element theorem.  Under the induced weight
vector its minimum cover has value at least tau, so it has an integral packing
of tau members.  Lifting those members gives tau feasible cube points with

    x_j = 0  =>  sum p_j <= w_j,
    x_j = 1  =>  sum p_j >= w_j.

Unlike v3, which imposed this only on the guaranteed infeasible Hamming star,
this file imposes the implication for every one of the 2^d cube points.
"""
from __future__ import annotations

import itertools

import general_cegar as base
import general_cegar_v3 as v3
import support


def add_guarded_feasible_row(enc, guard_point, row):
    guard = enc.x[guard_point]
    for p in range(1 << enc.d):
        enc.add_clause([guard, enc.x[p]] + support.mismatch_row(row, p))


def add_guarded_orthant_packing(enc, point):
    """If point is infeasible, witness the localization tau-packing."""
    guard = enc.x[point]
    rows = [[enc.new_var() for _ in range(enc.d)] for _ in range(enc.tau)]
    for row in rows:
        add_guarded_feasible_row(enc, point, row)

    for j in range(enc.d):
        column = [row[j] for row in rows]
        point_bit = (point >> j) & 1
        for bits in itertools.product((0, 1), repeat=enc.tau):
            count = sum(bits)
            bad = ((point_bit == 0 and count > enc.w[j]) or
                   (point_bit == 1 and count < enc.w[j]))
            if bad:
                enc.add_clause([guard] + [
                    variable if bit == 0 else -variable
                    for variable, bit in zip(column, bits)
                ])
    return rows


def add_all_localization_packings(enc):
    start_v, start_c = enc.var_count, enc.clause_count
    rows = 0
    for point in range(1 << enc.d):
        rows += len(add_guarded_orthant_packing(enc, point))
    return {
        "witnesses": 1 << enc.d,
        "rows": rows,
        "variables": enc.var_count - start_v,
        "clauses": enc.clause_count - start_c,
    }


def build_master(module, branch):
    enc, centre, residual, basis = v3.build_master(module, branch)
    residual["all_localization_packings"] = add_all_localization_packings(enc)
    return enc, centre, residual, basis


if __name__ == "__main__":
    base.build_master = build_master
    base.solve_with_timeout = v3.solve_without_unsupported_interrupt
    base.main()
