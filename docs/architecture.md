# Arquitetura — CryptoArbitrageGraph

## Fluxo de Dados

```
CoinGecko API
     │
     ▼
coingecko_client.py  ──→  dict[str, dict[str, float]]  (par → taxa)
     │
     ▼
currency_graph.py    ──→  Grafo direcionado G(V, E)
                          w(u,v) = -log(taxa(u,v))
     │
     ▼
bellman_ford.py      ──→  ciclos negativos (se existirem)
     │
     ▼
detector.py          ──→  ArbOpportunity(ciclo, lucro_pct)
     │
     ▼
CLI / Rich output
```

## Módulos

### `src/graph/currency_graph.py`
- Classe `CurrencyGraph` com lista de adjacência
- `add_currency(symbol)` / `add_rate(src, dst, rate)`
- `transform_weights()` — aplica $-\log(w)$ em todas as arestas
- Serialização para lista de arestas compatível com Bellman-Ford

### `src/graph/bellman_ford.py`
- `bellman_ford(graph, source) → (distances, predecessors, negative_cycle)`
- Sem dependência de bibliotecas externas
- Retorna o ciclo reconstruído via predecessores

### `src/api/coingecko_client.py`
- `get_exchange_rates(symbols: list[str]) → RateMatrix`
- Retry com backoff exponencial
- Cache em memória (TTL 60s) para não bater rate limit

### `src/arbitrage/detector.py`
- Orquestra: busca taxas → constrói grafo → roda BF → filtra ciclos
- `detect(symbols) → list[ArbOpportunity]`

### `src/benchmark/runner.py`
- Compara implementação própria vs NetworkX
- Métricas: `timeit` (médias de 10 runs) + `tracemalloc`
- Output: tabela Markdown em `docs/benchmark_results.md`
