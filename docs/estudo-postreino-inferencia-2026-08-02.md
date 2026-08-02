# Estudo — Pós-treino + Otimização de inferência + Unsloth (8 fontes) aplicado ao Bee

**Data:** 2026-08-02 · **Método:** multi-agente (4 pesquisadores paralelos) · **8 links** agrupados em 4 temas:
Unsloth (repo+notebook) · Pós-treino (PyTorch primer + OpenAI accuracy) · Otimização de inferência
(NVIDIA + Mirantis) · Speculative decoding (EAGLE-3 Vertex + DFlash DataCamp).

> **O fio que atravessa os 8 links:** todos tratam da fase **DEPOIS do pré-treino** (pós-treino + serving).
> E o veredito honesto, repetido pelos 4 agentes: **para um modelo pequeno (150M-1B), quase todo o
> "avançado" é overkill.** O valor está em **dados de SFT de qualidade** + **serving trivial (GGUF Q8 no
> llama.cpp)**. Inferência rápida/barata num 150M já é o comportamento default — o gargalo é treino, não serving.

---

## Veredito unificado (o que fazer nas próximas fases do Bee)

| Fase | Ferramenta/técnica | Fazer? |
|---|---|---|
| **SFT** (base → assistente PT) | Dados do teacher DeepSeek-V4 + **rejection sampling** → Unsloth (local, 8GB) | ✅ **é o degrau de maior ROI** |
| **CPT** opcional (reforçar PT antes do SFT) | Unsloth continued-pretraining (dual-LR, embed_tokens+lm_head) | 🟡 talvez, se o base pedir |
| **DPO** (preferência) | Reusar pares preferida/rejeitada do rejection sampling | 🟡 só depois do SFT bom |
| **RLHF/PPO/GRPO/RLVR** | RL online | ❌ **exagero pra 150M-1B** |
| **Serving/demo** | **llama.cpp + GGUF Q8** + HF ZeroGPU (link público) | ✅ resolve numa linha |
| **Quantização Q4** | GGUF Q4_K_M | 🟡 só no 1B+ (150M é sensível → fica em Q8) |
| **vLLM/TGI/TensorRT/PagedAttention/tensor-parallel** | serving datacenter | ❌ overkill até virar API com tráfego |
| **Speculative decoding** | EAGLE-3/DFlash | ❌ agora · 🟡 futuro (Bee-150M como *draft* do Bee-7B) |

---

## 1. Pós-treino — plano de SFT enxuto (PyTorch primer + OpenAI accuracy)

**Pipeline canônico:** Pré-treino → **SFT** → preferência (DPO/RLHF) → RL online (PPO/GRPO/RLVR). Pro Bee:
- **SFT = essencial e é onde está ~90% do valor.** Loss mascarada (treina só nos tokens do `assistant`),
  chat template fixo, LR baixo, 1-3 épocas, early stopping por eval. Começar com **10k-50k pares de alta
  qualidade** (não milhões — teto irreal pra 150M).
- ⚠️ **A regra que domina o SFT:** *"o teto é a sua PIOR resposta, não a melhor."* Qualidade ≫ quantidade.
- **Rejection sampling (maior ROI):** pra cada instrução, gerar **N respostas** com o DeepSeek-V4 → ficar
  com a melhor (juiz = próprio DeepSeek como LLM-judge, ou verificação determinística). Eleva o teto do SFT
  **antes** de pensar em DPO. Bônus: as respostas rejeitadas viram os **pares negativos** de um DPO futuro —
  colhe os dois de uma vez.
- **DPO** (se sobrar tempo, pós-SFT): barato/estável, único método de preferência realista num 150M. β alto,
  poucos passos, ganho pequeno. **RLHF/PPO/GRPO/RLVR = pular** (reward model ≈ tamanho do modelo; 150M não
  tem capacidade de raciocínio pra RL explorar — é hype pra esse porte).
- **Decisão prompt vs RAG vs fine-tuning (OpenAI):** o Bee é 100% problema "aprendido" (o base sabe PT mas
  não sabe *ser assistente*) → **SFT é a alavanca certa, não RAG.**
- ⚠️ **Armadilhas num 150M:** catastrophic forgetting (menos capacidade sobrando → sobrescreve fácil;
  mitigar com LR baixo, poucas épocas, mix de dado geral), overfitting em pouco dado, alignment tax.
