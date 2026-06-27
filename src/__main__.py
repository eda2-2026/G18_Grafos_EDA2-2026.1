"""Interface de linha de comando do CryptoArbitrageGraph.

Modos:
    python -m src --mock                      # snapshot (tabela rich)
    python -m src --symbols BTC ETH USDT      # snapshot com símbolos específicos
    python -m src --mock --watch --interval 5 # polling periódico (rich.live)
    python -m src --mock --graph              # grafo interativo (HTML/pyvis)

No modo real (sem --mock), --symbols espera ids da CoinGecko (ex: bitcoin ethereum tether).
"""

from __future__ import annotations

import argparse

from rich.console import Console

from src.arbitrage.detector import ArbitrageDetector
from src.cli import run_snapshot, run_watch

DEFAULT_SYMBOLS = ["BTC", "ETH", "USDT", "BNB", "USD"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Detecção de arbitragem triangular em criptomoedas via Bellman-Ford.",
    )
    parser.add_argument(
        "--symbols", nargs="+", default=DEFAULT_SYMBOLS,
        help="Moedas a analisar (default: %(default)s). No modo ao vivo os símbolos são "
             "mapeados automaticamente para ids da CoinGecko (BTC, ETH, USDT, BNB, USDC, "
             "SOL, XRP, ADA, DOGE, USD).",
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Atualiza periodicamente em vez de um único snapshot.",
    )
    parser.add_argument(
        "--interval", type=int, default=30,
        help="Segundos entre atualizações no modo --watch (default: %(default)s).",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Usa data/mock_rates.json em vez da API (offline).",
    )
    parser.add_argument(
        "--graph", action="store_true",
        help="Gera um grafo interativo em HTML (pyvis) com os ciclos destacados.",
    )
    parser.add_argument(
        "--graph-output", default="arbitrage_graph.html",
        help="Caminho do HTML do grafo (default: %(default)s).",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Não abre o navegador ao gerar o grafo (útil em headless/CI).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    console = Console()

    if args.mock:
        from src.api.coingecko_client import MockClient
        client = MockClient()
    else:
        from src.api.coingecko_client import SUPPORTED_LIVE, CoinGeckoClient
        client = CoinGeckoClient()
        unknown = [s for s in args.symbols if s not in SUPPORTED_LIVE]
        if unknown:
            console.print(
                f"[yellow]Ignorados no modo ao vivo (sem id CoinGecko): {', '.join(unknown)}[/yellow]"
            )

    detector = ArbitrageDetector(client)

    if args.watch:
        run_watch(detector, args.symbols, args.interval, console, mock=args.mock)
        return 0

    opportunities = run_snapshot(detector, args.symbols, console, mock=args.mock)

    if args.graph:
        from src.visualize import build_graph_html
        rates = client.get_rates(args.symbols)  # cacheado pelo client
        path = build_graph_html(
            rates, opportunities, args.graph_output, open_browser=not args.no_browser
        )
        console.print(f"[blue]Grafo interativo gerado em:[/blue] {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
