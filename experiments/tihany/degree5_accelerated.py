#!/usr/bin/env python3
"""Accelerated exact search using the proved degree-five independence theorem.

This is theorem-discovery acceleration only.  The direct core and ultracore remain
the certification paths.  Since accelerated mode already enforces delta(H)>=5,
a Boolean high_h can exactly encode d_H(h)>=6; every H-edge must then have at
least one high endpoint.
"""
from __future__ import annotations

import argparse

import core_search


BaseModel = core_search.ExactModel


class DegreeFiveModel(BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.accelerated:
            self._add_degree_five_independence()

    def _add_degree_five_independence(self) -> None:
        high = {}
        for h in self.h_vertices:
            incident = [
                self.edge(h, w)
                for w in self.h_vertices
                if w != h and self.edge(h, w) is not None
            ]
            flag = self._name_var(("hdeg6", h), f"hdeg6_{h}")
            high[h] = flag
            # flag <-> d_H(h)>=6, using the already encoded d_H(h)>=5.
            self._card_atleast(incident, 6, guard=(flag,))
            self._card_atmost(incident, 5, guard=(-flag,))

        # If hq is an H-edge, h and q cannot both have H-degree five.
        for i, h in enumerate(self.h_vertices):
            for q in self.h_vertices[i + 1 :]:
                edge_hq = self.edge(h, q)
                assert edge_hq is not None
                self.add_clause([-edge_hq, high[h], high[q]])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/degree5-accelerated")
    parser.add_argument("--solver", choices=("cadical", "glucose"), default="cadical")
    parser.add_argument("--max-iterations", type=int, default=1_000_000)
    parser.add_argument("--max-seconds", type=float, default=0.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--capacity", action="store_true")
    args = parser.parse_args()
    args.mode = "accelerated"
    args.common_rainbow = True

    original = core_search.ExactModel
    core_search.ExactModel = DegreeFiveModel
    try:
        return core_search.run(args)
    finally:
        core_search.ExactModel = original


if __name__ == "__main__":
    raise SystemExit(main())
