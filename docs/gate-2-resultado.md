# Gate 2 — Bee-150M (PT, do zero) × SmolLM2-135M (EN), em holdout PT

**Data:** 2026-07-31 · **Runtime:** Colab L4 · **Script:** [`bee/eval_gate2.py`](../bee/eval_gate2.py)

> A comparação externa que decide a aposta do nicho: **um 150M treinado em português bate
> um 135M treinado em inglês, no português?** A resposta honesta desta rodada: **não — ainda
> não.** E o diagnóstico é o previsto no plano: **falta token.**

---

## ⚡⚡ ATUALIZAÇÃO 2026-08-03 — v3 (corpus 2,6× maior, 1 época): a lição do v2 se confirmou, mas a lacuna continua

**O experimento:** o v2 provou que *mais épocas* não funciona (overfitting). O v3 testou a versão
correta da hipótese: **mais tokens ÚNICOS**. Corpus expandido de 3,74B → **9,87B tokens**,
**1 época só**. **Runtime:** Colab A100 (~8h) → migrado pro **RunPod A100-80GB** (21,76h) após o
Colab esgotar a cota de GPU. 18.816 passos, Liger, `--sem-compilar`. Custo ~$34 de crédito RunPod.

**Perplexidade de validação durante o treino:** 77,4 → 63,0 (queda monotônica, sem platô).

**Resultado — bits por byte (holdout PT limpo, menor = melhor):**

| | tokens únicos | épocas | PT bpb | vs SmolLM2 |
|---|---:|---:|---:|---:|
| **v1** | 3,74B | 1 | **3,460** | −72,2% |
| **v2** | 3,74B | 3 | 3,530 | −75,7% |
| **v3** (este) | **9,87B** | 1 | **3,457** | −72,0% |
| SmolLM2-135M | ~2T | — | **2,010** | — |

**v3 × v2, no MESMO holdout (comparação limpa):**

| fonte | idioma | v3 | v2 | vencedor |
|---|---|---:|---:|:---:|
| fineweb2-por (web) | pt | 2,203 | 2,202 | empate técnico |
| portuguese-pd (livros) | pt | **4,148** | 4,261 | **v3** ⭐ (+0,114) |
| **AGREGADO PT** | | **3,457** | 3,530 | **v3 (+2,1%)** |

Fertilidade idêntica (0,3114) — mesmo tokenizer, como esperado.

### 🟡 Veredito: v3 é o melhor Bee até agora, mas por margem mínima — 2,6× mais token rendeu ~0%

Dois fatos que precisam ser ditos juntos:

1. **O v3 desfez o dano do v2** (+2,1%) e ficou **na frente do v1 por 0,003 bpb** — ou seja, é o
   melhor Bee que já treinamos. A lição "mais tokens únicos > mais épocas" **se confirmou na
   direção**: o ganho veio justamente em `portuguese-pd`, a fonte pequena onde o v2 tinha
   memorizado.
2. **Mas o ganho absoluto é praticamente nulo.** Triplicar o corpus (3,74B → 9,87B) moveu o bpb PT
   de 3,460 → 3,457. **0,1% de melhora para 2,6× mais dado e ~22h de A100.** Isso não é o que a
   hipótese "falta token" previa.

**A leitura honesta:** o diagnóstico do v1 estava certo *em identificar o subtreino*, mas errado
*na magnitude do remédio*. Ir de 3,74B para 9,87B é ainda ~200× menos que os ~2T do SmolLM2 —
estamos comparando "pouco" com "pouquíssimo" dentro da mesma ordem de grandeza de déficit. A curva
de bpb × tokens é logarítmica: nesse regime, 2,6× praticamente não aparece. **Para fechar a lacuna
seria preciso ordem(ns) de magnitude, não fatores pequenos** — e isso muda a economia do projeto.

### O que isso reformula no plano

- **Parar de perseguir bpb com mais token no 150M.** O próximo run "só com mais dados" tende a
  render outro ~0%. O experimento decisivo foi feito e respondeu.
- **Hipóteses que passam a valer mais que "mais token":** (a) **qualidade/composição do corpus**
  — nossa mistura tem 15% de livros PD e ~10% de código, o SmolLM2 usou dado educacional
  altamente filtrado (FineWeb-Edu); (b) **arquitetura/geometria** — o ref `hundred-page-language-models`
  aponta a razão d_model/camadas do Bee (30×576 = 19,2) como muito fora do padrão dos modelos
  reais (85–130); (c) **hiperparâmetros** — LR 3e-3 é ~3× a referência para esta escala.
- **O gate real da próxima fase é outro:** bpb mede o modelo BASE. O plano já previa que
  utilidade se mede **após o SFT**. O v3 é uma base razoável para testar a fase de pós-treino —
  e o estudo de dados sintéticos de gramática PT (`estudo-gramatica-dados-sinteticos-2026-08-03.md`)
  ataca exatamente o que falta ali.

