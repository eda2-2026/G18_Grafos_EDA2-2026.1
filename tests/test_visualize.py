from src.api.coingecko_client import MockClient
from src.arbitrage.detector import ArbitrageDetector
from src.visualize import CYCLE_COLOR, build_graph_html

MOCK_SYMBOLS = ["BTC", "ETH", "USDT", "BNB", "USD"]


def _mock_rates_and_ops():
    client = MockClient()
    rates = client.get_rates(MOCK_SYMBOLS)
    ops = ArbitrageDetector(client).detect(MOCK_SYMBOLS)
    return rates, ops


def test_build_graph_html_creates_file(tmp_path):
    rates, ops = _mock_rates_and_ops()
    out = build_graph_html(rates, ops, tmp_path / "g.html", open_browser=False)

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    for symbol in MOCK_SYMBOLS:
        assert symbol in content


def test_table_shown_beside_graph(tmp_path):
    rates, ops = _mock_rates_and_ops()
    assert ops, "mock deve conter ao menos uma oportunidade para este teste"
    out = build_graph_html(rates, ops, tmp_path / "g.html", open_browser=False)
    content = out.read_text(encoding="utf-8")

    # painel de tabela + iframe do grafo coexistindo na mesma página
    assert "Oportunidades de Arbitragem" in content
    assert "<iframe" in content
    assert "<table>" in content
    assert f"+{ops[0].profit_pct:.2f}%" in content  # lucro na tabela


def test_cycle_edges_highlighted(tmp_path):
    rates, ops = _mock_rates_and_ops()
    assert ops
    out = build_graph_html(rates, ops, tmp_path / "g.html", open_browser=False)
    content = out.read_text(encoding="utf-8")

    assert CYCLE_COLOR in content      # cor de destaque presente
    assert "(ciclo +" in content       # tooltip de aresta de ciclo (só existe se houver ciclo)


def test_renders_without_opportunities(tmp_path):
    rates, _ = _mock_rates_and_ops()
    out = build_graph_html(rates, [], tmp_path / "g.html", open_browser=False)

    assert out.exists()
    content = out.read_text(encoding="utf-8")
    for symbol in MOCK_SYMBOLS:
        assert symbol in content
    assert "Nenhuma oportunidade" in content
    assert "(ciclo +" not in content   # nenhum tooltip de ciclo destacado


def test_self_contained_offline(tmp_path):
    # cdn_resources="in_line" => o vis.js deve estar embutido (sem depender de internet)
    rates, ops = _mock_rates_and_ops()
    out = build_graph_html(rates, ops, tmp_path / "g.html", open_browser=False)
    content = out.read_text(encoding="utf-8")
    assert "vis-network" in content or "vis.min.js" in content
