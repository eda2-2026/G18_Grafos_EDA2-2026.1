"""Renderização rich das oportunidades e os runners de snapshot/watch."""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from src.arbitrage.detector import ArbOpportunity, ArbitrageDetector


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_report(
    opportunities: list[ArbOpportunity],
    *,
    symbols: list[str],
    timestamp: str,
    mock: bool,
) -> Panel:
    """Monta o painel rich com a tabela de oportunidades (ou aviso de mercado eficiente)."""
    origem = "mock" if mock else "live"
    subtitle = f"{', '.join(symbols)}  ·  fonte: {origem}"

    body: Table | str
    if not opportunities:
        body = "[dim]Nenhuma oportunidade encontrada (mercado eficiente).[/dim]"
    else:
        table = Table(expand=True)
        table.add_column("Ciclo", style="cyan", no_wrap=True)
        table.add_column("Lucro", justify="right", style="green")
        table.add_column("Taxas", style="dim")
        for op in opportunities:
            ciclo = " → ".join(op.cycle)
            lucro = f"+{op.profit_pct:.2f}%"
            taxas = " / ".join(f"{r:g}" for r in op.rates_used)
            table.add_row(ciclo, lucro, taxas)
        body = table

    return Panel(
        body,
        title=f"Oportunidades de Arbitragem Triangular — {timestamp}",
        subtitle=subtitle,
        title_align="left",
        subtitle_align="right",
        border_style="blue",
        padding=(1, 2),
    )


def run_snapshot(
    detector: ArbitrageDetector,
    symbols: list[str],
    console: Console,
    *,
    mock: bool,
) -> list[ArbOpportunity]:
    """Executa uma única detecção e imprime o relatório. Retorna as oportunidades."""
    opportunities = detector.detect(symbols)
    console.print(build_report(opportunities, symbols=symbols, timestamp=_now(), mock=mock))
    return opportunities


def run_watch(
    detector: ArbitrageDetector,
    symbols: list[str],
    interval: int,
    console: Console,
    *,
    mock: bool,
) -> None:
    """Atualiza o relatório a cada `interval` segundos até Ctrl-C (encerra graciosamente)."""
    try:
        with Live(console=console, refresh_per_second=4, screen=False) as live:
            while True:
                opportunities = detector.detect(symbols)
                live.update(
                    build_report(opportunities, symbols=symbols, timestamp=_now(), mock=mock)
                )
                time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Encerrado pelo usuário.[/yellow]")
