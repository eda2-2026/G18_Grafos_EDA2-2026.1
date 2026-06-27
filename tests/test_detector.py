import math

import pytest

from src.api.coingecko_client import MockClient
from src.arbitrage.detector import ArbitrageDetector, ArbOpportunity

MOCK_SYMBOLS = ["BTC", "ETH", "USDT", "BNB", "USD"]


class FakeClient:
    """Client mínimo (duck typing) que devolve uma RateMatrix fixa, sem rede."""

    def __init__(self, rates):
        self._rates = rates

    def get_rates(self, symbols):
        return self._rates


# Triângulo controlado: A->B->C->A com produto 2*2*0.3 = 1.2 (lucro 20%)
TRIANGLE = {"A": {"B": 2.0}, "B": {"C": 2.0}, "C": {"A": 0.3}}


def test_detects_artificial_cycle_in_mock():
    detector = ArbitrageDetector(MockClient())
    ops = detector.detect(MOCK_SYMBOLS)

    assert len(ops) >= 1
    for op in ops:
        assert op.profit_pct > 0
        assert op.cycle[0] == op.cycle[-1]  # ciclo fechado


def test_profit_calculated_correctly():
    detector = ArbitrageDetector(FakeClient(TRIANGLE))
    ops = detector.detect(["A", "B", "C"])

    assert len(ops) == 1
    op = ops[0]
    assert op.cycle == ["A", "B", "C", "A"]
    assert op.rates_used == [2.0, 2.0, 0.3]
    assert op.profit_pct == pytest.approx(20.0)


def test_deduplicates_rotations():
    # Bellman-Ford roda de A, B e C, achando rotações do mesmo ciclo dirigido.
    detector = ArbitrageDetector(FakeClient(TRIANGLE))
    ops = detector.detect(["A", "B", "C"])
    assert len(ops) == 1


def test_no_arbitrage_returns_empty():
    rates = {"A": {"B": 1.0}, "B": {"A": 1.0}}  # produto 1.0, sem lucro
    detector = ArbitrageDetector(FakeClient(rates))
    assert detector.detect(["A", "B"]) == []


def test_sorted_by_profit_desc():
    # Dois triângulos disjuntos com lucros diferentes.
    rates = {
        "A": {"B": 2.0}, "B": {"C": 2.0}, "C": {"A": 0.3},   # lucro 20%
        "X": {"Y": 2.0}, "Y": {"Z": 2.0}, "Z": {"X": 0.4},   # lucro 60%
    }
    detector = ArbitrageDetector(FakeClient(rates))
    ops = detector.detect(["A", "B", "C", "X", "Y", "Z"])

    assert len(ops) == 2
    assert ops[0].profit_pct == pytest.approx(60.0)
    assert ops[1].profit_pct == pytest.approx(20.0)
    assert ops[0].profit_pct >= ops[1].profit_pct


def test_rates_used_matches_original_rates():
    detector = ArbitrageDetector(FakeClient(TRIANGLE))
    op = detector.detect(["A", "B", "C"])[0]

    # São as taxas crus (todas > 0), não os pesos -log (que seriam negativos/positivos)
    assert all(r > 0 for r in op.rates_used)
    assert math.prod(op.rates_used) == pytest.approx(1.0 + op.profit_pct / 100)


def test_canonical_rotation_invariant():
    a = ArbitrageDetector._canonical(["B", "C", "A", "B"])
    b = ArbitrageDetector._canonical(["A", "B", "C", "A"])
    assert a == b == ("A", "B", "C")


def test_returns_arb_opportunity_type():
    op = ArbitrageDetector(FakeClient(TRIANGLE)).detect(["A", "B", "C"])[0]
    assert isinstance(op, ArbOpportunity)


def test_consistent_matrix_has_no_arbitrage():
    # Matriz triangulada por preço (A=60000, B=2000, C=1 em USD): toda taxa cruzada
    # é consistente -> nenhum ciclo lucrativo, mesmo com ruído de float.
    price = {"A": 60000.0, "B": 2000.0, "C": 1.0}
    rates = {
        a: {b: price[a] / price[b] for b in price if b != a}
        for a in price
    }
    ops = ArbitrageDetector(FakeClient(rates)).detect(["A", "B", "C"])
    assert ops == []
