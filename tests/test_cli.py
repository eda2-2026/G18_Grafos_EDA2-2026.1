from rich.console import Console

from src.__main__ import DEFAULT_SYMBOLS, main, parse_args
from src.api.coingecko_client import MockClient
from src.arbitrage.detector import ArbitrageDetector, ArbOpportunity
from src.cli import build_report, run_snapshot, run_watch

MOCK_SYMBOLS = ["BTC", "ETH", "USDT", "BNB", "USD"]


def _render(renderable) -> str:
    console = Console(record=True, width=120)
    console.print(renderable)
    return console.export_text()


# --------------------------------------------------------------------------- #
# argparse
# --------------------------------------------------------------------------- #


def test_parse_args_defaults():
    args = parse_args([])
    assert args.mock is False
    assert args.watch is False
    assert args.graph is False
    assert args.interval == 30
    assert args.symbols == DEFAULT_SYMBOLS


def test_parse_args_overrides():
    args = parse_args(
        ["--watch", "--interval", "5", "--symbols", "BTC", "ETH", "--mock", "--graph"]
    )
    assert args.watch is True
    assert args.interval == 5
    assert args.symbols == ["BTC", "ETH"]
    assert args.mock is True
    assert args.graph is True


# --------------------------------------------------------------------------- #
# build_report
# --------------------------------------------------------------------------- #


def test_report_lists_opportunities():
    ops = [ArbOpportunity(cycle=["BTC", "ETH", "BTC"], profit_pct=20.0, rates_used=[15.8, 0.08])]
    out = _render(build_report(ops, symbols=["BTC", "ETH"], timestamp="2026-06-27 14:32:01", mock=True))
    assert "BTC → ETH" in out
    assert "+20.00%" in out
    assert "2026-06-27 14:32:01" in out


def test_report_empty_market():
    out = _render(build_report([], symbols=["BTC"], timestamp="2026-06-27 14:32:01", mock=True))
    assert "Nenhuma oportunidade" in out


def test_report_shows_source():
    out_mock = _render(build_report([], symbols=["BTC"], timestamp="t", mock=True))
    out_live = _render(build_report([], symbols=["BTC"], timestamp="t", mock=False))
    assert "mock" in out_mock
    assert "live" in out_live


# --------------------------------------------------------------------------- #
# runners
# --------------------------------------------------------------------------- #


def test_run_snapshot_with_mock():
    console = Console(record=True, width=120)
    detector = ArbitrageDetector(MockClient())
    ops = run_snapshot(detector, MOCK_SYMBOLS, console, mock=True)
    out = console.export_text()
    assert len(ops) >= 1
    assert "Arbitragem" in out


def test_watch_handles_keyboard_interrupt(monkeypatch):
    class FakeDetector:
        def detect(self, symbols):
            raise KeyboardInterrupt

    monkeypatch.setattr("src.cli.time.sleep", lambda _: None)
    console = Console(record=True, width=120)

    # Não deve propagar a exceção
    run_watch(FakeDetector(), ["BTC"], 1, console, mock=True)
    assert "Encerrado" in console.export_text()


def test_watch_updates_then_interrupts(monkeypatch):
    # detect funciona uma vez, depois o sleep dispara KeyboardInterrupt
    class FakeDetector:
        def detect(self, symbols):
            return []

    def fake_sleep(_):
        raise KeyboardInterrupt

    monkeypatch.setattr("src.cli.time.sleep", fake_sleep)
    console = Console(record=True, width=120)
    run_watch(FakeDetector(), ["BTC"], 1, console, mock=True)
    assert "Encerrado" in console.export_text()


# --------------------------------------------------------------------------- #
# main() — entrypoint end-to-end (modo mock)
# --------------------------------------------------------------------------- #


def test_main_snapshot_mock():
    assert main(["--mock", "--symbols", *MOCK_SYMBOLS]) == 0


def test_main_graph_generates_html(tmp_path):
    out = tmp_path / "arb.html"
    rc = main(
        ["--mock", "--graph", "--graph-output", str(out), "--no-browser", "--symbols", *MOCK_SYMBOLS]
    )
    assert rc == 0
    assert out.exists()
