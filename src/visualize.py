"""Geração da página interativa (pyvis / vis.js) com o grafo de taxas ao lado da
tabela de oportunidades de arbitragem detectadas."""

from __future__ import annotations

import html
import json
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.api.coingecko_client import RateMatrix
    from src.arbitrage.detector import ArbOpportunity

CYCLE_COLOR = "#e74c3c"        # vermelho: arestas de ciclos lucrativos
EDGE_COLOR = "#5a5a66"         # cinza: arestas comuns
NODE_COLOR = "#3498db"         # azul: moedas
CYCLE_NODE_COLOR = "#e67e22"   # laranja: moedas em ciclos
BG_COLOR = "#1e1e24"

# Opções do vis.js: nós pequenos, física que espalha, arestas curvas sem labels.
_VIS_OPTIONS = {
    "nodes": {
        "shape": "dot",
        "size": 18,
        "borderWidth": 2,
        "font": {"size": 16, "color": "#ffffff", "face": "monospace"},
    },
    "edges": {
        "color": {"inherit": False},
        "smooth": {"type": "curvedCW", "roundness": 0.2},
        "arrows": {"to": {"enabled": True, "scaleFactor": 0.6}},
        "font": {"size": 0},  # esconde label nas arestas (taxa vai no tooltip)
    },
    "physics": {
        "barnesHut": {
            "gravitationalConstant": -9000,
            "centralGravity": 0.3,
            "springLength": 220,
            "springConstant": 0.04,
            "damping": 0.09,
        },
        "minVelocity": 0.75,
        "stabilization": {"iterations": 200},
    },
    "interaction": {"hover": True, "tooltipDelay": 100, "navigationButtons": True},
}


def build_graph_html(
    rates: RateMatrix,
    opportunities: list[ArbOpportunity],
    output_path: str | Path,
    *,
    open_browser: bool = False,
) -> Path:
    """Gera um HTML interativo (zoom, arrastar, clicar) com o grafo de moedas à esquerda
    e a tabela de oportunidades à direita. Arestas de ciclos lucrativos ficam em vermelho.

    Retorna o caminho do HTML gerado.
    """
    from pyvis.network import Network  # import lazy: só quando --graph é usado

    output_path = Path(output_path)

    # Arestas e nós que fazem parte de algum ciclo lucrativo
    cycle_edges: set[tuple[str, str]] = set()
    cycle_nodes: set[str] = set()
    profit_by_edge: dict[tuple[str, str], float] = {}
    for op in opportunities:
        for i in range(len(op.cycle) - 1):
            edge = (op.cycle[i], op.cycle[i + 1])
            cycle_edges.add(edge)
            cycle_nodes.update(edge)
            profit_by_edge[edge] = op.profit_pct

    nodes: set[str] = set(rates.keys())
    for row in rates.values():
        nodes.update(row.keys())

    net = Network(
        height="100%",
        width="100%",
        directed=True,
        bgcolor=BG_COLOR,
        font_color="#ffffff",
        cdn_resources="in_line",  # JS embutido -> HTML autossuficiente/offline
    )
    net.set_options(json.dumps(_VIS_OPTIONS))

    for node in sorted(nodes):
        in_cycle = node in cycle_nodes
        net.add_node(
            node,
            label=node,
            color=CYCLE_NODE_COLOR if in_cycle else NODE_COLOR,
            title=f"Moeda: {node}",
            size=24 if in_cycle else 18,
        )

    for src, row in rates.items():
        for dst, rate in row.items():
            edge = (src, dst)
            if edge in cycle_edges:
                net.add_edge(
                    src, dst,
                    title=f"{src} → {dst}: {rate:g}  (ciclo +{profit_by_edge[edge]:.2f}%)",
                    color=CYCLE_COLOR,
                    width=4,
                )
            else:
                net.add_edge(
                    src, dst,
                    title=f"{src} → {dst}: {rate:g}",
                    color=EDGE_COLOR,
                    width=1,
                )

    graph_html = net.generate_html(notebook=False)
    graph_html = _fill_height(graph_html)
    page = _compose_page(graph_html, opportunities)
    output_path.write_text(page, encoding="utf-8")

    if open_browser:
        webbrowser.open(output_path.resolve().as_uri())

    return output_path


