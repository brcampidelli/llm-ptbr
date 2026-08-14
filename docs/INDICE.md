# Índice da documentação do Bee

56 arquivos `.md` acumulados em ~3 semanas. Este índice diz **o que ler, em que ordem, e o que
está morto**.

---

## 🔴 Leia primeiro (se você vai treinar ou avaliar qualquer coisa)

| documento | por quê |
|---|---|
| **[licoes-de-metodo.md](licoes-de-metodo.md)** | ⭐ **os cinco erros que não davam erro**, as leis medidas e o checklist de run longo. Se ler um só, leia este |
| [licoes-pretreino.md](licoes-pretreino.md) | detalhe do pré-treino: bug de rótulos, amostragem, throughput, $/B tokens |
| [agentico-medicao.md](agentico-medicao.md) | como se mede tool-use de verdade (execução, não semelhança) + os dois erros de avaliador |

---

## O estado atual — o que o Bee é hoje

| documento | cobre |
|---|---|
| [`../README.md`](../README.md) | visão geral, Gate 1, Gate 2, arquitetura, como rodar |
| [sft-resultado.md](sft-resultado.md) | SFT sobre a base correta; os 3 defaults errados |
| [agentico-medicao.md](agentico-medicao.md) | execução 65,9%, pass@k, over-calling, rejection sampling |
| [multiturno-adapter.md](multiturno-adapter.md) | ⭐ a abelha multi-turno e a validação da tese da COMEIA |
| [modelcards/](modelcards/) | cards publicados: base, sft, **sft-v2** |

## ⭐ O próximo degrau — Bee-350M

| documento | o que decide |
|---|---|
| **[estudo-bee-350m.md](estudo-bee-350m.md)** | ⭐ **~60 papers de ago/2026, 13 agentes, 4 afirmações passadas por refutação adversarial.** Receita, orçamento, o que NÃO fazer, e **três premissas do plano derrubadas** — inclusive "expandir o corpus para 30B" |
| **[teto-passk-medido.md](teto-passk-medido.md)** | ⭐ **US$ 0, e derruba 3 afirmações**: o corpus está limpo (0,28% de repetição — o item de maior ROI do estudo não existia), o holdout tinha 11,8% de itens impossíveis, e o "teto" de 72,9% era na verdade **85,3%**. A folga colhível é **21,2 pp**, não 15,3 |

## Gates e decisões

| documento | veredito |
|---|---|
| [gate-1-v2-tokenizador-2026-07-27.md](gate-1-v2-tokenizador-2026-07-27.md) | ✅ vocab 32k, fertilidade 0,2183 |
| [previsao-marco-10B.md](previsao-marco-10B.md) | ⚠️ previsão pré-registrada que **falhou o próprio critério** |
| [instant-clusters-avaliacao.md](instant-clusters-avaliacao.md) | ❌ cluster: não agora |
| [escada-custo-bee.md](escada-custo-bee.md) | custo por degrau da escada |

## Corpus e dados

[corpus-v1-aprovado-2026-07-27.md](corpus-v1-aprovado-2026-07-27.md) ·
[corpora-pt-avaliados.md](corpora-pt-avaliados.md) ·
[fineweb-edu-pt.md](fineweb-edu-pt.md) ·
[estudo-curriculo/00-CONSOLIDADO.md](estudo-curriculo/00-CONSOLIDADO.md) (BNCC)

## 🔴 Documentos INVÁLIDOS — preservados de propósito

Os números vieram do modelo treinado com o objetivo errado (previa t+2). **Não use nenhum
número deles.** Ficam porque mostram como uma conclusão errada se sustenta por semanas:

[gate-2-resultado.md](gate-2-resultado.md) · [escada-scaling.md](escada-scaling.md) ·
[gate-tucano.md](gate-tucano.md) · [gate-corpus-pt-plano.md](gate-corpus-pt-plano.md)

## Histórico (a fase anterior ao Bee)

[comeia-sobre-qwen.md](comeia-sobre-qwen.md) — o método COMEIA sobre Qwen3.5-4B ·
[avaliacao-do-projeto-2026-07-26.md](avaliacao-do-projeto-2026-07-26.md) — o dia em que o
projeto virou Bee · [dados-intermediarios-perdidos-2026-07-27.md](dados-intermediarios-perdidos-2026-07-27.md)

## Estudos de literatura (~20 arquivos)

O mais recente e mais relevante: **[leituras-2026-08.md](leituras-2026-08.md)** — 16 papers de
agosto avaliados contra o critério *"funciona em 151M?"*. Os demais seguem o padrão
`estudo-*-<data>.md` e cobrem tokenização, destilação, GPUs, ferramentas e fornecedores.

---

⚠️ **Nota de higiene:** esta pasta mistura documentos com ~25 arquivos `.log`/`.json` de
execução (`juntar-22b.log`, `upload-22b.log`, varreduras de LR). Eles não são documentação —
são artefatos de corrida guardados por rastreabilidade.
