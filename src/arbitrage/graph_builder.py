"""Tradução da RateMatrix da API para o grafo ponderado com pesos -log(taxa)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.graph.currency_graph import CurrencyGraph

if TYPE_CHECKING:
    from src.api.coingecko_client import RateMatrix


def build_graph(rates: RateMatrix) -> CurrencyGraph:
    """Constrói um CurrencyGraph a partir da matriz de taxas e aplica os pesos
    logarítmicos. Pares com taxa <= 0 são ignorados (não inseridos).

    Retorna o grafo já transformado (peso = -log(taxa)), pronto para o Bellman-Ford.
    """
    graph = CurrencyGraph()
    for src, row in rates.items():
        for dst, rate in row.items():
            if rate > 0:
                graph.add_rate(src, dst, rate)
    graph.transform_weights()
    return graph
