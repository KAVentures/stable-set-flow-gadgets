#!/usr/bin/env python3
"""Exact order-17 search restricted to one certified degree-eight neighbourhood.

This is a small structural split built on the reduction-independent ultracore.
It does not use alpha(G)=4, a fixed maximum independent four-set, attachment bounds,
or critical-complement structure.

If an order-17 counterexample has a degree-eight vertex x, relabel x as 0 and one
of its eight non-neighbours as 1.  Relabel the eight neighbours as 2,...,9.  The
independently certified degree-eight neighbourhood classification says that the
induced graph on 2,...,9 is isomorphic to one of

    GEnfbW, GEjfrw.

Thus these two cases are exhaustive up to relabelling.  The optional --neighbor10
constraint uses the separately certified order-17 theorem that every neighbour of
a degree-eight vertex has global degree at least ten.
"""
from __future__ import annotations

import argparse
import json
import signal
import time
from pathlib import Path
from typing import List, Sequence, Set, Tuple

from core_search import (
    ExactModel,
    append_cut_record,
    cut_record,
    dsatur_k_colouring,
    formula_sha256,
    graph6,
    independently_verify_candidate,
    load_cut_records,
    make_solver,
    verify_colouring,
    write_candidate,
    write_dimacs,
)

STOP = False
ALLOWED_TYPES = ("GEnfbW", "GEjfrw")


def stop(_signum, _frame):
    global STOP
    STOP = True


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)


def decode_short_graph6(text: str) -> List[List[int]]:
    if not text or ord(text[0]) < 63:
        raise ValueError("invalid graph6 string")
    n = ord(text[0]) - 63
    if not 0 <= n <= 62:
        raise ValueError("only short graph6 is supported")
    payload: List[int] = []
    for ch in text[1:]:
        value = ord(ch) - 63
        if not 0 <= value < 64:
            raise ValueError("invalid graph6 payload")
        payload.extend((value >> shift) & 1 for shift in range(5, -1, -1))
    need = n * (n - 1) // 2
    if len(payload) < need:
        raise ValueError("truncated graph6 payload")
    adj = [[0] * n for _ in range(n)]
    pos = 0
    for j in range(1, n):
        for i in range(j):
            if payload[pos]:
                adj[i][j] = adj[j][i] = 1
            pos += 1
    return adj


def add_degree8_case(model: ExactModel, local_type: str, neighbor10: bool) -> None:
    if local_type not in ALLOWED_TYPES:
        raise ValueError(local_type)
    local = decode_short_graph6(local_type)
    if len(local) != 8:
        raise AssertionError("degree-eight local graph must have order eight")

    # Vertex 0 is the degree-eight centre.  Edge 01 is already absent because the
    # ultracore fixes {0,1} as its relabelled nonedge.  Its eight neighbours are
    # exactly 2,...,9 and vertices 10,...,16 are the other seven non-neighbours.
    for v in range(2, 10):
        var = model.edge(0, v)
        assert var is not None
        model.add_clause([var])
    for v in range(10, 17):
        var = model.edge(0, v)
        assert var is not None
        model.add_clause([-var])

    # Canonically identify the completed neighbourhood G[N(0)] with local_type.
    for i in range(8):
        for j in range(i + 1, 8):
            var = model.edge(i + 2, j + 2)
            assert var is not None
            model.add_clause([var if local[i][j] else -var])

    if neighbor10:
        # Separately certified order-17 theorem: every neighbour of a degree-eight
        # vertex has degree at least ten.  This is structural acceleration only;
        # the ordinary core and ultracore encodings remain unchanged.
        for v in range(2, 10):
            incident = [
                var
                for w in model.vertices
                if w != v and (var := model.edge(v, w)) is not None
            ]
            model._card_atleast(incident, 10)


def build_degree8_model(local_type: str, neighbor10: bool) -> ExactModel:
    model = ExactModel(
        n=17,
        independent=(0, 1),
        min_degree=8,
        alpha_bound=None,
        attachment_bounds=None,
        accelerated=False,
        common_rainbow=False,
    )
    add_degree8_case(model, local_type, neighbor10)
    return model


