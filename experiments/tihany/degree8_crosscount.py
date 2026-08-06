#!/usr/bin/env python3
"""Exact symmetry-broken degree-eight search split by cross-edge count.

This is a theorem-discovery/certification split built on ``degree8_ultracore``.
It preserves the reduction-independent ultracore definition, fixes one of the two
independently certified degree-eight neighbourhood types, uses the separately
certified order-17 theorem that every neighbour of the degree-eight centre has
global degree at least ten, canonically orders the eight outside vertices by
their incidence signatures into the fixed neighbourhood, and then fixes the
*exact* number of cross edges between those two eight-vertex sets.

For GEnfbW the fixed neighbourhood is 4-regular, so every one of its eight
vertices needs at least five outside neighbours and the cross-edge count is at
least 40.  For GEjfrw the local degree sequence is 4^6 5^2, hence the lower
bound is 6*5 + 2*4 = 38.  Counts through 64 are possible a priori.  Therefore

    GEnfbW : 40,...,64  (25 cases)
    GEjfrw : 38,...,64  (27 cases)

form 52 pairwise disjoint and exhaustive branches of the degree-eight regime.
No new graph-theoretic assumption is introduced by the count split or by the
outside-label symmetry breaker.
"""
from __future__ import annotations

import argparse
import itertools
import sys

import degree8_ultracore as base

OUTSIDE = (1, 10, 11, 12, 13, 14, 15, 16)
NEIGHBOURHOOD = tuple(range(2, 10))
ORIGINAL_BUILD = base.build_degree8_model


def lex_leq_clauses(left, right):
    """CNF for the lexicographic relation left <= right, without auxiliaries."""
    if len(left) != len(right):
        raise ValueError("signature widths differ")
    clauses = []
    for i in range(len(left)):
        # For every equal prefix, forbid first difference 1 > 0.
        for mask in range(1 << i):
            clause = []
            for j in range(i):
                bit = (mask >> j) & 1
                if bit:
                    clause.extend((-left[j], -right[j]))
                else:
                    clause.extend((left[j], right[j]))
            clause.extend((-left[i], right[i]))
            clauses.append(clause)
    return clauses


def add_outside_signature_order(model) -> None:
    signatures = {}
    for o in OUTSIDE:
        sig = []
        for v in NEIGHBOURHOOD:
            var = model.edge(o, v)
            assert var is not None
            sig.append(var)
        signatures[o] = tuple(sig)
    for a, b in zip(OUTSIDE, OUTSIDE[1:]):
        for clause in lex_leq_clauses(signatures[a], signatures[b]):
            model.add_clause(clause)


def local_degrees(local_type: str):
    local = base.decode_short_graph6(local_type)
    return tuple(sum(row) for row in local)


def minimum_cross_count(local_type: str) -> int:
    # Each local vertex already sees the centre plus d_local neighbours.
    # The certified neighbour>=10 theorem therefore requires 9-d_local
    # neighbours among the eight outside vertices.
    return sum(max(0, 9 - d) for d in local_degrees(local_type))


def cross_edge_vars(model):
    result = []
    for o in OUTSIDE:
        for v in NEIGHBOURHOOD:
            var = model.edge(o, v)
            assert var is not None
            result.append(var)
    assert len(result) == 64 and len(set(result)) == 64
    return result


def build_degree8_crosscount_model(local_type: str, cross_count: int):
    lower = minimum_cross_count(local_type)
    if not lower <= cross_count <= 64:
        raise ValueError(
            f"cross count {cross_count} outside exhaustive range {lower}..64 "
            f"for {local_type}"
        )
    model = ORIGINAL_BUILD(local_type, True)
    add_outside_signature_order(model)
    cross = cross_edge_vars(model)
    model._card_atleast(cross, cross_count)
    model._card_atmost(cross, cross_count)
    return model


def _clause_satisfied(clause, assignment):
    return any(assignment[abs(lit)] == (lit > 0) for lit in clause)


def self_test() -> None:
    # Exhaustive truth-table check of the symmetry comparator through width four.
    for width in range(1, 5):
        left = tuple(range(1, width + 1))
        right = tuple(range(width + 1, 2 * width + 1))
        clauses = lex_leq_clauses(left, right)
        assert len(clauses) == (1 << width) - 1
        for lb in itertools.product((0, 1), repeat=width):
            for rb in itertools.product((0, 1), repeat=width):
                assignment = {left[i]: bool(lb[i]) for i in range(width)}
                assignment.update({right[i]: bool(rb[i]) for i in range(width)})
                actual = all(_clause_satisfied(c, assignment) for c in clauses)
                if actual != (lb <= rb):
                    raise AssertionError((width, lb, rb, actual, lb <= rb))

    if minimum_cross_count("GEnfbW") != 40:
        raise AssertionError(("GEnfbW", local_degrees("GEnfbW")))
    if minimum_cross_count("GEjfrw") != 38:
        raise AssertionError(("GEjfrw", local_degrees("GEjfrw")))
    if sum(65 - minimum_cross_count(t) for t in base.ALLOWED_TYPES) != 52:
        raise AssertionError("degree-eight cross-count split must contain 52 cases")
    if 7 * ((1 << 8) - 1) != 1785:
        raise AssertionError("unexpected symmetry-clause count")
    print("degree8_crosscount_self_test PASS")
    print("GEnfbW_range 40 64")
    print("GEjfrw_range 38 64")
    print("exhaustive_cases 52")
    print("symmetry_clauses 1785")


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cross-count", type=int, required=True)
    known, remaining = parser.parse_known_args()
    self_test()

    original = base.build_degree8_model

    def patched(local_type: str, neighbor10: bool):
        if not neighbor10:
            raise ValueError("cross-count split requires --neighbor10")
        return build_degree8_crosscount_model(local_type, known.cross_count)

    base.build_degree8_model = patched
    old_argv = sys.argv
    sys.argv = [old_argv[0], *remaining]
    try:
        return base.main()
    finally:
        sys.argv = old_argv
        base.build_degree8_model = original


if __name__ == "__main__":
    raise SystemExit(main())
