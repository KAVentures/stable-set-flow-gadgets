#!/usr/bin/env python3
"""Reduction-independent verifier for a decoded candidate graph.

Unlike verify_graph.py, this checker does not assume a particular maximum independent
set or attachment labelling. It is intended for ultracore searches that fix only one
nonedge. The file does not import the SAT generator.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


def read_graph(path: Path) -> List[int]:
    if path.suffix == ".json":
        payload = json.loads(path.read_text())
        n = int(payload["n"])
        edges = [tuple(map(int, edge)) for edge in payload["edges"]]
    else:
        lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
        n = int(lines[0])
        edges = [tuple(map(int, line.split())) for line in lines[1:]]
    adj = [0] * n
    for u, v in edges:
        if not (0 <= u < v < n):
            raise ValueError(f"bad edge {u},{v}")
        if (adj[u] >> v) & 1:
            raise ValueError(f"duplicate edge {u},{v}")
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    return adj


def proper(adj: Sequence[int], colouring: Dict[int, int], vertices: Sequence[int], k: int) -> bool:
    return (
        set(colouring) == set(vertices)
        and all(0 <= colouring[v] < k for v in vertices)
        and all(
            not ((adj[u] >> v) & 1) or colouring[u] != colouring[v]
            for u, v in itertools.combinations(vertices, 2)
        )
    )


def checker_static(adj: Sequence[int], vertices: Iterable[int], k: int) -> Optional[Dict[int, int]]:
    verts0 = list(vertices)
    allowed = set(verts0)
    verts = sorted(verts0, key=lambda v: (-sum((adj[v] >> w) & 1 for w in allowed), v))
    colour: Dict[int, int] = {}

    def rec(pos: int) -> bool:
        if pos == len(verts):
            return True
        v = verts[pos]
        blocked = {colour[w] for w in colour if (adj[v] >> w) & 1}
        for c in range(k):
            if c in blocked:
                continue
            colour[v] = c
            if rec(pos + 1):
                return True
            del colour[v]
        return False

    if rec(0):
        ans = dict(colour)
        assert proper(adj, ans, verts0, k)
        return ans
    return None


def checker_saturation(adj: Sequence[int], vertices: Iterable[int], k: int) -> Optional[Dict[int, int]]:
    verts = tuple(sorted(vertices))
    universe = set(verts)
    colour: Dict[int, int] = {}

    def pick() -> int:
        uncoloured = universe - set(colour)
        return max(
            uncoloured,
            key=lambda v: (
                len({colour[w] for w in colour if (adj[v] >> w) & 1}),
                sum((adj[v] >> w) & 1 for w in uncoloured),
                -v,
            ),
        )

    def rec() -> bool:
        if len(colour) == len(verts):
            return True
        v = pick()
        blocked = {colour[w] for w in colour if (adj[v] >> w) & 1}
        introduced = max(colour.values(), default=-1) + 1
        for c in range(min(k, introduced + 1)):
            if c in blocked:
                continue
            colour[v] = c
            if rec():
                return True
            del colour[v]
        return False

    if rec():
        ans = dict(colour)
        assert proper(adj, ans, list(verts), k)
        return ans
    return None


def independence_number(adj: Sequence[int]) -> int:
    n = len(adj)
    best = 0

    def branch(size: int, candidates: int) -> None:
        nonlocal best
        if size + candidates.bit_count() <= best:
            return
        if candidates == 0:
            best = max(best, size)
            return
        verts = [v for v in range(n) if (candidates >> v) & 1]
        v = max(verts, key=lambda x: (adj[x] & candidates).bit_count())
        branch(size + 1, candidates & ~adj[v] & ~(1 << v))
        branch(size, candidates & ~(1 << v))

    branch(0, (1 << n) - 1)
    return best


def connected(adj: Sequence[int]) -> bool:
    if not adj:
        return False
    seen = 1
    frontier = 1
    while frontier:
        bit = frontier & -frontier
        frontier ^= bit
        v = bit.bit_length() - 1
        new = adj[v] & ~seen
        seen |= new
        frontier |= new
    return seen.bit_count() == len(adj)


def verify(adj: Sequence[int], expected_order: int = 17, minimum_degree_bound: int = 8) -> dict:
    n = len(adj)
    vertices = list(range(n))
    if n != expected_order:
        raise AssertionError(f"order {n}, expected {expected_order}")
    if any((adj[u] >> u) & 1 for u in vertices):
        raise AssertionError("loop")
    if any(
        ((adj[u] >> v) & 1) != ((adj[v] >> u) & 1)
        for u, v in itertools.combinations(vertices, 2)
    ):
        raise AssertionError("asymmetric adjacency")
    if not connected(adj):
        raise AssertionError("graph is disconnected")
    if all((adj[u] >> v) & 1 for u, v in itertools.combinations(vertices, 2)):
        raise AssertionError("graph is complete")

    minimum_degree = min(row.bit_count() for row in adj)
    if minimum_degree < minimum_degree_bound:
        raise AssertionError(f"minimum degree {minimum_degree} < {minimum_degree_bound}")

    for checker in (checker_static, checker_saturation):
        if checker(adj, vertices, 5) is not None:
            raise AssertionError(f"{checker.__name__}: graph is 5-colourable")
        six = checker(adj, vertices, 6)
        if six is None or not proper(adj, six, vertices, 6):
            raise AssertionError(f"{checker.__name__}: graph is not verified 6-colourable")

    deletion_witnesses = []
    edge_count = 0
    for u, v in itertools.combinations(vertices, 2):
        if not ((adj[u] >> v) & 1):
            continue
        edge_count += 1
        remaining = [w for w in vertices if w not in (u, v)]
        for checker in (checker_static, checker_saturation):
            four = checker(adj, remaining, 4)
            if four is None or not proper(adj, four, remaining, 4):
                raise AssertionError(f"{checker.__name__}: deletion {u},{v} is not 4-colourable")
        if checker_saturation(adj, remaining, 3) is not None:
            raise AssertionError(f"deletion {u},{v} is 3-colourable")
        deletion_witnesses.append([u, v])

    return {
        "n": n,
        "edges": edge_count,
        "degrees": [row.bit_count() for row in adj],
        "minimum_degree": minimum_degree,
        "alpha": independence_number(adj),
        "chromatic_number": 6,
        "deletion_chromatic_number": 4,
        "verified_deletions": deletion_witnesses,
        "status": "verified noncomplete double-critical 6-chromatic graph",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("graph", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--order", type=int, default=17)
    parser.add_argument("--minimum-degree", type=int, default=8)
    args = parser.parse_args()
    result = verify(read_graph(args.graph), args.order, args.minimum_degree)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
