"""Fase 3 — SFT via QLoRA no Qwen3-4B (local, RTX 5070 8 GB).

Calibrado para caber em 8 GB de VRAM:
  - carga em 4-bit (NF4) + double quant
  - LoRA r=16 nas projeções de atenção e MLP
  - batch 1 + gradient accumulation (batch efetivo configurável)
  - gradient checkpointing ligado
  - max_seq_len 2048 por padrão (subir só se sobrar VRAM)

Uso:
    python train/sft_qlora.py --data data/processed/sft_ptbr.jsonl
    python train/sft_qlora.py --data ... --max-seq-len 1024 --epochs 2
    python train/sft_qlora.py --data ... --dry-run     # valida config sem treinar

Se estourar VRAM: baixar --max-seq-len (1024), manter batch 1, fechar apps de GPU.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "models" / "qwen3-4b-ptbr-sft"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    # 🔴 SEM DEFAULT, DE PROPOSITO. Este arquivo nasceu do plano de fine-tunar um
    #    Qwen3.5-4B, que foi ABANDONADO — o projeto pre-treina modelos proprios. O default
    #    antigo ("Qwen/Qwen3.5-4B") sobreviveu ao abandono: rodar isto hoje baixaria 8 GB e
    #    treinaria o modelo ERRADO sem emitir um unico aviso. Mesma familia de "o dado some
    #    e nada reclama" que ja custou tres vezes a este projeto (ver docs/licoes-de-metodo).
    #    Agora e' obrigatorio dizer qual modelo se esta treinando.
    #    Os modelos do projeto: BrCamp/bee-350m-pt-base · BrCamp/bee-150m-pt-base
    ap.add_argument("--model", required=True,
                    help="OBRIGATORIO. ex.: BrCamp/bee-350m-pt-base")
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "processed" / "sft_ptbr.jsonl")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-seq-len", type=int, default=2048)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch-size", type=int, default=1, help="por dispositivo — manter 1 em 8GB")
    ap.add_argument("--grad-accum", type=int, default=16, help="batch efetivo = batch-size * grad-accum")
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--save-steps", type=int, default=200)
    ap.add_argument("--max-steps", type=int, default=-1,
                    help="limita os passos (use para smoke test antes do treino real)")
    ap.add_argument("--packing", action="store_true",
                    help="empacota exemplos curtos numa mesma sequencia (mediana dos nossos "
                         "dados e ~450 tokens contra max_seq_len 2048 — reduz passos)")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def check_vram() -> None:
    import torch

    if not torch.cuda.is_available():
        print("ERRO: CUDA indisponivel. Confira o setup (torch cu128).", file=sys.stderr)
        raise SystemExit(1)
    name = torch.cuda.get_device_name(0)
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    cap = torch.cuda.get_device_capability(0)
    print(f"GPU: {name} | {total:.1f} GB | compute sm_{cap[0]}{cap[1]}")
    if total < 7.0:
        print("AVISO: menos de 7 GB de VRAM — reduza --max-seq-len para 1024.")


def main() -> int:
    args = parse_args()

    if not args.data.exists():
        print(f"ERRO: dataset nao encontrado: {args.data}", file=sys.stderr)
        print("Rode o pipeline de dados (data/01..05) antes.", file=sys.stderr)
        return 1

    n_examples = sum(1 for _ in args.data.open(encoding="utf-8") if _.strip())
    effective_batch = args.batch_size * args.grad_accum
    print("=== Config SFT QLoRA ===")
    print(f"  modelo        : {args.model}")
    print(f"  dados         : {args.data} ({n_examples} exemplos)")
    print(f"  saida         : {args.out}")
    print(f"  max_seq_len   : {args.max_seq_len}")
    print(f"  epochs        : {args.epochs}")
    print(f"  batch efetivo : {effective_batch} ({args.batch_size} x {args.grad_accum})")
    print(f"  LoRA          : r={args.lora_r} alpha={args.lora_alpha}")
    print(f"  lr            : {args.lr}")

    if args.dry_run:
        print("\n[dry-run] config validada, nada foi treinado.")
        return 0

    check_vram()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    print("\ncarregando tokenizer/modelo em 4-bit...")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb,
        dtype=torch.bfloat16,
        device_map={"": 0},
        trust_remote_code=True,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    lora = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    dataset = load_dataset("json", data_files=str(args.data), split="train")

    # ⚠️ DIAGNOSTICO DE MASCARAMENTO DA LOSS — nunca treinar as cegas de novo.
    # Bug real (2026-07-24): com {"messages"} + system prompt grande, o TRL calcula
    # a loss em TODOS os tokens (assistant_only_loss=False por padrao). No dataset
    # agentico o system tinha 928 tok (92,1% do exemplo) e era IDENTICO nos 1495
    # exemplos -> a loss caiu 1,273->0,0755 DECORANDO o catalogo, com so 6,2% dos
    # tokens medindo a habilidade real. O formato prompt/completion faz o TRL
    # mascarar o prompt sozinho (e nao exige {% generation %} no chat template).
    cols = set(dataset.column_names)
    if {"prompt", "completion"} <= cols:
        print("loss     : MASCARADA no prompt (dataset prompt/completion) ✅")
    elif "messages" in cols:
        print("loss     : em TODOS os tokens (dataset 'messages')")
        print("           ⚠️ se houver system prompt grande e repetido, o sinal fica")
        print("           diluido. Regere os splits com 05_build_splits --prompt-completion.")
    else:
        print(f"AVISO: colunas inesperadas no dataset: {sorted(cols)}", file=sys.stderr)

    cfg = SFTConfig(
        output_dir=str(args.out),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        gradient_checkpointing=True,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=10,
        save_steps=args.save_steps,
        save_total_limit=2,
        bf16=True,
        max_length=args.max_seq_len,
        packing=args.packing,
        optim="paged_adamw_8bit",
        report_to="none",
        seed=42,
    )

    trainer = SFTTrainer(model=model, args=cfg, train_dataset=dataset, processing_class=tokenizer)

    print("\ntreinando... (Ctrl+C interrompe; checkpoints em save_steps)")
    trainer.train()

    args.out.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.out))
    tokenizer.save_pretrained(str(args.out))
    (args.out / "training_args.json").write_text(
        json.dumps(vars(args), default=str, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nAdapter LoRA salvo em {args.out}")
    print("Proximo: avaliar (eval/) e comparar com o baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
