#!/usr/bin/env python3
"""Probe orders 18 and above with exact necessary-condition SAT formulas.

This is theorem discovery, not a substitute for the direct core CEGAR certificate.  For
each possible independence number allowed by the established reductions, the script
constructs an accelerated formula with all edge-deletion colourings and KPT
common-rainbow witnesses.  UNSAT is a valid finite exclusion once independently
certified; SAT exposes a concrete relaxed ambient structure for further cuts.
"""
from __future__ import annotations

import argparse
import itertools
import json
import multiprocessing as mp
import os
import time
from pathlib import Path
from typing import List

from pysat.solvers import Cadical195

from core_search import ExactModel, graph6


def worker(payload: dict, queue: mp.Queue) -> None:
    try:
        n = payload["n"]
        alpha = payload["alpha"]
        h_order = n - alpha
        model = ExactModel(
            n=n,
            independent=tuple(range(alpha)),
            min_degree=8,
            alpha_bound=alpha,
            attachment_bounds=(8, h_order - 2),
            accelerated=payload["accelerated"],
            capacity=payload["capacity"],
            common_rainbow=payload["rainbow"],
        )
        started = time.time()
        with Cadical195(bootstrap_with=model.cnf.clauses) as solver:
            sat = solver.solve()
            raw = solver.get_model() if sat else None
        result = {
            **payload,
            "h_order": h_order,
            "result": "SAT" if sat else "UNSAT",
            "variables": model.pool.top,
            "clauses": len(model.cnf.clauses),
            "elapsed_seconds": time.time() - started,
        }
        if sat:
            adj = model.graph_from_model(raw)
            result.update({
                "graph6": graph6(adj),
                "degrees": sorted(row.bit_count() for row in adj),
                "edges": sum(row.bit_count() for row in adj) // 2,
                "attachment_degrees": [sum((adj[x] >> h) & 1 for h in model.h_vertices) for x in model.independent],
            })
        queue.put(result)
    except BaseException as exc:
        queue.put({**payload, "result": "ERROR", "error": repr(exc)})


def timed(payload: dict, seconds: float) -> dict:
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=worker, args=(payload, q))
    p.start()
    p.join(seconds)
    if p.is_alive():
        p.terminate(); p.join(10)
        if p.is_alive(): p.kill(); p.join()
        return {**payload, "result": "UNKNOWN", "reason": "timeout", "timeout_seconds": seconds}
    if q.empty():
        return {**payload, "result": "ERROR", "error": f"worker exited {p.exitcode} without a result"}
    return q.get()


def possible_alphas(n: int) -> List[int]:
    # n <= 4 alpha + 2 and |G-I| >= 12.
    lower = max(4, (n - 2 + 3) // 4)
    upper = n - 12
    return list(range(lower, upper + 1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders", nargs="+", type=int, default=[18, 19])
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--out", type=Path, default=Path("artifacts/tihany-order-sweep"))
    parser.add_argument("--capacity", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "results.jsonl"
    done = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                item = json.loads(line); done[(item["n"], item["alpha"])] = item

    experiments = []
    for n in args.orders:
        for alpha in possible_alphas(n):
            experiments.append({
                "n": n,
                "alpha": alpha,
                "accelerated": True,
                "rainbow": True,
                "capacity": bool(args.capacity),
            })
    summary = {}
    for pos, payload in enumerate(experiments, 1):
        key = (payload["n"], payload["alpha"])
        if key in done:
            result = done[key]
        else:
            print(f"c sweep {pos}/{len(experiments)} n={key[0]} alpha={key[1]}", flush=True)
            result = timed(payload, args.timeout)
            with path.open("a") as handle:
                handle.write(json.dumps(result, sort_keys=True) + "\n")
                handle.flush(); os.fsync(handle.fileno())
        summary[result["result"]] = summary.get(result["result"], 0) + 1
        print(json.dumps(result, sort_keys=True), flush=True)
    (args.out / "summary.json").write_text(json.dumps({
        "counts": summary,
        "experiments": len(experiments),
        "orders": args.orders,
        "timeout_seconds": args.timeout,
    }, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
