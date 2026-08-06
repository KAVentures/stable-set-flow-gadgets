#!/usr/bin/env python3
"""Systematically minimize the exact order-17 common-rainbow obstruction.

This program is theorem-discovery infrastructure.  It does not replace the direct core
certificate.  Each row records whether a deliberately weakened necessary-condition
formula is SAT, UNSAT, or UNKNOWN under a wall-clock limit.
"""
from __future__ import annotations

import argparse
import itertools
import json
import multiprocessing as mp
import os
import signal
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from pysat.card import CardEnc, EncType
from pysat.solvers import Cadical195

from core_search import ExactModel

Pair = Tuple[int, int]


class FilteredModel(ExactModel):
    def __init__(self, deletion_filter: Callable[[int, int], bool], **kwargs) -> None:
        self.deletion_filter = deletion_filter
        super().__init__(**kwargs)

    def _add_all_deletion_blocks(self) -> None:
        for (u, v), guard in sorted(self.edge_vars.items()):
            if not self.deletion_filter(u, v):
                continue
            remaining = [w for w in self.vertices if w not in (u, v)]
            for w in remaining:
                colours = [self._deletion_colour(u, v, w, c) for c in range(4)]
                self._guarded_onehot(guard, colours)
            self.add_clause([-guard, self._deletion_colour(u, v, remaining[0], 0)])
            for a, b in itertools.combinations(remaining, 2):
                edge_ab = self.edge(a, b)
                if edge_ab is None:
                    continue
                for c in range(4):
                    self.add_clause([
                        -guard,
                        -edge_ab,
                        -self._deletion_colour(u, v, a, c),
                        -self._deletion_colour(u, v, b, c),
                    ])
            if self.common_rainbow:
                self._add_common_rainbow_block(u, v, guard, remaining)


def add_exact_attachment_degrees(model: ExactModel, degrees: Sequence[int]) -> None:
    if len(degrees) != len(model.independent):
        raise ValueError("degree profile length does not equal |I|")
    for x, degree in zip(model.independent, degrees):
        lits = [model.edge(x, h) for h in model.h_vertices]
        clean = [lit for lit in lits if lit is not None]
        enc = CardEnc.equals(lits=clean, bound=degree, vpool=model.pool, encoding=EncType.seqcounter)
        for clause in enc.clauses:
            model.add_clause(clause)


def selected_filter(kind: str, selected: Set[int], independent: Set[int]) -> Callable[[int, int], bool]:
    if kind == "all":
        return lambda _u, _v: True
    if kind == "I-H":
        return lambda u, v: (u in independent) ^ (v in independent)
    if kind == "selected-I":
        return lambda u, v: ((u in selected) ^ (v in selected)) and ((u in independent) ^ (v in independent))
    if kind == "touch-selected":
        return lambda u, v: u in selected or v in selected
    if kind == "H-H":
        return lambda u, v: u not in independent and v not in independent
    raise ValueError(kind)


def solve_worker(payload: dict, queue: mp.Queue) -> None:
    try:
        independent = set(range(4))
        chosen = set(payload["selected"])
        filt = selected_filter(payload["kind"], chosen, independent)
        model = FilteredModel(
            deletion_filter=filt,
            n=17,
            independent=(0, 1, 2, 3),
            min_degree=8 if payload["degree"] else None,
            alpha_bound=4 if payload["alpha"] else None,
            attachment_bounds=(8, 11) if payload["attachments"] else None,
            accelerated=payload["accelerated"],
            common_rainbow=payload["rainbow"],
        )
        if payload.get("profile") is not None:
            add_exact_attachment_degrees(model, payload["profile"])
        started = time.time()
        with Cadical195(bootstrap_with=model.cnf.clauses) as solver:
            sat = solver.solve()
            model_data = solver.get_model() if sat else None
        queue.put({
            **payload,
            "result": "SAT" if sat else "UNSAT",
            "variables": model.pool.top,
            "clauses": len(model.cnf.clauses),
            "elapsed_seconds": time.time() - started,
            "edge_count": None if not sat else sum(1 for var in model.edge_vars.values() if var in set(x for x in model_data if x > 0)),
        })
    except BaseException as exc:
        queue.put({**payload, "result": "ERROR", "error": repr(exc)})


def timed_solve(payload: dict, timeout: float) -> dict:
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    proc = ctx.Process(target=solve_worker, args=(payload, queue))
    proc.start()
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(10)
        if proc.is_alive():
            proc.kill()
            proc.join()
        return {**payload, "result": "UNKNOWN", "reason": "timeout", "timeout_seconds": timeout}
    if queue.empty():
        return {**payload, "result": "ERROR", "error": f"worker exited {proc.exitcode} without result"}
    return queue.get()


def experiment_grid(include_profiles: bool) -> List[dict]:
    rows: List[dict] = []
    common = {
        "alpha": True,
        "degree": True,
        "attachments": True,
        "accelerated": False,
        "rainbow": True,
        "profile": None,
    }
    rows.append({**common, "name": "all-deletions", "kind": "all", "selected": []})
    rows.append({**common, "name": "I-H-deletions", "kind": "I-H", "selected": []})
    rows.append({**common, "name": "H-H-deletions", "kind": "H-H", "selected": []})
    for size in range(1, 5):
        for chosen in itertools.combinations(range(4), size):
            rows.append({
                **common,
                "name": "selected-I-" + "".join(map(str, chosen)),
                "kind": "selected-I",
                "selected": list(chosen),
            })
    # Group ablations around the strongest small selected-I experiments.
    for chosen in ((0,), (0, 1), (0, 1, 2)):
        for alpha, degree, attachments in itertools.product((False, True), repeat=3):
            if alpha and degree and attachments:
                continue
            rows.append({
                **common,
                "name": f"groups-I{''.join(map(str, chosen))}-a{int(alpha)}d{int(degree)}t{int(attachments)}",
                "kind": "selected-I",
                "selected": list(chosen),
                "alpha": alpha,
                "degree": degree,
                "attachments": attachments,
            })
    if include_profiles:
        for profile in itertools.combinations_with_replacement(range(8, 12), 4):
            # Store nonincreasing profiles to match the mathematical convention.
            p = tuple(sorted(profile, reverse=True))
            rows.append({
                **common,
                "name": "profile-" + "".join(map(str, p)),
                "kind": "selected-I",
                "selected": [0, 1],
                "profile": list(p),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("artifacts/tihany-ablation"))
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--profiles", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    output = args.out / "results.jsonl"
    completed: Dict[str, dict] = {}
    if output.exists():
        for line in output.read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                completed[item["name"]] = item

    grid = experiment_grid(args.profiles)
    summary: Dict[str, int] = {}
    for pos, payload in enumerate(grid, 1):
        if payload["name"] in completed:
            result = completed[payload["name"]]
        else:
            print(f"c experiment {pos}/{len(grid)} {payload['name']}", flush=True)
            result = timed_solve(payload, args.timeout)
            with output.open("a") as handle:
                handle.write(json.dumps(result, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        summary[result["result"]] = summary.get(result["result"], 0) + 1
        print(json.dumps(result, sort_keys=True), flush=True)
    (args.out / "summary.json").write_text(json.dumps({
        "experiments": len(grid),
        "counts": summary,
        "timeout_seconds": args.timeout,
    }, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
