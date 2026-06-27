"""Pipeline de detecção de arbitragem: taxas -> grafo -> Bellman-Ford -> oportunidades."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.arbitrage.graph_builder import build_graph
from src.graph.bellman_ford import bellman_ford

if TYPE_CHECKING:
    from src.api.coingecko_client import CoinGeckoClient, MockClient

# Abaixo deste lucro (%) é ruído numérico de float (matriz consistente), não arbitragem.
PROFIT_EPSILON = 1e-6


@dataclass
class ArbOpportunity:
    cycle: list[str]          # ex: ["BTC", "USDT", "ETH", "BTC"] (fechado)
    profit_pct: float         # lucro percentual (ex: 0.31 para 0.31%)
    rates_used: list[float]   # taxas originais de cada passo do ciclo


class ArbitrageDetector:
    """Orquestra o pipeline completo de detecção de arbitragem triangular."""

    def __init__(self, client: CoinGeckoClient | MockClient) -> None:
        self._client = client

    def detect(self, symbols: list[str]) -> list[ArbOpportunity]:
        """Busca taxas, constrói o grafo e roda Bellman-Ford a partir de cada nó,
        coletando ciclos lucrativos (deduplicados e ordenados por lucro decrescente)."""
        rates = self._client.get_rates(symbols)
        graph = build_graph(rates)
        edges = graph.get_edges()          # pesos -log (para o Bellman-Ford)
        nodes = graph.get_currencies()

        seen: set[tuple[str, ...]] = set()
        opportunities: list[ArbOpportunity] = []

        for source in nodes:
            result = bellman_ford(edges, source, nodes)
            if not result.negative_cycle:
                continue

            key = self._canonical(result.negative_cycle)
            if key in seen:
                continue
            seen.add(key)

            closed = list(key) + [key[0]]   # ciclo fechado normalizado
            rates_used = [rates[closed[i]][closed[i + 1]] for i in range(len(closed) - 1)]
            profit_pct = (math.prod(rates_used) - 1) * 100
            if profit_pct < PROFIT_EPSILON:
                continue  # ruído de float numa matriz consistente, não é lucro real
            opportunities.append(
                ArbOpportunity(cycle=closed, profit_pct=profit_pct, rates_used=rates_used)
            )

        opportunities.sort(key=lambda o: o.profit_pct, reverse=True)
        return opportunities

    @staticmethod
    def _canonical(cycle: list[str]) -> tuple[str, ...]:
        """Rotaciona o ciclo (sem o nó de fechamento) para começar no nó mínimo,
        preservando a direção. Rotações do mesmo ciclo dirigido -> mesma chave."""
        core = cycle[:-1]                  # remove o nó repetido de fechamento
        i = core.index(min(core))
        return tuple(core[i:] + core[:i])
