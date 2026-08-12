---
language:
- pt
license: apache-2.0
library_name: transformers
pipeline_tag: text-generation
tags:
- portuguese
- pretrained-from-scratch
- llama
---

# Bee-150M-PT (base)

Modelo de linguagem de **151,2M parâmetros** pré-treinado **do zero** em português do Brasil:
tokenizador próprio, corpus próprio, pesos inicializados aleatoriamente. Sem destilação, sem
continuação de pré-treino de outro modelo.

## Resultado

**bits-por-byte** em holdout PT limpo (parquet 40 do `fineweb-2 por_Latn`, região que nenhuma
coleta do treino tocou). Menor é melhor. bpb é comparável entre tokenizadores diferentes —
perplexidade não seria.

| modelo | tokens de treino | **bpb PT** | fertilidade (tok/byte) |
|---|---:|---:|---:|
| **Bee-150M-PT** | **21,7B** | **0,844** | 0,2183 |
| Tucano-160m | ~200B | 0,884 | 0,2074 |
| SmolLM2-135M | ~2T (inglês) | 1,551 | 0,3576 |

O Bee supera o Tucano-160m usando **9× menos tokens**.

**Curva medida** (marcos salvos durante o treino, mesmo holdout e procedimento):

| tokens | 1B | 3B | 6B | 10B | 15B | 21B | final |
|---|---:|---:|---:|---:|---:|---:|---:|
| bpb | 1,021 | 0,947 | 0,920 | 0,897 | 0,870 | 0,845 | **0,844** |

## Arquitetura

`LlamaForCausalLM` — 30 camadas · d_model 576 · intermediate 2048 (SwiGLU) · 9 cabeças de
atenção com 3 KV heads (GQA) · RoPE (theta 10000) · RMSNorm · `seq_len` 2048 · vocab 32.000
com embeddings amarrados.

## Dados

100% português. `HuggingFaceFW/fineweb-2` config `por` (ODC-By 1.0) + fontes de domínio
público. A procedência foi verificada **na origem**, nunca pelo rótulo. Nenhum conteúdo com
paywall ou de licença indeterminada entrou no corpus.

## Treino

RTX 5090, 96,5 h, ~US$ 97. Batch global 524k tokens/passo, LR 3e-3 cosine, AdamW
(0,9/0,95), weight decay 0,1, clip 1,0, bf16, `torch.compile`.

## ⚠️ Limitações — leia antes de usar

Este é um modelo **base**: ele completa texto, não segue instruções. Para a versão ajustada,
veja `bee-150m-pt-sft`.

Com 151M parâmetros, ele **escreve português muito bem e não sabe fatos**. Conhecimento
factual é impreciso e **varia entre gerações** — ele amostra plausibilidade, não consulta
memória. Não use para perguntas factuais de mundo aberto. Use onde o conhecimento **vem no
contexto**: extração estruturada, resumo, reescrita, classificação.

## Reprodução

Código, corpus e todas as medições: <https://github.com/brcampidelli/llm-ptbr>.
As lições do projeto — inclusive o bug de uma linha que invalidou duas semanas de treino —
estão em `docs/licoes-pretreino.md`.
