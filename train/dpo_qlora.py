"""Fase 4 — DPO (Direct Preference Optimization) via QLoRA no Qwen3.5-4B.

ESQUELETO. Roda DEPOIS do SFT: refina o modelo com pares de preferência
(escolhido > rejeitado) sem precisar de reward model nem RL (o "barato e alto
impacto" do roadmap). Espelha train/sft_qlora.py (mesma calibração de VRAM para L4).

═══════════════════════════════════════════════════════════════════════════════
⚠️ DUAS DEPENDÊNCIAS QUE AINDA NÃO EXISTEM (marcar antes de rodar de verdade):

1) DADOS DE PREFERÊNCIA (`data/processed/preferences_ptbr.jsonl`)
   Formato por linha (não-conversacional, o que o TRL DPOTrainer consome):
       {"prompt": "...", "chosen": "resposta boa", "rejected": "resposta pior"}
   NÃO temos isso ainda. Falta um `data/06_build_preferences.py` que gere os pares.
   Estratégias possíveis (a decidir):
     - amostrar 2 respostas do professor por prompt (temperaturas diferentes) e o
       juiz aberto (mesmo do quantibias_gate) escolhe a melhor → chosen/rejected;
     - chosen = resposta do professor forte (DeepSeek V4 Pro), rejected = resposta
       do próprio 4B pós-SFT (o modelo aprende a preferir o que é melhor que ele);
     - datasets de preferência PT-BR traduzidos (UltraFeedback) com QC (script 02).
   O 2º casa com o "error bootstrapping" (Learn2Zinc) que ficou no estudo.

2) MODELO DE REFERÊNCIA (escolha teórica — ler o bloco em `main`):
   O DPO precisa de um ref model congelado. Aqui usamos o base (adapter desligado)
   como referência implícita — simples e funciona, mas o ideal teórico é a
   referência ser o próprio SFT. Ver TODO no código para a versão de 2 adapters.
═══════════════════════════════════════════════════════════════════════════════

Uso (na L4 do Colab, depois de ter os dados de preferência):
    python train/dpo_qlora.py --sft-adapter /content/drive/MyDrive/qwen35-4b-ptbr-sft \
        --data data/processed/preferences_ptbr.jsonl --epochs 1
    python train/dpo_qlora.py --data ... --dry-run     # valida config sem treinar
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "models" / "qwen3.5-4b-ptbr-dpo"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B", help="modelo base")
    ap.add_argument("--sft-adapter", default=None,
                    help="adapter LoRA do SFT — ponto de partida do DPO (recomendado). "
                         "Sem ele, treina DPO direto sobre o base (menos eficaz).")
    ap.add_argument("--data", type=Path,
                    default=ROOT / "data" / "processed" / "preferences_ptbr.jsonl")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    # DPO segura chosen+rejected → ~2x memória do SFT. Sequência mais curta por padrão.
    ap.add_argument("--max-seq-len", type=int, default=1536)
    ap.add_argument("--max-prompt-len", type=int, default=512)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--lr", type=float, default=5e-6, help="DPO usa LR bem menor que SFT")
    ap.add_argument("--beta", type=float, default=0.1,
                    help="força do KO ao ref: menor=mais livre, maior=mais conservador")
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=16)
    ap.add_argument("--lora-r", type=int, default=16, help="só usado se NÃO houver --sft-adapter")
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--save-steps", type=int, default=100)
    ap.add_argument("--max-steps", type=int, default=-1, help="limita passos (smoke test)")
    ap.add_argument("--max-grad-norm", type=float, default=0.3,
                    help="clipping de gradiente — rede contra spikes no DPO (o estudo sugeriu "
                         "percentile_clipping=5 no bnb; via HF Trainer usamos max_grad_norm)")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def check_data(path: Path) -> int:
    """Valida o formato do jsonl de preferência. Retorna nº de linhas válidas."""
    if not path.exists():
        print(f"ERRO: dados de preferência não encontrados: {path}", file=sys.stderr)
        print("      Falta gerar os pares chosen/rejected (ver docstring). Nada para treinar.",
              file=sys.stderr)
        return 0
    n, bad = 0, 0
    with path.open(encoding="utf-8-sig") as f:  # utf-8-sig: tolera BOM (lição do common.py)
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if all(k in row for k in ("prompt", "chosen", "rejected")):
                n += 1
            else:
                bad += 1
    if bad:
        print(f"AVISO: {bad} linhas sem os campos prompt/chosen/rejected.", file=sys.stderr)
    return n


def check_vram() -> None:
    import torch
    if not torch.cuda.is_available():
        print("ERRO: CUDA indisponível.", file=sys.stderr)
        raise SystemExit(1)
    p = torch.cuda.get_device_properties(0)
    print(f"GPU: {p.name} | {p.total_memory/1024**3:.1f} GB | sm_{p.major}{p.minor}")
    if p.total_memory / 1024**3 < 16:
        print("AVISO: DPO segura 2 sequências (chosen+rejected). <16GB pode faltar — "
              "reduza --max-seq-len ou rode na L4.")


def main() -> int:
    args = parse_args()

    n_valid = check_data(args.data)
    effective_batch = args.batch_size * args.grad_accum
    print("=== Config DPO QLoRA ===")
    print(f"  modelo        : {args.model}")
    print(f"  sft-adapter   : {args.sft_adapter or '(nenhum — DPO direto no base)'}")
    print(f"  dados         : {args.data} ({n_valid} pares válidos)")
    print(f"  saida         : {args.out}")
    print(f"  max_seq/prompt: {args.max_seq_len} / {args.max_prompt_len}")
    print(f"  epochs        : {args.epochs} | beta: {args.beta} | lr: {args.lr}")
    print(f"  batch efetivo : {effective_batch} ({args.batch_size} x {args.grad_accum})")

    if args.dry_run:
        print("\n[dry-run] config validada, nada foi treinado.")
        if n_valid == 0:
            print("[dry-run] ⚠️ 0 pares de preferência — gerar os dados antes do run real.")
        return 0

    if n_valid == 0:
        return 1

    check_vram()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, PeftModel, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import DPOConfig, DPOTrainer

    print("\ncarregando base em 4-bit...")
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
        args.model, quantization_config=bnb, dtype=torch.bfloat16,
        device_map={"": 0}, trust_remote_code=True,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    # ── POLÍTICA (o que treinamos) ──
    # Se há adapter do SFT, partimos DELE (o DPO refina o modelo já instruído).
    # Senão, criamos um LoRA novo sobre o base.
    peft_config = None
    if args.sft_adapter:
        print(f"partindo do adapter SFT: {args.sft_adapter}")
        model = PeftModel.from_pretrained(model, args.sft_adapter, is_trainable=True)
    else:
        peft_config = LoraConfig(
            r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05, bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                            "gate_proj", "up_proj", "down_proj"],
        )

    # ── REFERÊNCIA ──
    # ref_model=None + modelo PEFT → o DPOTrainer usa "adapter desligado" como
    # referência. Como o único adapter é o que treinamos, a referência = BASE.
    # ⚠️ TODO teórico: o ideal é ref = SFT congelado (não o base). Para isso, usar
    # DOIS adapters: carregar o SFT como `ref_adapter_name` (congelado) e um NOVO
    # adapter DPO como `model_adapter_name` (treinável). Requer criar o adapter DPO
    # separado e passar model_adapter_name/ref_adapter_name ao DPOConfig. Fica como
    # melhoria — o base-como-ref já roda e é usado na prática.
    ref_model = None

    dataset = load_dataset("json", data_files=str(args.data), split="train")

    cfg = DPOConfig(
        output_dir=str(args.out),
        num_train_epochs=args.epochs,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        gradient_checkpointing=True,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        logging_steps=10,
        save_steps=args.save_steps,
        save_total_limit=2,
        bf16=True,
        beta=args.beta,
        max_length=args.max_seq_len,
        max_prompt_length=args.max_prompt_len,
        max_grad_norm=args.max_grad_norm,
        optim="paged_adamw_8bit",
        report_to="none",
        seed=42,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=ref_model,
        args=cfg,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,  # None se partimos do adapter SFT
    )

    print("\ntreinando DPO... (Ctrl+C interrompe; checkpoints em save_steps)")
    trainer.train()

    args.out.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.out))
    tokenizer.save_pretrained(str(args.out))
    (args.out / "training_args.json").write_text(
        json.dumps(vars(args), default=str, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nAdapter DPO salvo em {args.out}")
    print("Proximo: avaliar (eval/run_baseline.py --peft ...) e comparar com o SFT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
