#!/usr/bin/env python3
"""Exhaustive direct-core search split by the 35 attachment degree profiles.

Every order-17 graph in the established reduction can be relabelled inside the fixed
maximum independent set I so that its four attachment degrees are nonincreasing.
Thus the 35 profiles in {8,9,10,11}^4, modulo permutation, form an exhaustive and
disjoint split.  Each branch retains the direct defining-problem encoding and its own
permanent CEGAR cut log and static DIMACS output.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import signal
import time
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

from pysat.card import CardEnc, EncType

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


def profiles() -> List[Tuple[int, int, int, int]]:
    return sorted(
        {tuple(sorted(p, reverse=True)) for p in itertools.product(range(8, 12), repeat=4)},
        reverse=True,
    )


def add_profile(model: ExactModel, profile: Sequence[int]) -> None:
    for x, degree in zip(model.independent, profile):
        lits = [model.edge(x, h) for h in model.h_vertices]
        clean = [lit for lit in lits if lit is not None]
        enc = CardEnc.equals(lits=clean, bound=int(degree), vpool=model.pool, encoding=EncType.seqcounter)
        for clause in enc.clauses:
            model.add_clause(clause)


def edge_cut(model: ExactModel, colouring: Dict[int, int]) -> Tuple[int, ...]:
    clause = model.edge_cut_from_colouring(colouring)
    edge_by_var = {var: pair for pair, var in model.edge_vars.items()}
    return clause, edge_by_var


def solve_profile(profile: Tuple[int, int, int, int], root: Path, args: argparse.Namespace) -> dict:
    name = "-".join(map(str, profile))
    out = root / name
    out.mkdir(parents=True, exist_ok=True)
    result_path = out / "result.json"
    if result_path.exists() and args.resume:
        prior = json.loads(result_path.read_text())
        if prior.get("status") in {"unsat", "counterexample"}:
            return prior

    model = ExactModel(
        accelerated=False,
        common_rainbow=False,
        min_degree=8,
        alpha_bound=4,
        attachment_bounds=(8, 11),
    )
    add_profile(model, profile)
    model.write_variable_map(out / "variables.json")
    cuts_path = out / "cuts.jsonl"
    records = load_cut_records(cuts_path) if args.resume else []
    if not args.resume and cuts_path.exists():
        cuts_path.unlink(); records = []

    clauses = [list(c) for c in model.cnf.clauses]
    known: Set[Tuple[int, ...]] = set()
    for record in records:
        clause = tuple(sorted(int(x) for x in record["clause"]))
        if clause not in known:
            known.add(clause); clauses.append(list(clause))

    solver = make_solver(args.solver, clauses)
    started = time.time()
    iterations = len(records)
    status = "running"
    try:
        while iterations < args.max_iterations and not STOP:
            if args.branch_seconds and time.time() - started >= args.branch_seconds:
                status = "time_limit"; break
            if not solver.solve():
                static = out / "static.cnf"
                write_dimacs(static, clauses, model.pool.top)
                result = {
                    "profile": profile,
                    "status": "unsat",
                    "variables": model.pool.top,
                    "clauses": len(clauses),
                    "cuts": len(known),
                    "iterations": iterations,
                    "elapsed_seconds": time.time() - started,
                    "static_cnf": static.name,
                    "static_cnf_sha256": formula_sha256(static),
                }
                result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
                return result

            raw = solver.get_model()
            adj = model.graph_from_model(raw)
            model.validate_graph_reduction(adj)
            actual_profile = tuple(sum((adj[x] >> h) & 1 for h in model.h_vertices) for x in model.independent)
            if actual_profile != profile:
                raise AssertionError((profile, actual_profile))
            colouring = dsatur_k_colouring(adj, model.vertices, 5)
            if colouring is not None:
                if not verify_colouring(adj, colouring, model.vertices, 5):
                    raise AssertionError("invalid 5-colouring witness")
                clause, edge_by_var = edge_cut(model, colouring)
                if any((adj[edge_by_var[var][0]] >> edge_by_var[var][1]) & 1 for var in clause):
                    raise AssertionError("cut is not violated by source graph")
                if clause in known:
                    raise AssertionError("duplicate violated cut")
                record = cut_record("G_not_5_colourable", colouring, clause)
                append_cut_record(cuts_path, record)
                known.add(clause); clauses.append(list(clause)); solver.add_clause(list(clause))
                iterations += 1
                if iterations % 100 == 0:
                    checkpoint = {
                        "profile": profile,
                        "status": "running",
                        "iterations": iterations,
                        "cuts": len(known),
                        "elapsed_seconds": time.time() - started,
                        "graph6": graph6(adj),
                    }
                    (out / "checkpoint.json").write_text(json.dumps(checkpoint, indent=2) + "\n")
                    print("c", json.dumps(checkpoint, sort_keys=True), flush=True)
                continue

            verification = independently_verify_candidate(adj)
            write_candidate(out / "candidate", adj)
            result = {
                "profile": profile,
                "status": "counterexample",
                "iterations": iterations,
                "cuts": len(known),
                "elapsed_seconds": time.time() - started,
                "graph6": graph6(adj),
                **verification,
            }
            result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
            return result
    finally:
        solver.delete()

    result = {
        "profile": profile,
        "status": "interrupted" if STOP else status,
        "iterations": iterations,
        "cuts": len(known),
        "elapsed_seconds": time.time() - started,
    }
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("artifacts/tihany-profile-core"))
    parser.add_argument("--solver", choices=("cadical", "glucose"), default="cadical")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--branch-seconds", type=float, default=1800)
    parser.add_argument("--max-iterations", type=int, default=1_000_000)
    parser.add_argument("--only", nargs="*", help="profiles such as 11-10-9-8")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    chosen = profiles()
    if args.only:
        wanted = {tuple(map(int, text.split("-"))) for text in args.only}
        chosen = [p for p in chosen if p in wanted]
    summary = {}
    results = []
    for pos, profile in enumerate(chosen, 1):
        if STOP: break
        print(f"c profile {pos}/{len(chosen)} {profile}", flush=True)
        result = solve_profile(profile, args.out, args)
        results.append(result)
        summary[result["status"]] = summary.get(result["status"], 0) + 1
        (args.out / "summary.json").write_text(json.dumps({
            "profiles_total": len(chosen),
            "profiles_completed": len(results),
            "counts": summary,
            "results": results,
        }, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, sort_keys=True), flush=True)
        if result["status"] == "counterexample": break


if __name__ == "__main__":
    main()
