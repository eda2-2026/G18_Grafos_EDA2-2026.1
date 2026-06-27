"""Benchmark: Bellman-Ford próprio vs NetworkX.

Execução: python -m src.benchmark.runner
"""

from __future__ import annotations

import math
import random
import timeit
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from rich.table import Table
from rich.console import Console

from src.graph.bellman_ford import bellman_ford
from src.graph.currency_graph import CurrencyGraph


@dataclass
class BenchResult:
    label: str
    nodes: int
    edges: int
    own_time_ms: float
    nx_time_ms: float
    own_mem_kb: float
    nx_mem_kb: float
    own_cycles: int
    nx_cycles: int


def _build_synthetic_graph(n_nodes: int, seed: int = 42) -> CurrencyGraph:
    rng = random.Random(seed)
    symbols = [f"C{i:02d}" for i in range(n_nodes)]
    g = CurrencyGraph()
    for src in symbols:
        for dst in symbols:
            if src != dst:
                g.add_rate(src, dst, rng.uniform(0.5, 2.0))

    # Planta ciclo negativo: C00 → C01 → C02 → C00 com produto > 1 antes do log
    g.add_rate("C00", "C01", 1.5)
    g.add_rate("C01", "C02", 1.5)
    g.add_rate("C02", "C00", 1.5)

    g.transform_weights()
    return g


def _count_cycles_nx(G: nx.DiGraph, source: str) -> int:
    try:
        nx.find_negative_cycle(G, source)
        return 1
    except nx.NetworkXError:
        return 0


def _run_own(g: CurrencyGraph) -> tuple[float, float, int]:
    edges = g.get_edges()
    nodes = g.get_currencies()
    source = nodes[0]

    def run():
        bellman_ford(edges, source, nodes)

    time_ms = timeit.timeit(run, number=10) / 10 * 1000

    tracemalloc.start()
    result = bellman_ford(edges, source, nodes)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    cycles = 1 if result.negative_cycle is not None else 0
    return time_ms, peak / 1024, cycles


def _run_nx(g: CurrencyGraph) -> tuple[float, float, int]:
    G = nx.DiGraph()
    for u, v, w in g.get_edges():
        G.add_edge(u, v, weight=w)
    source = g.get_currencies()[0]

    def run():
        _count_cycles_nx(G, source)

    time_ms = timeit.timeit(run, number=10) / 10 * 1000

    tracemalloc.start()
    cycles = _count_cycles_nx(G, source)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return time_ms, peak / 1024, cycles


SIZES = [
    ("XS", 5),
    ("S", 10),
    ("M", 20),
    ("L", 50),
]


def run_benchmark() -> list[BenchResult]:
    results = []
    for label, n in SIZES:
        g = _build_synthetic_graph(n)
        edges = len(g.get_edges())

        own_time, own_mem, own_cyc = _run_own(g)
        nx_time, nx_mem, nx_cyc = _run_nx(g)

        results.append(BenchResult(
            label=label,
            nodes=n,
            edges=edges,
            own_time_ms=own_time,
            nx_time_ms=nx_time,
            own_mem_kb=own_mem,
            nx_mem_kb=nx_mem,
            own_cycles=own_cyc,
            nx_cycles=nx_cyc,
        ))
    return results


def _print_table(results: list[BenchResult]) -> None:
    console = Console()
    table = Table(title="Bellman-Ford: Próprio vs NetworkX", show_lines=True)

    table.add_column("Tamanho", style="bold")
    table.add_column("Nós", justify="right")
    table.add_column("Arestas", justify="right")
    table.add_column("Tempo (próprio) ms", justify="right")
    table.add_column("Tempo (NX) ms", justify="right")
    table.add_column("Mem (próprio) KB", justify="right")
    table.add_column("Mem (NX) KB", justify="right")
    table.add_column("Ciclos (próprio)", justify="right")
    table.add_column("Ciclos (NX)", justify="right")

    for r in results:
        table.add_row(
            r.label,
            str(r.nodes),
            str(r.edges),
            f"{r.own_time_ms:.3f}",
            f"{r.nx_time_ms:.3f}",
            f"{r.own_mem_kb:.1f}",
            f"{r.nx_mem_kb:.1f}",
            str(r.own_cycles),
            str(r.nx_cycles),
        )

    console.print(table)


def _write_markdown(results: list[BenchResult], path: Path) -> None:
    lines = [
        "# Benchmark Results\n",
        "Bellman-Ford próprio vs NetworkX — média de 10 execuções.\n",
        "| Tamanho | Nós | Arestas | Tempo próprio (ms) | Tempo NX (ms) | Mem próprio (KB) | Mem NX (KB) | Ciclos próprio | Ciclos NX |",
        "|---------|-----|---------|--------------------|---------------|-----------------|-------------|----------------|-----------|",
    ]
    for r in results:
        lines.append(
            f"| {r.label} | {r.nodes} | {r.edges} | {r.own_time_ms:.3f} | {r.nx_time_ms:.3f} "
            f"| {r.own_mem_kb:.1f} | {r.nx_mem_kb:.1f} | {r.own_cycles} | {r.nx_cycles} |"
        )
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    results = run_benchmark()
    _print_table(results)
    out = Path(__file__).parent.parent.parent / "docs" / "benchmark_results.md"
    out.parent.mkdir(exist_ok=True)
    _write_markdown(results, out)
    print(f"\nResultados salvos em {out}")
