#!/usr/bin/env python3
"""Degree-eight alpha4 cross-count search with degree-eight independence.

This is a parallel exact certification path.  It leaves the direct core and
unrestricted ultracore untouched.  It starts from ``degree8_alpha_crosscount``
and additionally encodes the established theorem that vertices of degree eight
form an independent set.

In the fixed degree-eight case the centre is already anticomplete to the eight
outside vertices and every vertex in its neighbourhood has degree at least ten.
Thus the only remaining instances of the theorem are pairs inside
O={1,10,...,16}: if two outside vertices are adjacent, at least one must have
degree at least nine.  Fresh indicators h_o are used only as an equisatisfiable
encoding of that disjunction:

    e(op) -> h_o or h_p,       h_o -> degree(o) >= 9.

Because the base model already enforces minimum degree eight, this is exactly
the exclusion of an edge joining two degree-eight outside vertices.  The same
builder is used for static-CNF reconstruction before proof checking.
"""
from __future__ import annotations

import argparse
import itertools
import sys

import degree8_alpha_crosscount as alpha
import degree8_crosscount as split
import degree8_ultracore as base


def add_degree_eight_independence(model) -> None:
    high = {}
    for o in split.OUTSIDE:
        h = model._name_var(("outside_degree_ge9", o), f"outside_degree_ge9_{o}")
        high[o] = h
        incident = [
            var
            for v in model.vertices
            if v != o and (var := model.edge(o, v)) is not None
        ]
        model._card_atleast(incident, 9, guard=(h,))

    for u, v in itertools.combinations(split.OUTSIDE, 2):
        edge = model.edge(u, v)
        assert edge is not None
        model.add_clause([-edge, high[u], high[v]])


def build_model(local_type: str, cross_count: int):
    model = alpha.build_model(local_type, cross_count)
    add_degree_eight_independence(model)
    return model


def self_test() -> None:
    alpha.self_test()
    # There are eight outside degree>=9 indicators and 28 guarded pair clauses.
    model = build_model("GEnfbW", 40)
    indicators = [
        model.pool.id(("outside_degree_ge9", o)) for o in split.OUTSIDE
    ]
    assert len(set(indicators)) == 8
    for u, v in itertools.combinations(split.OUTSIDE, 2):
        edge = model.edge(u, v)
        assert edge is not None
        assert [-edge, model.pool.id(("outside_degree_ge9", u)),
                model.pool.id(("outside_degree_ge9", v))] in model.cnf.clauses
    print("degree8_alpha_independent_crosscount_self_test PASS")
    print("outside_high_indicators 8")
    print("outside_pair_implications 28")


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cross-count", type=int, required=True)
    known, remaining = parser.parse_known_args()
    self_test()

    original = base.build_degree8_model

    def patched(local_type: str, neighbor10: bool):
        if not neighbor10:
            raise ValueError("independence split requires --neighbor10")
        return build_model(local_type, known.cross_count)

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
