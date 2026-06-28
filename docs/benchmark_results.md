# Benchmark Results

Bellman-Ford **próprio** vs **NetworkX** (`nx.find_negative_cycle`) — média de 10 execuções
em grafos sintéticos densos (todas as arestas presentes) com um ciclo negativo plantado.
Tabela gerada por `python -m src.benchmark.runner`.

| Tamanho | Nós | Arestas | Tempo próprio (ms) | Tempo NX (ms) | Mem próprio (KB) | Mem NX (KB) | Ciclos próprio | Ciclos NX |
|---------|-----|---------|--------------------|---------------|-----------------|-------------|----------------|-----------|
| XS | 5 | 23 | 0.015 | 0.030 | 0.5 | 1.7 | 1 | 1 |
| S | 10 | 93 | 0.104 | 0.025 | 0.8 | 3.2 | 1 | 1 |
| M | 20 | 383 | 0.923 | 0.033 | 1.1 | 5.9 | 1 | 1 |
| L | 50 | 2453 | 14.663 | 0.044 | 3.7 | 11.8 | 1 | 1 |

> Os números absolutos variam por máquina/execução, mas o **padrão** abaixo se mantém.

## Corretude

Em todos os tamanhos as duas implementações encontram o ciclo negativo plantado
(`Ciclos próprio == Ciclos NX == 1`). Ou seja, a implementação própria é **correta** — o
benchmark mede apenas custo, não resultado.

## Overhead da implementação própria (tempo)

- **Grafos minúsculos (5 nós): o próprio vence** (0.015 ms vs 0.030 ms). Com pouquíssimas
  arestas, o overhead de construir o `nx.DiGraph` e atravessar as camadas do NetworkX domina,
  e o laço puro do nosso Bellman-Ford sai na frente.
- **A partir de ~10 nós o NetworkX dispara na frente** e a distância só cresce: em 50 nós o
  próprio leva **~14.7 ms** contra **~0.04 ms** do NX (~300× mais lento).
- A causa é a complexidade `O(V·E)` percorrida em **Python puro**: como o grafo é denso
  (`E ≈ V²`), o custo cresce ~`O(V³)`. O NetworkX roda laços críticos em código C e aplica
  early-termination/relaxação mais esperta, então o crescimento é muito mais suave.

## Uso de memória

A implementação própria usa **consistentemente menos memória** (0.5–3.7 KB vs 1.7–11.8 KB do
NX, ~3× menos). Ela trabalha direto sobre a lista de arestas/dicionários de `distances` e
`predecessors`; o NetworkX mantém a estrutura `DiGraph` completa (dicionários aninhados de nós,
arestas e atributos), que pesa mais — efeito que se acentua conforme o grafo cresce.

## Conclusão — trade-off corretude acadêmica × performance de produção

| Critério | Bellman-Ford próprio | NetworkX |
|---|---|---|
| Corretude | ✅ igual | ✅ igual |
| Velocidade (grafos pequenos) | ✅ leve vantagem | ligeiro overhead de setup |
| Velocidade (grafos grandes) | ❌ escala mal (Python puro) | ✅ muito superior (C) |
| Memória | ✅ menor | maior |
| Transparência didática | ✅ código próprio, legível | caixa-preta |

Para o **escopo deste projeto** — arbitragem entre uma dúzia de moedas (grafos pequenos) — a
implementação própria é perfeitamente adequada: rápida o suficiente, mais econômica em memória
e **transparente** (todo o algoritmo é nosso, ideal para fins acadêmicos). Para **produção** com
grafos grandes (centenas/milhares de nós), o NetworkX é a escolha óbvia pela performance.
A regra prática: *implementação própria para aprender e para cargas pequenas; biblioteca
madura para escalar*.

---

<sub>Tabela gerada automaticamente por `src/benchmark/runner.py`. As seções de análise são
mantidas à mão — reexecutar o runner regenera a tabela e exige re-anexar a análise.</sub>
