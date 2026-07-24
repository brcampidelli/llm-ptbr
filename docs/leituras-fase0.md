# Fase 0 — Leituras (fechar o gap da pasta)

A pasta `artigos para estudos/` é forte em panorama/histórico e e-book introdutório, mas **fraca em
literatura de construir/treinar modelo**. Esta lista completa o essencial. Ordem sugerida de leitura.

## Núcleo — arquitetura e pós-treino (obrigatório)
| # | Leitura | Por quê |
|---|---|---|
| 1 | **Attention Is All You Need** (Vaswani et al., 2017) | O Transformer. Base de tudo. |
| 2 | **InstructGPT / RLHF** (Ouyang et al., 2022) | Como um modelo "cru" vira assistente que segue instrução. |
| 3 | **LoRA** (Hu et al., 2021) + **QLoRA** (Dettmers et al., 2023) | Fine-tune barato — o motor do Tier A. |
| 4 | **DPO** (Rafailov et al., 2023) | Otimização de preferência sem RL complexo. Fase 4. |
| 5 | **GRPO / DeepSeekMath** (Shao et al., 2024) | RL em tarefas verificáveis. Fase 5. |
| 6 | **Tülu 3** (AI2, 2024) | Receita ABERTA de pós-treino ponta-a-ponta — o mapa de referência. |
| 7 | **Chinchilla / Scaling Laws** (Hoffmann et al., 2022) | Entender a relação dados×parâmetros×compute. |

## PT-BR — o que já existe (estudar antes de reinventar)
| # | Leitura | Por quê |
|---|---|---|
| 8 | **Sabiá** (Maritaca AI) | Modelo PT-BR de referência comercial; que benchmarks usaram. |
| 9 | **Tucano + corpus GigaVerbo** | Esforço aberto PT-BR do zero; fonte de dados/lições. |
| 10 | **Bode / Cabrita / Gervásio / Albertina** | Panorama dos fine-tunes PT existentes — o que já foi tentado. |
| 11 | **Open PT-LLM Leaderboard** (metodologia) | Define como "competitivo em PT-BR" é medido. Copiar a metodologia. |

## Já na pasta — usar como técnica nas fases certas
| Paper | Fase de uso |
|---|---|
| **PEARL** `2607.18256` — RL agêntico + eficiência de modelo pequeno | Fase 5 (RL) — a prova da tese |
| **REGEN** `2607.19450` — destilação expert→generalista com offline RL | Fase 2/5 |
| **Distilled-RL** `2607.17247` — destilação + RL no pós-treino | Fase 5 |
| **CriPO** `2607.18082` — RL por rubrica + self-distillation | Fase 5 |
| **LLM-as-a-Coach** `2607.18110` — aprendizado experiencial em tarefas não-verificáveis | Fase 4/5 |
| **Model Merging** `2607.18026` — média ponderada de pesos sem treino | Fase 6 |
| **SelectInfer** `2607.18081` — seleção de neurônios para inferência on-device | Fase 6 |
| **PRADA** `2607.18244` — colaboração edge↔servidor por destilação | Fase 6 (deploy) |
| **RAG Survey** `s10462-026-11605-7` | Complemento pós-release (produto), não treino |

## Papers do arXiv que NÃO entram (fora de escopo — registrado para não revisitar)
QNLP hindi `2607.16765`, fMRI `2607.12079`, EvoDRC `2607.20019`, RF-Agent `2607.18772`,
DepRepair `2607.17957`, HyGRL `2607.19398`, AHEAD `2607.18465`, Sentence Splitter `2607.19845`,
BERT-tradução `2607.12612`, "Do It Right" `2607.05644`, migração acadêmica `2607.02416`,
segurança de componentes `2607.16660`, workflow ComfyUI `2607.15845`. São NLP aplicado/meta —
interessantes, mas não são receita de foundation model.
