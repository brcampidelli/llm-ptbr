# Gate 2 — Bee-150M (PT, do zero) × SmolLM2-135M (EN), em holdout PT

**Data:** 2026-07-31 · **Runtime:** Colab L4 · **Script:** [`bee/eval_gate2.py`](../bee/eval_gate2.py)

> A comparação externa que decide a aposta do nicho: **um 150M treinado em português bate
> um 135M treinado em inglês, no português?** A resposta honesta desta rodada: **não — ainda
> não.** E o diagnóstico é o previsto no plano: **falta token.**

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
