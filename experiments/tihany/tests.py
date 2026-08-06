#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
import tempfile
from pathlib import Path

import networkx as nx
from pysat.solvers import Cadical195

from audit_static import audit
from core_search import (
    ExactModel,
    cut_record,
    dsatur_k_colouring,
    maximum_independent_set_size,
    plain_k_colouring,
    verify_colouring,
    write_dimacs,
)


def adjacency(n: int, edges):
    adj = [0] * n
    for u, v in edges:
        adj[u] |= 1 << v
        adj[v] |= 1 << u
    return adj


def fixed_formula(model: ExactModel, adj):
    clauses = [list(c) for c in model.cnf.clauses]
    for (u, v), var in model.edge_vars.items():
        clauses.append([var if (adj[u] >> v) & 1 else -var])
    return clauses


def test_colouring_checkers() -> None:
    k6 = adjacency(6, itertools.combinations(range(6), 2))
    assert dsatur_k_colouring(k6, range(6), 5) is None
    assert plain_k_colouring(k6, range(6), 5) is None
    c1 = dsatur_k_colouring(k6, range(6), 6)
    c2 = plain_k_colouring(k6, range(6), 6)
    assert c1 is not None and verify_colouring(k6, c1, range(6), 6)
    assert c2 is not None and verify_colouring(k6, c2, range(6), 6)
    assert maximum_independent_set_size(k6) == 1


def test_generic_deletion_module_on_k6() -> None:
    model = ExactModel(
        n=6,
        independent=(),
        min_degree=None,
        alpha_bound=None,
        attachment_bounds=None,
    )
    k6 = adjacency(6, itertools.combinations(range(6), 2))
    with Cadical195(bootstrap_with=fixed_formula(model, k6)) as solver:
        assert solver.solve(), "the generic deletion-colouring module must accept fixed K6"


def test_common_rainbow_module_on_k6() -> None:
    model = ExactModel(
        n=6,
        independent=(),
        min_degree=None,
        alpha_bound=None,
        attachment_bounds=None,
        common_rainbow=True,
    )
    k6 = adjacency(6, itertools.combinations(range(6), 2))
    with Cadical195(bootstrap_with=fixed_formula(model, k6)) as solver:
        assert solver.solve(), "the KPT common-rainbow module must accept fixed K6"


def test_valid_five_colour_cut_eliminates_fixed_k6_minus_edge() -> None:
    edges = [e for e in itertools.combinations(range(6), 2) if e != (0, 1)]
    graph = adjacency(6, edges)
    model = ExactModel(
        n=6,
        independent=(),
        min_degree=None,
        alpha_bound=None,
        attachment_bounds=None,
    )
    colouring = dsatur_k_colouring(graph, range(6), 5)
    assert colouring is not None
    assert verify_colouring(graph, colouring, range(6), 5)
    cut = model.edge_cut_from_colouring(colouring)
    edge_by_var = {var: pair for pair, var in model.edge_vars.items()}
    assert all(not ((graph[edge_by_var[var][0]] >> edge_by_var[var][1]) & 1) for var in cut)
    clauses = fixed_formula(model, graph) + [list(cut)]
    with Cadical195(bootstrap_with=clauses) as solver:
        assert not solver.solve(), "a valid colouring cut must eliminate its fixed source graph"


def test_static_cut_ledger_auditor() -> None:
    edges = [e for e in itertools.combinations(range(6), 2) if e != (0, 1)]
    graph = adjacency(6, edges)
    model = ExactModel(
        n=6,
        independent=(),
        min_degree=None,
        alpha_bound=None,
        attachment_bounds=None,
    )
    colouring = dsatur_k_colouring(graph, range(6), 5)
    assert colouring is not None
    clause = model.edge_cut_from_colouring(colouring)
    record = cut_record("G_not_5_colourable", colouring, clause)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cuts = root / "cuts.jsonl"
        static = root / "static.cnf"
        cuts.write_text(json.dumps(record, sort_keys=True) + "\n")
        write_dimacs(static, [*model.cnf.clauses, list(clause)], model.pool.top)
        result = audit(model, "core", cuts, static)
        assert result["status"] == "AUDITED"
        assert result["unique_cuts"] == 1

        bad = dict(record)
        bad["clause"] = []
        cuts.write_text(json.dumps(bad, sort_keys=True) + "\n")
        try:
            audit(model, "core", cuts, static)
        except ValueError:
            pass
        else:
            raise AssertionError("tampered cut ledger was accepted")


def exact_chromatic_at_most(adj, k):
    return dsatur_k_colouring(adj, range(len(adj)), k) is not None


def double_critical_six(adj) -> bool:
    n = len(adj)
    if exact_chromatic_at_most(adj, 5) or not exact_chromatic_at_most(adj, 6):
        return False
    for u, v in itertools.combinations(range(n), 2):
        if not ((adj[u] >> v) & 1):
            continue
        remaining = [w for w in range(n) if w not in (u, v)]
        if dsatur_k_colouring(adj, remaining, 4) is None:
            return False
    return True


def test_graph_atlas_through_seven_vertices() -> None:
    survivors = []
    for graph in nx.graph_atlas_g():
        n = graph.number_of_nodes()
        if n == 0 or n > 7 or not nx.is_connected(graph):
            continue
        edges = list(graph.edges())
        adj = adjacency(n, edges)
        if double_critical_six(adj):
            survivors.append((n, graph.number_of_edges(), nx.to_graph6_bytes(graph, header=False).decode().strip()))
    assert len(survivors) == 1, survivors
    assert survivors[0][0:2] == (6, 15), survivors


def test_order17_core_builds_and_has_expected_primary_variables() -> None:
    model = ExactModel()
    assert len(model.edge_vars) == 130  # C(17,2)-C(4,2)
    assert all(model.edge(u, v) is None for u, v in itertools.combinations(range(4), 2))
    assert len(model.cnf.clauses) > 0


def main() -> None:
    tests = [
        test_colouring_checkers,
        test_generic_deletion_module_on_k6,
        test_common_rainbow_module_on_k6,
        test_valid_five_colour_cut_eliminates_fixed_k6_minus_edge,
        test_static_cut_ledger_auditor,
        test_graph_atlas_through_seven_vertices,
        test_order17_core_builds_and_has_expected_primary_variables,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS all {len(tests)} tests")


if __name__ == "__main__":
    main()
