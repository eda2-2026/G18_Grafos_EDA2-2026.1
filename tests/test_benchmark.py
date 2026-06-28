from src.benchmark.runner import (
    BenchResult,
    _build_synthetic_graph,
    _write_markdown,
    run_benchmark,
)


def test_synthetic_graph_has_expected_size():
    g = _build_synthetic_graph(5)
    assert len(g.get_currencies()) == 5
    # grafo denso dirigido V*(V-1) = 20, mais 3 arestas do ciclo plantado (duplicadas)
    assert len(g.get_edges()) == 5 * 4 + 3


def test_synthetic_graph_has_negative_cycle():
    # ciclo C00->C01->C02->C00 plantado com produto > 1 -> negativo após -log
    from src.graph.bellman_ford import bellman_ford

    g = _build_synthetic_graph(5)
    result = bellman_ford(g.get_edges(), g.get_currencies()[0], g.get_currencies())
    assert result.negative_cycle is not None


def test_run_benchmark_returns_four_sizes():
    results = run_benchmark()
    assert len(results) == 4
    assert [r.nodes for r in results] == [5, 10, 20, 50]
    for r in results:
        assert isinstance(r, BenchResult)
        # as duas implementações encontram o ciclo plantado
        assert r.own_cycles == 1
        assert r.nx_cycles == 1


def test_write_markdown_creates_table(tmp_path):
    results = [
        BenchResult("XS", 5, 23, 0.01, 0.02, 0.5, 1.7, 1, 1),
        BenchResult("S", 10, 93, 0.10, 0.03, 0.8, 3.2, 1, 1),
    ]
    out = tmp_path / "bench.md"
    _write_markdown(results, out)

    content = out.read_text(encoding="utf-8")
    assert "| Tamanho |" in content
    assert "| XS | 5 | 23 |" in content
    assert "| S | 10 | 93 |" in content