> ⚠️ **Ressalva metodológica desta rodada:** o holdout usou **2 shards {7, 23}** em vez dos 3
> originais {7, 23, 41} — o shard 0041 não baixou (rate-limit do Google Drive após transferir
> 3,2GB). A comparação **v3 × v2 é limpa** (mesmo holdout, mesma execução). Já os números de
> v1/v2 na tabela histórica vêm do holdout de 3 shards, então o "v3 vs v1" tem um asterisco —
> a diferença de 0,003 bpb está dentro do ruído dessa mudança de amostra. O que é sólido:
> **v3 > v2 no mesmo teste**, e **nenhuma das versões chega perto do SmolLM2**.

**Arquivos:** `gate2_v3_vs_smol.json` e `gate2_v3_vs_v2.json` (no pod RunPod). Modelo v3 em
`bee-150m-v3/modelo`.

---

## ⚡ ATUALIZAÇÃO 2026-08-02 — v2 (3 épocas) testado: NÃO fechou a lacuna (na verdade, piorou)

**O experimento:** re-treinar o mesmo Bee-150M por **3 épocas** (11,22B tokens vistos, mesmo
corpus de 3,74B) na A100 + Liger, pra testar a hipótese "falta token". Re-rodamos o Gate 2 nos
mesmos shards {7,23,41}. **Runtime:** Colab A100 · treino 7,63h · perplexidade de treino 72→60,3.

**Resultado — bits por byte (holdout PT limpo, menor = melhor):**

| | PT bpb (agregado) | gap vs SmolLM2 | EN bpb |
|---|---:|---:|---:|
| **v1** (1 época, 3,74B tok) | **3,460** | −72,2% | 3,688 |
| **v2** (3 épocas, 11,22B tok) | **3,530** | **−75,7%** | 3,723 |
| SmolLM2-135M (referência) | 2,010 | — | 0,846 |

**v2 × v1, decomposto por fonte:**

| fonte | idioma | v2 | v1 | vencedor |
|---|---|---:|---:|:---:|
| fineweb2-por (web) | pt | **2,202** | 2,207 | **v2** ⭐ (+0,005) |
| portuguese-pd (livros) | pt | 4,261 | **4,150** | v1 (v2 −0,112) |
| fineweb-edu-en | en | 3,723 | **3,688** | v1 |
| **AGREGADO PT** | | 3,530 | **3,460** | **v1 (−2,0%)** |

### 🔴 Veredito: mais épocas ≠ mais tokens. As 3 épocas OVERFITARAM.

O v2 ficou **2,0% PIOR que o v1 no holdout limpo** em PT, **apesar** da perplexidade de treino
ter caído de 72→60. Isso é a assinatura clássica de **overfitting**: repetir os mesmos 3,74B
tokens 3× fez o modelo **memorizar** melhor o treino (perplexidade de treino cai) mas
**generalizar pior** no texto nunca visto (bpb do holdout sobe).

O padrão por fonte é a prova: no source **grande e diverso** (`fineweb2-por`, 35% do corpus, web),
o v2 melhorou um tiquinho ⭐ — ali ainda havia sinal novo a extrair. No source **pequeno**
(`portuguese-pd`, 15%, livros), o v2 piorou nitidamente — 3 passagens sobre pouca diversidade =
memorização. A média fica negativa.

**A lição que reformula o degrau de escalonamento:** o diagnóstico "falta token" continua
correto, **mas o remédio NÃO é mais épocas — é mais tokens ÚNICOS.** O SmolLM2 venceu porque viu
~535× mais tokens **distintos**, não porque repetiu os mesmos. Reprocessar o 3,74B não fecha nada;
**expandir o corpus** (fineweb-2 `por` tem >1T tokens disponíveis) é o caminho. Épocas ≈ 1 é o
certo pra esta escala; ir a 3 já cobra overfitting no corpus atual.

> Nota honesta: o delta é pequeno (2%) e parte pode ser ruído de 400 docs — mas a **direção é
> consistente** nas duas comparações (v2 perde do SmolLM2 por mais que v1; v2 perde do próprio v1)
> e o padrão fonte-grande-melhora / fonte-pequena-piora é coerente com overfitting, não com acaso.
> O que NÃO aconteceu, com certeza: as 3 épocas **não** aproximaram o Bee do SmolLM2.

**Arquivos:** `gate2_v2_vs_smol.json` e `gate2_v2_vs_v1.json` no Drive (`/MyDrive/BEE/`).
v1 preservado intacto em `bee-150m/`; v2 em `bee-150m-v2/`.

---

## Método (por que estes números valem)

| decisão | por quê |
|---|---|
| **Métrica: bits-por-byte (bpb)**, não perplexidade | Perplexidade só é comparável sob o MESMO tokenizador. O Bee tem vocab 32k próprio; o SmolLM2, 49k. bpb normaliza pela representação em **bytes** (a mesma string = os mesmos bytes p/ os dois) → mede compressão real do texto. Régua canônica (The Pile, GPT-3). |
| **Não múltipla escolha** | Modelo BASE de 150M sem SFT não "responde", só completa texto. MC a 150M fica perto do acaso e já nos enganou uma vez (a `chat_ptbr`). bpb mede o que o base realmente faz: modelar a distribuição do português. |
| **Holdout limpo, contaminação verificada** | Shards `{7, 23, 41}` — os MESMOS que `prepare_data.py` excluiu do treino do Bee (`SHARDS_VAL`). O Bee **nunca viu** este texto; o SmolLM2 também não. Páreo limpo dos dois lados. |
| **Decomposto por fonte + trade-off EN** | A média esconde regressão por fonte (lição recorrente dos estudos). Mede EN também, para expor o preço consciente de concentrar 32k de vocab em PT. |

