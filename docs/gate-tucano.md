# Bee-150M × Tucano-160m — o par honesto (2026-08-06)

O Gate 2 comparou o Bee com o **SmolLM2-135M**, um modelo *inglês*. Comparação injusta nos dois
sentidos: ele tem 200× mais token, mas não foi feito para português. O par de verdade é o
**Tucano-160m** — mesmo tamanho, mesma língua, feito no Brasil.

| | Bee-150M v3 | Tucano-160m | SmolLM2-135M |
|---|---:|---:|---:|
| parâmetros | 151,2M | **162,4M** | 135M |
| tokens de treino | 9,87B (~70% PT) | ~200B (GigaVerbo, **100% PT**) | ~2T (inglês) |
| licença | — | Apache-2.0 | Apache-2.0 |

⚠️ O card do Tucano dá 320k passos e ctx 2048 mas **não dá o batch**, então "~200B" é a ordem de
grandeza (o GigaVerbo inteiro, ~1 época), não um número exato.

## Resultado — bits por byte, holdout [7,23], menor = melhor

| fonte | Bee-150M | **Tucano-160m** | SmolLM2-135M |
|---|---:|---:|---:|
| `fineweb2-por` (web, Common Crawl) | 2,203 | **0,896** | 1,560 |
| `portuguese-pd` (livros domínio público) | 4,148 | **2,204** | 2,257 |
| **AGREGADO PT** | **3,457** | **1,739** | 2,010 |
| fertilidade (tokens/byte) | 0,3114 | **0,2907** | 0,3938 |

⭐ **Controle de sanidade que valida a medição:** o bpb do Bee saiu **3,457** nas duas rodadas
(contra o Tucano e contra o SmolLM2), reproduzindo exatamente o valor medido em 2026-08-03 numa
GPU diferente (A100 → RTX A4000). O aparato está correto.

## ⚠️ O número agregado do Tucano está contaminado — e dá para provar

`0,896 bpb` num modelo de 162M é bom demais. A prova é comparar a vantagem do Tucano sobre o
SmolLM2 **fonte por fonte**:

| fonte | risco de contaminação | Tucano vs SmolLM2 |
|---|---|---:|
| `fineweb2-por` (Common Crawl) | **alto** — o GigaVerbo agrega brWaC/OSCAR/CulturaX, todos derivados de CC | **−42,6%** |
| `portuguese-pd` (livros PD do PleIAs) | **baixo** — não faz parte do GigaVerbo | **−2,3%** |

Se a vantagem do Tucano viesse de saber português de verdade, apareceria nas **duas** fontes. Ela
aparece esmagadora onde ele provavelmente **memorizou o texto** e praticamente some onde não
memorizou. Isso é assinatura de contaminação, não de capacidade.

**Consequência metodológica:** contra o SmolLM2 (modelo inglês, corpus inglês) o agregado servia.
Contra um modelo PT treinado em web PT, **a linha de `portuguese-pd` é a única régua limpa.**

## ⭐ O veredito, na régua limpa

Em `portuguese-pd`, onde ninguém memorizou nada:

| | bpb | vs Bee |
|---|---:|---:|
| **Bee-150M** | **4,148** | — |
| Tucano-160m | 2,204 | **1,88× melhor** |
| SmolLM2-135M | 2,257 | 1,84× melhor |

**O Bee perde para os dois pares, por quase o dobro, em texto que nenhum deles viu.** A
contaminação do Tucano não salva o Bee — só corrige o tamanho da derrota (de 98,8% para 88%).

E um detalhe que precisa ser dito: **o tokenizador do Tucano é melhor que o nosso** (0,2907 contra
0,3114 tokens/byte, 7% mais enxuto). O nosso passou o gate contra o SmolLM2 (0,3938), mas contra o
par certo ele perde. A "primeira coisa genuinamente nossa" não é a melhor disponível em PT.

## 🔴 O que este resultado FAZ COM A ESCADA DE SCALING — correção

A escada (medida horas antes, mesmo dia) concluiu: *"o gargalo é o tamanho do modelo, não a
quantidade de dado; 10× mais token compraria 8% de perplexidade; o piso é ~57"*.

**O Tucano contradiz isso.** Mesmo tamanho de modelo, 20× mais token, e é **1,88× melhor em bpb**
em texto limpo. Se o piso fosse mesmo intransponível para 150M, o Tucano estaria empatado conosco.
Não está.

Onde a escada errou:

1. ⚠️ **A extrapolação nunca foi testável, e eu avisei disso — mas mesmo assim tirei conclusão
   forte dela.** O ajuste `E + A·D^-α` tinha 3 parâmetros e 3 pontos: zero graus de liberdade,
   cobrindo uma única década (1B→10B). O "piso E = 4,04" era **artefato do ajuste**, não medição.
   O Tucano é um ponto empírico a 200B que o derruba.
2. ⭐ **A escada mediu a saturação do NOSSO corpus, não do português.** Todos os três pontos usaram
   a mesma mistura. O que ela mostrou é que **aquela mistura** se esgota perto de 10B — o que é
   informação valiosa, mas não é o mesmo que "modelos de 150M se esgotam perto de 10B".
3. ⭐ **A conta de tokens PT estava errada por um fator de 1,4.** Nosso corpus é ~70% português:
   de 9,87B tokens, só **~6,9B são PT**. O Tucano tem ~200B, todos PT. São **~29× mais português**,
   não 20×. E os outros 30% (inglês + código) ocupam capacidade de um modelo minúsculo em algo que
   **nunca medimos**.

## O que realmente está errado com o Bee, em ordem

| # | causa | evidência |
|---|---|---|
| 1 | **poucos tokens de português** (~6,9B contra ~200B) | Tucano, mesmo tamanho, 1,88× melhor |
| 2 | **30% da capacidade gasta em EN + código** que nunca avaliamos | mistura 70/20/10 por design |
| 3 | qualidade/diversidade do corpus | escada satura em ~10B na nossa mistura |
| 4 | tamanho do modelo | terceiro fator, não o primeiro |

## O que isto muda na decisão do dinheiro

A recomendação anterior — "gastar ~$140 num Bee-500M no mesmo corpus" — **fica enfraquecida**. Um
500M treinado nos mesmos ~6,9B tokens de português herdaria a causa nº 1 intacta.

⭐ **A mudança de maior alavancagem não custa GPU:** mudar a mistura para ~100% português e
aumentar o volume de PT. O `fineweb-2 por_Latn` tem 66 parquets, ~158B tokens crus estimados — a
escala existe na fonte, e é **download, não aluguel**. É exatamente para isso que o pipeline
FineWeb-Edu-PT foi construído.

**Ordem revisada:**
1. Coletar PT em volume (fineweb-2 `por_Latn`) e filtrar em ~10% → alvo de 30-50B tokens **100% PT**
2. Retreinar o Bee-150M **nesse** corpus — mesmo tamanho, mesmo custo (~$42 a 9,87B, ou mais se
   subir o volume). Isola a variável "dado" sem pagar por "tamanho".
3. Só então decidir o Bee-500M, com a curva de dado já corrigida

Isto também dá o teste que falta: se o Bee-150M em 30B de PT limpo chegar perto do Tucano, a causa
era dado; se não chegar, aí sim é tamanho, e o 500M é o caminho.

## Custo desta medição

RTX A4000, $0,25/h, ~12 minutos, **~$0,05**. As duas rodadas (Tucano + controle SmolLM2) no mesmo
pod, mesmo holdout, mesmo processo.
