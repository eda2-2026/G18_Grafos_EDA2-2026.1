import json
import math
from pathlib import Path

import pytest

from src.arbitrage.graph_builder import build_graph

MOCK_RATES_PATH = Path(__file__).resolve().parents[1] / "data" / "mock_rates.json"


def weight(graph, src, dst) -> float:
    neighbors = dict(graph.neighbors(src))
    assert dst in neighbors, f"aresta {src}->{dst} não encontrada"
    return neighbors[dst]


def test_rate_one_yields_zero_weight():
    g = build_graph({"A": {"B": 1.0}})
    assert weight(g, "A", "B") == pytest.approx(0.0)


def test_rate_above_one_negative_weight():
    g = build_graph({"A": {"B": 2.0}})
    w = weight(g, "A", "B")
    assert w == pytest.approx(-math.log(2.0))  # ~ -0.693
    assert w < 0


def test_rate_below_one_positive_weight():
    g = build_graph({"A": {"B": 0.5}})
    w = weight(g, "A", "B")
    assert w == pytest.approx(-math.log(0.5))  # ~ +0.693
    assert w > 0


def test_zero_rate_is_ignored():
    g = build_graph({"A": {"B": 0.0, "C": 1.0}})
    assert len(g.get_edges()) == 1
    assert "B" not in dict(g.neighbors("A"))
    assert "C" in dict(g.neighbors("A"))


def test_negative_rate_is_ignored():
    g = build_graph({"A": {"B": -1.5}})
    assert g.get_edges() == []


def test_self_loop_is_ignored():
    # Self-loop com taxa > 1 geraria peso negativo e falso positivo no Bellman-Ford
    g = build_graph({"A": {"A": 1.5, "B": 1.0}})
    assert len(g.get_edges()) == 1
    assert "B" in dict(g.neighbors("A"))
    assert "A" not in dict(g.neighbors("A"))


def test_build_from_mock_has_correct_edge_count():
    rates = json.loads(MOCK_RATES_PATH.read_text(encoding="utf-8"))["rates"]
    g = build_graph(rates)
    assert len(g.get_edges()) == 20
    assert len(g.get_currencies()) == 5
