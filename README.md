# CryptoArbitrageGraph

Detecção de arbitragem triangular em mercados de criptomoedas usando Teoria de Grafos e o algoritmo de Bellman-Ford.

Projeto acadêmico — Estrutura de Dados 2 (EDA2), 2026.1.

---

## Conceito

Arbitragem triangular ocorre quando é possível lucrar convertendo moeda A → B → C → A sem risco, desde que o produto das taxas de câmbio seja maior que 1:

$$Taxa_{A \to B} \times Taxa_{B \to C} \times Taxa_{C \to A} > 1$$

### Modelagem como Grafo

- **Nós:** moedas (BTC, ETH, USDT, BRL, USD…)
- **Arestas:** taxa de câmbio direta entre dois pares (direcionada e ponderada)
- **Transformação:** aplicamos $w = -\log(taxa)$ em cada aresta

Com essa transformação, multiplicar taxas equivale a somar pesos, e um ciclo de arbitragem lucrativo se torna um **ciclo negativo** — detectável diretamente pelo algoritmo de Bellman-Ford.

```
BTC ──0.032──> ETH
 ↑               │
 0.041          0.067
 │               ↓
USDT <──0.051── BNB
```

Se $\sum_{i} -\log(w_i) < 0$ ao longo do ciclo → oportunidade de arbitragem.

---

## Estrutura do Projeto

```
CryptoArbitrageGraph/
├── src/
│   ├── graph/
│   │   ├── currency_graph.py       # Grafo direcionado ponderado
│   │   └── bellman_ford.py         # Implementação do Bellman-Ford
│   ├── api/
│   │   └── coingecko_client.py     # Cliente REST da CoinGecko API
│   ├── arbitrage/
│   │   └── detector.py             # Pipeline de detecção de arbitragem
│   └── benchmark/
│       └── runner.py               # Suite de benchmark comparativo
├── tests/
│   ├── test_graph.py
│   ├── test_bellman_ford.py
│   ├── test_arbitrage.py
│   └── test_api.py
├── notebooks/
│   └── analysis.ipynb              # Análise exploratória e visualizações
├── data/
│   └── mock_rates.json             # Taxas mockadas para testes offline
├── docs/
│   └── architecture.md
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Algoritmo Principal

### Bellman-Ford com Detecção de Ciclos Negativos

1. Buscar taxas de câmbio via CoinGecko API
2. Construir grafo direcionado: $w(u \to v) = -\log(taxa_{u \to v})$
3. Rodar Bellman-Ford a partir de cada nó fonte
4. Na $|V|$-ésima iteração, se alguma aresta ainda relaxa → ciclo negativo encontrado
5. Reconstruir o ciclo via backtracking dos predecessores
6. Calcular lucro real: $\prod taxa_i - 1$ (em %)

**Complexidade:** $O(V \times E)$ por fonte → $O(V^2 \times E)$ no pior caso

---

## Setup

```bash
git clone git@github.com:eda2-2026/G18_Grafos_EDA2-2026.1.git
cd G18_Grafos_EDA2-2026.1

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Variáveis de Ambiente

```bash
cp .env.example .env
# Preencher COINGECKO_API_KEY se usar plano Pro (free tier não precisa)
```

### Executar

```bash
# Detecção ao vivo
python -m src.arbitrage.detector

# Benchmark
python -m src.benchmark.runner
```

### Testes

```bash
pytest tests/ -v
```

---

## Tecnologias

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Linguagem | Python 3.11+ | Ecossistema científico, prototipagem rápida |
| Grafo | Implementação própria + NetworkX | Exercício acadêmico + validação |
| API | CoinGecko REST (free tier) | Dados reais sem chave obrigatória |
| HTTP | `httpx` | Async-ready, melhor que `requests` |
| Testes | `pytest` | Padrão de mercado |
| Benchmark | `timeit` + `tracemalloc` | CPU time + memória |
| Análise | `jupyter` + `matplotlib` | Visualização do grafo e resultados |

---

## Benchmark

O módulo `src/benchmark/runner.py` compara:

- **Bellman-Ford próprio** vs **NetworkX** (referência)
- Métricas: tempo de execução (ms), memória (KB), ciclos encontrados
- Variação de carga: 5, 10, 20, 50 moedas no grafo

Resultados serão publicados em `docs/benchmark_results.md`.

---

## Equipe — Grupo 18

| Membro | Foco |
|---|---|
| P1 | Core algorítmico (grafo + Bellman-Ford + benchmark) |
| P2 | Integração (API + detecção + CLI + documentação) |

---

## Referências

- Cormen et al., *Introduction to Algorithms* — Cap. 24 (Single-Source Shortest Paths)
- [CoinGecko API Docs](https://docs.coingecko.com/reference/introduction)
- Ahuja, Magnanti, Orlin — *Network Flows: Theory, Algorithms, and Applications*
