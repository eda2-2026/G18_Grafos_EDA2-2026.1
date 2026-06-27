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


def _fake_response(payload):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    return FakeResponse()


def test_retries_then_raises_api_error(monkeypatch):
    client = CoinGeckoClient(base_url="http://test.local")
    attempts = {"n": 0}

    def always_fail(*args, **kwargs):
        attempts["n"] += 1
        raise httpx.ConnectError("boom")

    monkeypatch.setattr("src.api.coingecko_client.httpx.get", always_fail)
    monkeypatch.setattr("src.api.coingecko_client.time.sleep", lambda _: None)

    with pytest.raises(APIError):
        client.get_rates(["BTC", "ETH"])

    assert attempts["n"] == 3  # 3 tentativas


def test_succeeds_after_transient_failure(monkeypatch):
    client = CoinGeckoClient(base_url="http://test.local")
    state = {"n": 0}

    def flaky_get(*args, **kwargs):
        state["n"] += 1
        if state["n"] == 1:
            raise httpx.ConnectError("transient")
        return _fake_response({"bitcoin": {"usd": 60000.0}, "ethereum": {"usd": 2000.0}})

    monkeypatch.setattr("src.api.coingecko_client.httpx.get", flaky_get)
    monkeypatch.setattr("src.api.coingecko_client.time.sleep", lambda _: None)

    matrix = client.get_rates(["BTC", "ETH"])

    assert state["n"] == 2  # falhou 1x, sucesso na 2ª
    assert matrix["BTC"]["ETH"] == pytest.approx(30.0)   # 60000 / 2000
    assert "BTC" not in matrix["BTC"]                    # sem self-loop


# ---------------------------------------------------------------------------
# Modo ao vivo: triangulação via USD (sem rede real)
# ---------------------------------------------------------------------------

LIVE_PAYLOAD = {
    "bitcoin": {"usd": 60123.0},
    "ethereum": {"usd": 1575.4},
    "tether": {"usd": 0.998553},
    "binancecoin": {"usd": 557.5},
}


def test_live_builds_cross_matrix(monkeypatch):
    client = CoinGeckoClient(base_url="http://test.local")
    monkeypatch.setattr(
        "src.api.coingecko_client.httpx.get", lambda *a, **k: _fake_response(LIVE_PAYLOAD)
    )

    matrix = client.get_rates(["BTC", "ETH", "USDT", "BNB", "USD"])

    assert "USD" in matrix
    assert matrix["BTC"]["USD"] == pytest.approx(60123.0)
    assert matrix["USD"]["BTC"] == pytest.approx(1 / 60123.0)
    assert matrix["BTC"]["ETH"] == pytest.approx(60123.0 / 1575.4)
    for src, row in matrix.items():
        assert src not in row  # sem self-loops


def test_live_requests_mapped_ids(monkeypatch):
    client = CoinGeckoClient(base_url="http://test.local")
    captured = {}

    def capturing_get(url, *, params, headers, timeout):
        captured["params"] = params
        return _fake_response(LIVE_PAYLOAD)

    monkeypatch.setattr("src.api.coingecko_client.httpx.get", capturing_get)
    client.get_rates(["BTC", "ETH", "USD"])

    assert captured["params"]["vs_currencies"] == "usd"
    ids = captured["params"]["ids"].split(",")
    assert "bitcoin" in ids and "ethereum" in ids
    assert "USD" not in captured["params"]["ids"]  # âncora não é id


def test_live_drops_unmapped_symbols(monkeypatch):
    client = CoinGeckoClient(base_url="http://test.local")
    monkeypatch.setattr(
        "src.api.coingecko_client.httpx.get",
        lambda *a, **k: _fake_response({"bitcoin": {"usd": 60000.0}}),
    )

    matrix = client.get_rates(["BTC", "FOOBAR"])

    assert "BTC" in matrix
    assert "FOOBAR" not in matrix


def test_no_mappable_symbols_returns_empty(monkeypatch):
    client = CoinGeckoClient(base_url="http://test.local")

    def must_not_call(*a, **k):
        raise AssertionError("não deveria chamar a rede sem símbolos mapeáveis")

    monkeypatch.setattr("src.api.coingecko_client.httpx.get", must_not_call)
    assert client.get_rates(["FOOBAR"]) == {}
