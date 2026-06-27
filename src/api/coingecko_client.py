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

# data/mock_rates.json a partir de src/api/coingecko_client.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
MOCK_RATES_PATH = _REPO_ROOT / "data" / "mock_rates.json"


class APIError(Exception):
    """Erro ao buscar taxas após esgotar todas as tentativas."""


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
        """Faz a requisição com retry; levanta APIError se todas falharem."""
        url = f"{self._base_url}/simple/price"
        params = {"ids": ",".join(symbols), "vs_currencies": ",".join(symbols)}
        headers = {"x-cg-demo-api-key": self._api_key} if self._api_key else {}

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = httpx.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return self._parse(response.json(), symbols)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # backoff: 1s, 2s, 4s...

        raise APIError(
            f"Falha ao buscar taxas após {MAX_RETRIES} tentativas para {symbols}"
        ) from last_error

    def _parse(self, data: dict, symbols: list[str]) -> RateMatrix:
        """Filtra a resposta da API para os símbolos pedidos, sem self-loops."""
        matrix: RateMatrix = {}
        requested = set(symbols)
        for src in symbols:
            row = data.get(src, {})
            matrix[src] = {
                dst: float(rate)
                for dst, rate in row.items()
                if dst in requested and dst != src
            }
        return matrix


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
        return self._parse(self._load(), symbols)
