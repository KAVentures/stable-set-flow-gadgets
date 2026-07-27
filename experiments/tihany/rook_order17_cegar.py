#!/usr/bin/env python3
"""Exact order-17 completion search for the exceptional degree-8/degree-9 interface.

A separate exhaustive local analysis leaves one rooted degree-8/degree-9 interface
and sixteen possible cross completions.  A degree/common-neighbour multicover
bound shows that an order-17 completion (four outside vertices) can use only
patterns 0, 2, 3, 4, and 6.  This script attacks each of those five patterns with
an exact graph-level SAT+CEGAR model.

The graph formula fixes the complete induced graph on vertices 0..12 and forces
centres 0 and 1 to have their prescribed exact degrees 8 and 9.  It then imposes:
  * alpha(G) <= 4;
  * minimum degree at least 8;
  * a guarded proper four-colouring of G-u-v for every potential edge uv;
  * optionally, the KPT common-rainbow condition in those deletion colourings;
  * non-five-colourability through permanent independently checked CEGAR cuts.

A verified SAT model is an actual order-17 counterexample in this subcase.  A
checked UNSAT certificate excludes the chosen rooted pattern.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import signal
import sys
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
    maximum_independent_set_size,
    plain_k_colouring,
    verify_colouring,
    write_candidate,
    write_dimacs,
)


BASE_EDGES = {
    (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8),
    (1, 2), (1, 3), (1, 5), (1, 7), (1, 9), (1, 10), (1, 11), (1, 12),
    (2, 5), (2, 6), (2, 7), (2, 12),
    (3, 6), (3, 7), (3, 8), (3, 9), (3, 11),
    (4, 5), (4, 6), (4, 7), (4, 8),
    (5, 8), (5, 11), (5, 12),
    (6, 8),
    (7, 10),
    (9, 10), (9, 11), (9, 12), (10, 11), (10, 12),
}
X = (4, 6, 8)
Y = (9, 10, 11, 12)
CROSS_PAIRS = tuple((x, y) for x in X for y in Y)
PATTERN_MASKS = {0: 0, 2: 16, 3: 17, 4: 64, 6: 128}
OUTSIDE = (13, 14, 15, 16)
STOP_REQUESTED = False


def request_stop(signum, frame) -> None:  # noqa: ARG001
    global STOP_REQUESTED
    STOP_REQUESTED = True


def interface_edges(pattern: int) -> Set[Tuple[int, int]]:
    if pattern not in PATTERN_MASKS:
        raise ValueError(f"unsupported residual pattern {pattern}; choose from {sorted(PATTERN_MASKS)}")
    edges = set(BASE_EDGES)
    mask = PATTERN_MASKS[pattern]
    for bit, pair in enumerate(CROSS_PAIRS):
        if (mask >> bit) & 1:
            edges.add(pair)
    return edges


def build_model(pattern: int, common_rainbow: bool) -> ExactModel:
    model = ExactModel(
        n=17,
        independent=(),
        min_degree=8,
        alpha_bound=4,
        attachment_bounds=None,
        accelerated=False,
        common_rainbow=common_rainbow,
    )
    fixed_edges = interface_edges(pattern)
    for u, v in itertools.combinations(range(13), 2):
        var = model.edge(u, v)
        assert var is not None
        model.add_clause([var if (u, v) in fixed_edges else -var])
    # Centres have exact degrees eight and nine in the local classification.
    for w in OUTSIDE:
        for centre in (0, 1):
            var = model.edge(centre, w)
            assert var is not None
            model.add_clause([-var])
    return model


def verify_fixed_interface(adj: Sequence[int], pattern: int) -> None:
    fixed_edges = interface_edges(pattern)
    for u, v in itertools.combinations(range(13), 2):
        actual = bool((adj[u] >> v) & 1)
        if actual != ((u, v) in fixed_edges):
            raise AssertionError(f"fixed interface mismatch at {u},{v}")
    for w in OUTSIDE:
        if ((adj[0] >> w) & 1) or ((adj[1] >> w) & 1):
            raise AssertionError("centre acquired an outside neighbour")
    if adj[0].bit_count() != 8 or adj[1].bit_count() != 9:
        raise AssertionError("centre degree mismatch")


def reconstruct_cut(model: ExactModel, record: dict) -> Tuple[int, ...]:
    raw = record.get("classes")
    if record.get("kind") != "G_not_5_colourable" or not isinstance(raw, list):
        raise ValueError("invalid rook-interface cut record")
    colouring: Dict[int, int] = {}
    for colour, group in enumerate(raw):
        if not isinstance(group, list):
            raise ValueError("invalid colour class")
        for vertex in group:
            v = int(vertex)
            if v in colouring:
                raise ValueError("duplicate vertex in cut record")
            colouring[v] = colour
    if set(colouring) != set(range(17)) or len(raw) > 5:
        raise ValueError("cut record is not a partition of all 17 vertices into at most five classes")
    clause = model.edge_cut_from_colouring(colouring)
    stored = tuple(sorted(int(x) for x in record.get("clause", [])))
    if clause != stored:
        raise ValueError("stored cut does not match its colouring partition")
    return clause


def run(args: argparse.Namespace) -> int:
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    out = Path(args.out) / f"pattern-{args.pattern}"
    out.mkdir(parents=True, exist_ok=True)
    model = build_model(args.pattern, args.common_rainbow)
    model.write_variable_map(out / "variables.json")
    metadata = {
        "problem": "order17_degree8_rook_interface",
        "pattern": args.pattern,
        "cross_mask": PATTERN_MASKS[args.pattern],
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

    clauses: List[List[int]] = [list(c) for c in model.cnf.clauses]
    known: Set[Tuple[int, ...]] = set()
    for record in records:
        clause = reconstruct_cut(model, record)
        if clause not in known:
            known.add(clause)
            clauses.append(list(clause))

    solver = make_solver(args.solver, clauses)
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
            if not solver.solve():
                status = "unsat"
                static_path = out / "static.cnf"
                write_dimacs(static_path, clauses, model.pool.top)
                result = {
                    **metadata,
                    "status": status,
                    "iterations": iteration,
                    "cuts": len(known),
                    "variables": model.pool.top,
                    "clauses": len(clauses),
                    "static_cnf_sha256": formula_sha256(static_path),
                    "elapsed_seconds": time.time() - started,
                }
                (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
                print(json.dumps(result, sort_keys=True), flush=True)
                return 20

            adj = model.graph_from_model(solver.get_model())
            verify_fixed_interface(adj, args.pattern)
            if min(row.bit_count() for row in adj) < 8:
                raise AssertionError("decoded graph violates minimum degree")
            if maximum_independent_set_size(adj) > 4:
                raise AssertionError("decoded graph violates alpha<=4")

            colouring_a = dsatur_k_colouring(adj, range(17), 5)
            colouring_b = plain_k_colouring(adj, range(17), 5)
            if (colouring_a is None) != (colouring_b is None):
                raise AssertionError("independent five-colour checkers disagree")
            if colouring_a is None:
                verification = independently_verify_candidate(adj)
                verification.update({
                    "pattern": args.pattern,
                    "graph6": graph6(adj),
                    "interface_verified": True,
                })
                write_candidate(out / "candidate", adj)
                (out / "candidate-verification.json").write_text(
                    json.dumps(verification, indent=2, sort_keys=True) + "\n"
                )
                print(json.dumps({"status": "SAT_COUNTEREXAMPLE", **verification}, sort_keys=True), flush=True)
                return 10

            assert colouring_b is not None
            if not verify_colouring(adj, colouring_a, range(17), 5):
                raise AssertionError("DSATUR returned an invalid colouring")
            if not verify_colouring(adj, colouring_b, range(17), 5):
                raise AssertionError("plain checker returned an invalid colouring")
            clause = model.edge_cut_from_colouring(colouring_a)
            if clause in known:
                raise AssertionError("solver repeated a graph excluded by an existing cut")
            record = cut_record("G_not_5_colourable", colouring_a, clause)
            append_cut_record(cuts_path, record)
            solver.add_clause(list(clause))
            clauses.append(list(clause))
            known.add(clause)
            iteration += 1
            if iteration % 100 == 0:
                print(
                    f"c pattern={args.pattern} iteration={iteration} cuts={len(known)} "
                    f"elapsed={time.time()-started:.1f}",
                    flush=True,
                )
    finally:
        solver.delete()

    result = {
        **metadata,
        "status": status,
        "iterations": iteration,
        "cuts": len(known),
        "variables": model.pool.top,
        "clauses": len(clauses),
        "elapsed_seconds": time.time() - started,
    }
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", type=int, choices=sorted(PATTERN_MASKS), required=True)
    parser.add_argument("--out", default="artifacts/rook-order17")
    parser.add_argument("--solver", choices=("cadical", "glucose"), default="cadical")
    parser.add_argument("--common-rainbow", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=1_000_000)
    parser.add_argument("--max-seconds", type=float, default=0.0)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
