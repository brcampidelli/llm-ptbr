# Escada de scaling do Bee-150M — em andamento (2026-08-05)

Mede **quanto de perplexidade cada 10x de token compra**, para decidir se o run
grande (~100B tokens, ~$250) se justifica. Custo da escada: ~$18 pelos dois
primeiros pontos, contra os $250 que ela ajuda a decidir.

## Pontos

| tokens | perplexidade de validação | status |
|---:|---:|---|
| 1,00B | **115,2** | ✅ 4,41 h · RTX 5090 · ~$4,4 |
| 3,00B | — | 🔄 ~13,6 h |
| 9,87B | 63,0 | ✅ v3 (histórico) |

⭐ **Todos os pontos saem do MESMO `train.bin`**, mesma ordem, mesmo tokenizador,
mesma GPU, mesmo batch global (524k tok/passo). A única variável é o orçamento de
tokens — é isso que torna a inclinação interpretável.

De 1B para 9,87B (10x) a perplexidade caiu 45%, o que dá expoente ~0,26 em
`L(D)` — próximo do 0,28 da literatura. O ponto de 3B é o que testa se a reta em
log-log se sustenta ou dobra.

## Hardware — medido, não estimado

| | throughput | $/h | **$ / bilhão de tokens** |
|---|---:|---:|---:|
| A100 SXM (v3) | ~70k tok/s | $1,59 | $6,31 |
| **RTX 5090** | **64k tok/s** | **$0,99** | **$4,30** |

A 5090 entrega 91% da A100 por 62% do preço. ⚠️ Eu havia estimado "60-80% da
A100" e errei para baixo — daí a regra: **medir throughput antes de dimensionar
custo**, nunca extrapolar de especificação.

⚠️ Benchmark isolado deu 78k tok/s; em produção são 64k. A diferença é o
grad_accum (sincronização por passo) e a leitura do `train.bin` no volume de
rede. **Não usar número de benchmark para orçar run longo.**

## PENDENTE — medir a A40 antes do run grande

A40: 48 GB, **$0,44/h** (menos da metade da 5090), disponível em EUR-IS-1.

Estimativa (NÃO medida): banda de memória ~696 GB/s contra ~1790 da 5090, ou
seja ~39%. Se render ~40% do throughput, sai a ~$1,09/B contra $0,86 — mais cara
no que importa. **Mas isto é exatamente o tipo de previsão que errei hoje com a
5090**, então medir antes de descartar.

⚠️ **Por que NÃO trocar no meio da escada:** os pontos precisam diferir só no
volume de tokens. Rodar 1B na 5090 e 3B numa A40 misturaria hardware com escala e
contaminaria a inclinação — o mesmo cuidado do gate pareado.

**Quando medir:** ao decidir o run grande, que é experimento novo e sem
pareamento. Se a A40 render melhor que os 40% supostos, 100B a $0,44/h muda a
conta de ~$250 para bem menos.
