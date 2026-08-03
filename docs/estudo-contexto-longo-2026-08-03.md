# Estudo — Contexto Longo em LLMs, aplicado ao Bee

**Data:** 2026-08-03 · **Método:** multi-agente (4 pesquisadores em paralelo, 8 fontes) · **Contexto:** o Bee treina hoje em `seq_len 2048`; este estudo mapeia como **estender** e como **treinar/servir** contexto longo, e o que vale pro nosso porte (150M→1B, 1 GPU).

> **Veredito global — a resposta em uma frase:** o gargalo do Bee **não é** contexto longo (é quantidade de token de treino). Então a rota certa é **pré-treinar barato em 2048 e, só depois e só se precisar, esticar a janela com YaRN** (~0,1% dos tokens, ~300 passos de fine-tune). Quase tudo que as fontes chamam de "milhões de tokens" é maquinaria de **cluster** ou de **serving de fronteira** — inaplicável por escala, não por falta de recurso. O que aproveitar **agora** numa A100 é curto e barato: **FlashAttention** no treino, o **GQA** que o Bee já tem, e (ao servir) **KV-cache quantizado**.

---

## A ideia que amarra tudo: RoPE não extrapola de graça

RoPE (que o Bee usa, `theta=10000`) codifica posição girando pares de dimensões por um ângulo `m·θ_i`, com `θ_i = base^(−2i/d)`. Dimensões baixas giram rápido (relação local), altas giram devagar (longo alcance). Durante o pré-treino o modelo só vê ângulos até `m_max·θ` com `m_max = 2048`. **Passar disso põe a atenção em ângulos nunca observados → degrada rápido.** Não falta "espaço"; a geometria sai da distribuição treinada. É por isso que estender contexto **exige** algum ajuste — e a boa notícia é que o ajuste barato existe e é padrão da indústria.

---

## As 4 frentes (ranqueadas por utilidade pro Bee)

### 🥇 Extensão de contexto pós-treino — **5/5** (a única acionável de verdade)
Como levar um modelo de 2048 → 8k/32k **sem re-treinar do zero**. Do mais simples ao SOTA:

| Método | Mecanismo | Fine-tune? | Nota |
|---|---|---|---|
| **Position Interpolation (PI)** | *Comprime* posições p/ caber na janela treinada (`pos·L_treino/L_alvo`) | ~2000 passos | Colapsa vizinhança se exagera |
| **NTK-aware** | Muda a **base θ** (escala pouco alta freq., muito baixa freq.) | 0 p/ extensões moderadas | Base ótima é empírica |
| **Dynamic NTK** | NTK com fator que **cresce com o tamanho real** da sequência (1 em 2048) | 0 | Ótimo p/ servir sem treino |
| **YaRN** ⭐ | NTK-by-parts (linear nas altas freq. + NTK nas baixas + zona de transição) **+ temperatura de atenção** | **~400 passos (~0,1% dos tokens)** | **SOTA de eficiência**; Qwen/DeepSeek/Llama usam |
| **Subir `rope_theta` + fine-tune curto** | Força bruta (Llama 3 foi 10k→500k) | curto | 1 knob, um pouco abaixo do YaRN em 32x |

**Números do YaRN (paper 2309.00071):** 400 passos (~0,1% dos tokens de pré-treino) levaram o LLaMA-2-7B de 4k → **32k (8x)**; o 70B a 64k; a linha chega a **128k+**. É **5× menos treino que o PI** com resultado melhor.

**Regra de fator:** até 2x, PI/NTK sem treino aguentam · 4–8x, **YaRN + fine-tune curto** · 8x+ (32k), **YaRN obrigatório**.

### 🥈 NVIDIA — treino e inferência de contexto longo — **3/5**
- **Treino (Megatron/NeMo):** a memória de ativações da atenção cresce **~quadrática** no comprimento → soluções: **não materializar** (FlashAttention) ou **fatiar a sequência entre GPUs** (**Context Parallelism / ring attention**, >2× speedup no Llama-3-8B em B200, obrigatório a 1M tokens). CP, sequence parallelism, CPU-offload, receitas 16k/64k/128k = **tudo multi-GPU/NVLink** → overkill de cluster.
- **Inferência:** KV-cache = `2·camadas·kv_heads·head_dim·seq·batch·bytes` — cresce **linear com seq e batch** (é o que estrangula). **PagedAttention/vLLM** (blocos não-contíguos → batches maiores), **GQA/MQA** (corta o cache — o Bee já faz 9/3), **FlashAttention** (idêntico à atenção, sem materializar a matriz), **decode é memory-bound** (não compute-bound), **continuous batching**, **speculative decoding**, **quantização de KV-cache**.
- **Honestidade:** os ">2×" e "1M tokens" são reais **mas em B200 com CP** — cluster, não replicável solo.

