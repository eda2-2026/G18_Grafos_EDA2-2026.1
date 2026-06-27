import json
import math
from pathlib import Path

import pytest

from src.graph.bellman_ford import BFResult, bellman_ford
from src.graph.currency_graph import CurrencyGraph


def _mock_graph() -> CurrencyGraph:
    path = Path(__file__).parent.parent / "data" / "mock_rates.json"
    data = json.loads(path.read_text())
    g = CurrencyGraph()
    for src, targets in data["rates"].items():
        for dst, rate in targets.items():
            g.add_rate(src, dst, rate)
    return g


class TestBellmanFordBasic:
    def test_no_negative_cycle(self) -> None:
        # Grafo simples sem ciclo negativo
        edges = [("A", "B", 1.0), ("B", "C", 2.0), ("A", "C", 5.0)]
        nodes = ["A", "B", "C"]
        result = bellman_ford(edges, "A", nodes)
        assert result.negative_cycle is None
        assert result.distances["A"] == 0.0
        assert result.distances["B"] == pytest.approx(1.0)
        assert result.distances["C"] == pytest.approx(3.0)

    def test_predecessors_correct(self) -> None:
        edges = [("A", "B", 1.0), ("B", "C", 2.0)]
        nodes = ["A", "B", "C"]
        result = bellman_ford(edges, "A", nodes)
        assert result.predecessors["A"] is None
        assert result.predecessors["B"] == "A"
        assert result.predecessors["C"] == "B"

    def test_unreachable_node_stays_inf(self) -> None:
        edges = [("A", "B", 1.0)]
        nodes = ["A", "B", "C"]
        result = bellman_ford(edges, "A", nodes)
        assert result.distances["C"] == math.inf

    def test_detects_negative_cycle(self) -> None:
        # Ciclo negativo simples: A→B→C→A com soma -1
        edges = [("A", "B", 1.0), ("B", "C", 1.0), ("C", "A", -3.0)]
        nodes = ["A", "B", "C"]
        result = bellman_ford(edges, "A", nodes)
        assert result.negative_cycle is not None
        assert len(result.negative_cycle) >= 2

    def test_negative_cycle_nodes_are_valid(self) -> None:
        edges = [("A", "B", 1.0), ("B", "C", 1.0), ("C", "A", -3.0)]
        nodes = ["A", "B", "C"]
        result = bellman_ford(edges, "A", nodes)
        assert result.negative_cycle is not None
        for node in result.negative_cycle:
            assert node in nodes

    def test_negative_cycle_forms_valid_path(self) -> None:
        edges = [("A", "B", 1.0), ("B", "C", 1.0), ("C", "A", -3.0)]
        nodes = ["A", "B", "C"]
        edge_set = {(u, v) for u, v, _ in edges}
        result = bellman_ford(edges, "A", nodes)
        assert result.negative_cycle is not None
        cycle = result.negative_cycle
        for i in range(len(cycle) - 1):
            assert (cycle[i], cycle[i + 1]) in edge_set

    def test_returns_bf_result_type(self) -> None:
        edges = [("X", "Y", 0.5)]
        result = bellman_ford(edges, "X", ["X", "Y"])
        assert isinstance(result, BFResult)


class TestBellmanFordMockRates:
    def test_finds_arbitrage_in_mock_data(self) -> None:
        g = _mock_graph()
        g.transform_weights()
        edges = g.get_edges()
        nodes = g.get_currencies()
        result = bellman_ford(edges, nodes[0], nodes)
        assert result.negative_cycle is not None, (
            "mock_rates.json deve conter ao menos uma oportunidade de arbitragem"
        )

    def test_cycle_is_closed(self) -> None:
        g = _mock_graph()
        g.transform_weights()
        edges = g.get_edges()
        nodes = g.get_currencies()
        result = bellman_ford(edges, nodes[0], nodes)
        if result.negative_cycle is None:
            pytest.skip("Nenhum ciclo encontrado — verifique mock_rates.json")
        cycle = result.negative_cycle
        # Primeiro e último nó devem ser iguais (ciclo fechado)
        assert cycle[0] == cycle[-1]

    def test_cycle_has_negative_weight_sum(self) -> None:
        g = _mock_graph()
        g.transform_weights()
        edges = g.get_edges()
        nodes = g.get_currencies()
        result = bellman_ford(edges, nodes[0], nodes)
        if result.negative_cycle is None:
            pytest.skip("Nenhum ciclo encontrado")

        edge_weights = {(u, v): w for u, v, w in edges}
        cycle = result.negative_cycle
        total = sum(edge_weights[(cycle[i], cycle[i + 1])] for i in range(len(cycle) - 1))
        assert total < 0, f"Soma dos pesos do ciclo deve ser negativa, obteve {total}"
