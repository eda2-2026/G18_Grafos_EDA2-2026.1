# Roteiro de Apresentação — CryptoArbitrageGraph

**Disciplina:** Estrutura de Dados 2 (EDA2) — Tema: **Grafos**
**Grupo 18:** Heitor e Zanetti
**Formato:** vídeo **gravado de forma assíncrona** e unido na edição · **Duração-alvo:** 10–12 min

> Projeto: detecção de **arbitragem triangular** em criptomoedas modelando o câmbio como um
> **grafo dirigido e ponderado** e usando **Bellman-Ford** para encontrar **ciclos negativos**.

---

## Como vamos gravar (assíncrono, meio a meio, contínuo)

- O vídeo é dividido em **duas metades contínuas**. Cada um grava a sua de uma vez só.
- **Ordem na edição:** **Parte 1 (Zanetti)** → **Parte 2 (Heitor)**. Foundations primeiro, demo no final.
- Entre as duas, entra um **card de transição** (1–2 s) — facilita o corte.
- Para o vídeo soar coeso mesmo gravado separado:
  - usar a **mesma terminologia** (nó/aresta, dirigido/ponderado, ciclo negativo);
  - cada um **se apresenta no início** da sua parte;
  - Zanetti **encerra com a passagem de bastão** (frase pronta abaixo) e Heitor **retoma** com a
    frase de gancho — assim o corte fica natural.

| Parte | Quem | Tempo | Conteúdo |
|---|---|---|---|
| **Parte 1** | **Zanetti** | ~5–6 min | Problema → modelagem em grafo → estrutura de dados → algoritmo → benchmark (metodologia) |
| **Parte 2** | **Heitor** | ~5–6 min | Pipeline com dados reais → 3 demonstrações → análise do benchmark → conclusão |

> Divisão de autoria do código: **Zanetti** fez o núcleo de Estrutura de Dados (`CurrencyGraph`,
> `bellman_ford.py`, benchmark runner, CI). **Heitor** fez a camada de aplicação (cliente
> CoinGecko, `graph_builder`, `detector`, CLI + grafo interativo, modo ao vivo, documentação).
> A apresentação segue essa mesma divisão.

---

# ───────── PARTE 1 — ZANETTI (Fundamentos / Estrutura de Dados) ─────────

> Grave esta parte inteira de uma vez. Abertura + teoria + estrutura + algoritmo + benchmark.

## 1.1 — Abertura e problema · ~1 min

**Tela:** README no GitHub (ou slide de título).

**Fala (pontos):**
- "Olá professor, somos o Grupo 18 — eu sou o Zanetti, e na segunda parte o Heitor continua.
  Nosso trabalho aplica **Teoria dos Grafos** a um problema real: **arbitragem triangular** em
  criptomoedas."
- Explicar arbitragem simples: "É lucrar trocando moeda A → B → C → e voltando para A, quando o
  **produto das taxas** de câmbio do ciclo é maior que 1. Ex.: começo com 1 BTC, faço três trocas
  e volto com 1,02 BTC — 2% sem risco."
- "A pergunta central: **como achar essas voltas lucrativas automaticamente?** A resposta vem da
  Estrutura de Dados — modelando o mercado como um grafo."

## 1.2 — Modelagem como grafo · ~1,5 min

**Tela:** diagrama do README (ASCII do grafo) ou o grafo interativo.

**Fala (pontos):**
- "Modelamos o mercado como um **grafo dirigido e ponderado**:
  - **Nós** = moedas (BTC, ETH, USDT…);
  - **Arestas dirigidas** = taxa de câmbio de uma moeda para outra — dirigido porque BTC→ETH ≠ ETH→BTC."
- **Insight central (mostrar):** "Arbitragem é **produto** de taxas > 1, mas algoritmos de grafo
  **somam** pesos. A ponte é o **logaritmo**: peso = **−log(taxa)**."
  ```
  ∏ taxaᵢ > 1   ⟺   ∑ log(taxaᵢ) > 0   ⟺   ∑ −log(taxaᵢ) < 0
  ```
- "Ou seja: **ciclo lucrativo vira ciclo de soma negativa**. E achar ciclo negativo é problema
  clássico de grafos — resolvido por Bellman-Ford."
- (Bônus): "Não dá para usar **Dijkstra**: ele não aceita pesos negativos, e o nosso grafo tem
  pesos negativos de propósito."

## 1.3 — A estrutura de dados: `CurrencyGraph` · ~1,5 min

**Tela:** `src/graph/currency_graph.py`.

**Fala (pontos):**
- "A estrutura é uma **lista de adjacência**: um dicionário `{ moeda: [(vizinho, peso), …] }`.
  Cada moeda guarda só seus vizinhos diretos."