Amostra: 400 docs por fonte, truncados a 4000 chars, NLL por documento a partir de contexto
frio (mesma penalidade para os dois modelos → comparação justa).

---

## Resultado — bits por byte (menor = melhor)

| fonte | idioma | Bee-150M | SmolLM2-135M | Δ | vencedor |
|---|---|---:|---:|---:|:---:|
| fineweb2-por | pt | 2.207 | **1.560** | −0.646 | SmolLM2 |
| portuguese-pd | pt | 4.150 | **2.257** | −1.893 | SmolLM2 |
| fineweb-edu-en | en | 3.688 | **0.846** | −2.842 | SmolLM2 |
| **AGREGADO PT** | | 3.460 | **2.010** | −1.450 | **SmolLM2 (−72,2%)** |
| **AGREGADO EN** | | 3.688 | **0.846** | −2.842 | SmolLM2 (−336%) |

**Fertilidade** (tokens/byte, menor = tokenizador mais eficiente):
**Bee 0.3107 · SmolLM2 0.3359** → o **tokenizer do Bee venceu** (~7,5% mais eficiente em PT).

---

## Veredito: 🔴 a aposta NÃO se confirmou em bpb

O SmolLM2-135M modela o português **72% melhor** que o Bee-150M, apesar de nunca ter sido
treinado em PT. O Bee perde inclusive nos **livros de domínio público** (`portuguese-pd`),
que estavam no seu próprio corpus de treino (embora não nestes shards específicos).

Sinal revelador: o Bee é **quase igualmente ruim** em PT (3.46) e EN (3.69). Um modelo que
treinou 70% PT / 20% EN deveria ser bem melhor em PT que em EN. A quase-uniformidade indica
um modelo **subtreinado em termos absolutos**, não um modelo PT-forte — coerente com a
perplexidade final de validação **72** (alta; modelos pequenos bem-treinados ficam em 15–25).

### Diagnóstico — é **token**, o caso mais provável (previsto no plano)

O fator dominante é o **abismo de orçamento de treino**:

| | tokens de treino | razão |
|---|---:|---:|
| Bee-150M | **3,74 B** | 1× |
| SmolLM2-135M | **~2 T** | **~535×** |

O SmolLM2 viu ~535× mais tokens. Esse volume dá priors de subword e de modelagem de
sequência tão fortes que **transferem para o português** e superam a vantagem de focar o
nicho. A aposta original assumia treino comparável; na prática não foi comparável — foi
150M @ 3,74 B contra 135M @ 2 T. **Não era para ganhar nesta rodada.**

Não é (principalmente) arquitetura nem dado: a arquitetura Llama-style está correta, o
corpus é PT-forte e limpo, e o **tokenizer até venceu**. O gargalo é volume de treino.

---

## O que o gate entregou (o valor real)

1. **Uma medição externa, limpa e inequívoca** — exatamente o que um gate serve para dar.
   O plano dizia: *"Se perder, o diagnóstico dirá se falta token (o mais provável), dado
   ou arquitetura — e isso informa o próximo degrau em vez de virar frustração."* Foi isso.
2. **O 1º gate (tokenizer) segue de pé** — fertilidade em PT melhor que a do rival. A peça
   genuinamente nossa e mais barata de acertar está certa.
3. **O trade-off EN é o esperado** (−336%): concentrar 32k de vocab em PT cobra em inglês.
   Isso é a aposta funcionando como desenhada, não um defeito.

## Próximo degrau (informado pelo diagnóstico)

O diagnóstico "falta token" aponta para a **escada de escalonamento** do plano — o código é
o mesmo, muda o orçamento:

- **Mais tokens no mesmo 150M** — o caminho mais barato para testar a hipótese de subtreino:
  continuar o pré-treino além de 1 época / expandir o corpus (fineweb-2 `por` tem >1 T tokens
  disponíveis). Re-rodar este mesmo Gate 2 e ver o bpb PT cair. É o experimento decisivo.
- **Degrau de parâmetros** (350M → 500M) só depois — não adianta mais parâmetros com o mesmo
  déficit de tokens.
- **Referência honesta:** igualar um modelo de 2 T tokens exige orçamento de 2 T tokens.
  A conta `tokens × params = dinheiro` do plano continua valendo; o 150M é a esteira que
  roda em qualquer escala, não o produto final.

> ⚠️ **Ressalva:** bpb mede modelagem de linguagem do modelo **base**. Fluência de resposta
> e consistência sob paráfrase só se avaliam **após o SFT** — é o gate da próxima fase.
> Um base fraco em bpb dificilmente vira um chat forte, mas a régua de "útil" é outra.
