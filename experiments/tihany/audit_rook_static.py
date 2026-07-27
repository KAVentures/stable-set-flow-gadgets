#!/usr/bin/env python3
"""Reconstruct and audit a static residual-rook DIMACS formula."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_static import read_dimacs
from core_search import formula_sha256
from rook_order17_cegar import build_model, reconstruct_cut


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", type=int, choices=(0, 2, 3, 4, 6), required=True)
    parser.add_argument("--common-rainbow", action="store_true")
    parser.add_argument("--cuts", type=Path, required=True)
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    model = build_model(args.pattern, args.common_rainbow)
    unique = []
    seen = set()
    records = 0
    for line_no, line in enumerate(args.cuts.read_text().splitlines(), 1):
        if not line.strip():
            continue
        records += 1
        record = json.loads(line)
        clause = reconstruct_cut(model, record)
        if clause not in seen:
            seen.add(clause)
            unique.append(list(clause))

    nvars, actual = read_dimacs(args.static)
    expected = [list(c) for c in model.cnf.clauses] + unique
    if nvars != model.pool.top:
        raise ValueError(f"variable count {nvars} != {model.pool.top}")
    if actual != expected:
        mismatch = next(
            (i for i, (a, b) in enumerate(zip(actual, expected), 1) if a != b),
            min(len(actual), len(expected)) + 1,
        )
        raise ValueError(
            f"formula mismatch at clause {mismatch}; actual={len(actual)} expected={len(expected)}"
        )
    result = {
        "status": "AUDITED",
        "pattern": args.pattern,
        "common_rainbow": args.common_rainbow,
        "records": records,
        "unique_cuts": len(unique),
        "variables": nvars,
        "clauses": len(actual),
        "base_clauses": len(model.cnf.clauses),
        "static_cnf_sha256": formula_sha256(args.static),
        "cuts_sha256": formula_sha256(args.cuts),
    }
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
