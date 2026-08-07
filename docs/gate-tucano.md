# Bee-150M × Tucano-160m — o par honesto (2026-08-06)

> # 🔴 DOCUMENTO INVÁLIDO — 2026-08-07
>
> **Todos os números abaixo foram produzidos por um modelo treinado com o objetivo errado.**
>
> `bee/pretrain.py` passava `labels=y` com `y` já deslocado, e o `LlamaForCausalLM` desloca
> de novo por dentro. O Bee foi treinado para prever **t+2**, não o próximo token — e foi
> medido prevendo **t+1**, uma tarefa que nunca aprendeu. Medido no `bee-150m-v3-base`:
>
> | alvo | Bee-150M-v3 | SmolLM2-135M (controle) |
> |---|---:|---:|
> | t+1 (correto) | ppl 898,2 | ppl **16,7** ✅ |
> | t+2 | ppl **130,2** ✅ | ppl 15.388,9 |
>
> O mínimo do Bee está em t+2. Corrigido em `196ed5b`, com guarda que aborta o treino se
> a convenção estiver errada. Some-se a isso que a amostragem descartava 37% do corpus
> (corrigido em `a4aed0e`).
>
> **Nada aqui deve ser usado para decidir nada.** Preservado porque a mecânica do erro
> vale mais que os números — e porque o sinal estava no repositório: o `gate_pareado.py`,
> com o código correto e **75× menos dado**, media bpb 40% melhor.



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

## 🔴 RETRATAÇÃO (mesmo dia, algumas horas depois)

**A seção abaixo afirmava que o número do Tucano estava contaminado e que "dá para provar".
Não estava provado, e a conclusão caiu.** Ver [`holdout-limpo.json`](holdout-limpo.json).

Construí um holdout de web PT em outra série do crawl (`002_00012`, parquet 40) — região que
nenhuma coleta do Bee jamais tocou — e remedi os três modelos. Os números **se reproduzem
dentro de ~1%**:

| modelo | bpb no holdout limpo | bpb em `[7,23]` | diferença |
|---|---:|---:|---:|
| Tucano-160m | **0,884** | 0,896 | +1,3% |
| SmolLM2-135M | **1,551** | 1,560 | +0,6% |
| Bee-150M-v3 | **2,228** | 2,203 | −1,1% |

O padrão que eu usei como prova (vantagem grande em web, quase nula em livros) é real, mas
tem **outra explicação que serve igualmente bem**: o Tucano é *especialista em web PT
moderna* (200B tokens de GigaVerbo, majoritariamente web), e livros de ortografia arcaica com
ruído de OCR são fora de distribuição **para ele também** — enquanto o SmolLM2, com 2T tokens
muito mais diversos, generaliza melhor para texto estranho. É **deslocamento de domínio**,
não memorização. Eu tinha duas hipóteses compatíveis com o mesmo padrão e chamei uma de
provada.

⚠️ **Alcance do teste, para não repetir o erro na direção oposta:** o parquet 40 é limpo em
relação ao **Bee**, não ao Tucano — `fineweb-2` e GigaVerbo derivam os dois do Common Crawl.
Eu **não provei que o Tucano está limpo**; provei que o meu argumento de que estava sujo não
se sustenta. Separar de vez exigiria texto PT posterior ao treino dos dois (2025-2026).

**Consequência para o Bee: piora.** Na régua limpa a distância é **2,52×**, não os 1,88× de
`portuguese-pd`. E o holdout `[7,23]` fica **reabilitado** — reproduz o limpo, logo não estava
viciado.

<details>
<summary>Texto original da seção, preservado (a inferência está errada; o padrão medido não)</summary>

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

</details>

## ⭐ O veredito, nas duas réguas

**Web PT limpa** (parquet 40, `002_00012` — série do crawl que nenhuma coleta do Bee tocou):

| | bpb | vs Bee | fertilidade |
|---|---:|---:|---:|
| Tucano-160m | **0,884** | **2,52× melhor** | 0,2074 |
| SmolLM2-135M | 1,551 | 1,44× melhor | 0,3576 |
| **Bee-150M v3** | **2,228** | — | 0,2183 |

**Livros de domínio público** (`portuguese-pd`, holdout `[7,23]`):

| | bpb | vs Bee |
|---|---:|---:|
| Tucano-160m | 2,204 | **1,88× melhor** |
| SmolLM2-135M | 2,257 | 1,84× melhor |
| **Bee-150M** | **4,148** | — |

**O Bee perde para os dois pares nas duas réguas.** Em web moderna, que é o caso de uso real,
por **2,52×**.

⭐ **A diferença entre as duas tabelas é informação, não ruído.** O Tucano abre 2,52× em web e
só 1,88× em livros; o SmolLM2 faz o inverso relativo (1,44× em web, 1,84× em livros). Isso
desenha os dois perfis com clareza: o Tucano é **especialista em web PT**, o SmolLM2 é
**generalista** que aguenta texto estranho. Nenhum dos dois é "melhor" em abstrato — e o Bee
está atrás dos dois em ambos.

E um detalhe que precisa ser dito: **o tokenizador do Tucano é melhor que o nosso** — 0,2074
contra 0,2183 tok/byte em web PT limpa (5% mais enxuto). O nosso passou o gate contra o
SmolLM2 (0,3576 na mesma régua), mas contra o par certo perde. A "primeira coisa genuinamente
nossa" não é a melhor disponível em PT.

## 🔴 O que este resultado FAZ COM A ESCADA DE SCALING — correção

A escada (medida horas antes, mesmo dia) concluiu: *"o gargalo é o tamanho do modelo, não a
quantidade de dado; 10× mais token compraria 8% de perplexidade; o piso é ~57"*.

**O Tucano contradiz isso.** Mesmo tamanho de modelo, 20× mais token, e é **2,52× melhor em bpb**
em web PT limpa. Se o piso fosse mesmo intransponível para 150M, o Tucano estaria empatado
conosco. Não está — e não está por uma margem grande.

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
| 1 | **poucos tokens de português** (~6,9B contra ~200B) | Tucano, mesmo tamanho, **2,52× melhor em web PT limpa** |
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
1. Coletar PT em volume (fineweb-2 `por_Latn`) — ⚠️ **filtrar em ~10% NÃO**: o gate pareado
   mediu que filtrar dá +1,6% e não cresce com escala, enquanto volume dá +88%. Coletar em
   faixas de qualidade e decidir o corte no treino (ver `bee/coletar_pt_volume.py`)
2. Retreinar o Bee-150M **nesse** corpus — mesmo tamanho, mesmo custo (~$42 a 9,87B, ou mais se
   subir o volume). Isola a variável "dado" sem pagar por "tamanho".
3. Só então decidir o Bee-500M, com a curva de dado já corrigida

Isto também dá o teste que falta: se o Bee-150M em 30B de PT limpo chegar perto do Tucano, a causa
era dado; se não chegar, aí sim é tamanho, e o 500M é o caminho.

## Custo desta medição

RTX A4000, $0,25/h, ~12 minutos, **~$0,05**. As duas rodadas (Tucano + controle SmolLM2) no mesmo
pod, mesmo holdout, mesmo processo.
