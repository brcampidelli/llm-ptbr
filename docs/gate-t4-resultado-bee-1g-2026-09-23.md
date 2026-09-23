# Gate T4 — resultado do Bee-1G no ponto final (2026-09-23)

> Critérios declarados **antes** do run em [`gate-sucesso-bee-1g.md`](gate-sucesso-bee-1g.md) §3.
> Medido no próprio pod do treino (RTX 5090, `transformers` 5.16.1), ~35 min de GPU; **as
> referências foram remedidas na mesma GPU** (§2ae) — o Bee-350M entrou com um diretório de nome
> próprio (`bee-350m-base-5090`) para não sobrescrever os artefatos `base350m` do git (§2z).
> Logs completos em `docs/logs-t4-2026-09-23/`.

**O modelo:** `bee-1g/modelo` · 1,05B parâmetros · vocab 64k multilíngue · **20,0B tokens** (pool
pt-50: ~10B de PT + ~10B em 7 idiomas) · WSD, decaimento nos últimos 20% · 610.353 passos ·
366,4 h · val final **2,8103 (ppl 16,6)** · md5 `6dba7d30…` (conferido na origem e na cópia local).

**Em uma frase:** o 1G **não bateu o 350M em português** (o critério principal) — ficou 1,4% e 0,6%
pior em bpb, com metade dos tokens de PT —, **bateu o Qwen3-0.6B-Base em 5 dos 8 idiomas**
(incluindo PT, espanhol, francês, árabe e japonês), **empatou ou regrediu pouco** nas capacidades
do base, e saiu do decaimento **bem mais afiado** que o platô (a previsão do 2609.08966).

---

## 3.1 Português — bpb · ❌ REPROVADO

| modelo | `wiki/limpo` | `corpus_multi_pt/limpo` | tokens PT vistos |
|---|---:|---:|---:|
| **Bee-1G final** | **0,9370** | **0,9105** | ~10B |
| Bee-350M = âncora | 0,9239 | 0,9052 | 21,75B |
| diferença do 1G | **+1,4%** | **+0,6%** | |
| Qwen3-0.6B-Base (externo) | 0,9423 | 1,0986 | — |
| `marco_15B` (controle de hardware) | 1,0467 | 1,0366 | ~7,5B |

**A régua é boa (§2aa + §2ae):** o 350M reproduziu as âncoras publicadas (0,9239 × 0,9240;
0,9052 × 0,9052) e o `marco_15B` mediu 1,0467 na 5090 contra 1,0468 na 5070. A diferença é do
modelo.

**Leitura — hipótese, não conclusão:** o critério pedia ≤ 350M e o 1G viu **metade** do português
do 350M (~10B contra 21,75B), dividindo capacidade com 7 idiomas e um vocab de 64k multilíngue
contra os 32k especializados em PT. O decaimento tirou −0,110 de bpb do platô de 15B; não bastou.
O que o experimento **não** separa: se a falta é de token de PT, de fatia do vocab, ou de disputa de
capacidade entre idiomas (o gate T2 mediu a troca "3,5× a favor do PT" em mini-runs, não neste
regime). ⚠️ E o 1G bate o Qwen3-0.6B (36T tokens) em PT nas duas réguas.

## 3.2 Os outros idiomas — bpb por coluna · 5 de 8 ≤ Qwen3-0.6B

Holdout `sha1 % 100 < 2` do `corpus_multi`, 1,5 MB por idioma (limpo para o 1G: a metade não-PT do
pool foi filtrada pelo mesmo balde, `tokenizar_naopt_1g.py`). **Ler por coluna, nunca entre
colunas** (2608.25089).

| | por | spa | fra | deu | eng | arb | cmn | jpn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Bee-1G final** | **0,866** | **0,940** | **0,979** | 1,558 | 1,091 | **0,836** | 1,475 | **0,939** |
| Qwen3-0.6B-Base | 1,022 | 0,992 | 1,004 | **1,546** | **0,923** | 0,930 | **1,361** | 0,955 |
| Bee-350M (vocab PT) | 0,858 | 1,210 | 1,568 | 2,422 | 1,337 | 1,969 | 3,303 | 2,254 |
| piso gzip | 3,061 | 3,037 | 3,042 | 3,392 | 3,189 | 2,248 | 3,855 | 2,885 |
| 1G ≤ Qwen? | ✅ −15% | ✅ −5% | ✅ −2% | ❌ +0,8% | ❌ **+18%** | ✅ −10% | ❌ +8% | ✅ −2% |

⚠️ A coluna `por` aqui é o `corpus_multi` PT **completo** (inclui os 56% contaminados no 350M) — o
critério de PT é a §3.1. ⚠️ Inglês é a maior perda (+18%): é o idioma em que o Qwen tem mais dado,
e o gate já avisava que perder para um vocab de 150k em CJK pode ser tokenizador (a §3.3, NLL em
corpus paralelo, não foi rodada — fica em aberto).

## 3.5 Capacidades do base — sem `--chat` · empate ou regressão pequena; sentimento reprova

