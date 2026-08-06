#!/usr/bin/env python3
"""Direct SAT/CEGAR search for an order-17 noncomplete double-critical 6-chromatic graph.

The core mode encodes the defining graph problem after the proved order-17 reduction.
The accelerated mode adds only separately proved necessary structural constraints.

An UNSAT claim is not accepted from this incremental run alone.  On convergence the
program emits one deterministic static DIMACS formula consisting of the base CNF and
all preserved colouring cuts.  That formula is intended for an external proof-producing
solver and independent DRAT/LRAT checking.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from pysat.card import CardEnc, EncType
from pysat.formula import CNF, IDPool
from pysat.solvers import Cadical195, Glucose4

Pair = Tuple[int, int]
Colouring = Dict[int, int]

STOP_REQUESTED = False


def _request_stop(signum: int, _frame: object) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True
    print(f"c received signal {signum}; checkpointing after current solver call", flush=True)


signal.signal(signal.SIGINT, _request_stop)
signal.signal(signal.SIGTERM, _request_stop)


def ordered_pair(u: int, v: int) -> Pair:
    if u == v:
        raise ValueError("loops are not graph variables")
    return (u, v) if u < v else (v, u)


def verify_colouring(adj: Sequence[int], colouring: Colouring, vertices: Iterable[int], k: int) -> bool:
    verts = list(vertices)
    if set(colouring) != set(verts):
        return False
    if any(not (0 <= colouring[v] < k) for v in verts):
        return False
    return all(
        not ((adj[u] >> v) & 1) or colouring[u] != colouring[v]
        for u, v in itertools.combinations(verts, 2)
    )


def dsatur_k_colouring(adj: Sequence[int], vertices: Iterable[int], k: int) -> Optional[Colouring]:
    """Exact DSATUR-style k-colourability checker, returning a witness when one exists."""
    verts = tuple(sorted(vertices))
    target = set(verts)
    colour: Dict[int, int] = {}

    def choose_vertex() -> int:
        uncoloured = target.difference(colour)
        return max(
            uncoloured,
            key=lambda v: (
                len({colour[w] for w in colour if (adj[v] >> w) & 1}),
                sum(1 for w in uncoloured if (adj[v] >> w) & 1),
                sum(1 for w in target if (adj[v] >> w) & 1),
                -v,
            ),
        )

    def search() -> bool:
        if len(colour) == len(verts):
            return True
        v = choose_vertex()
        forbidden = {colour[w] for w in colour if (adj[v] >> w) & 1}
        used = max(colour.values(), default=-1) + 1
        # First-use symmetry breaking is complete: any colouring can be relabelled in
        # the order in which new colours first appear.
        for c in range(min(k, used + 1)):
            if c in forbidden:
                continue
            colour[v] = c
            if search():
                return True
            del colour[v]
        return False

    if search():
        ans = dict(colour)
        assert verify_colouring(adj, ans, verts, k)
        return ans
    return None


def plain_k_colouring(adj: Sequence[int], vertices: Iterable[int], k: int) -> Optional[Colouring]:
    """A deliberately separate exact checker with a static vertex order."""
    verts = sorted(vertices, key=lambda v: (-sum((adj[v] >> w) & 1 for w in vertices), v))
    colour: Dict[int, int] = {}

    def search(pos: int) -> bool:
        if pos == len(verts):
            return True
        v = verts[pos]
        forbidden = {colour[w] for w in colour if (adj[v] >> w) & 1}
        for c in range(k):
            if c in forbidden:
                continue
            colour[v] = c
            if search(pos + 1):
                return True
            del colour[v]
        return False

    if search(0):
        ans = dict(colour)
        assert verify_colouring(adj, ans, verts, k)
        return ans
    return None


def maximum_independent_set_size(adj: Sequence[int]) -> int:
    n = len(adj)
    best = 0

    def expand(size: int, candidates: int) -> None:
        nonlocal best
        if size + candidates.bit_count() <= best:
            return
        if not candidates:
            best = max(best, size)
            return
        while candidates:
            if size + candidates.bit_count() <= best:
                return
            bit = candidates & -candidates
            v = bit.bit_length() - 1
            candidates ^= bit
            expand(size + 1, candidates & ~adj[v] & ~(1 << v))

    expand(0, (1 << n) - 1)
    return best


def graph6(adj: Sequence[int]) -> str:
    n = len(adj)
    if not (0 <= n <= 62):
        raise ValueError("short graph6 writer supports n <= 62")
    bits: List[int] = []
    for j in range(1, n):
        for i in range(j):
            bits.append((adj[i] >> j) & 1)
    while len(bits) % 6:
        bits.append(0)
    return chr(n + 63) + "".join(
        chr(63 + sum(bits[p + t] << (5 - t) for t in range(6)))
        for p in range(0, len(bits), 6)
    )


def formula_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class ExactModel:
    def __init__(
        self,
        n: int = 17,
        independent: Sequence[int] = (0, 1, 2, 3),
        min_degree: Optional[int] = 8,
        alpha_bound: Optional[int] = 4,
        attachment_bounds: Optional[Tuple[int, int]] = (8, 11),
        accelerated: bool = False,
        capacity: bool = False,
        common_rainbow: bool = False,
    ) -> None:
        self.n = n
        self.vertices = tuple(range(n))
        self.independent = tuple(sorted(independent))
        self.independent_set = set(self.independent)
        self.h_vertices = tuple(v for v in self.vertices if v not in self.independent_set)
        self.min_degree = min_degree
        self.alpha_bound = alpha_bound
        self.attachment_bounds = attachment_bounds
        self.accelerated = accelerated
        self.capacity = capacity
        self.common_rainbow = common_rainbow
        self.pool = IDPool(start_from=1)
        self.cnf = CNF()
        self.edge_vars: Dict[Pair, int] = {}
        self.var_names: Dict[int, str] = {}
        self._make_edge_variables()
        self._build_core()
        if accelerated:
            self._build_accelerated()

    def _name_var(self, key: Tuple[object, ...], label: str) -> int:
        var = self.pool.id(key)
        self.var_names.setdefault(var, label)
        return var

    def _make_edge_variables(self) -> None:
        for u, v in itertools.combinations(self.vertices, 2):
            if u in self.independent_set and v in self.independent_set:
                continue
            pair = (u, v)
            self.edge_vars[pair] = self._name_var(("e", u, v), f"e_{u}_{v}")

    def edge(self, u: int, v: int) -> Optional[int]:
        return self.edge_vars.get(ordered_pair(u, v))

    def add_clause(self, clause: Iterable[int]) -> None:
        values = list(dict.fromkeys(int(x) for x in clause))
        if any(-x in values for x in values):
            return
        self.cnf.append(values)

    def _card_atleast(self, lits: Sequence[int], bound: int, guard: Sequence[int] = ()) -> None:
        if bound <= 0:
            return
        if bound > len(lits):
            self.add_clause([-x for x in guard])
            return
        enc = CardEnc.atleast(lits=list(lits), bound=bound, vpool=self.pool, encoding=EncType.seqcounter)
        prefix = [-x for x in guard]
        for clause in enc.clauses:
            self.add_clause(prefix + clause)

    def _card_atmost(self, lits: Sequence[int], bound: int, guard: Sequence[int] = ()) -> None:
        if bound >= len(lits):
            return
        if bound < 0:
            self.add_clause([-x for x in guard])
            return
        enc = CardEnc.atmost(lits=list(lits), bound=bound, vpool=self.pool, encoding=EncType.seqcounter)
        prefix = [-x for x in guard]
        for clause in enc.clauses:
            self.add_clause(prefix + clause)

    def _guarded_onehot(self, guard: int, variables: Sequence[int]) -> None:
        self.add_clause([-guard, *variables])
        for var in variables:
            self.add_clause([-var, guard])
        for a, b in itertools.combinations(variables, 2):
            self.add_clause([-a, -b])

    def _unguarded_onehot(self, variables: Sequence[int]) -> None:
        self.add_clause(variables)
        for a, b in itertools.combinations(variables, 2):
            self.add_clause([-a, -b])

    def _build_core(self) -> None:
        # I is independent by omission of its six edge variables.
        if self.alpha_bound is not None:
            size = self.alpha_bound + 1
            for subset in itertools.combinations(self.vertices, size):
                clause = [
                    var
                    for u, v in itertools.combinations(subset, 2)
                    if (var := self.edge(u, v)) is not None
                ]
                self.add_clause(clause)

        if self.min_degree is not None:
            for v in self.vertices:
                incident = [
                    var
                    for w in self.vertices
                    if w != v and (var := self.edge(v, w)) is not None
                ]
                self._card_atleast(incident, self.min_degree)

        if self.attachment_bounds is not None:
            lower, upper = self.attachment_bounds
            for x in self.independent:
                incident = [self.edge(x, h) for h in self.h_vertices]
                clean = [v for v in incident if v is not None]
                self._card_atleast(clean, lower)
                self._card_atmost(clean, upper)

        self._add_all_deletion_blocks()

    def _deletion_colour(self, u: int, v: int, w: int, colour: int) -> int:
        a, b = ordered_pair(u, v)
        return self._name_var(("dc", a, b, w, colour), f"dc_{a}_{b}_{w}_{colour}")

    def _add_all_deletion_blocks(self) -> None:
        for (u, v), guard in sorted(self.edge_vars.items()):
            remaining = [w for w in self.vertices if w not in (u, v)]
            for w in remaining:
                colours = [self._deletion_colour(u, v, w, c) for c in range(4)]
                self._guarded_onehot(guard, colours)
            # Safe colour-permutation symmetry breaking.
            self.add_clause([-guard, self._deletion_colour(u, v, remaining[0], 0)])
            for a, b in itertools.combinations(remaining, 2):
                edge_ab = self.edge(a, b)
                if edge_ab is None:
                    continue
                for c in range(4):
                    self.add_clause(
                        [
                            -guard,
                            -edge_ab,
                            -self._deletion_colour(u, v, a, c),
                            -self._deletion_colour(u, v, b, c),
                        ]
                    )
            if self.common_rainbow:
                self._add_common_rainbow_block(u, v, guard, remaining)

    def _and_aux(self, key: Tuple[object, ...], label: str, signed_inputs: Sequence[int]) -> int:
        aux = self._name_var(key, label)
        for lit in signed_inputs:
            self.add_clause([-aux, lit])
        self.add_clause([aux, *(-lit for lit in signed_inputs)])
        return aux

    def _add_common_rainbow_block(self, u: int, v: int, guard: int, remaining: Sequence[int]) -> None:
        for c in range(4):
            witnesses: List[int] = []
            for w in remaining:
                uw = self.edge(u, w)
                vw = self.edge(v, w)
                if uw is None or vw is None:
                    continue
                colour = self._deletion_colour(u, v, w, c)
                witnesses.append(
                    self._and_aux(
                        ("rainbow", u, v, w, c),
                        f"rainbow_{u}_{v}_{w}_{c}",
                        (uw, vw, colour),
                    )
                )
            self.add_clause([-guard, *witnesses])

    def _build_accelerated(self) -> None:
        # H has minimum degree at least five.
        for v in self.h_vertices:
            incident = [self.edge(v, w) for w in self.h_vertices if w != v]
            self._card_atleast([x for x in incident if x is not None], 5)

        # The fixed independent set is maximal; this is redundant with alpha <= 4,
        # but retained as a transparent accelerated constraint.
        for h in self.h_vertices:
            self.add_clause([self.edge(x, h) for x in self.independent if self.edge(x, h) is not None])

        self._add_h_vertex_critical_upper_witnesses()
        self._add_local_neighbourhood_three_colourings()
        self._add_common_neighbour_lower_bounds()
        self._add_attachment_antichain()
        if self.capacity:
            self._add_capacity_inequalities()

    def _h_colour(self, deleted: int, w: int, colour: int) -> int:
        return self._name_var(("hdel", deleted, w, colour), f"hdel_{deleted}_{w}_{colour}")

    def _add_h_vertex_critical_upper_witnesses(self) -> None:
        # H-v is 4-colourable for every v.  CEGAR separately enforces that H is not
        # 4-colourable, making H exactly 5-chromatic and vertex-critical.
        for deleted in self.h_vertices:
            remaining = [w for w in self.h_vertices if w != deleted]
            for w in remaining:
                self._unguarded_onehot([self._h_colour(deleted, w, c) for c in range(4)])
            self.add_clause([self._h_colour(deleted, remaining[0], 0)])
            for a, b in itertools.combinations(remaining, 2):
                edge_ab = self.edge(a, b)
                assert edge_ab is not None
                for c in range(4):
                    self.add_clause([-edge_ab, -self._h_colour(deleted, a, c), -self._h_colour(deleted, b, c)])

    def _local_colour(self, root: int, w: int, colour: int) -> int:
        return self._name_var(("local3", root, w, colour), f"local3_{root}_{w}_{colour}")

    def _add_local_neighbourhood_three_colourings(self) -> None:
        for root in self.vertices:
            possible = [w for w in self.vertices if w != root and self.edge(root, w) is not None]
            for w in possible:
                guard = self.edge(root, w)
                assert guard is not None
                self._guarded_onehot(guard, [self._local_colour(root, w, c) for c in range(3)])
            for a, b in itertools.combinations(possible, 2):
                edge_ab = self.edge(a, b)
                if edge_ab is None:
                    continue
                for c in range(3):
                    self.add_clause([-edge_ab, -self._local_colour(root, a, c), -self._local_colour(root, b, c)])

    def _add_common_neighbour_lower_bounds(self) -> None:
        for (u, v), guard in sorted(self.edge_vars.items()):
            common: List[int] = []
            for w in self.vertices:
                if w in (u, v):
                    continue
                uw = self.edge(u, w)
                vw = self.edge(v, w)
                if uw is None or vw is None:
                    continue
                common.append(
                    self._and_aux(("common", u, v, w), f"common_{u}_{v}_{w}", (uw, vw))
                )
            self._card_atleast(common, 4, guard=(guard,))

    def _add_attachment_antichain(self) -> None:
        for x in self.independent:
            for y in self.independent:
                if x == y:
                    continue
                differences: List[int] = []
                for h in self.h_vertices:
                    xh = self.edge(x, h)
                    yh = self.edge(y, h)
                    assert xh is not None and yh is not None
                    differences.append(
                        self._and_aux(
                            ("diff", x, y, h),
                            f"diff_{x}_{y}_{h}",
                            (xh, -yh),
                        )
                    )
                self.add_clause(differences)

    def _add_capacity_inequalities(self) -> None:
        # If S is independent in N_H(c) and J is a subset of the I-vertices adjacent
        # to c and anticomplete to S, then d_G(c) >= |S| + |J| + 5.
        for c in self.h_vertices:
            degree_lits = [
                var for w in self.vertices if w != c and (var := self.edge(c, w)) is not None
            ]
            candidates = [w for w in self.h_vertices if w != c]
            for size in range(1, min(4, len(candidates)) + 1):
                for subset in itertools.combinations(candidates, size):
                    base_guard: List[int] = []
                    for s in subset:
                        cs = self.edge(c, s)
                        assert cs is not None
                        base_guard.append(cs)
                    for a, b in itertools.combinations(subset, 2):
                        ab = self.edge(a, b)
                        assert ab is not None
                        base_guard.append(-ab)
                    for jsize in range(0, len(self.independent) + 1):
                        for jset in itertools.combinations(self.independent, jsize):
                            threshold = size + jsize + 5
                            if threshold <= (self.min_degree or 0):
                                continue
                            guard = list(base_guard)
                            for x in jset:
                                xc = self.edge(x, c)
                                assert xc is not None
                                guard.append(xc)
                                for s in subset:
                                    xs = self.edge(x, s)
                                    assert xs is not None
                                    guard.append(-xs)
                            self._card_atleast(degree_lits, threshold, guard=guard)

    def graph_from_model(self, model: Sequence[int]) -> List[int]:
        positive = {lit for lit in model if lit > 0}
        adj = [0] * self.n
        for (u, v), var in self.edge_vars.items():
            if var in positive:
                adj[u] |= 1 << v
                adj[v] |= 1 << u
        return adj

    def edge_cut_from_colouring(self, colouring: Colouring) -> Tuple[int, ...]:
        classes: Dict[int, List[int]] = {}
        for v, c in colouring.items():
            classes.setdefault(c, []).append(v)
        clause: Set[int] = set()
        for group in classes.values():
            for u, v in itertools.combinations(sorted(group), 2):
                var = self.edge(u, v)
                if var is not None:
                    clause.add(var)
        if not clause:
            raise AssertionError("colouring cut unexpectedly has no graph-edge literal")
        return tuple(sorted(clause))

    def validate_graph_reduction(self, adj: Sequence[int]) -> None:
        if any((adj[x] >> y) & 1 for x, y in itertools.combinations(self.independent, 2)):
            raise AssertionError("fixed independent set is not independent")
        if self.alpha_bound is not None and maximum_independent_set_size(adj) > self.alpha_bound:
            raise AssertionError("model violates independence-number bound")
        if self.min_degree is not None and min(row.bit_count() for row in adj) < self.min_degree:
            raise AssertionError("model violates minimum degree")
        if self.attachment_bounds is not None:
            lower, upper = self.attachment_bounds
            for x in self.independent:
                degree = sum((adj[x] >> h) & 1 for h in self.h_vertices)
                if not (lower <= degree <= upper):
                    raise AssertionError("model violates attachment bound")

    def write_variable_map(self, path: Path) -> None:
        data = {
            "n": self.n,
            "independent": list(self.independent),
            "edge_variables": {f"{u},{v}": var for (u, v), var in sorted(self.edge_vars.items())},
            "named_variables": {str(k): v for k, v in sorted(self.var_names.items())},
            "max_variable": self.pool.top,
        }
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def make_solver(name: str, clauses: Sequence[Sequence[int]]):
    if name == "cadical":
        return Cadical195(bootstrap_with=clauses)
    if name == "glucose":
        return Glucose4(bootstrap_with=clauses)
    raise ValueError(f"unknown solver {name}")


def cut_record(kind: str, colouring: Colouring, clause: Sequence[int]) -> dict:
    classes: Dict[int, List[int]] = {}
    for v, c in colouring.items():
        classes.setdefault(c, []).append(v)
    return {
        "kind": kind,
        "classes": [sorted(group) for _, group in sorted(classes.items())],
        "clause": list(clause),
        "sha256": hashlib.sha256(" ".join(map(str, clause)).encode()).hexdigest(),
    }


def load_cut_records(path: Path) -> List[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def append_cut_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_dimacs(path: Path, clauses: Sequence[Sequence[int]], nvars: int) -> None:
    with path.open("w", encoding="ascii") as handle:
        handle.write(f"p cnf {nvars} {len(clauses)}\n")
        for clause in clauses:
            handle.write(" ".join(map(str, clause)) + " 0\n")


def write_candidate(path: Path, adj: Sequence[int]) -> None:
    edges = [(u, v) for u, v in itertools.combinations(range(len(adj)), 2) if (adj[u] >> v) & 1]
    payload = {
        "n": len(adj),
        "graph6": graph6(adj),
        "degrees": [row.bit_count() for row in adj],
        "edges": edges,
    }
    path.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n")
    with path.with_suffix(".edges").open("w") as handle:
        handle.write(f"{len(adj)}\n")
        for u, v in edges:
            handle.write(f"{u} {v}\n")


def independently_verify_candidate(adj: Sequence[int]) -> dict:
    n = len(adj)
    vertices = tuple(range(n))
    five_a = dsatur_k_colouring(adj, vertices, 5)
    five_b = plain_k_colouring(adj, vertices, 5)
    if five_a is not None or five_b is not None:
        raise AssertionError("candidate is 5-colourable")
    six_a = dsatur_k_colouring(adj, vertices, 6)
    six_b = plain_k_colouring(adj, vertices, 6)
    if six_a is None or six_b is None:
        raise AssertionError("candidate is not verified 6-colourable")
    deletion_data = []
    for u, v in itertools.combinations(vertices, 2):
        if not ((adj[u] >> v) & 1):
            continue
        remaining = [w for w in vertices if w not in (u, v)]
        ca = dsatur_k_colouring(adj, remaining, 4)
        cb = plain_k_colouring(adj, remaining, 4)
        if ca is None or cb is None:
            raise AssertionError(f"edge deletion {u},{v} is not verified 4-colourable")
        deletion_data.append([u, v])
    return {
        "chromatic_number": 6,
        "alpha": maximum_independent_set_size(adj),
        "minimum_degree": min(row.bit_count() for row in adj),
        "verified_edge_deletions": deletion_data,
    }


def run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    accelerated = args.mode == "accelerated"
    model = ExactModel(
        accelerated=accelerated,
        capacity=args.capacity,
        common_rainbow=args.common_rainbow,
    )
    model.write_variable_map(out / "variables.json")
    metadata = {
        "mode": args.mode,
        "capacity": bool(args.capacity),
        "common_rainbow": bool(args.common_rainbow),
        "base_variables": model.pool.top,
        "base_clauses": len(model.cnf.clauses),
        "python": sys.version,
        "started_unix": time.time(),
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")

    cuts_path = out / "cuts.jsonl"
    records = load_cut_records(cuts_path) if args.resume else []
    if not args.resume and cuts_path.exists():
        cuts_path.unlink()
        records = []

    all_clauses: List[List[int]] = [list(c) for c in model.cnf.clauses]
    known_cuts: Set[Tuple[int, ...]] = set()
    for record in records:
        clause = tuple(sorted(int(x) for x in record["clause"]))
        if clause not in known_cuts:
            known_cuts.add(clause)
            all_clauses.append(list(clause))

    solver = make_solver(args.solver, all_clauses)
    started = time.time()
    iteration = len(records)
    status = "running"
    try:
        while iteration < args.max_iterations:
            if STOP_REQUESTED:
                status = "interrupted"
                break
            if args.max_seconds and time.time() - started >= args.max_seconds:
                status = "time_limit"
                break
            sat = solver.solve()
            if not sat:
                status = "unsat"
                static_path = out / f"static_{args.mode}.cnf"
                write_dimacs(static_path, all_clauses, model.pool.top)
                result = {
                    **metadata,
                    "status": status,
                    "iterations": iteration,
                    "cuts": len(known_cuts),
                    "variables": model.pool.top,
                    "clauses": len(all_clauses),
                    "elapsed_seconds": time.time() - started,
                    "static_cnf": static_path.name,
                    "static_cnf_sha256": formula_sha256(static_path),
                }
                (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
                print("s UNSATISFIABLE")
                print(json.dumps(result, sort_keys=True))
                return 20

            raw_model = solver.get_model()
            adj = model.graph_from_model(raw_model)
            model.validate_graph_reduction(adj)

            # In accelerated mode H must be non-4-colourable.  Each H-v upper
            # witness is already in the CNF, so a permanent H-colouring cut is valid.
            if accelerated:
                h_colouring = dsatur_k_colouring(adj, model.h_vertices, 4)
                if h_colouring is not None:
                    assert verify_colouring(adj, h_colouring, model.h_vertices, 4)
                    clause = model.edge_cut_from_colouring(h_colouring)
                    if any((adj[u] >> v) & 1 for group in _classes(h_colouring) for u, v in itertools.combinations(group, 2)):
                        raise AssertionError("invalid H-colouring witness")
                    if clause in known_cuts:
                        raise AssertionError("duplicate violated H cut; solver/model inconsistency")
                    record = cut_record("H_not_4_colourable", h_colouring, clause)
                    append_cut_record(cuts_path, record)
                    known_cuts.add(clause)
                    all_clauses.append(list(clause))
                    solver.add_clause(list(clause))
                    iteration += 1
                    _checkpoint(out, status, iteration, known_cuts, started, adj, "H4 cut")
                    continue

            colouring = dsatur_k_colouring(adj, model.vertices, 5)
            if colouring is not None:
                assert verify_colouring(adj, colouring, model.vertices, 5)
                clause = model.edge_cut_from_colouring(colouring)
                # Every literal in the cut must currently be false; this directly
                # validates the colouring witness and hence the logical cut.
                edge_by_var = {var: pair for pair, var in model.edge_vars.items()}
                if any((adj[edge_by_var[var][0]] >> edge_by_var[var][1]) & 1 for var in clause):
                    raise AssertionError("generated cut is not violated by its source model")
                if clause in known_cuts:
                    raise AssertionError("duplicate violated G cut; solver/model inconsistency")
                record = cut_record("G_not_5_colourable", colouring, clause)
                append_cut_record(cuts_path, record)
                known_cuts.add(clause)
                all_clauses.append(list(clause))
                solver.add_clause(list(clause))
                iteration += 1
                _checkpoint(out, status, iteration, known_cuts, started, adj, "G5 cut")
                continue

            # A model surviving the CEGAR checker is not announced until a second,
            # separately written exact checker and all deletion checks agree.
            verification = independently_verify_candidate(adj)
            write_candidate(out / "candidate", adj)
            (out / "candidate_verification.json").write_text(json.dumps(verification, indent=2) + "\n")
            result = {
                **metadata,
                "status": "counterexample",
                "iterations": iteration,
                "cuts": len(known_cuts),
                "elapsed_seconds": time.time() - started,
                "graph6": graph6(adj),
                **verification,
            }
            (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            print("s SATISFIABLE COUNTEREXAMPLE")
            print(json.dumps(result, sort_keys=True))
            return 10
    finally:
        solver.delete()

    _checkpoint(out, status, iteration, known_cuts, started, None, "stopped")
    result = {
        **metadata,
        "status": status,
        "iterations": iteration,
        "cuts": len(known_cuts),
        "elapsed_seconds": time.time() - started,
    }
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


def _classes(colouring: Colouring) -> List[List[int]]:
    groups: Dict[int, List[int]] = {}
    for v, c in colouring.items():
        groups.setdefault(c, []).append(v)
    return [sorted(group) for _, group in sorted(groups.items())]


def _checkpoint(
    out: Path,
    status: str,
    iteration: int,
    cuts: Set[Tuple[int, ...]],
    started: float,
    adj: Optional[Sequence[int]],
    note: str,
) -> None:
    payload = {
        "status": status,
        "iteration": iteration,
        "cuts": len(cuts),
        "elapsed_seconds": time.time() - started,
        "note": note,
    }
    if adj is not None:
        payload.update(
            {
                "graph6": graph6(adj),
                "degrees": [row.bit_count() for row in adj],
                "edges": sum(row.bit_count() for row in adj) // 2,
            }
        )
    (out / "checkpoint.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if iteration % 100 == 0 or note == "stopped":
        print("c checkpoint", json.dumps(payload, sort_keys=True), flush=True)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("core", "accelerated"), default="core")
    parser.add_argument("--out", default="artifacts/tihany-core")
    parser.add_argument("--solver", choices=("cadical", "glucose"), default="cadical")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--capacity", action="store_true", help="add the proved local capacity inequalities")
    parser.add_argument("--common-rainbow", action="store_true", help="add KPT common-rainbow witnesses")
    parser.add_argument("--max-iterations", type=int, default=1_000_000)
    parser.add_argument("--max-seconds", type=float, default=0.0)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