def verify_fixed_case(adj: Sequence[int], local_type: str, neighbor10: bool) -> None:
    if ((adj[0] >> 1) & 1) != 0:
        raise AssertionError("01 must be a nonedge")
    if adj[0].bit_count() != 8:
        raise AssertionError("centre does not have degree eight")
    if {v for v in range(17) if (adj[0] >> v) & 1} != set(range(2, 10)):
        raise AssertionError("centre neighbourhood mismatch")
    local = decode_short_graph6(local_type)
    for i in range(8):
        for j in range(i + 1, 8):
            actual = (adj[i + 2] >> (j + 2)) & 1
            if actual != local[i][j]:
                raise AssertionError("completed neighbourhood mismatch")
    if neighbor10 and min(adj[v].bit_count() for v in range(2, 10)) < 10:
        raise AssertionError("degree-eight neighbour theorem constraint violated")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=ALLOWED_TYPES, required=True)
    parser.add_argument("--neighbor10", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--solver", choices=("cadical", "glucose"), default="cadical")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-seconds", type=float, default=0)
    parser.add_argument("--max-iterations", type=int, default=1_000_000)
    args = parser.parse_args()

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    model = build_degree8_model(args.type, args.neighbor10)
    model.write_variable_map(out / "variables.json")
    cuts_path = out / "cuts.jsonl"
    records = load_cut_records(cuts_path) if args.resume else []
    if not args.resume and cuts_path.exists():
        cuts_path.unlink()
        records = []

    clauses: List[List[int]] = [list(c) for c in model.cnf.clauses]
    known: Set[Tuple[int, ...]] = set()
    for record in records:
        clause = tuple(sorted(int(x) for x in record["clause"]))
        if clause not in known:
            known.add(clause)
            clauses.append(list(clause))

    solver = make_solver(args.solver, clauses)
    started = time.time()
    iteration = len(records)
    try:
        while iteration < args.max_iterations and not STOP:
            if args.max_seconds and time.time() - started >= args.max_seconds:
                break
            if not solver.solve():
                static = out / "static_degree8.cnf"
                write_dimacs(static, clauses, model.pool.top)
                result = {
                    "status": "unsat",
                    "local_type": args.type,
                    "neighbor10": bool(args.neighbor10),
                    "variables": model.pool.top,
                    "clauses": len(clauses),
                    "cuts": len(known),
                    "iterations": iteration,
                    "elapsed_seconds": time.time() - started,
                    "static_cnf": static.name,
                    "static_cnf_sha256": formula_sha256(static),
                }
                (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
                print("s UNSATISFIABLE")
                print(json.dumps(result, sort_keys=True))
                return 20

            raw = solver.get_model()
            adj = model.graph_from_model(raw)
            model.validate_graph_reduction(adj)
            verify_fixed_case(adj, args.type, args.neighbor10)
            colouring = dsatur_k_colouring(adj, model.vertices, 5)
            if colouring is not None:
                if not verify_colouring(adj, colouring, model.vertices, 5):
                    raise AssertionError("invalid five-colouring witness")
                clause = model.edge_cut_from_colouring(colouring)
                edge_by_var = {var: pair for pair, var in model.edge_vars.items()}
                if any((adj[edge_by_var[var][0]] >> edge_by_var[var][1]) & 1 for var in clause):
                    raise AssertionError("colouring cut is not violated by source graph")
                if clause in known:
                    raise AssertionError("duplicate violated cut")
                append_cut_record(cuts_path, cut_record("G_not_5_colourable", colouring, clause))
                known.add(clause)
                clauses.append(list(clause))
                solver.add_clause(list(clause))
                iteration += 1
                if iteration % 100 == 0:
                    checkpoint = {
                        "status": "running",
                        "local_type": args.type,
                        "neighbor10": bool(args.neighbor10),
                        "iteration": iteration,
                        "cuts": len(known),
                        "elapsed_seconds": time.time() - started,
                        "graph6": graph6(adj),
                    }
                    (out / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
                    print("c", json.dumps(checkpoint, sort_keys=True), flush=True)
                continue

            verification = independently_verify_candidate(adj)
            verify_fixed_case(adj, args.type, args.neighbor10)
            write_candidate(out / "candidate", adj)
            result = {
                "status": "counterexample",
                "local_type": args.type,
                "neighbor10": bool(args.neighbor10),
                "iterations": iteration,
                "cuts": len(known),
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

    result = {
        "status": "interrupted" if STOP else "time_limit",
        "local_type": args.type,
        "neighbor10": bool(args.neighbor10),
        "iterations": iteration,
        "cuts": len(known),
        "elapsed_seconds": time.time() - started,
    }
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
