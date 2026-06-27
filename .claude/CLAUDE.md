# CryptoArbitrageGraph — Contexto do Projeto

## O Projeto
Detecção de arbitragem triangular em criptomoedas via Teoria de Grafos.
EDA2 2026.1 — Grupo 18.

## Arquitetura Central
- `src/graph/currency_graph.py` — grafo direcionado ponderado (implementação própria)
- `src/graph/bellman_ford.py` — Bellman-Ford sem dependências externas
- `src/api/coingecko_client.py` — cliente CoinGecko (free tier, sem chave obrigatória)
- `src/arbitrage/detector.py` — pipeline principal
- `src/benchmark/runner.py` — benchmark próprio vs NetworkX

## Regras do Projeto
- Bellman-Ford deve ser implementado do zero (sem NetworkX para a lógica principal)
- NetworkX é usado APENAS como referência no benchmark
- Transformação: `w = -log(taxa)` para converter multiplicação em soma
- Testes devem usar `data/mock_rates.json` para não depender da API
- Python 3.11+, sem type: ignore nos arquivos de src/

## Comandos Úteis
```bash
python -m src.arbitrage.detector          # rodar detecção
python -m src.benchmark.runner            # rodar benchmark
pytest tests/ -v                           # rodar testes
```
