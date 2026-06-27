import math
from dataclasses import dataclass


@dataclass
class BFResult:
    distances: dict[str, float]
    predecessors: dict[str, str | None]
    negative_cycle: list[str] | None


def bellman_ford(edges: list[tuple[str, str, float]], source: str, nodes: list[str]) -> BFResult:
    dist: dict[str, float] = {n: math.inf for n in nodes}
    pred: dict[str, str | None] = {n: None for n in nodes}
    dist[source] = 0.0

    for _ in range(len(nodes) - 1):
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                pred[v] = u

    cycle_node: str | None = None
    for u, v, w in edges:
        if dist[u] + w < dist[v]:
            cycle_node = v
            break

    if cycle_node is None:
        return BFResult(distances=dist, predecessors=pred, negative_cycle=None)

    # Avança |V| vezes para garantir estar dentro do ciclo
    node = cycle_node
    for _ in range(len(nodes)):
        node = pred[node]  # type: ignore[assignment]

    # Reconstrói o ciclo a partir de um nó garantidamente dentro dele
    cycle: list[str] = []
    visited: set[str] = set()
    current = node
    while current not in visited:
        visited.add(current)
        cycle.append(current)
        current = pred[current]  # type: ignore[assignment]

    # Fecha o ciclo e inverte para ordem de travessia
    cycle.append(current)
    start = cycle.index(current)
    cycle = cycle[start:]
    cycle.reverse()

    return BFResult(distances=dist, predecessors=pred, negative_cycle=cycle)
