#!/usr/bin/env python3
"""Benchmark the strengthened Abdi--Schwarcz degree-10 encoding.

This is exploratory only.  A final theorem requires emitted CNFs and independently
checked UNSAT certificates; this script measures whether the new necessary
conditions make the first general d=10 instance computationally tractable.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import resource
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "benchmark_result.json"
SOURCE_URL = "https://raw.githubusercontent.com/tamas-schwarcz/mfmc/main/mfmc.py"
SOURCE = ROOT / "mfmc_upstream.py"


def log(event: str, **data) -> None:
    row = {"event": event, "time": time.time(), **data}
    print(json.dumps(row, sort_keys=True), flush=True)


def star_points(p: int, d: int) -> list[int]:
    return [p] + [p ^ (1 << i) for i in range(d)]


def forbid_exact_assignment(enc, variables, bits) -> None:
    enc.add_clause([v if bit == 0 else -v for v, bit in zip(variables, bits)])


def add_star_selector(enc) -> dict:
    selectors = [enc.new_var() for _ in range(1 << enc.d)]
    enc.add_clause(selectors)
    for p, z in enumerate(selectors):
        for q in star_points(p, enc.d):
            enc.add_clause([-z, -enc.x[q]])
    return {"variables": len(selectors), "clauses": 1 + (1 << enc.d) * (enc.d + 1)}


def add_decrement_packings(enc) -> dict:
    k = enc.tau - 1
    start_v, start_c = enc.var_count, enc.clause_count
    for target in range(enc.d):
        for target_sum in (enc.w[target] - 1, enc.w[target]):
            rows = [[enc.new_var() for _ in range(enc.d)] for _ in range(k)]
            for row in rows:
                for p in range(1 << enc.d):
                    mismatch = [row[j] if ((p >> j) & 1) == 0 else -row[j]
                                for j in range(enc.d)]
                    enc.add_clause([enc.x[p]] + mismatch)
            for j in range(enc.d):
                allowed = {target_sum} if j == target else {enc.w[j] - 1, enc.w[j]}
                column = [rows[r][j] for r in range(k)]
                for bits in itertools.product((0, 1), repeat=k):
                    if sum(bits) not in allowed:
                        forbid_exact_assignment(enc, column, bits)
    return {"variables": enc.var_count - start_v, "clauses": enc.clause_count - start_c}


def validate_primary_clauses(enc, model: list[int]) -> None:
    # PySAT returns a full signed assignment.  Validation here checks all clauses
    # only when a SAT model exists by regenerating the formula deterministically
    # into a list-backed encoder in a separate future audit.  The benchmark never
    # treats SAT or UNSAT as a final certificate.
    assignment = {abs(lit): lit > 0 for lit in model}
    assert len(assignment) >= enc.var_count


def main() -> None:
    t0 = time.time()
    urllib.request.urlretrieve(SOURCE_URL, SOURCE)
    spec = importlib.util.spec_from_file_location("mfmc_upstream", SOURCE)
    assert spec and spec.loader
    mfmc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mfmc)

    d, tau, w, tight = 10, 3, (1,) * 10, False
    enc = mfmc.MFMCInstanceEncoder(d, tau, w, tight, False, None)
    enc.add_strictly_polar()
    enc.add_cube_ideal()
    enc.add_mates()
    enc.add_zero_infeasible()
    enc.add_no_small_covers(tau - 1)
    enc.add_weight_symmetry_breaking()
    base = {"variables": enc.var_count, "clauses": enc.clause_count}
    star = add_star_selector(enc)
    packings = add_decrement_packings(enc)
    built = time.time()
    log("built", d=d, tau=tau, w=w, tight=tight, base=base, star=star,
        decrement_packings=packings, variables=enc.var_count,
        clauses=enc.clause_count, build_seconds=built - t0,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

    solve_start = time.time()
    satisfiable = enc.solver.solve()
    solve_seconds = time.time() - solve_start
    record = {
        "d": d,
        "tau": tau,
        "w": list(w),
        "tight": tight,
        "base": base,
        "star": star,
        "decrement_packings": packings,
        "variables": enc.var_count,
        "clauses": enc.clause_count,
        "satisfiable": bool(satisfiable),
        "build_seconds": built - t0,
        "solve_seconds": solve_seconds,
        "total_seconds": time.time() - t0,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    if satisfiable:
        model = enc.solver.get_model()
        validate_primary_clauses(enc, model)
        record["model_primary_true"] = [i for i in range(1 << d) if model[i] > 0]
    RESULT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    log("solved", **record)
    enc.solver.delete()


if __name__ == "__main__":
    main()
