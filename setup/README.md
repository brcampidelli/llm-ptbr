# Setup do ambiente local (RTX 5070 / Blackwell sm_120)

## ✅ STATUS: INSTALADO E VALIDADO (2026-07-23)

Ambiente de pé em `.venv/` (5,1 GB). Versões travadas e testadas nesta máquina:

| Pacote | Versão |
|---|---|
| torch | **2.11.0+cu128** |
| transformers | 5.14.1 |
| trl | 1.9.0 |
| peft | 0.19.1 |
| bitsandbytes | 0.49.2 |
| accelerate | 1.14.0 |
| datasets | 5.0.0 |
| lm_eval | 0.4.12 |
| CUDA | 12.8 · RTX 5070 Laptop GPU |

**Testes que passaram:**
- ✅ `torch.cuda.is_available()` → True; matmul real na GPU (kernel sm_120 OK)
- ✅ **QLoRA 4-bit NF4 + forward + backward** no Qwen3-0.6B → loss 4.96, 0.89 GB VRAM.
  Confirma que os kernels do bitsandbytes rodam em Blackwell — era o maior risco do setup local.
- ✅ Pipeline de dados 03→04→05 end-to-end com fixtures sintéticos (todos os filtros corretos)
- ✅ Guard de licença bloqueia GPT/Claude/Gemini e modelos não-listados

**Notas:**
- `triton not found` — aviso benigno (só afeta contagem de FLOPs). **Unsloth não foi instalado**
  (precisa de triton, problemático no Windows) — e não é necessário: `train/sft_qlora.py` usa
  transformers+peft+trl direto.
- Symlinks do cache HF desativados (Windows sem Developer Mode) → usa mais disco, funciona igual.
- Recomendado: `huggingface-cli login` para downloads mais rápidos e sem rate limit.

---


⚠️ **Gotcha crítico:** o RTX 5070 Laptop é **Blackwell (compute sm_120)**. O PyTorch estável comum
(builds cu121/cu124) **não traz kernels sm_120** → erro `no kernel image is available for execution on
the device`. É obrigatório instalar o **PyTorch com CUDA 12.8 (cu128)**.

Estado da máquina (verificado 2026-07-23): Python 3.11.15 ✅ · torch ❌ · CUDA toolkit ❌ · Ollama instalado.

## Passo 1 — venv
```powershell
cd "C:\Users\brcam\Desktop\Desenvolvendo Projetos\Desenvolvendo LLM"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
```

## Passo 2 — PyTorch cu128 (Blackwell) — NÃO pular a flag do índice
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```
Validar (tem que dar `True` + a GPU + CUDA 12.8):
```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.version.cuda, torch.cuda.get_device_name(0))"
```
Teste real de kernel sm_120 (tem que rodar sem erro):
```powershell
python -c "import torch; x=torch.randn(1024,1024,device='cuda'); print((x@x).sum().item())"
```

## Passo 3 — Stack de treino/avaliação
```powershell
pip install -U transformers accelerate datasets peft trl bitsandbytes
pip install -U "lm-eval[api]"
# Unsloth (QLoRA rápido em ≤4B na 8GB). Se a versão reclamar do torch cu128, usar transformers+peft+trl direto.
pip install -U unsloth
```

## Passo 4 — Login no Hugging Face (baixar Qwen3 + publicar depois)
```powershell
pip install -U huggingface_hub
huggingface-cli login   # colar o token (o Bruno gera em huggingface.co/settings/tokens)
```

## Notas de VRAM (8 GB é o teto)
- **Qwen3-4B QLoRA (4-bit):** cabe (~5–7 GB) com `max_seq_len` moderado (2k–4k) e batch 1–2 + grad accumulation.
- **Qwen3-8B:** só **inferência** quantizada aqui (Q4 GGUF via llama.cpp/Ollama). Treino do 8B → cloud.
- Se estourar VRAM: reduzir `max_seq_len`, batch=1, ativar gradient checkpointing, fechar Chrome/apps de GPU.

## Próximo
Depois do setup: `eval/README.md` → rodar o **baseline do Qwen3-4B** (o número a bater).