### 🥉 InfiniteHiP (arXiv 2502.08910) — **2/5**
Paper KAIST/DeepAuto (fev/2025): servir **até 3M tokens numa GPU só**, *training-free*. Combina **poda hierárquica de tokens** (achado forte: ~75% dos chunks de 64 tokens não têm nenhum token top-2K), **cache da máscara de atenção**, **RoPE dinâmico por camada** e **offload de KV-cache p/ host (LRU)**. Ganhos: prefill ~20× vs FlashAttention2 em 1M tokens, 6,1 GB de VRAM em 3M, LongBench +7 pts.
- **Ressalvas honestas:** resultados de **1M/3M são "estimados"** (excedem a memória de teste); prefill fica **~1,6× mais lento** com a extensão ligada; exige **tuning empírico**; ganho de qualidade é **incremental** sobre InfLLM — é bom paper de *sistemas*, não salto de capacidade.
- É maquinaria de **serving de fronteira** (100k–3M tokens). O Bee não tem esse problema.

### Gemini long-context (Google) — **1,5/5**
Playbook de **consumir** um modelo fechado gigante (janela 1M–2M): RAG "in-context" (documento inteiro no prompt), vídeo/áudio de horas, many-shot, codebase inteira, **context caching** (cachear o prefixo longo, pagar por hora), needle-in-a-haystack (>99% recall com **1** agulha, mas **cai com múltiplas**). **~90% irrelevante** p/ treinar um 150M. Transferível: (1) **prefix/KV-cache** ao servir, (2) o critério **contexto-longo vs RAG**, (3) **needle-in-a-haystack** como avaliação.

---

## Aplicação ao Bee — o que fazer, o que adiar, o que ignorar

**Contexto:** Bee = 150M, Llama-arch (30 camadas, d_model 576, GQA 9/3, RMSNorm, SwiGLU, RoPE θ=10000, seq_len 2048, BPE PT 32k), pré-treino do zero numa A100 (RunPod), escada 150M→1B, servir local GGUF/llama.cpp.

### ✅ Fazer AGORA (1 A100, contexto curto)
1. **FlashAttention/SDPA no treino.** Não-negociável. A 2048 a matriz de atenção ainda cabe, mas economiza VRAM e acelera de graça — casa com o Liger fused-CE (que já ataca o gargalo dos logits 32k) liberando micro-batch maior.
2. **GQA 9/3 já está certo.** É a técnica de KV-cache mais impactante e o Bee já adotou. No treino a economia é modesta (contexto curto); ao servir em GGUF corta 1/3 do KV-cache vs MHA. **Não mexer.**
3. **Activation checkpointing: só se faltar VRAM.** A 150M numa A100 sobra memória → **não ligar** (evita o imposto de ~30% por passo). Guardar pro degrau de 1B.
4. **Ao servir (llama.cpp): KV-cache quantizado** (`--cache-type-k/v q8_0`). A 2048 o KV-cache é minúsculo (poucos MB/sequência no Bee) → ganho real só com batch alto ou contexto maior. Trivial de ligar depois.

### 🔜 Fica pra quando precisar de 8k/32k (rota barata, recomendada)
**Manter o pré-treino em 2048 e esticar depois com YaRN.** Não vale re-treinar o Bee em contexto longo desde o zero (perde a barateza que é o ponto do projeto). Passo-a-passo mínimo:
1. **Não mudar nada no pré-treino atual** (2048, θ=10000). Terminar a 1 época.
2. **Empacotar corpus PT em janelas longas** (8192 ou 32768 tokens) — pode ser o próprio corpus re-empacotado. Mirar **~0,1–0,5% dos tokens** do pré-treino.
3. **Ativar YaRN na config** (HF `rope_scaling`): `{"type":"yarn","factor":4}` p/ 8k ou `factor:16` p/ 32k (defaults `beta_fast=32`, `beta_slow=1`).
4. **Fine-tune curto no comprimento-alvo**, FlashAttention ligado, **LR baixo (1e-5–2e-5)**, **~200–400 passos**. Direto no 8k; p/ 32k, em duas etapas (2k→8k→32k) ou direto se a VRAM aguentar.
5. **Avaliar** bpb em holdout PT longo **+ passkey retrieval** (esconder um número no meio de um doc longo) — confirmar que o modelo **usa** a janela, não só tolera.
- *Alternativa 1-knob:* subir `rope_theta` (~80k–500k, empírico) + o mesmo fine-tune curto. Mais simples, qualidade um pouco abaixo em 32x.
- *Atalho zero-treino p/ prototipar:* servir com **Dynamic NTK** até ~4k sem fine-tune e medir a degradação (baseline barato antes de investir).

