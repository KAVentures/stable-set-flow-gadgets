#!/usr/bin/env python3
"""Sound wrapper around general_cegar.py.

The first validation run exposed a PySAT API mismatch: CaDiCaL does not support
solve_limited/clear_interrupt. We use ordinary CaDiCaL solve calls and let the
GitHub Actions job timeout bound wall time. This wrapper also adds the complete
one-pair decrement hierarchy implied by entrywise minimality: after decrementing
a,b units in the two elements of one complementary pair, every cover loses at
most a+b while that pair cover loses exactly a+b, fixing the new cover value.
"""
from __future__ import annotations

import general_cegar as base
import support


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
    selectors = base.add_star_selector(enc)
    residual = support.add_single_decrement_residual_holes(enc)
    residual["pair_decrement_hierarchy"] = support.add_pair_decrement_hierarchy(enc)
    basis = support.add_support(enc, branch["support_size"])
    return enc, selectors, residual, basis


def solve_without_unsupported_interrupt(solver, seconds):
    del seconds
    return solver.solve()


if __name__ == "__main__":
    base.build_master = build_master
    base.solve_with_timeout = solve_without_unsupported_interrupt
    base.main()
