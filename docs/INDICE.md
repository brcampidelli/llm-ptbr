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
| **[tres-lacunas-medidas.md](tres-lacunas-medidas.md)** | ⭐ **US$ 0, três achados**: a geometria do 350M é idêntica ao **MobileLLM-350M** (2ª fonte, com ablação); 🔴 **ativações massivas de 1616× e attention sink de 85% CONFIRMADOS em 151M** — mata quantização por-tensor; e quem desvia na razão intermediate é o **150M**, não o 350M |
| **[estudo-qwen38-slm.md](estudo-qwen38-slm.md)** | ⭐ **13 agentes sobre Qwen3.8 + survey de SLM + 10 refs.** Qwen3.8 = Qwen3.5 em arquitetura (params idênticos na unidade). **Duas refutações medidas na escala do Bee**: Gated DeltaNet perde 0,2 pp em 340M/20B, e MTP piora abaixo de ~1,3B. A lacuna: MobileLLM é o único trabalho medido em 125M **e** 350M |
| **[throughput-350m-medido.md](throughput-350m-medido.md)** | ⭐ **US$ 0,15 e cortou o custo do run pela metade**: 53,73k tok/s medidos (a extrapolação do 151M subestimava 60%). Run principal = **US$ 115**, não US$ 218. Liger habilita desligar o checkpointing (+23%); `torch.compile` é incompatível com Liger |
| **[fork-decaimento.md](fork-decaimento.md)** | 🔴 **US$ 22, e inverte o sinal de um resultado**: a curva pareada do 350M contra o 150M media o **schedule**, não o modelo. Decair uma cópia levou o 350M de **2,51% pior** em 10B a **~0,6% melhor** em 13B — **sem um token novo**. Fecha a hipótese registrada em 10/08 e deixada sem teste, e **invalida os marcos 1B–10B como comparação** |
| **[teto-passk-medido.md](teto-passk-medido.md)** | ⭐ **US$ 0, e derruba 3 afirmações**: o corpus está limpo (0,28% de repetição — o item de maior ROI do estudo não existia), o holdout tinha 11,8% de itens impossíveis, e o "teto" de 72,9% era na verdade **85,3%**. A folga colhível é **21,2 pp**, não 15,3 |

## 🐝 Pós-treino do Bee-350M (em curso)

| documento | o que traz |
|---|---|
| **[plano-pos-treino-350m.md](plano-pos-treino-350m.md)** | o plano aprovado: estágios E0–E8, orçamento e os critérios declarados **antes** de medir |
| **[reguas-e-pisos-e0.md](reguas-e-pisos-e0.md)** | ⭐ **as 8 réguas e o piso de cada uma.** Copiar 2 frases resume 51,3%; contar a palavra "não" faz 79,0% em sentimento; copiar a fonte marca chrF++ 21,5 em tradução. E a régua de tradução reproduziu o **BLEU 50,4 publicado do opus-mt em 50,5** — validação do aparato, não só do modelo |
| [censo-mistura-350m.md](censo-mistura-350m.md) | censo por TOKEN: o agêntico recebe 2,7% do gradiente, não 20,9% |

## Infraestrutura

| documento | decide |
|---|---|
| **[colab-cli-avaliacao-2026-08-19.md](colab-cli-avaliacao-2026-08-19.md)** | ⭐ **Colab volta ao jogo — para carga diferente.** A CLI do Colab (jun/2026) faz `colab run --gpu A100 script.py` com keep-alive sem navegador; instalada e verificada aqui (v0.6.0, via WSL — não roda em Windows). Aceleradores **T4/L4/G4/H100/A100**, e o G4 é RTX PRO 6000 Blackwell de 96 GB, exclusivo do Pro+. A migração para o RunPod continua certa para **run longo**; os 15 SFTs curtos do E2 cabem nas 600 unidades já pagas. ❓ Falta medir a taxa de queima por GPU-hora antes de decidir |

## Estudos de fontes externas — o que NÃO adotar também é resultado

| documento | veredito |
|---|---|
| **[estudo-ml-guide-mikeroyal-2026-08-19.md](estudo-ml-guide-mikeroyal-2026-08-19.md)** | ❌ **2/10.** Guia de ML com 709★ pedido para análise: índice de links de engenharia acadêmica de ~2021 com uma prateleira de LLM pendurada em 2023. "MATLAB" aparece **103 vezes**, "attention" **zero**, "Portug" **zero**. Podridão de link é baixa (6,7%) — o problema é obsolescência técnica, que nenhum código HTTP detecta |

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