- **Cuidado de destilação:** o Bee (150M) imita **estilo/formato** do teacher muito melhor que **capacidade**.
  Manter respostas do teacher **curtas e diretas**; CoT longo do teacher vira ruído pra um 150M.

**Eval do pós-treino (bpb mede só o base):** montar **eval set PT de 100+ instruções com ground-truth ANTES
de treinar** (define "funcionou"); **LLM-judge (DeepSeek-V4) win-rate** Bee-SFT vs base; checagem
anti-forgetting (bpb num holdout PT antes/depois). Iterar nos **dados**, não no algoritmo.

## 2. Unsloth — a ferramenta do SFT/serving (repo + notebook)

- **Fine-tuning/CPT, NÃO pré-treino do zero.** Confirma o estudo anterior: entra nas fases 2-3, não na 1.
  Novidade útil: **Continued Pretraining "for learning another language"** — receita com dual-LR
  (`embedding_learning_rate` 10× menor) + `target_modules` incluindo `embed_tokens`/`lm_head`. Candidato a
  reforçar PT antes do SFT.
- Ganhos: **2× mais rápido, 70% menos VRAM** (kernels Triton — mesma família do Liger que já usamos). ⚠️
  paridade de acurácia **não garantida** nas fontes → **medir vs TRL puro antes de adotar**.
- **Llama suportado, RTX série 50 (Blackwell) suportada, mínimo 3GB VRAM** → o Bee 150M-1B **sobra no laptop
  8GB** (dá até **full fine-tuning**, não só LoRA — no 150M o ganho de VRAM do LoRA é marginal; o valor é
  velocidade + export GGUF fácil).
- Workflow: `FastLanguageModel.from_pretrained → get_peft_model(LoRA) → SFTTrainer(TRL) → train →
  save_pretrained_gguf(q8_0/q4_k_m)`. Serving: vLLM/Ollama/llama.cpp/endpoint OpenAI-compat.
- ⚠️ **Risco de integração nº1:** carregar o checkpoint do Bee em **formato HF Llama** (config.json+safetensors).
  **Nosso `pretrain.py` já salva com `cru(modelo).save_pretrained(out/"modelo")`** → deve encaixar direto. Confirmar.
- Licença: lib **Apache-2.0** (ok); só a UI Studio é AGPL-3.0.

## 3. Otimização de inferência — quase tudo é datacenter (NVIDIA + Mirantis)

**Achado central:** as duas fontes são de **datacenter/GPU de servidor**; a Mirantis admite não cobrir edge/
modelo pequeno. **Para o Bee-150M, quase tudo é irrelevante** — resolve problemas que não temos (modelo que
não cabe em 1 GPU; milhares de requests concorrentes).
- **Conceito que vale guardar:** geração de texto é **memory-bound** (fase *decode* = matriz-vetor, limitada
  por banda de memória, não compute). Num 150M os pesos cabem em cache/RAM rápida → **já é rápido por default.**
- **IMPORTA pro Bee pequeno:** **quantização GGUF** (por *footprint*/distribuição, não VRAM), KV-cache (grátis
  no runtime), GQA (decisão de **treino**, não serving — usar já na arquitetura pro futuro 1B+).
- **OVERKILL:** tensor/pipeline parallelism (o 150M ocupa ~300MB FP16/~90MB Q4 — cabe até no celular),
  PagedAttention/batching contínuo (só com muitos usuários), vLLM/TGI/TensorRT-LLM.
- ⚠️ **Quantização em modelo pequeno é MAIS sensível** (menos redundância pra absorver erro). O "-75% custo /
  99,5% qualidade do Q4" é medido em 7B+. **Pro 150M: ficar em Q8** (~160MB, sem perda perceptível — Q4 quase
  não ganha nada e degrada mais). **Q4_K_M só no 1B+.** Sempre medir bpb/holdout PT antes/depois (temos o harness).
- **Métricas:** TTFT (⚠️ no ZeroGPU o **cold start** domina a percepção), TPOT, throughput (tok/s). Medir com
  **`llama-bench`** variando quant e threads.

## 4. Speculative decoding — PULAR agora, guardar pro Bee grande (EAGLE-3 + DFlash)