def _fill_height(graph_html: str) -> str:
    """Força o grafo pyvis a preencher toda a altura do iframe e herdar o fundo escuro
    (o template padrão usa alturas fixas e fundo branco)."""
    override = (
        "<style>"
        f"html,body{{height:100%;margin:0;background:{BG_COLOR};overflow:hidden}}"
        "#mynetwork{height:100vh!important;width:100%!important;border:none!important}"
        f".card{{height:100vh!important;border:none!important;background:{BG_COLOR}!important;"
        "box-shadow:none!important}"
        "</style>"
    )
    if "</head>" in graph_html:
        return graph_html.replace("</head>", override + "</head>", 1)
    return override + graph_html


def _compose_page(graph_html: str, opportunities: list[ArbOpportunity]) -> str:
    """Embute o grafo (pyvis) num iframe à esquerda e a tabela de oportunidades à direita."""
    graph_srcdoc = html.escape(graph_html, quote=True)

    if opportunities:
        rows = "\n".join(
            f"<tr><td class='cycle'>{' &rarr; '.join(html.escape(c) for c in op.cycle)}</td>"
            f"<td class='profit'>+{op.profit_pct:.2f}%</td>"
            f"<td class='rates'>{' / '.join(f'{r:g}' for r in op.rates_used)}</td></tr>"
            for op in opportunities
        )
        table = (
            "<table><thead><tr><th>Ciclo</th><th>Lucro</th><th>Taxas</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )
    else:
        table = "<p class='empty'>Nenhuma oportunidade encontrada (mercado eficiente).</p>"

    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>CryptoArbitrageGraph</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: system-ui, sans-serif; background: {BG_COLOR}; color: #eee; }}
  header {{ padding: 14px 22px; background: #15151a; border-bottom: 1px solid #2c2c36; }}
  header h1 {{ margin: 0; font-size: 18px; }}
  header span {{ color: #8a8a99; font-size: 13px; }}
  .container {{ display: flex; height: calc(100vh - 58px); }}
  .graph {{ flex: 1 1 65%; border: none; height: 100%; }}
  .panel {{ flex: 0 0 35%; max-width: 480px; padding: 18px 20px; overflow-y: auto;
            border-left: 1px solid #2c2c36; background: #1a1a20; }}
  .panel h2 {{ margin: 0 0 12px; font-size: 15px; color: #cfcfe0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #2c2c36; }}
  th {{ color: #8a8a99; font-weight: 600; }}
  td.cycle {{ font-family: monospace; color: #5dade2; }}
  td.profit {{ color: #2ecc71; font-weight: 700; text-align: right; white-space: nowrap; }}
  td.rates {{ color: #8a8a99; font-family: monospace; }}
  .empty {{ color: #8a8a99; font-style: italic; }}
  .legend {{ margin-top: 18px; font-size: 12px; color: #8a8a99; line-height: 1.7; }}
  .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }}
</style>
</head>
<body>
  <header>
    <h1>CryptoArbitrageGraph</h1>
    <span>Grafo de câmbio &amp; oportunidades de arbitragem triangular</span>
  </header>
  <div class="container">
    <iframe class="graph" srcdoc="{graph_srcdoc}"></iframe>
    <aside class="panel">
      <h2>Oportunidades de Arbitragem</h2>
      {table}
      <div class="legend">
        <div><span class="dot" style="background:{CYCLE_COLOR}"></span>aresta de ciclo lucrativo</div>
        <div><span class="dot" style="background:{CYCLE_NODE_COLOR}"></span>moeda em ciclo</div>
        <div><span class="dot" style="background:{NODE_COLOR}"></span>moeda comum</div>
        <div style="margin-top:8px">scroll = zoom · arrastar = mover · hover na aresta = taxa</div>
      </div>
    </aside>
  </div>
</body>
</html>"""
