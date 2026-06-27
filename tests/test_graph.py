import math
import pytest
from src.graph.currency_graph import CurrencyGraph


def make_graph() -> CurrencyGraph:
    g = CurrencyGraph()
    g.add_rate("BTC", "ETH", 15.8)
    g.add_rate("ETH", "USDT", 3500.0)
    g.add_rate("USDT", "BTC", 0.0000149)
    return g


def test_add_currency_creates_node():
    g = CurrencyGraph()
    g.add_currency("BTC")
    assert "BTC" in g.get_currencies()


def test_add_rate_creates_both_nodes():
    g = CurrencyGraph()
    g.add_rate("BTC", "ETH", 15.8)
    assert "BTC" in g.get_currencies()
    assert "ETH" in g.get_currencies()


def test_neighbors():
    g = make_graph()
    neighbors = dict(g.neighbors("BTC"))
    assert "ETH" in neighbors
    assert neighbors["ETH"] == pytest.approx(15.8)


def test_get_edges_count():
    g = make_graph()
    assert len(g.get_edges()) == 3


def test_transform_weights():
    g = CurrencyGraph()
    g.add_rate("A", "B", 2.0)
    g.transform_weights()
    _, w = g.neighbors("A")[0]
    assert w == pytest.approx(-math.log(2.0))


def test_transform_weight_one():
    g = CurrencyGraph()
    g.add_rate("A", "B", 1.0)
    g.transform_weights()
    _, w = g.neighbors("A")[0]
    assert w == pytest.approx(0.0)


def test_invalid_rate_raises():
    g = CurrencyGraph()
    with pytest.raises(ValueError):
        g.add_rate("A", "B", 0.0)
    with pytest.raises(ValueError):
        g.add_rate("A", "B", -1.5)


def test_empty_graph():
    g = CurrencyGraph()
    assert g.get_currencies() == []
    assert g.get_edges() == []
    assert g.neighbors("X") == []


def test_duplicate_currency_idempotent():
    g = CurrencyGraph()
    g.add_currency("BTC")
    g.add_currency("BTC")
    assert g.get_currencies().count("BTC") == 1
