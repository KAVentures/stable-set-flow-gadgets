#!/usr/bin/env python3
"""Audit a Tihany CEGAR cut ledger and its emitted static DIMACS formula.

A DRAT/LRAT certificate only proves the DIMACS formula UNSAT. This auditor checks
that every appended clause is a mathematically valid colouring-partition cut and
that the static DIMACS file is exactly the deterministic base CNF plus those audited
cuts. It must pass before proof certification is accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from core_search import ExactModel, formula_sha256


def canonical_classes(raw: object, expected: Sequence[int], max_colours: int) -> List[List[int]]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("classes must be a nonempty list")
    classes: List[List[int]] = []
    seen: set[int] = set()
    for group in raw:
        if not isinstance(group, list) or not group:
            raise ValueError("every colour class must be a nonempty list")
        clean = sorted(int(v) for v in group)
        if len(clean) != len(set(clean)):
            raise ValueError("duplicate vertex inside a colour class")
        if seen.intersection(clean):
            raise ValueError("vertex appears in more than one colour class")
        seen.update(clean)
        classes.append(clean)
    if len(classes) > max_colours:
        raise ValueError(f"partition uses {len(classes)} colours, limit is {max_colours}")
    if seen != set(expected):
        missing = sorted(set(expected) - seen)
        extra = sorted(seen - set(expected))
        raise ValueError(f"partition mismatch: missing={missing}, extra={extra}")
    return sorted(classes, key=lambda group: (group[0], len(group), group))


def clause_from_classes(model: ExactModel, classes: Sequence[Sequence[int]]) -> Tuple[int, ...]:
    clause: set[int] = set()
    for group in classes:
        for i, u in enumerate(group):
            for v in group[i + 1 :]:
                var = model.edge(u, v)
                if var is not None:
                    clause.add(var)
    if not clause:
        raise ValueError("colouring cut contains no graph-edge literal")
    return tuple(sorted(clause))


def clause_hash(clause: Sequence[int]) -> str:
    return hashlib.sha256(" ".join(map(str, clause)).encode()).hexdigest()


def read_records(path: Path) -> List[dict]:
    records: List[dict] = []
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_no}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"line {line_no} is not an object")
        record["_line"] = line_no
        records.append(record)
    return records


def read_dimacs(path: Path) -> Tuple[int, List[List[int]]]:
    nvars = None
    expected = None
    clauses: List[List[int]] = []
    pending: List[int] = []
    for line_no, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("p"):
            if nvars is not None:
                raise ValueError("multiple DIMACS headers")
            parts = line.split()
            if len(parts) != 4 or parts[:2] != ["p", "cnf"]:
                raise ValueError(f"bad DIMACS header on line {line_no}")
            nvars = int(parts[2])
            expected = int(parts[3])
            continue
        for token in line.split():
            lit = int(token)
            if lit == 0:
                clauses.append(pending)
                pending = []
            else:
                pending.append(lit)
    if pending:
        raise ValueError("unterminated DIMACS clause")
    if nvars is None or expected is None:
        raise ValueError("missing DIMACS header")
    if expected != len(clauses):
        raise ValueError(f"header says {expected} clauses, parsed {len(clauses)}")
    return nvars, clauses


def build_model(mode: str, profile: Tuple[int, int, int, int] | None) -> ExactModel:
    if mode == "core":
        return ExactModel(accelerated=False, common_rainbow=False)
    if mode == "accelerated":
        return ExactModel(accelerated=True, common_rainbow=True)
    if mode == "ultracore":
        return ExactModel(
            n=17,
            independent=(0, 1),
            min_degree=8,
            alpha_bound=None,
            attachment_bounds=None,
            accelerated=False,
            common_rainbow=False,
        )
    if mode == "profile":
        if profile is None:
            raise ValueError("--profile is required in profile mode")
        from profile_core import add_profile

        model = ExactModel(
            accelerated=False,
            common_rainbow=False,
            min_degree=8,
            alpha_bound=4,
            attachment_bounds=(8, 11),
        )
        add_profile(model, profile)
        return model
    raise ValueError(mode)


def audit(model: ExactModel, mode: str, cuts_path: Path, static_path: Path) -> dict:
    records = read_records(cuts_path)
    audited: List[List[int]] = []
    known: set[Tuple[int, ...]] = set()
    kinds: Dict[str, int] = {}
    for record in records:
        line_no = record.pop("_line")
        kind = record.get("kind")
        if kind == "G_not_5_colourable":
            expected = model.vertices
            max_colours = 5
        elif kind == "H_not_4_colourable" and mode == "accelerated":
            expected = model.h_vertices
            max_colours = 4
        else:
            raise ValueError(f"line {line_no}: invalid cut kind {kind!r} for mode {mode}")
        classes = canonical_classes(record.get("classes"), expected, max_colours)
        clause = clause_from_classes(model, classes)
        stored_clause = tuple(sorted(int(x) for x in record.get("clause", [])))
        if clause != stored_clause:
            raise ValueError(f"line {line_no}: stored clause does not match partition")
        if record.get("sha256") != clause_hash(clause):
            raise ValueError(f"line {line_no}: clause hash mismatch")
        if any(lit <= 0 or lit > model.pool.top for lit in clause):
            raise ValueError(f"line {line_no}: clause literal out of range")
        kinds[kind] = kinds.get(kind, 0) + 1
        if clause not in known:
            known.add(clause)
            audited.append(list(clause))

    nvars, static_clauses = read_dimacs(static_path)
    expected_clauses = [list(c) for c in model.cnf.clauses] + audited
    if nvars != model.pool.top:
        raise ValueError(f"DIMACS variable count {nvars} != generator count {model.pool.top}")
    if static_clauses != expected_clauses:
        mismatch = next(
            (i for i, (a, b) in enumerate(zip(static_clauses, expected_clauses), 1) if a != b),
            min(len(static_clauses), len(expected_clauses)) + 1,
        )
        raise ValueError(
            f"static formula differs from audited reconstruction at clause {mismatch}; "
            f"static={len(static_clauses)}, expected={len(expected_clauses)}"
        )
    return {
        "status": "AUDITED",
        "mode": mode,
        "records": len(records),
        "unique_cuts": len(audited),
        "cut_kinds": kinds,
        "variables": nvars,
        "clauses": len(static_clauses),
        "base_clauses": len(model.cnf.clauses),
        "static_cnf_sha256": formula_sha256(static_path),
        "cuts_sha256": formula_sha256(cuts_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("core", "accelerated", "ultracore", "profile"), required=True)
    parser.add_argument("--cuts", type=Path, required=True)
    parser.add_argument("--static", type=Path, required=True)
    parser.add_argument("--profile", help="four comma-separated attachment degrees")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    profile = tuple(map(int, args.profile.split(","))) if args.profile else None
    if profile is not None and len(profile) != 4:
        raise ValueError("profile must contain four degrees")
    result = audit(build_model(args.mode, profile), args.mode, args.cuts, args.static)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
