"""Cliente para buscar taxas de câmbio na CoinGecko API.

Expõe um cliente resiliente (`CoinGeckoClient`) com cache em memória e retry
com backoff exponencial, e um `MockClient` que lê de `data/mock_rates.json`
para rodar testes e o pipeline offline (sem internet).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# par origem -> par destino -> taxa de câmbio
RateMatrix = dict[str, dict[str, float]]

DEFAULT_BASE_URL = "https://api.coingecko.com/api/v3"
CACHE_TTL_SECONDS = 60.0
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10.0

# Moeda âncora (fiat): seu preço em USD é 1.0 por definição.
ANCHOR = "USD"

# Símbolo -> id da CoinGecko. A API usa ids ("bitcoin"), não símbolos ("BTC").
SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "BNB": "binancecoin",
    "USDC": "usd-coin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
}

# Símbolos que o modo ao vivo consegue resolver.
SUPPORTED_LIVE = set(SYMBOL_TO_ID) | {ANCHOR}

# data/mock_rates.json a partir de src/api/coingecko_client.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
MOCK_RATES_PATH = _REPO_ROOT / "data" / "mock_rates.json"


class APIError(Exception):
    """Erro ao buscar taxas após esgotar todas as tentativas."""


def _filter_matrix(symbol_keyed: dict, symbols: list[str]) -> RateMatrix:
    """Filtra uma matriz já indexada por símbolo para os símbolos pedidos, sem self-loops."""
    matrix: RateMatrix = {}
    requested = set(symbols)
    for src in symbols:
        row = symbol_keyed.get(src, {})
        matrix[src] = {
            dst: float(rate)
            for dst, rate in row.items()
            if dst in requested and dst != src
        }
    return matrix


def _build_cross_matrix(data: dict, symbols: list[str]) -> RateMatrix:
    """Constrói a matriz de taxas cruzadas triangulando pelo USD.

    `data` é a resposta da CoinGecko no formato {id: {"usd": preço}}. O preço de 1 A em USD
    e de 1 B em USD dão a taxa A->B = usd[A] / usd[B] (1 A vira usd[A]/usd[B] unidades de B).
    Símbolos sem preço disponível são descartados.
    """
    usd_price: dict[str, float] = {}
    for symbol in symbols:
        if symbol == ANCHOR:
            usd_price[symbol] = 1.0
        elif symbol in SYMBOL_TO_ID:
            row = data.get(SYMBOL_TO_ID[symbol])
            if row and row.get("usd") is not None:
                usd_price[symbol] = float(row["usd"])

    matrix: RateMatrix = {}
    for a, pa in usd_price.items():
        matrix[a] = {b: pa / pb for b, pb in usd_price.items() if b != a}
    return matrix


class CoinGeckoClient:
    """Busca taxas reais via `/simple/price` com cache (TTL 60s) e retry."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        load_dotenv()
        self._base_url = (base_url or os.getenv("COINGECKO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._api_key = api_key or os.getenv("COINGECKO_API_KEY") or None
        # chave (tupla ordenada de símbolos) -> (instante_monotonic, matriz)
        self._cache: dict[tuple[str, ...], tuple[float, RateMatrix]] = {}

    def get_rates(self, symbols: list[str]) -> RateMatrix:
        """Retorna a matriz de taxas para `symbols`, usando cache quando válido."""
        key = tuple(sorted(symbols))
        cached = self._cache.get(key)
        if cached is not None and (time.monotonic() - cached[0]) < CACHE_TTL_SECONDS:
            return cached[1]

        matrix = self._fetch(symbols)
        self._cache[key] = (time.monotonic(), matrix)
        return matrix

    def clear_cache(self) -> None:
        """Esvazia o cache em memória."""
        self._cache.clear()

    def _fetch(self, symbols: list[str]) -> RateMatrix:
        """Busca os preços em USD (com retry) e triangula a matriz cruzada.

        Mapeia os símbolos para ids da CoinGecko; símbolos sem id são ignorados.
        Levanta APIError se todas as tentativas falharem.
        """
        ids = [SYMBOL_TO_ID[s] for s in symbols if s in SYMBOL_TO_ID]
        if not ids:
            return {}

        url = f"{self._base_url}/simple/price"
        params = {"ids": ",".join(ids), "vs_currencies": "usd"}
        headers = {"x-cg-demo-api-key": self._api_key} if self._api_key else {}

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = httpx.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return _build_cross_matrix(response.json(), symbols)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # backoff: 1s, 2s, 4s...

        raise APIError(
            f"Falha ao buscar taxas após {MAX_RETRIES} tentativas para {symbols}"
        ) from last_error


class MockClient(CoinGeckoClient):
    """Cliente offline que lê as taxas de `data/mock_rates.json`.

    Reaproveita o cache e a interface de `CoinGeckoClient`, sobrescrevendo
    apenas a busca para não acessar a rede.
    """

    def __init__(self, mock_path: str | Path = MOCK_RATES_PATH) -> None:
        self._mock_path = Path(mock_path)
        self._cache: dict[tuple[str, ...], tuple[float, RateMatrix]] = {}
        self._rates: RateMatrix | None = None

    def _load(self) -> RateMatrix:
        if self._rates is None:
            with open(self._mock_path, encoding="utf-8") as f:
                self._rates = json.load(f)["rates"]
        return self._rates

    def _fetch(self, symbols: list[str]) -> RateMatrix:
        return _filter_matrix(self._load(), symbols)
