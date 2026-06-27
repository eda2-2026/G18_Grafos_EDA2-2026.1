import math


class CurrencyGraph:
    def __init__(self) -> None:
        self._adj: dict[str, list[tuple[str, float]]] = {}

    def add_currency(self, symbol: str) -> None:
        if symbol not in self._adj:
            self._adj[symbol] = []

    def add_rate(self, src: str, dst: str, rate: float) -> None:
        if rate <= 0:
            raise ValueError(f"Taxa deve ser positiva, recebeu {rate}")
        self.add_currency(src)
        self.add_currency(dst)
        self._adj[src].append((dst, rate))

    def get_currencies(self) -> list[str]:
        return list(self._adj.keys())

    def get_edges(self) -> list[tuple[str, str, float]]:
        return [(src, dst, w) for src, neighbors in self._adj.items() for dst, w in neighbors]

    def neighbors(self, node: str) -> list[tuple[str, float]]:
        return list(self._adj.get(node, []))

    def transform_weights(self) -> None:
        for src in self._adj:
            self._adj[src] = [(dst, -math.log(w)) for dst, w in self._adj[src]]