- "Escolhemos lista de adjacência em vez de **matriz de adjacência** por eficiência de memória em
  grafos esparsos e por permitir iterar direto nos vizinhos — o que o Bellman-Ford precisa."
- Mostrar `add_rate` (valida taxa > 0), `get_edges`, `neighbors`, e `transform_weights()` (aplica
  o `−log`). "Ele é **destrutivo e de mão única** — por isso montamos com taxas cruas e
  transformamos **uma vez**."

## 1.4 — O algoritmo: Bellman-Ford · ~2 min

**Tela:** `src/graph/bellman_ford.py`.

**Fala (pontos):**
- "Bellman-Ford acha caminhos mínimos **relaxando** arestas: se `dist[u] + w < dist[v]`,
  atualiza `dist[v]`. Repetimos **V−1 vezes** (um caminho mínimo tem no máximo V−1 arestas)."
- **A detecção:** "Depois de V−1 passadas, se **ainda** existe aresta que relaxa, só pode haver
  um **ciclo negativo** — é a V-ésima iteração que delata a arbitragem."
- Mostrar a **reconstrução** via vetor de **predecessores**: anda V passos para entrar no ciclo e
  segue os predecessores até fechar a volta.
- **Complexidade:** "Cada passada visita todas as arestas, V passadas → **O(V·E)**. Grafo denso
  tem E ≈ V², então ~O(V³)."
- "Validamos com testes unitários: grafo sem ciclo, com ciclo negativo e reconstrução do caminho."

## 1.5 — Benchmark (metodologia) + passagem de bastão · ~30 s

**Tela:** `src/benchmark/runner.py`.

**Fala (pontos):**
- "Para medir o custo na prática, construí um **benchmark** que compara a nossa implementação com
  a do **NetworkX** (biblioteca de referência) em grafos de 5, 10, 20 e 50 nós, medindo tempo
  (`timeit`) e memória (`tracemalloc`)."
- **🎬 Passagem de bastão (frase de corte):** "Essa é a base de Estrutura de Dados do projeto.
  **Agora passo para o Heitor**, que vai mostrar tudo isso funcionando com dados reais e os
  resultados do benchmark."

---

# ═════════ [CARD DE TRANSIÇÃO — 1 a 2 segundos] ═════════

---

# ───────── PARTE 2 — HEITOR (Aplicação / Demonstração) ─────────

> Grave esta parte inteira de uma vez. Retomada + pipeline + 3 demos + análise + conclusão.

## 2.1 — Retomada e pipeline · ~1,5 min

**Tela:** `docs/architecture.md` (diagrama de fluxo) e os arquivos de `src/`.

**Fala (pontos):**
- **🎬 Gancho de retomada (frase de corte):** "Valeu, Zanetti. Com a estrutura e o algoritmo
  prontos, eu construí a camada que liga tudo a **dados reais**."
- "É uma **linha de montagem** de 3 peças:
  1. **`coingecko_client.py`** — busca as taxas (CoinGecko ao vivo, ou arquivo local no `--mock`),
     com **cache** de 60s e **retry** com backoff;
  2. **`graph_builder.py`** — traduz a matriz de taxas para o `CurrencyGraph` e aplica o `−log`
     (é onde a minha camada encontra a estrutura do Zanetti);
  3. **`detector.py`** — roda o Bellman-Ford a partir de **cada nó**, deduplica rotações do mesmo
     ciclo e calcula o lucro (`∏ taxas − 1`)."
- "Tudo coberto por **68 testes** automatizados rodando no CI."

## 2.2 — Demo 1: detecção local · ~40 s

> **Grave a tela rodando de verdade.** Antes: `source .venv/bin/activate`.

```bash
python -m src --mock
```
Narração: "No modo local, com um dataset que tem uma inconsistência plantada, detectamos o ciclo
**BNB → USDT → BNB** com **+147%** de lucro. A tabela mostra o ciclo, o lucro e as taxas usadas."

## 2.3 — Demo 2: grafo interativo · ~40 s

```bash
python -m src --mock --graph
```
Narração: "O mesmo grafo, **interativo**: dá para dar **zoom**, **arrastar** os nós e passar o
mouse nas arestas para ver as taxas. As arestas em **vermelho** são o ciclo lucrativo, e ao lado
fica a tabela de oportunidades." (Mostre o zoom e o hover.)

## 2.4 — Demo 3: dados reais do momento · ~40 s

```bash
python -m src --symbols BTC ETH USDT BNB USD
```
Narração: "Agora **ao vivo**, com preços reais da CoinGecko. O grafo vem com as taxas atuais, mas
a tabela diz **'mercado eficiente'** — e esse é o resultado **honesto**: como a API dá um preço
médio único por moeda, não existe arbitragem real. O `--mock` existe justamente para demonstrar a
detecção funcionando."

