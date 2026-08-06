#!/usr/bin/env python3
"""Accelerated exact search using proved low-degree structural theorems.

This is theorem-discovery acceleration only. The direct core and ultracore remain
the certification paths.

The model uses three independently checked necessary conditions:

* accelerated mode already enforces delta(H)>=5, so a Boolean high_h exactly
  encodes d_H(h)>=6; every H-edge must have at least one high endpoint;
* the core enforces delta(G)>=8, so a Boolean deg8_v exactly encodes d_G(v)=8;
  degree-eight vertices are independent;
* at order 17, the certified degree-eight/degree-nine interface elimination proves
  that every neighbour of a degree-eight vertex has global degree at least ten.

The last item is deliberately confined to this order-17 theorem-discovery model. It is
not added to either the direct core or the reduction-independent ultracore.
"""
from __future__ import annotations

import argparse

import core_search


BaseModel = core_search.ExactModel


class StructuralModel(BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.accelerated:
            self._add_degree_five_independence()
            self._add_degree_eight_structure()

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

    def _add_degree_eight_structure(self) -> None:
        degree_eight = {}
        incident_by_vertex = {}
        for v in self.vertices:
            incident = [
                self.edge(v, w)
                for w in self.vertices
                if w != v and self.edge(v, w) is not None
            ]
            incident_by_vertex[v] = incident
            flag = self._name_var(("gdeg8", v), f"gdeg8_{v}")
            degree_eight[v] = flag
            # With the core's d_G(v)>=8: flag <-> d_G(v)=8.
            self._card_atmost(incident, 8, guard=(flag,))
            self._card_atleast(incident, 9, guard=(-flag,))

        for (u, v), edge_uv in self.edge_vars.items():
            # Global theorem: degree-eight vertices form an independent set.
            self.add_clause([-edge_uv, -degree_eight[u], -degree_eight[v]])

            # Order-17 theorem: if a degree-eight vertex is adjacent to a vertex,
            # that neighbour cannot have degree eight or nine, hence has degree >=10.
            # The condition is encoded in both orientations of each possible edge.
            self._card_atleast(
                incident_by_vertex[v],
                10,
                guard=(edge_uv, degree_eight[u]),
            )
            self._card_atleast(
                incident_by_vertex[u],
                10,
                guard=(edge_uv, degree_eight[v]),
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="artifacts/structural-accelerated")
    parser.add_argument("--solver", choices=("cadical", "glucose"), default="cadical")
    parser.add_argument("--max-iterations", type=int, default=1_000_000)
    parser.add_argument("--max-seconds", type=float, default=0.0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--capacity", action="store_true")
    args = parser.parse_args()
    args.mode = "accelerated"
    args.common_rainbow = True

    original = core_search.ExactModel
    core_search.ExactModel = StructuralModel
    try:
        return core_search.run(args)
    finally:
        core_search.ExactModel = original


if __name__ == "__main__":
    raise SystemExit(main())