- Draft+verify: um rascunho barato propõe N tokens, o modelo grande verifica em 1 forward paralelo (saída
  **matematicamente exata**). EAGLE-3 = **draft head treinada** (2-5% do alvo, ~1 dia de treino, 2-3× no Llama-70B);
  DFlash = **draft model separado** plug-and-play (3,2-3,8× em código, ~2,4× em texto livre, no 31B).
- ⚠️ **Não faz sentido num modelo já pequeno (150M-1B):** a técnica ataca o custo por token de modelos
  **grandes** (70B/31B rodam a ~40 tok/s); um 150M roda a **centenas de tok/s** — não há gargalo pra amortizar,
  e **o próprio modelo já é do tamanho de uma draft head.** O overhead pode até piorar. Nenhuma fonte testou <1B.
- ✅ **Onde faria sentido no futuro (sacada boa):** um **Bee-150M/1B como *draft* de um Bee-7B** — self-speculative
  na mesma família, **mesmo tokenizer/corpus PT → taxa de aceitação alta → ganho maior**, com o draft "de graça"
  como subproduto do modelo pequeno. **Ação barata HOJE: manter o tokenizer unificado em toda a família Bee**
  (custo zero agora, habilita a auto-especulação depois). Nada além disso.
- (Curiosidade: o fork "BeeLlama.cpp" do tutorial DFlash **não tem relação** com o nosso Bee — homônimo.)

---

## Plano de ação consolidado (roadmap pós-pré-treino do Bee)

1. **Fechar o pré-treino** (v3 em curso) + Gate 2. *(RunPod/Colab + Liger — inalterado.)*
2. **Fixar o chat template** do Bee + **montar eval set PT** (100+ instruções com referência). Antes de treinar.
3. **Gerar dados de SFT** com **DeepSeek-V4** (build.nvidia grátis) via **rejection sampling** (N respostas →
   melhor por LLM-judge; guardar rejeitadas). 10k-50k pares curtos/de qualidade.
4. **(Opcional) CPT em PT** com Unsloth (dual-LR) se o base precisar de reforço de idioma.
5. **SFT** com **Unsloth local** (RTX 5070 8GB, grátis) — confirmar antes: (a) checkpoint carrega em HF Llama;
   (b) paridade vs TRL puro; (c) full-FT vs LoRA no 150M.
6. **Avaliar:** LLM-judge win-rate + anti-forgetting. Iterar nos **dados**.
7. **(Opcional) DPO** reusando os pares do rejection sampling. β alto, ganho marginal.
8. **Servir/demo:** `save_pretrained_gguf` **Q8** → **llama.cpp/`llama-server`** local + **HF Space (ZeroGPU)**
   pro link público. Medir com `llama-bench`.
9. **Guardar pro futuro (1B+/7B):** GQA na arquitetura, Q4_K_M, vLLM/TGI (se virar API com tráfego),
   speculative decoding self-family (Bee pequeno = draft do Bee grande).

**A verdade que amarra tudo:** pro Bee, as próximas fases são **um problema de dados (SFT) e de uma linha de
serving (GGUF), não de algoritmos sofisticados.** O avançado (RL, speculative decoding, vLLM/TensorRT) é
para quando/se o Bee ficar grande. Ver [estudo-teachers-destilacao](estudo-teachers-destilacao-2026-08-01.md),
[estudo-unsloth-studio](estudo-unsloth-studio-2026-08-02.md), [estudo-huggingface](estudo-huggingface-2026-08-02.md).

## Incertezas honestas
- Números de quantidade de dados de SFT vêm de modelos grandes; o ótimo pra 150M é **empírico**.
- "Pular RL" pra <1B é extrapolação (custo de reward model + falta de raciocínio), não afirmação direta das fontes.
- Perda de qualidade exata de Q4 num 150M não medida (fontes medem 7B+); recomendação Q8 é conservadora.
- Ganhos de speculative (2-3,8×) são casos favoráveis de fontes interessadas (Google/DataCamp); tratar como teto.
- Paridade de acurácia do Unsloth não garantida nas fontes → medir.
- O Colab share do notebook Unsloth só renderizou login; usei o GitHub/docs oficiais (mesmo conteúdo).
