# FineWeb-Edu em português — resultado (2026-08-04)

Replicação das três etapas da receita do FineWeb-Edu para o português, para testar a **única
hipótese que sobrou** sobre a saturação do Bee: qualidade e composição do corpus.

## Por que esta era a hipótese viva

O Gate 2 mostrou que o Bee não está na curva de scaling — triplicar o corpus deveria cortar 23,8%
da loss redutível e cortou 0,1%. Ao longo de 2026-08-04, as alternativas caíram uma a uma:

| hipótese | status | evidência |
|---|---|---|
| geometria | ❌ refutada | `config.json` do SmolLM2-135M e do MobileLLM-125M são idênticos ao do Bee |
| LR de pré-treino | ❌ refutada | Step Law dá 3,09e-3 para N=151M/D=9,87B; usamos 3e-3 |
| medidor de bpb com viés | ❌ auditado | truncamento em 4.000 chars não dispara; holdout limpo |
| duplicata no corpus | ❌ eliminada | 0,90% cruzando a fronteira = 0,09B de 9,87B |
| pós-treino mal ajustado | ❌ espremido | varredura de LR fechada; eval_loss −44% e os fatos continuam errados |
| **qualidade do corpus** | ⭐ **viva** | é o que sobrou |

## As três etapas

**1. Anotar** (`bee/anotar_edu.py`) — 2.828 docs do `fineweb-2 por_Latn` anotados de 0 a 5 pelo
professor aberto `deepseek/deepseek-v3.2`, com rubrica aditiva **reescrita em PT-BR** (não
traduzida: tradução arrasta o critério da língua de origem). Distribuição: 39% nota 0, 37% ≥3.

**2. Treinar** (`bee/treinar_classificador_edu.py`) — TF-IDF palavra + caractere → Ridge (nota) e
regressão logística (manter/descartar). Holdout por `sha1`, não por posição. CPU, segundos.

TF-IDF **de propósito** como baseline honesto: se ele já separa, embedding neural só melhora; se
não separasse, o problema seria o **sinal**, não a representação — e embedding caro não salvaria.

**3. Aplicar** — corte por percentil sobre o score do regressor.

## O classificador separa em português

| | |
|---|---:|
| correlação de Pearson com o professor | **0,705** |
| erro absoluto médio | 0,941 (baseline "chuta a média": 1,451) — **−35%** |
| F1 da decisão binária em ≥3 | 0,723 · acurácia 78,0% |

## ⭐ A curva que decide o corte

Ranking do regressor, corte por percentil, medido no holdout:

| mantém | nota média | ganho | ≥3 | ≥4 |
|---:|---:|---:|---:|---:|
| 100% | 1,66 | — | 38% | 15% |
| 60% | 2,41 | +0,74 | 59% | 24% |
| 41% | 2,87 | +1,21 | 74% | 34% |
| 30% | 3,08 | +1,42 | 79% | 43% |
| 19% | 3,33 | +1,67 | 85% | 51% |
| **10%** | **3,70** | **+2,03** | **91%** | 68% |
| 5% | 3,82 | +2,16 | 93% | 71% |

**O joelho está em ~10%** — exatamente o regime do FineWeb-Edu original (~9%). De 19% para 10% a
nota média sobe +0,37; de 10% para 5%, só +0,12 pela metade dos dados.

⚠️ **Não usar o classificador binário em corte 4.** Ele mantém 19% com precisão de 0,514 — metade
do que guarda seria rejeitado pelo professor. É artefato do `class_weight="balanced"`, que empurra
recall à custa de precisão. O **ranking do regressor** no mesmo 19% entrega 85% de ≥3. Mesma
retenção, muito menos ruído.

## ⚠️ A conclusão desconfortável: filtrar sozinho NÃO resolve

No regime certo (~10%), os **9,87B tokens do v3 viram ~1B**. E o par honesto do Bee, o
**Tucano-160m**, treinou em **200B**.

Ou seja: filtrar o corpus que temos nos deixa com **menos** token, não mais. A lição do FineWeb-Edu
é que corpus filtrado bate corpus 10× maior — o que colocaria 1B filtrado no páreo de ~10B cru, que
é aproximadamente o que já temos. **Empate, não salto.**

⭐ **O plano que decorre disso:** filtrar não substitui coletar, multiplica. Para chegar a ~10B
tokens de alta qualidade é preciso um pool bruto de **~100B** e aplicar o corte de 10%. O
`fineweb-2 por_Latn` tem 66 parquets e usamos uma fração — a escala existe na fonte. O custo real
passa a ser a **anotação em escala**, e é por isso que o benchmark de professores importa:

| professor | formato | concorda com v3.2 | \|dif\| | custo |
|---|---:|---:|---:|---|
| `ling-3.0-flash:free` | 88% | 63% | 0,49 | **grátis** |
| `nemotron-3-super:free` | 92% | 62% | 0,57 | **grátis** |
| `nemotron-3-ultra:free` | 90% | 61% | 0,58 | **grátis** |
| `mistral-nemo` | 52% | 48% | 0,76 | pago |
| `gemma-4-31b:free` | 0% | — | — | — |
| `qwen3.5-flash` | 0% | — | — | — |

⚠️ **`deepseek-v4-flash-0731` custa $0,18/M — metade do v3.2 — e sai ~6× MAIS CARO na prática:**
gasta **384 tokens** de raciocínio para dar uma nota que cabe em **27**. Modelo de reasoning cobra o
raciocínio; em tarefa estruturada curta isso domina o custo. Só compensaria se o v3.2 passasse de
$2,56/M de saída.

## Próximo passo, e o gate

1. Coletar pool bruto grande de `fineweb-2 por_Latn` (a fonte tem escala)
2. Anotar em volume com professor **gratuito** (`ling-3.0-flash` ou `nemotron-3-super`)
3. Retreinar o classificador com a anotação maior
4. Filtrar em ~10% → alvo de ~10B tokens de alta qualidade
5. ⭐ **Gate pareado barato antes do run longo**: treinar dois Bees pequenos e curtos — um no corpus
   cru, outro no filtrado, mesmo orçamento de tokens — e comparar bpb. ~5% do GPU-hora.
   **Teria matado o v3 por ~R$ 50** em vez de US$ 34 e 22 h.

O gate 5 é o que realmente testa a hipótese. Tudo antes dele é preparação.
