import httpx
import pytest

from src.api.coingecko_client import (
    APIError,
    CoinGeckoClient,
    MockClient,
    RateMatrix,
)

MOCK_SYMBOLS = ["BTC", "ETH", "USDT"]


# ---------------------------------------------------------------------------
# MockClient — modo offline (sem hit real na API)
# ---------------------------------------------------------------------------


def test_mock_get_rates_returns_valid_matrix():
    client = MockClient()
    matrix = client.get_rates(MOCK_SYMBOLS)

    assert set(matrix.keys()) == set(MOCK_SYMBOLS)
    assert matrix["BTC"]["ETH"] == pytest.approx(15.8)
    assert matrix["USDT"]["BTC"] == pytest.approx(0.0000149)


def test_mock_excludes_symbols_not_requested():
    client = MockClient()
    matrix = client.get_rates(MOCK_SYMBOLS)

    # BNB e USD existem no arquivo mas não foram pedidos
    for row in matrix.values():
        assert "BNB" not in row
        assert "USD" not in row


def test_mock_has_no_self_loops():
    client = MockClient()
    matrix = client.get_rates(MOCK_SYMBOLS)
    for src, row in matrix.items():
        assert src not in row


def test_mock_unknown_symbol_yields_empty_row():
    client = MockClient()
    matrix = client.get_rates(["BTC", "DOGE"])
    assert matrix["DOGE"] == {}


def test_mock_matrix_is_rate_matrix_shape():
    client = MockClient()
    matrix: RateMatrix = client.get_rates(MOCK_SYMBOLS)
    for row in matrix.values():
        assert all(isinstance(rate, float) for rate in row.values())


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def test_cache_returns_same_object(monkeypatch):
    client = MockClient()
    calls = {"n": 0}
    original_fetch = client._fetch

    def counting_fetch(symbols):
        calls["n"] += 1
        return original_fetch(symbols)

    monkeypatch.setattr(client, "_fetch", counting_fetch)

    first = client.get_rates(MOCK_SYMBOLS)
    second = client.get_rates(MOCK_SYMBOLS)

    assert first is second
    assert calls["n"] == 1  # segunda chamada veio do cache


def test_clear_cache_forces_refetch(monkeypatch):
    client = MockClient()
    calls = {"n": 0}
    original_fetch = client._fetch

    def counting_fetch(symbols):
        calls["n"] += 1
        return original_fetch(symbols)

    monkeypatch.setattr(client, "_fetch", counting_fetch)

    client.get_rates(MOCK_SYMBOLS)
    client.clear_cache()
    client.get_rates(MOCK_SYMBOLS)

    assert calls["n"] == 2


def test_cache_expires_after_ttl(monkeypatch):
    client = MockClient()
    calls = {"n": 0}
    original_fetch = client._fetch

    def counting_fetch(symbols):
        calls["n"] += 1
        return original_fetch(symbols)

    monkeypatch.setattr(client, "_fetch", counting_fetch)

    fake_time = {"now": 1000.0}
    monkeypatch.setattr("src.api.coingecko_client.time.monotonic", lambda: fake_time["now"])

    client.get_rates(MOCK_SYMBOLS)
    fake_time["now"] += 61.0  # passa do TTL de 60s
    client.get_rates(MOCK_SYMBOLS)

    assert calls["n"] == 2


# ---------------------------------------------------------------------------
# Retry / APIError (sem rede real)
# ---------------------------------------------------------------------------


def test_retries_then_raises_api_error(monkeypatch):
    client = CoinGeckoClient(base_url="http://test.local")
    attempts = {"n": 0}

    def always_fail(*args, **kwargs):
        attempts["n"] += 1
        raise httpx.ConnectError("boom")

    monkeypatch.setattr("src.api.coingecko_client.httpx.get", always_fail)
    monkeypatch.setattr("src.api.coingecko_client.time.sleep", lambda _: None)

    with pytest.raises(APIError):
        client.get_rates(["bitcoin"])

    assert attempts["n"] == 3  # 3 tentativas


def test_succeeds_after_transient_failure(monkeypatch):
    client = CoinGeckoClient(base_url="http://test.local")
    state = {"n": 0}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"bitcoin": {"ethereum": 15.8}, "ethereum": {"bitcoin": 0.0633}}

    def flaky_get(*args, **kwargs):
        state["n"] += 1
        if state["n"] == 1:
            raise httpx.ConnectError("transient")
        return FakeResponse()

    monkeypatch.setattr("src.api.coingecko_client.httpx.get", flaky_get)
    monkeypatch.setattr("src.api.coingecko_client.time.sleep", lambda _: None)

    matrix = client.get_rates(["bitcoin", "ethereum"])

    assert state["n"] == 2  # falhou 1x, sucesso na 2ª
    assert matrix["bitcoin"]["ethereum"] == pytest.approx(15.8)
    assert "bitcoin" not in matrix["bitcoin"]  # sem self-loop
