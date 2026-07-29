#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import threading
import time
import urllib.request
from pathlib import Path

import sympy as sp
from pysat.solvers import Cadical195

import support

FREE = 2
PARAMETERS = ((5, 2, 3), (7, 2, 4), (8, 3, 3), (9, 2, 5))
ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "mfmc_upstream.py"
UPSTREAM_URL = "https://raw.githubusercontent.com/tamas-schwarcz/mfmc/669b761fd9be6fa920513c0675e48e28a4d38de7/mfmc.py"


def load_upstream():
    if not UPSTREAM.exists():
        urllib.request.urlretrieve(UPSTREAM_URL, UPSTREAM)
    spec = importlib.util.spec_from_file_location("mfmc_upstream", UPSTREAM)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import upstream encoder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_support_sizes(d, tau, w):
    counts = [0] * tau
    for value in w:
        counts[value] += 1
        counts[tau - value] += 1
    answer = []
    for size in range(tau + 1, d + 2):
        admissible = all(
            k * size * size
            - size * (tau - 2) * (size - tau)
            + k * size * (size - tau)
            <= sum((k + 1 - i) * (size - tau + i - 1)
                   * (size - tau) * counts[i]
                   for i in range(1, k + 1))
            for k in range(1, tau)
        )
        if admissible:
            answer.append(size)
    return answer