### ❌ Overkill (ignorar até sair de 1 GPU / contexto de fronteira)
- **Context/sequence parallelism, ring attention, CPU-offload, Megatron/NeMo multi-GPU** — só fatiam sequência entre GPUs. 1 GPU + 2048 = zero utilidade.
- **InfiniteHiP inteiro** (poda hierárquica, máscara-cache, RoPE por-camada, KV-offload) — serving de 100k–3M tokens. Pro Bee, o "primo pobre" já basta: llama.cpp faz KV-cache streaming estilo StreamingLLM.
- **PagedAttention / continuous batching / speculative decoding** — serving concorrente em produção. O Bee serve local single-user. *(Guardável: o Bee-150M poderia ser draft do Bee-1B em speculative decoding **no futuro** — mantendo o tokenizer unificado.)*

---

## Temas transversais (o que apareceu em 3+ fontes)
- **RoPE não extrapola** → extensão exige ajuste (YaRN é o barato). *(fontes 1, 3)*
- **FlashAttention** é pré-requisito de qualquer contexto >curto — no treino e no fine-tune de extensão. *(1, 2, 3)*
- **GQA** = a decisão arquitetural de KV-cache mais impactante; o Bee já a tem. *(2)*
- **Treinar curto + estender depois** é o padrão de custo da indústria (Llama/Qwen/DeepSeek). *(2, 3)*
- **Contexto-longo NÃO substitui RAG** quando a janela não comporta o corpus → **PassaPro = RAG** (o Bee em 2k nunca comporta um edital inteiro). *(4)*
- **Needle-in-a-haystack / passkey** = avaliação barata de recall e de extensão de contexto. *(3, 4)*

---

## Incertezas honestas
- **Reddit r/LocalLLaMA não abriu** (WebFetch bloqueado, inclusive `.json`) — o ângulo de praticantes foi coberto pelo paper YaRN + deep-dives independentes.
- **Towards Data Science é raso** — cita YaRN/PI por alto, sem mecanismo nem receita; números vieram das outras fontes.
- **InfiniteHiP:** 1M/3M tokens são **estimados**, não medidos ponta a ponta.
- **NVIDIA:** os ganhos (>2×, 1M tokens) são de **B200 + cluster com CP** — não replicáveis solo.
- Fatores de extensão e nº de passos do YaRN são do LLaMA-2-7B; num 150M PT esperar **re-medir** (modelo pequeno degrada antes do limite nominal).

## Fontes
- [InfiniteHiP — arXiv 2502.08910v1](https://arxiv.org/html/2502.08910v1) (Lee et al., KAIST/DeepAuto, fev/2025)
- [NVIDIA — Scaling to Millions of Tokens (long-context training)](https://developer.nvidia.com/blog/scaling-to-millions-of-tokens-with-efficient-long-context-llm-training/)
- [NVIDIA — Mastering LLM Techniques: Inference Optimization](https://developer.nvidia.com/blog/mastering-llm-techniques-inference-optimization/)
- [Towards Data Science — Extending Context Length in LLMs](https://towardsdatascience.com/extending-context-length-in-large-language-models-74e59201b51f/) (panorama raso)
- [YaRN — arXiv 2309.00071](https://arxiv.org/pdf/2309.00071) (Peng et al., Nous Research — fonte primária do método recomendado)
- [Google — intro_long_context.ipynb (Gemini)](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/long-context/intro_long_context.ipynb)
- [Google Cloud — Gemini long context (docs)](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/long-context?hl=pt-br)
- Reddit r/LocalLLaMA "how to create long past 4000 context" — **não acessível**

> Ver também: [estudo-postreino-inferencia](estudo-postreino-inferencia-2026-08-02.md) (SFT/serving) e o `refs/harness-engineering` global (contexto é orçamento).
