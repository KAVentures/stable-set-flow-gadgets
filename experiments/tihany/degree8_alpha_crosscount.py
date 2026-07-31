#!/usr/bin/env python3
"""Order-17 degree-eight cross-count search with the established alpha(G)=4 bound.

This is a parallel certification path.  It does not modify the ordinary direct core
or unrestricted ultracore.  Starting from degree8_crosscount, it adds only the
established order-17 reduction alpha(G)<=4 (and the fixed degree-eight case already
contains an independent set of size at least two, while the reduction gives equality
for a counterexample).  Equivalently, every five-set must contain an edge.

Because vertex 0 is anticomplete to O={1,10,...,16}, these clauses in particular force
alpha(G[O])<=3.  No new variables are introduced by the alpha clauses, so the globally
valid ultracore colouring-cut seed remains reusable.
"""
from __future__ import annotations

import argparse
import itertools
import sys

import degree8_crosscount as split
import degree8_ultracore as base


def add_alpha_at_most_four(model) -> None:
    count = 0
    for subset in itertools.combinations(model.vertices, 5):
        clause = []
        for u, v in itertools.combinations(subset, 2):
            var = model.edge(u, v)
            if var is not None:
                clause.append(var)
        if not clause:
            raise AssertionError(f"empty alpha clause for {subset}")
        model.add_clause(clause)
        count += 1
    if count != 6188:
        raise AssertionError(count)


def build_model(local_type: str, cross_count: int):
    model = split.build_degree8_crosscount_model(local_type, cross_count)
    add_alpha_at_most_four(model)
    return model


def self_test() -> None:
    split.self_test()
    assert len(list(itertools.combinations(range(17), 5))) == 6188
    # In the fixed degree-eight labelling, 0 is anticomplete to the eight outside
    # vertices.  Therefore each outside four-set must contain an edge.
    assert len(list(itertools.combinations(split.OUTSIDE, 4))) == 70
    print("degree8_alpha_crosscount_self_test PASS")
    print("alpha_five_sets 6188")
    print("outside_four_sets 70")


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cross-count", type=int, required=True)
    known, remaining = parser.parse_known_args()
    self_test()

    original = base.build_degree8_model

    def patched(local_type: str, neighbor10: bool):
        if not neighbor10:
            raise ValueError("alpha cross-count split requires --neighbor10")
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
