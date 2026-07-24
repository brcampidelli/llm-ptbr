# Fases 3–5 — Treino (SFT → DPO → RL)

Loop atual: **local, Qwen3-4B, QLoRA, US$0** na RTX 5070 (8 GB).
Escala para Qwen3-8B em cloud alugada só depois que o benchmark provar ganho.

## Fase 3 — SFT (implementado: `sft_qlora.py`)

```powershell
.\.venv\Scripts\Activate.ps1

# validar a config sem treinar
python train/sft_qlora.py --data data/processed/sft_ptbr.jsonl --dry-run

# treinar
python train/sft_qlora.py --data data/processed/sft_ptbr.jsonl

# se estourar VRAM
python train/sft_qlora.py --data data/processed/sft_ptbr.jsonl --max-seq-len 1024
```

### Por que estes números (calibrado para 8 GB)
| Parâmetro | Valor | Motivo |
|---|---|---|
| Quantização | 4-bit NF4 + double quant | Qwen3-4B em bf16 não caberia; em 4-bit fica ~3 GB e sobra para ativações. |
| `batch_size` | 1 | Acima disso estoura. O volume vem do `grad_accum`. |
| `grad_accum` | 16 | Batch efetivo 16 sem custo de VRAM. |
| `max_seq_len` | 2048 | Ativações crescem com o quadrado do contexto — é o primeiro dial a baixar se faltar VRAM. |
| `gradient_checkpointing` | on | Troca compute por memória. Essencial em 8 GB. |
| LoRA r=16, alpha=32 | — | Bom equilíbrio capacidade/memória para 4B. |
| `optim` | `paged_adamw_8bit` | Otimizador paginado evita picos de VRAM. |

**Alvos LoRA:** `q/k/v/o_proj` + `gate/up/down_proj` (atenção + MLP) — cobertura ampla, ainda leve.

## Fase 4 — Preferência (DPO/ORPO) — a implementar
Consome `preferences_ptbr.jsonl`. Mesma receita de VRAM (4-bit + LoRA). Barato e alto impacto
em qualidade percebida.

## Fase 5 — RL (GRPO) — a implementar, requer cloud
Tarefas verificáveis (matemática/código/seguir-instrução), abordagem PEARL/CriPO/Distilled-RL.
Não cabe em 8 GB — só ao escalar.

## Convenção de rodadas
Cada treino grava em `models/<nome>/` com `training_args.json` (config exata usada).
Sempre avaliar contra o **baseline** (`eval/`) antes de aceitar um checkpoint como melhoria.

## Regra
**Iterar dados > iterar hiperparâmetros.** Se o resultado não melhorar, o problema quase sempre está
na Fase 2 (quantidade/variedade/qualidade das sementes), não no learning rate.
