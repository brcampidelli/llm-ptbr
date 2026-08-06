# Escada de scaling do Bee-150M — FECHADA (2026-08-06)

Mede **quanto de perplexidade cada 10x de token compra**, para decidir se o run
grande (~100B tokens) se justifica. Custo da escada: **~$17** pelos dois pontos
novos, contra os ~$430 que ela decide.

**Veredito: NÃO rodar 100B tokens no 151M.** A curva dobra cedo e forte. Os
detalhes abaixo.

## Os três pontos

| tokens | loss de validação | perplexidade | custo |
|---:|---:|---:|---|
| 1,00B | 4,7463 | **115,2** | 4,4 h · RTX 5090 · ~$4,4 |
| 3,00B | 4,3200 | **75,2** | 12,9 h · RTX 5090 · ~$12,8 |
| 9,87B | 4,1431 | **63,0** | v3, A100, 21,8 h · ~$34 |

### ⭐ Por que os três são comparáveis (conferido linha a linha nos logs)

| | v3 (9,87B) | 1B | 3B |
|---|---|---|---|
| parâmetros | 151,2M · vocab 32000 | idêntico | idêntico |
| seq_len | 2048 | 2048 | 2048 |
| batch global | 64×4×2048 = **524k tok/passo** | 8×32×2048 = **524k** | 8×32×2048 = **524k** |
| LR | 3e-3 cosine → 3e-4 | idêntico | idêntico |
| holdout de validação | **185,2M tok** | idêntico | idêntico |
| épocas | 1,00 | 1,00 (prefixo) | 1,00 (prefixo) |

As duas únicas diferenças são `--sem-liger` (kernel fundido — muda velocidade,
não a matemática) e A100 vs 5090 (bf16 nas duas). **Nenhuma altera o número.**

⚠️ Os pontos de 1B e 3B leem o **prefixo** do mesmo `train.bin`, na mesma ordem.
Isso é a construção certa para uma escada de dados — e vale porque o corpus foi
embaralhado na montagem. Se não tivesse sido, o ponto de 1B mediria "as primeiras
fontes", não "menos dados".

## ⭐ A curva dobra, e dobra feio

Expoente medido entre pontos consecutivos:

| trecho | fator de tokens | queda de perplexidade | expoente |
|---|---:|---:|---:|
| 1B → 3B | 3,0× | −34,7% | **0,39** |
| 3B → 9,87B | 3,3× | −16,2% | **0,15** |

O expoente **cai pela metade e meia** num único degrau. Ajustando
`L(D) = E + A·D^-α` aos três pontos:

```
E = 4,042   (piso irredutível → perplexidade ~57)
A = 0,705
α = 0,845
```

⚠️ **Três parâmetros em três pontos = zero graus de liberdade.** O ajuste passa
exato por construção; não há resíduo para checar. Ele descreve os dados, não os
valida. Mas o fato bruto não depende de ajuste nenhum: **1B→3B cortou 40 pontos
de perplexidade; 3B→9,87B cortou 12.** Para 100B valer a pena, a curva teria que
se desdobrar — e nada indica isso.

### O que a extrapolação diz

| tokens | perplexidade prevista | ganho sobre o v3 |
|---:|---:|---:|
| 9,87B (hoje) | 63,0 | — |
| 20B | 60,2 | −4,4% |
| 30B | 59,2 | −6,0% |
| **100B** | **57,7** | **−8,4%** |
| ∞ | 56,9 (o piso E) | −9,7% |

**10× mais token compra 8% de perplexidade.** E o piso teórico deste modelo neste
corpus é ~57 — mesmo com tokens infinitos. Não há run longo que salve.

⚠️ **A extrapolação é o elo fraco, e não dá para testá-la.** Só temos 9,87B
tokenizados; qualquer 4º ponto seria *interpolado* (ex.: 0,3B ou 5,5B) e testaria
a forma da curva onde já sabemos, não o extremo que importa. Um ponto de 0,3B
custa ~$1,30 — barato, mas responde a pergunta errada. **Não gastar.**

## O que isto significa: o gargalo é o MODELO, não o dado

Chinchilla-ótimo para N=151M é ~3B tokens (20×N). O v3 está em **9,87B = 65×N**,
ou seja **3,3× além do ponto ótimo**. A escada confirma exatamente onde a teoria
diz que os retornos morrem — e é o **terceiro** sinal independente apontando para
o mesmo lugar:

| medição | o que disse |
|---|---|
| Gate 2 (bpb) | 2,6× mais token → ~0% de ganho em bpb |
| Gate pareado (131M tok) | filtrar dá +1,6%, real, mas **não cresce com escala** |
| **Escada de scaling** | **expoente 0,39 → 0,15; piso de perplexidade em ~57** |

## ⭐ Onde gastar os ~$430

Compute ∝ N×D. O run de 151M @ 100B equivale, no mesmo orçamento, a:

| alternativa | Chinchilla-ótimo | posição |
|---|---:|---|
| **Bee-500M @ 30B tok** | 10B | 3× sobre-treinado — mesmo recipe do Bee atual ✅ |
| Bee-1B @ 15B tok | 20B | sub-treinado ⚠️ |
| Bee-150M @ 100B | 3B | **33× sobre-treinado** ❌ |

**Recomendação: Bee-500M em ~30B tokens.** Mesmo código, só o config muda — é
literalmente o degrau que o plano já previa.

⚠️ **O bloqueio agora é dado, não dinheiro:** temos 9,87B tokens e o degrau pede
~30B. É aqui que o filtro FineWeb-Edu-PT volta a importar — pool bruto de ~300B
do `fineweb-2 por_Latn` (a fonte tem 66 parquets, ~158B tokens crus estimados) e
corte em 10%. Coletar e filtrar vem **antes** de alugar GPU.

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

⚠️ **Correção de orçamento:** este documento estimava o run de 100B em ~$250.
Com o custo medido de $4,30/B, o número real é **~$430** na 5090. Errei para
baixo duas vezes seguidas nesta sessão (custo do run e throughput da GPU) —
sempre otimista. Tratar minhas estimativas de custo como piso, não como centro.

## PENDENTE — medir a A40 antes do run grande

A40: 48 GB, **$0,44/h** (menos da metade da 5090), disponível em EUR-IS-1.

Estimativa (NÃO medida): banda de memória ~696 GB/s contra ~1790 da 5090, ou
seja ~39%. Se render ~40% do throughput, sai a ~$1,09/B contra $0,86 — mais cara
no que importa. **Mas isto é exatamente o tipo de previsão que errei com a
5090**, então medir antes de descartar.

⚠️ **Por que NÃO se trocou hardware no meio da escada:** os pontos precisam
diferir só no volume de tokens. Rodar 1B na 5090 e 3B numa A40 misturaria
hardware com escala e contaminaria a inclinação — o mesmo cuidado do gate
pareado.

**Quando medir:** ao decidir o Bee-500M, que é experimento novo e sem pareamento.