def enumerate_branches(module, d):
    branches = []
    for tau in range(3, d + 1):
        for w in itertools.combinations_with_replacement(
                range(1, tau // 2 + 1), d):
            admissibility = module.is_admissible(d, tau, w)
            if not admissibility:
                continue
            for support_size in valid_support_sizes(d, tau, w):
                branches.append({
                    "d": d,
                    "tau": tau,
                    "w": tuple(w),
                    "tight": admissibility == 2,
                    "support_size": support_size,
                })
    return branches


def add_star_selector(enc):
    selectors = [enc.new_var() for _ in range(1 << enc.d)]
    enc.add_clause(selectors)
    for centre, selector in enumerate(selectors):
        for point in [centre] + [centre ^ (1 << i) for i in range(enc.d)]:
            enc.add_clause([-selector, -enc.x[point]])
        for i in range(enc.d):
            restriction = tuple(
                FREE if j == i else ((centre >> j) & 1)
                for j in range(enc.d)
            )
            enc.add_clause([-selector, -enc.y[restriction]])
    return selectors


def build_master(module, branch):
    d = branch["d"]
    tau = branch["tau"]
    w = branch["w"]
    tight = branch["tight"]
    enc = module.MFMCInstanceEncoder(d, tau, w, tight, False, "memory")
    enc.add_mates()
    enc.add_zero_infeasible()
    enc.add_no_small_covers(tau if tight else tau - 1)
    enc.add_weight_symmetry_breaking()
    selectors = add_star_selector(enc)
    residual = support.add_single_decrement_residual_holes(enc)
    basis = support.add_support(enc, branch["support_size"])
    return enc, selectors, residual, basis


def model_dictionary(model):
    return {abs(literal): literal > 0 for literal in model}


def support_assignment(values, rows):
    return [[1 if values.get(variable, False) else 0 for variable in row]
            for row in rows]


def exact_support_check(bits, d, tau, w):
    size = len(bits)
    matrix = sp.Matrix(
        [[1] * size]
        + [[bits[row][coordinate] for row in range(size)]
           for coordinate in range(d)]
    )
    target = sp.Matrix([tau] + list(w))
    rank = matrix.rank()
    if rank != size or matrix.row_join(target).rank() != rank:
        return False, None, rank
    solutions = sp.linsolve((matrix, target))
    if solutions is sp.EmptySet:
        return False, None, rank
    coefficients = [sp.Rational(value) for value in next(iter(solutions))]
    valid = all(value > 0 and value < 1 for value in coefficients)
    return valid, coefficients, rank


def block_support_assignment(rows, bits):
    clause = []
    for row, assignment in zip(rows, bits):
        clause.extend(variable if bit == 0 else -variable
                      for variable, bit in zip(row, assignment))
    return tuple(clause)


def coefficient_mate_clauses(enc, rows, bits, coefficients):
    guard = list(block_support_assignment(rows, bits))
    clauses = []
    for point_bits, coefficient in zip(bits, coefficients):
        point = sum(bit << i for i, bit in enumerate(point_bits))
        candidates = []
        for B in itertools.product((support.NEG, support.POS, support.NONE),
                                   repeat=enc.d):
            weight = support.cover_weight(enc, B)
            hits = support.intersection(B, point)
            if (hits >= 2
                    and weight - hits <= enc.tau - 2
                    and coefficient * (hits - 1) <= weight - enc.tau):
                candidates.append(-enc.y[support.cover_restr(B)])
        clauses.append(tuple(guard + candidates))
    return clauses


def find_exact_packing(feasible, d, tau, w):
    points = sorted(feasible)
    bit_vectors = [tuple((point >> j) & 1 for j in range(d))
                   for point in points]
    states = {(0,) * d: ()}
    for step in range(tau):
        remaining = tau - step - 1
        next_states = {}
        for state, path in states.items():
            for point, bits in zip(points, bit_vectors):
                new_state = tuple(state[j] + bits[j] for j in range(d))
                if any(new_state[j] > w[j]
                       or new_state[j] + remaining < w[j]
                       for j in range(d)):
                    continue
                next_states.setdefault(new_state, path + (point,))
        states = next_states
        if not states:
            return None
    return states.get(tuple(w))


def strict_violations(feasible, d, limit):
    result = []
    for restriction in itertools.product((0, 1, FREE), repeat=d):
        free = [i for i, value in enumerate(restriction) if value == FREE]
        if len(free) < 3:
            continue
        fixed_one = sum(1 << i for i, value in enumerate(restriction)
                        if value == 1)
        fixed_zero = sum(1 << i for i, value in enumerate(restriction)
                         if value == 0)
        points = [point for point in feasible
                  if (point & fixed_one) == fixed_one
                  and (point & fixed_zero) == 0]
        if not points:
            continue
        if any(all(((point >> i) & 1) == ((points[0] >> i) & 1)
                   for point in points)
               for i in free):
            continue
        free_mask = sum(1 << i for i in free)
        point_set = set(points)
        if any((point ^ free_mask) in point_set for point in points):
            continue
        result.append(restriction)
        if len(result) >= limit:
            break
    return result


def strict_clause(enc, restriction):
    free = [i for i, value in enumerate(restriction) if value == FREE]
    fixed = sum(1 << i for i, value in enumerate(restriction) if value == 1)
    free_mask = sum(1 << i for i in free)
    clause = []
    for assignment in range(1 << (len(free) - 1)):
        point = fixed
        for j, coordinate in enumerate(free[:-1]):
            if (assignment >> j) & 1:
                point |= 1 << coordinate
        clause.append(enc.new_iff_and([enc.x[point], enc.x[point ^ free_mask]]))
    for coordinate in free:
        for value in (0, 1):
            child = list(restriction)
            child[coordinate] = value
            clause.append(-enc.y[tuple(child)])
    return tuple(clause)


def localized_patterns(feasible, coordinates, outside, operations):
    return tuple(sorted({
        sum(((point >> coordinates[j]) & 1) << j
            for j in range(len(coordinates)))
        for point in feasible
        if all(operation == FREE
               or ((point >> outside[index]) & 1) == operation
               for index, operation in enumerate(operations))
    }))


def cube_violations(feasible, d, limit):
    answer = []
    for m, radius, cover_size in PARAMETERS:
        if m > d:
            continue
        for coordinates in itertools.combinations(range(d), m):
            coordinate_set = set(coordinates)
            outside = tuple(i for i in range(d) if i not in coordinate_set)
            for operations in itertools.product((0, 1, FREE),
                                                repeat=d - m):
                localized = localized_patterns(
                    feasible, coordinates, outside, operations)
                if not localized:
                    continue
                for centre in range(1 << m):
                    if any((point ^ centre).bit_count() <= radius - 1
                           for point in localized):
                        continue
                    if any(
                        not any(all(((point >> j) & 1)
                                    == ((centre >> j) & 1)
                                    for j in B)
                                for point in localized)
                        for B in itertools.combinations(range(m), cover_size - 1)
                    ):
                        continue
                    answer.append((m, radius, cover_size, coordinates,
                                   outside, operations, centre))
                    if len(answer) >= limit:
                        return answer
    return answer


def cube_clause(enc, obstruction):
    m, radius, cover_size, coordinates, outside, operations, centre = obstruction
    restriction = [FREE] * enc.d
    for index, coordinate in enumerate(outside):
        restriction[coordinate] = operations[index]
    clause = []
    for D in itertools.combinations(range(m), m - radius + 1):
        child = restriction.copy()
        for j in D:
            child[coordinates[j]] = (centre >> j) & 1
        clause.append(enc.y[tuple(child)])
    for B in itertools.combinations(range(m), cover_size - 1):
        child = restriction.copy()
        for j in B:
            child[coordinates[j]] = (centre >> j) & 1
        clause.append(-enc.y[tuple(child)])
    return tuple(clause)


def solve_with_timeout(solver, seconds):
    timer = threading.Timer(seconds, solver.interrupt)
    timer.daemon = True
    timer.start()
    try:
        result = solver.solve_limited(expect_interrupt=True)
    finally:
        timer.cancel()
        solver.clear_interrupt()
    return result


def write_cnf(enc, path):
    with path.open("w") as handle:
        handle.write(f"c d={enc.d} tau={enc.tau} "
                     f"w={','.join(map(str, enc.w))}\n")
        handle.write(f"p cnf {enc.var_count} {enc.clause_count}\n")
        for clause in enc.clauses:
            handle.write(" ".join(map(str, clause)) + " 0\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--d", type=int, required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--solve-timeout", type=int, default=1200)
    parser.add_argument("--strict-batch", type=int, default=4000)
    parser.add_argument("--cube-batch", type=int, default=4000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started = time.time()
    module = load_upstream()
    branches = enumerate_branches(module, args.d)
    if not (0 <= args.index < len(branches)):
        raise SystemExit(f"branch index {args.index} outside 0..{len(branches)-1}")
    branch = branches[args.index]
    args.output.mkdir(parents=True, exist_ok=True)
    tag = (f"d{branch['d']}_i{args.index:03d}_t{branch['tau']}_"
           f"s{branch['support_size']}_"
           + "".join(map(str, branch["w"])))

    enc, selectors, residual, basis = build_master(module, branch)
    solver = Cadical195(bootstrap_with=enc.clauses)
    original_add_clause = enc.add_clause

    def add_clause_both(clause):
        original_add_clause(list(clause))
        solver.add_clause(list(clause))

    enc.add_clause = add_clause_both
    seen = set()
    records = []
    final = "UNKNOWN"
    survivor = None

    for iteration in range(args.iterations):
        solve_started = time.time()
        satisfiable = solve_with_timeout(solver, args.solve_timeout)
        record = {
            "iteration": iteration,
            "solve_seconds": time.time() - solve_started,
            "variables": enc.var_count,
            "clauses": enc.clause_count,
        }
        if satisfiable is False:
            final = "UNSAT"
            record["status"] = final
            records.append(record)
            print(json.dumps(record, sort_keys=True), flush=True)
            break
        if satisfiable is not True:
            final = "TIMEOUT"
            record["status"] = final
            records.append(record)
            print(json.dumps(record, sort_keys=True), flush=True)
            break

        values = model_dictionary(solver.get_model())
        feasible = {point for point in range(1 << branch["d"])
                    if values.get(point + 1, False)}
        cuts = 0
        record["feasible_points"] = len(feasible)

        packing = find_exact_packing(
            feasible, branch["d"], branch["tau"], branch["w"])
        record["packing"] = None if packing is None else list(packing)
        if packing is not None:
            clause = tuple(sorted({-(point + 1) for point in packing}))
            key = ("packing", clause)
            if key not in seen:
                seen.add(key)
                enc.add_clause(list(clause))
                cuts += 1

        bits = support_assignment(values, basis["rows"])
        valid_support, coefficients, rank = exact_support_check(
            bits, branch["d"], branch["tau"], branch["w"])
        record["support_rank"] = rank
        record["coefficients"] = (None if coefficients is None
                                  else [str(value) for value in coefficients])
        if not valid_support:
            clause = block_support_assignment(basis["rows"], bits)
            key = ("support", clause)
            if key not in seen:
                seen.add(key)
                enc.add_clause(list(clause))
                cuts += 1
        else:
            for clause in coefficient_mate_clauses(
                    enc, basis["rows"], bits, coefficients):
                key = ("coefficient-mate", clause)
                if key not in seen:
                    seen.add(key)
                    enc.add_clause(list(clause))
                    cuts += 1

        strict = strict_violations(feasible, branch["d"], args.strict_batch)
        new_strict = 0
        for restriction in strict:
            key = ("strict", restriction)
            if key in seen:
                continue
            seen.add(key)
            enc.add_clause(list(strict_clause(enc, restriction)))
            new_strict += 1
            cuts += 1

        cube = cube_violations(feasible, branch["d"], args.cube_batch)
        new_cube = 0
        for obstruction in cube:
            clause = cube_clause(enc, obstruction)
            key = ("cube", tuple(sorted(clause)))
            if key in seen:
                continue
            seen.add(key)
            enc.add_clause(list(clause))
            new_cube += 1
            cuts += 1

        record.update({
            "strict_violations": len(strict),
            "new_strict_cuts": new_strict,
            "cube_violations": len(cube),
            "new_cube_cuts": new_cube,
            "new_cuts": cuts,
        })
        if cuts == 0:
            final = "SURVIVOR"
            survivor = {
                "feasible_points": sorted(feasible),
                "support": bits,
                "coefficients": [str(value) for value in coefficients],
            }
            record["status"] = final
            records.append(record)
            print(json.dumps(record, sort_keys=True), flush=True)
            break

        record["status"] = "CUT"
        records.append(record)
        print(json.dumps(record, sort_keys=True), flush=True)

    cnf_path = args.output / f"{tag}.cnf"
    write_cnf(enc, cnf_path)
    summary = {
        "schema": 1,
        "branch_index": args.index,
        "branch_count": len(branches),
        "branch": {
            "d": branch["d"],
            "tau": branch["tau"],
            "w": list(branch["w"]),
            "tight": branch["tight"],
            "support_size": branch["support_size"],
        },
        "star_selectors": len(selectors),
        "residual_holes": residual,
        "basis": {key: value for key, value in basis.items() if key != "rows"},
        "final": final,
        "survivor": survivor,
        "variables": enc.var_count,
        "clauses": enc.clause_count,
        "records": records,
        "seconds": time.time() - started,
        "cnf": cnf_path.name,
    }
    summary_path = args.output / f"{tag}.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "event": "final",
        "tag": tag,
        "final": final,
        "seconds": summary["seconds"],
        "variables": enc.var_count,
        "clauses": enc.clause_count,
    }, sort_keys=True), flush=True)
    solver.delete()

    if final == "SURVIVOR":
        raise SystemExit(10)
    if final == "UNSAT":
        raise SystemExit(20)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