> 💡 Esse ponto pesa positivo na nota: mostra que entendemos a diferença entre **o algoritmo
> funcionar** e **o mercado real ser eficiente**, e fomos honestos sobre isso.

## 2.5 — Análise do benchmark · ~1 min

**Tela:** `docs/benchmark_results.md` e o gráfico de complexidade do `notebooks/analysis.ipynb`.

**Fala (pontos):**
- "Analisando o benchmark que o Zanetti montou: ele mostra a **complexidade na prática**. A nossa
  implementação **vence em grafos minúsculos** (5 nós) e usa ~3× menos memória, mas o **NetworkX
  escala muito melhor** — em 50 nós é ~300× mais rápido, porque roda os laços em C."
- "As duas são **igualmente corretas** (acham o mesmo ciclo). A conclusão é o **trade-off**:
  implementação própria para **aprender e cargas pequenas**; biblioteca madura para **produção**."

## 2.6 — Conclusão · ~1 min

**Tela:** `notebooks/analysis.ipynb` (heatmap + grafo) ou slide de fechamento.

**Fala (pontos):**
- "Recapitulando os conceitos de **Estrutura de Dados** aplicados:
  - grafo **dirigido e ponderado** em **lista de adjacência**;
  - **transformação de pesos** (`−log`): vira multiplicação em soma;
  - **Bellman-Ford** com detecção de **ciclo negativo** e reconstrução por predecessores;
  - **análise de complexidade** O(V·E) validada empiricamente."
- "Mais do que um detector de arbitragem, o projeto mostra como uma **boa escolha de estrutura de
  dados e algoritmo** transforma um problema financeiro em um problema clássico de grafos."
- "Obrigado, professor!"

---

## Checklist antes de gravar (os dois)

- [ ] `source .venv/bin/activate` (senão dá `ModuleNotFoundError: rich`).
- [ ] Combinar **antes** a terminologia e a ordem (Parte 1 Zanetti → Parte 2 Heitor).
- [ ] Gravar a frase de **passagem de bastão** (fim da Parte 1) e o **gancho** (início da Parte 2)
      exatamente como no roteiro — é o que faz o corte ficar natural.
- [ ] Heitor: testar os 3 comandos da demo antes de gravar; internet ativa para a demo ao vivo.
- [ ] Heitor: deixar o grafo interativo aberto no navegador com o zoom já enquadrado.
- [ ] Mesma fonte/tema de terminal grande e legível nas duas gravações.
- [ ] Conferir áudio dos dois (volume parecido, para não dar diferença no corte).

## Possíveis perguntas do professor (preparem-se os dois)

- **"Por que não Dijkstra?"** → não admite pesos negativos; após o `−log` o grafo tem pesos
  negativos de propósito (é o que detecta o lucro).
- **"Por que lista de adjacência e não matriz?"** → memória e iteração direta nos vizinhos; matriz
  seria O(V²) de espaço mesmo para grafos esparsos.
- **"Complexidade e por que rodar de cada nó?"** → O(V·E) por fonte; rodar de cada nó garante achar
  ciclos alcançáveis de qualquer ponto → O(V²·E) no pior caso.
- **"Como sabem que está correto?"** → 68 testes + comparação com NetworkX (mesmo resultado) + um
  ciclo plantado que é sempre encontrado.
- **"Por que ao vivo não acha arbitragem?"** → a CoinGecko dá preço médio único por moeda → matriz
  consistente (mercado eficiente). Arbitragem real exigiria preços por corretora (bid/ask).

## Mapa rápido código → conceito → autor (cola para a gravação)

| Arquivo | Autor | Conceito de ED |
|---|---|---|
| `src/graph/currency_graph.py` | Zanetti | Lista de adjacência, grafo dirigido ponderado, `−log` |
| `src/graph/bellman_ford.py` | Zanetti | Bellman-Ford, relaxamento, ciclo negativo, predecessores |
| `src/benchmark/runner.py` | Zanetti | Medição de complexidade (tempo/memória) |
| `src/api/coingecko_client.py` | Heitor | Fonte de dados (cache, retry, mock × ao vivo) |
| `src/arbitrage/graph_builder.py` | Heitor | Construção do grafo a partir das taxas |
| `src/arbitrage/detector.py` | Heitor | Pipeline, deduplicação de ciclos, cálculo de lucro |
| `src/cli.py` · `src/visualize.py` | Heitor | Interface (rich) e visualização interativa (pyvis) |
| `notebooks/analysis.ipynb` | Heitor | Heatmap, grafo, curva de complexidade |
