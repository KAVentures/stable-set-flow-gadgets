#!/usr/bin/env python3
"""Reduction-independent direct search at order 17.

Any noncomplete graph has a nonedge, so after relabelling we may fix `01` as a
nonedge.  Apart from the proved minimum-degree bound, this encoding uses only the
definition of a noncomplete double-critical 6-chromatic graph:

- graph variables on 17 vertices, with edge 01 absent;
- minimum degree at least eight;
- every possible edge activates an exact four-colouring of its endpoint deletion;
- CEGAR excludes every independently found five-colouring.

It does not use alpha=4, a maximum independent set, the 13-vertex complement,
attachment bounds, critical-complement lemmas, or local KPT structure.  A checked
UNSAT certificate for its completed static CNF is therefore the strongest finite
crosscheck of an order-17 exclusion.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

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


def stop(_signum, _frame):
    global STOP
    STOP = True


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("artifacts/tihany-ultracore"))
    parser.add_argument("--solver", choices=("cadical", "glucose"), default="cadical")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-seconds", type=float, default=0)
    parser.add_argument("--max-iterations", type=int, default=1_000_000)
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    model = ExactModel(
        n=17,
        independent=(0, 1),
        min_degree=8,
        alpha_bound=None,
        attachment_bounds=None,
        accelerated=False,
        common_rainbow=False,
    )
    model.write_variable_map(out / "variables.json")
    cuts_path = out / "cuts.jsonl"
    records = load_cut_records(cuts_path) if args.resume else []
    if not args.resume and cuts_path.exists():
        cuts_path.unlink(); records = []

    clauses: List[List[int]] = [list(c) for c in model.cnf.clauses]
    known: Set[Tuple[int, ...]] = set()
    for record in records:
        clause = tuple(sorted(int(x) for x in record["clause"]))
        if clause not in known:
            known.add(clause); clauses.append(list(clause))

    solver = make_solver(args.solver, clauses)
    started = time.time()
    iteration = len(records)
    try:
        while iteration < args.max_iterations and not STOP:
            if args.max_seconds and time.time() - started >= args.max_seconds:
                break
            if not solver.solve():
                static = out / "static_ultracore.cnf"
                write_dimacs(static, clauses, model.pool.top)
                result = {
                    "status": "unsat",
                    "fixed_nonedge": [0, 1],
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
            if (adj[0] >> 1) & 1:
                raise AssertionError("fixed nonedge 01 became an edge")
            colouring = dsatur_k_colouring(adj, model.vertices, 5)
            if colouring is not None:
                if not verify_colouring(adj, colouring, model.vertices, 5):
                    raise AssertionError("invalid five-colouring witness")
                clause = model.edge_cut_from_colouring(colouring)
                edge_by_var = {var: pair for pair, var in model.edge_vars.items()}
                if any((adj[edge_by_var[var][0]] >> edge_by_var[var][1]) & 1 for var in clause):
                    raise AssertionError("colouring cut is not violated by its source graph")
                if clause in known:
                    raise AssertionError("duplicate violated cut")
                append_cut_record(cuts_path, cut_record("G_not_5_colourable", colouring, clause))
                known.add(clause); clauses.append(list(clause)); solver.add_clause(list(clause))
                iteration += 1
                if iteration % 100 == 0:
                    checkpoint = {
                        "status": "running",
                        "iteration": iteration,
                        "cuts": len(known),
                        "elapsed_seconds": time.time() - started,
                        "graph6": graph6(adj),
                        "minimum_degree": min(row.bit_count() for row in adj),
                    }
                    (out / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
                    print("c", json.dumps(checkpoint, sort_keys=True), flush=True)
                continue

            verification = independently_verify_candidate(adj)
            write_candidate(out / "candidate", adj)
            result = {
                "status": "counterexample",
                "fixed_nonedge": [0, 1],
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
        "fixed_nonedge": [0, 1],
        "iterations": iteration,
        "cuts": len(known),
        "elapsed_seconds": time.time() - started,
    }
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
