#!/usr/bin/env python3
"""Exact cutting-plane search for one tau=3 fixed-star orbit.

The master formula contains strict polarity, cover/mate conditions, a fixed
full infeasible star, stabilizer symmetry, and the complete pair-decrement
packing hierarchy. Two omitted universal conditions are separated exactly:

* every exact 3-packing present in a model yields a blocking clause;
* every violated Abdi--Schwarcz width--length condition yields precisely the
  corresponding published cube-idealness clause.

A surviving model is not automatically a counterexample: its packing property
must still be checked over every minor. An UNSAT result is exploratory until a
proof certificate for the final deterministic formula is independently checked.
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
FREE = 2
PARAMETERS = ((5, 2, 3), (7, 2, 4), (8, 3, 3), (9, 2, 5))


def load_upstream():
    if not UPSTREAM.exists():
        urllib.request.urlretrieve(UPSTREAM_URL, UPSTREAM)
    spec = importlib.util.spec_from_file_location("mfmc_upstream", UPSTREAM)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def log(event: str, **data) -> None:
    print(json.dumps({"event": event, **data}, sort_keys=True), flush=True)


def forbid(enc, variables, bits) -> None:
    enc.add_clause([v if bit == 0 else -v for v, bit in zip(variables, bits)])


def add_fixed_star(enc, centre: int) -> None:
    for q in [centre] + [centre ^ (1 << i) for i in range(enc.d)]:
        enc.add_clause([-enc.x[q]])


def swap_point(p: int, i: int, j: int) -> int:
    if ((p >> i) & 1) == ((p >> j) & 1):
        return p
    return p ^ (1 << i) ^ (1 << j)


def add_stabilizer_symmetry(enc, centre: int) -> int:
    count = 0
    for i, j in itertools.combinations(range(enc.d), 2):
        if enc.w[i] != enc.w[j] or ((centre >> i) & 1) != ((centre >> j) & 1):
            continue
        enc.add_lex_geq(
            [enc.x[p] for p in range(1 << enc.d)],
            [enc.x[swap_point(p, i, j)] for p in range(1 << enc.d)],
        )
        count += 1
    return count


def add_pair_decrement_packings(enc) -> dict:
    start_v, start_c = enc.var_count, enc.clause_count
    witnesses = rows_total = row_symmetries = 0
    for target in range(enc.d):
        wp, wn = enc.w[target], enc.tau - enc.w[target]
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
                    col = [rows[r][j] for r in range(m)]
                    for bits in itertools.product((0, 1), repeat=m):
                        if sum(bits) not in allowed:
                            forbid(enc, col, bits)
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


def build_master(mod, centre_weight: int):
    d, tau, w, tight = 10, 3, (1,) * 10, False
    centre = (1 << centre_weight) - 1
    enc = mod.MFMCInstanceEncoder(d, tau, w, tight, False, None)
    enc.add_strictly_polar()
    # Cube-idealness is separated lazily.
    enc.add_mates()
    enc.add_zero_infeasible()
    enc.add_no_small_covers(tau - 1)
    add_fixed_star(enc, centre)
    stabilizer = add_stabilizer_symmetry(enc, centre)
    hierarchy = add_pair_decrement_packings(enc)
    return enc, centre, stabilizer, hierarchy


def model_set(model: list[int], d: int) -> set[int]:
    values = {abs(lit): lit > 0 for lit in model}
    return {p for p in range(1 << d) if values.get(p + 1, False)}


def exact_tau3_packings(S: set[int], d: int, limit: int) -> list[tuple[int, int, int]]:
    """Enumerate exact w=(1,...,1) three-packings, i.e. set partitions."""
    allmask = (1 << d) - 1
    points = sorted(S)
    pointset = S
    out: list[tuple[int, int, int]] = []
    for ai, a in enumerate(points):
        for b in points[ai:]:
            if a & b:
                continue
            c = allmask ^ (a | b)
            if c < b or c not in pointset:
                continue
            out.append((a, b, c))
            if len(out) >= limit:
                return out
    return out


def localized_patterns(S: set[int], K: tuple[int, ...], outside: tuple[int, ...],
                       ops: tuple[int, ...]) -> tuple[int, ...]:
    vals = set()
    for q in S:
        if all(op == FREE or ((q >> outside[a]) & 1) == op for a, op in enumerate(ops)):
            vals.add(sum(((q >> K[j]) & 1) << j for j in range(len(K))))
    return tuple(sorted(vals))


def cube_obstructions(S: set[int], d: int, limit: int):
    """Yield exact violated width--length conditions, in published order."""
    yielded = 0
    for m, r, s in PARAMETERS:
        for K in itertools.combinations(range(d), m):
            Kset = set(K)
            outside = tuple(i for i in range(d) if i not in Kset)
            for ops in itertools.product((0, 1, FREE), repeat=d - m):
                T = localized_patterns(S, K, outside, ops)
                if not T:
                    continue
                for p in range(1 << m):
                    if any((q ^ p).bit_count() <= r - 1 for q in T):
                        continue
                    has_small_cover = False
                    for B in itertools.combinations(range(m), s - 1):
                        if not any(all(((q >> j) & 1) == ((p >> j) & 1) for j in B) for q in T):
                            has_small_cover = True
                            break
                    if has_small_cover:
                        continue
                    yield {"m": m, "r": r, "s": s, "K": K,
                           "outside": outside, "ops": ops, "p": p}
                    yielded += 1
                    if yielded >= limit:
                        return


def obstruction_clause(obs, d: int, y) -> list[int]:
    m, r, s = obs["m"], obs["r"], obs["s"]
    K, outside, ops, p = obs["K"], obs["outside"], obs["ops"], obs["p"]
    restriction = [FREE] * d
    for a, i in enumerate(outside):
        restriction[i] = ops[a]
    clause: list[int] = []
    for D in itertools.combinations(range(m), m - (r - 1)):
        rr = restriction.copy()
        for j in D:
            rr[K[j]] = (p >> j) & 1
        clause.append(y[tuple(rr)])
    for B in itertools.combinations(range(m), s - 1):
        rr = restriction.copy()
        for j in B:
            rr[K[j]] = (p >> j) & 1
        clause.append(-y[tuple(rr)])
    return clause


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--centre-weight", type=int, required=True, choices=range(11))
    ap.add_argument("--iterations", type=int, default=2000)
    ap.add_argument("--packing-batch", type=int, default=2000)
    ap.add_argument("--cube-batch", type=int, default=100)
    args = ap.parse_args()

    t0 = time.time()
    mod = load_upstream()
    enc, centre, stabilizer, hierarchy = build_master(mod, args.centre_weight)
    base_vars, base_clauses = enc.var_count, enc.clause_count
    result_path = ROOT / f"tau3_cegar_{args.centre_weight}.json"
    records = []
    packing_cut_keys: set[tuple[int, ...]] = set()
    cube_cut_keys: set[tuple[int, ...]] = set()
    log("built", centre_weight=args.centre_weight, centre=centre,
        variables=base_vars, clauses=base_clauses,
        stabilizer_transpositions=stabilizer, hierarchy=hierarchy,
        seconds=time.time() - t0,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

    final = "UNKNOWN"
    survivor = None
    for iteration in range(args.iterations):
        ts = time.time()
        sat = enc.solver.solve()
        solve_seconds = time.time() - ts
        rec = {"iteration": iteration, "sat": bool(sat),
               "solve_seconds": solve_seconds,
               "solver_stats": enc.solver.accum_stats(),
               "packing_cuts_total": len(packing_cut_keys),
               "cube_cuts_total": len(cube_cut_keys)}
        if not sat:
            final = "UNSAT"
            records.append(rec)
            log("iteration", **rec)
            break
        S = model_set(enc.solver.get_model(), 10)
        rec["feasible_points"] = len(S)
        packings = exact_tau3_packings(S, 10, args.packing_batch)
        new_packing = 0
        for packing in packings:
            clause = tuple(sorted(-(p + 1) for p in set(packing)))
            if clause not in packing_cut_keys:
                packing_cut_keys.add(clause)
                enc.add_clause(list(clause))
                new_packing += 1
        rec["new_packing_cuts"] = new_packing
        if new_packing:
            records.append(rec)
            log("iteration", **rec)
            continue

        obs_batch = list(cube_obstructions(S, 10, args.cube_batch))
        new_cube = 0
        obs_summary = []
        for obs in obs_batch:
            clause = tuple(obstruction_clause(obs, 10, enc.y))
            key = tuple(sorted(clause))
            if key not in cube_cut_keys:
                cube_cut_keys.add(key)
                enc.add_clause(list(clause))
                new_cube += 1
                obs_summary.append({"m": obs["m"], "r": obs["r"], "s": obs["s"],
                                    "K": list(obs["K"]), "outside": list(obs["outside"]),
                                    "ops": list(obs["ops"]), "p": obs["p"],
                                    "clause_length": len(clause)})
        rec["new_cube_cuts"] = new_cube
        rec["cube_obstructions"] = obs_summary
        records.append(rec)
        log("iteration", **rec)
        if new_cube:
            continue

        final = "SURVIVOR"
        survivor = sorted(S)
        break

    summary = {
        "centre_weight": args.centre_weight,
        "centre": centre,
        "base_variables": base_vars,
        "base_clauses": base_clauses,
        "stabilizer_transpositions": stabilizer,
        "hierarchy": hierarchy,
        "final": final,
        "iterations": len(records),
        "packing_cuts": len(packing_cut_keys),
        "cube_cuts": len(cube_cut_keys),
        "survivor": survivor,
        "records": records,
        "total_seconds": time.time() - t0,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    result_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    log("final", **{k: v for k, v in summary.items() if k not in ("records", "survivor")},
        survivor_points=0 if survivor is None else len(survivor))
    enc.solver.delete()


if __name__ == "__main__":
    main()
