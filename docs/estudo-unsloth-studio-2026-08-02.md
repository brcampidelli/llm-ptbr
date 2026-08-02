# Estudo — Unsloth Studio aplicado ao Bee

**Data:** 2026-08-02 · **Fonte:** `unsloth.ai/docs/new/studio` (lido via WebFetch).

> O que é e serve pro Bee? **Resposta curta: é uma UI no-code LOCAL e gratuita por cima da lib Unsloth —
> mas faz FINE-TUNING, não pré-treino do zero. Não muda o pré-treino do Bee (segue RunPod + pretrain.py +
> Liger); entra como a ferramenta da fase de SFT, provavelmente rodando LOCAL no laptop do Bruno, de graça.**

## O que é
- **UI no-code local** (open-source) para treinar / rodar / exportar modelos abertos numa interface unificada.
- **Grátis:** core Apache-2.0; a UI do Studio é **AGPL-3.0**.
- Roda no **próprio hardware**: NVIDIA/Intel/Apple/AMD · macOS/Windows/Linux/WSL. CPU-only só pra inferência.
- 500+ modelos (transformers-compatible; cita Qwen3.5, Gemma, Nemotron-3, GLM-5.2). Inferência via llama.cpp.
- Features: self-healing tool calling, web search, **Data Recipes** (dataset sintético), **Model Arena**, export **GGUF/safetensors**.
- Claim: **2× mais rápido, 70% menos VRAM** (fine-tuning). É a UI por cima dos kernels da lib Unsloth.

## ⚠️ A distinção decisiva: fine-tuning, NÃO pré-treino do zero
Unsloth/Studio fazem **ajuste fino** (LoRA/QLoRA/SFT) de modelos que **já existem** — não treinam pesos
aleatórios do zero. O pré-treino do Bee (`bee/pretrain.py` + Liger, random init) **não é o caso de uso**.

## Aplicação ao Bee — por fase
| Fase do Bee | Unsloth Studio serve? |
|---|---|
| **Pré-treino do zero** (agora) | ❌ **Não.** Segue loop próprio + Liger no RunPod/Colab. |
| **SFT / pós-treino** (próxima fase) | ✅ **Sim, é onde brilha** (ver abaixo). |
| **Demo / serving** | ✅ export **GGUF** → llama.cpp local (casa com ZeroGPU/HF). |

### Onde é ótimo (fase de SFT)
1. **Roda LOCAL no laptop do Bruno (RTX 5070 8GB), de graça.** O Bee (150M-1B) cabe folgado em 8GB com
   QLoRA + os 70% de economia de VRAM → **SFT local a $0**, sem alugar GPU. Diferencial real.
2. **2× mais rápido** no fine-tune (kernels Triton próprios — mesma família do Liger que já usamos).
3. **Data Recipes** — geração de dataset sintético local: complementa o plano do teacher DeepSeek-V4.
4. **No-code** — itera rápido no SFT sem escrever loop.

## Ressalvas honestas
- **Re-medir paridade de acurácia** antes de adotar (o plano do Bee já alertava: "o README não garante
  paridade"). Kernels agressivos às vezes trocam fidelidade numérica.
- **Licença:** AGPL-3.0 é só da **UI** — **não contamina os pesos treinados** (o modelo é seu). Só importaria
  se construísse um produto *em cima da UI* do Studio. Os pesos/output ficam livres.
- Já havia `sft_qlora.py` (PEFT+QLoRA) planejado — Unsloth seria um **backend alternativo mais rápido** pra
  essa mesma fase, a medir contra o PEFT puro (paridade + velocidade).

## Veredito
Não muda o pré-treino (**RunPod segue principal** pra isso). Entra como **ferramenta da fase de SFT** —
provavelmente **local no laptop, de graça**: SFT leve local $0 + pré-treino pesado no RunPod. **Complemento,
não substituto.** Casa com o resto do plano: teacher DeepSeek-V4 (dados) → Unsloth (SFT rápido local) →
GGUF (demo). Ver [estudo-teachers-destilacao](estudo-teachers-destilacao-2026-08-01.md) e
[estudo-huggingface](estudo-huggingface-2026-08-02.md).
