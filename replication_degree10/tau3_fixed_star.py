#!/usr/bin/env python3
"""Solve one symmetry orbit of the tau=3 general degree-10 frontier.

The branch fixes a full infeasible Hamming star whose centre has the requested
Hamming weight.  For w=(1,...,1), coordinate permutations make the eleven
weights 0,...,10 a complete orbit list.  Global symmetry constraints are
removed and replaced by transpositions in the stabilizer of the fixed centre.

The formula contains the Abdi--Schwarcz conditions plus the complete hierarchy
of pair-cover decrement packing witnesses forced by entrywise minimality.
Results are exploratory until an independently checked proof is produced.
"""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import resource
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "mfmc_upstream.py"
UPSTREAM_URL = "https://raw.githubusercontent.com/tamas-schwarcz/mfmc/main/mfmc.py"


def log(event: str, **data) -> None:
    print(json.dumps({"event": event, **data}, sort_keys=True), flush=True)


def import_upstream():
    if not UPSTREAM.exists():
        urllib.request.urlretrieve(UPSTREAM_URL, UPSTREAM)
    spec = importlib.util.spec_from_file_location("mfmc_upstream", UPSTREAM)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def forbid(enc, variables, bits) -> None:
    enc.add_clause([v if bit == 0 else -v for v, bit in zip(variables, bits)])


def add_fixed_star(enc, centre: int) -> None:
    enc.add_clause([-enc.x[centre]])
    for i in range(enc.d):
        enc.add_clause([-enc.x[centre ^ (1 << i)]])


def swap_point(p: int, i: int, j: int) -> int:
    if ((p >> i) & 1) == ((p >> j) & 1):
        return p
    return p ^ (1 << i) ^ (1 << j)


def add_stabilizer_symmetry(enc, centre: int) -> int:
    count = 0
    for i, j in itertools.combinations(range(enc.d), 2):
        if enc.w[i] != enc.w[j]:
            continue
        if ((centre >> i) & 1) != ((centre >> j) & 1):
            continue
        a = [enc.x[p] for p in range(1 << enc.d)]
        b = [enc.x[swap_point(p, i, j)] for p in range(1 << enc.d)]
        enc.add_lex_geq(a, b)
        count += 1
    return count


def add_pair_decrement_packings(enc, sort_rows: bool = True) -> dict:
    start_v, start_c = enc.var_count, enc.clause_count
    witnesses = rows_total = row_symmetries = 0
    for target in range(enc.d):
        wp = enc.w[target]
        wn = enc.tau - wp
        for dec_pos in range(wp + 1):
            for dec_neg in range(wn + 1):
                dec = dec_pos + dec_neg
                if dec == 0 or dec == enc.tau:
                    continue
                m = enc.tau - dec
                witnesses += 1
                rows_total += m
                rows = [[enc.new_var() for _ in range(enc.d)] for _ in range(m)]
                for row in rows:
                    for p in range(1 << enc.d):
                        mismatch = [row[j] if ((p >> j) & 1) == 0 else -row[j]
                                    for j in range(enc.d)]
                        enc.add_clause([enc.x[p]] + mismatch)
                for j in range(enc.d):
                    if j == target:
                        allowed = {wp - dec_pos}
                    else:
                        lo = max(0, enc.w[j] - dec)
                        hi = min(m, enc.w[j])
                        allowed = set(range(lo, hi + 1))
                    column = [rows[r][j] for r in range(m)]
                    for bits in itertools.product((0, 1), repeat=m):
                        if sum(bits) not in allowed:
                            forbid(enc, column, bits)
                if sort_rows:
                    for r in range(m - 1):
                        enc.add_lex_geq(rows[r], rows[r + 1])
                        row_symmetries += 1
    return {
        "witnesses": witnesses,
        "rows": rows_total,
        "row_symmetries": row_symmetries,
        "added_variables": enc.var_count - start_v,
        "added_clauses": enc.clause_count - start_c,
    }


def build_formula(mod, centre_weight: int):
    d, tau, w, tight = 10, 3, (1,) * 10, False
    centre = (1 << centre_weight) - 1
    enc = mod.MFMCInstanceEncoder(d, tau, w, tight, False, None)
    enc.add_strictly_polar()
    enc.add_cube_ideal()
    enc.add_mates()
    enc.add_zero_infeasible()
    enc.add_no_small_covers(tau - 1)
    add_fixed_star(enc, centre)
    stabilizer = add_stabilizer_symmetry(enc, centre)
    hierarchy = add_pair_decrement_packings(enc, sort_rows=True)
    return enc, centre, stabilizer, hierarchy


def validate_model(mod, centre_weight: int, model: list[int]) -> dict:
    assignment = {abs(lit): lit > 0 for lit in model}

    class Evaluator(mod.MFMCInstanceEncoder):
        def __init__(self, *args, **kwargs):
            self.bad = 0
            self.seen = 0
            super().__init__(*args, **kwargs)
        def add_clause(self, clause):
            self.clause_count += 1
            self.seen += 1
            if not any(assignment.get(abs(lit), False) == (lit > 0) for lit in clause):
                self.bad += 1
        def new_var(self):
            self.var_count += 1
            return self.var_count

    d, tau, w, tight = 10, 3, (1,) * 10, False
    centre = (1 << centre_weight) - 1
    ev = Evaluator(d, tau, w, tight, False, "EVAL")
    ev.add_strictly_polar()
    ev.add_cube_ideal()
    ev.add_mates()
    ev.add_zero_infeasible()
    ev.add_no_small_covers(tau - 1)
    add_fixed_star(ev, centre)
    add_stabilizer_symmetry(ev, centre)
    add_pair_decrement_packings(ev, sort_rows=True)
    return {"checked_clauses": ev.seen, "failed_clauses": ev.bad,
            "variables": ev.var_count, "valid": ev.bad == 0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--centre-weight", type=int, required=True, choices=range(11))
    args = ap.parse_args()
    t0 = time.time()
    mod = import_upstream()
    enc, centre, stabilizer, hierarchy = build_formula(mod, args.centre_weight)
    built = time.time()
    result_path = ROOT / f"tau3_centre_{args.centre_weight}.json"
    log("built", centre_weight=args.centre_weight, centre=centre,
        variables=enc.var_count, clauses=enc.clause_count,
        stabilizer_transpositions=stabilizer, hierarchy=hierarchy,
        build_seconds=built - t0,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    ts = time.time()
    sat = enc.solver.solve()
    solve_seconds = time.time() - ts
    record = {
        "centre_weight": args.centre_weight,
        "centre": centre,
        "variables": enc.var_count,
        "clauses": enc.clause_count,
        "stabilizer_transpositions": stabilizer,
        "hierarchy": hierarchy,
        "satisfiable": bool(sat),
        "build_seconds": built - t0,
        "solve_seconds": solve_seconds,
        "total_seconds": time.time() - t0,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "solver_stats": enc.solver.accum_stats(),
    }
    if sat:
        model = enc.solver.get_model()
        audit = validate_model(mod, args.centre_weight, model)
        record["model_audit"] = audit
        record["feasible_points"] = [p for p in range(1 << 10) if model[p] > 0]
        if not audit["valid"]:
            raise RuntimeError(f"solver returned invalid model: {audit}")
    result_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    log("solved", **record)
    enc.solver.delete()


if __name__ == "__main__":
    main()