| capacidade | Bee-1G | Bee-350M (5090) | 350M publicado (5070) | piso | critério |
|---|---:|---:|---:|---:|---|
| tradução en→pt chrF2 | 50,85 | 51,31 | 51,12 | 21,5 | ≥ 350M → **−0,46, empate na prática** |
| tradução pt→en chrF2 | 40,41 | 42,57 | 43,30 | 22,7 | ≥ 350M → ❌ **−2,2** |
| tradução pt→en idioma-alvo | **91%** | 86% | — | | (o 1G responde mais em inglês) |
| resumo — cobertura | **88,0%** | 83,3% | 84,0% | — | ✅ +4,7 |
| resumo — sem invenção | **84,7%** | 70,0% | — | — | ✅ +14,7 |
| resumo — útil | 0,0% | 0,0% | 0,0% | 51,3% | sem critério |
| atendimento — útil | 0,0% | 0,0% | 0,0% | 60,4% | sem critério (1G inventa 5,6% × 0,8%) |
| sentimento (logprob) | **43,5%** | 49,7% | 49,7% | **79,0%** | ❌ **abaixo do piso léxico** (revocação do negativo 1%) |
| IFEval-PT estrito/instrução | 30,2% | 30,9% | 30,4% | — | ✅ −0,7 (ruído 2,3 pp) |
| código pass@1 (interno / HumanEval-XL) | 0% / 0% | 0% / 0% | 0% | — | sem critério |
| agêntico (holdout antigo) | 0/85 | 0/85 | 0/85 | — | sem critério |
| matemática pass@256 | **não medida** | — | 44/200 | — | fica para outra rodada (5–7 h de pod) |

O 350M remedido na 5090 ficou a ≤0,7 do publicado em todas as réguas — a deriva de hardware é
menor que qualquer diferença lida acima, exceto en→pt, que por isso fica como empate.

## Densidade de solução — decaído × platô 15B (2609.08966)

Mesmas 100 amostras de ruído, pod-com-pod, guarda §2aa ok nos dois.

| σ (absoluto) | ΔL mediana final | ΔL 15B | final pior em | densidade τ=0,90 final / 15B |
|---:|---:|---:|---:|---|
| 0,01 | +6,22 | +0,31 | 100/100 | 0% / 0% |
| 0,005 | +0,69 | +0,074 | 100/100 | **0% / 100%** |
| 0,001 | +0,026 | +0,003 | 100/100 | 100% / 100% |

⚠️ **Confusor declarado:** o desvio mediano dos pesos 2D caiu de **0,0498 (15B) para 0,0271
(final)**. Com σ absoluto, a mesma perturbação é ~1,8× maior, em proporção, no final. Corrigindo
pela escala (ΔL ÷ (σ/std)²): **~19–20 no final contra ~7,3–7,7 no 15B — ~2,6× mais curvo**, não
9–20×. Comparação sem modelo quadrático: com σ/std quase igual (0,18 × 0,20), a loss do final sobe
0,69 contra 0,31. **A direção é inequívoca; a magnitude é ~2,6×.** E a queda de 46% na escala dos
pesos em 5B tokens de decaimento **não está explicada** — a investigar antes de usar este número
para decidir qualquer coisa além da direção.

**Implicação para o pós-treino:** não assumir que o checkpoint de melhor loss é o melhor ponto de
partida. O teste que decide é barato — SFT do 15B contra SFT do final, mesma receita, 3 sementes.

## G-C4 — calibração do base no holdout agêntico (texto cru)

| | Noul "chamar?" | Choice "qual ferramenta?" acc · ECE · AUROC | acaso / "sempre a 1ª" |
|---|---|---|---|
| **Bee-1G** | nunca chama (under-call 100%) | **0,622 · 0,084 · 0,761** | 0,280 / 0,295 |
| Bee-350M | nunca chama (under-call 100%) | 0,374 · 0,298 · 0,640 | 0,280 / 0,295 |

O Noul não tem leitura num base (ele não sabe o formato de chamada — §2e). O **Choice** tem: com
o prefixo `{"tool": "` dado, o 1G escolhe a ferramenta certa em 62% (acaso 28%) **e calibrado**
(ECE 0,08, AUROC 0,76); o 350M mal sai do acaso e é descalibrado. **A escala comprou seleção e
calibração no base** — o SFT agêntico do 1G parte de um ponto bem melhor que o do 350M. Não há
evidência aqui que justifique RL de calibração (G-C6 continua fora da fila).

## 3.6 Throughput e custo · ✅

15,0k tok/s sustentado contra 14,47k do gate (≥ 13,0k); 366,4 h × US$ 1,00 ≈ **US$ 366** por 20B
= **US$ 18,3/B** contra 19,00 projetado.

## O que ficou de fora — declarado

§3.3 (NLL em FLORES paralelo), §3.4 fora de en↔pt (6 pares FLORES), matemática pass@256. Nenhum
deles muda o veredito da §3.1; os dois primeiros separariam "tokenizador" de "modelo" na §3.2.
