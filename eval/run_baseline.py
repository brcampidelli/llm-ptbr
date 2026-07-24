"""Fase 1 — Rodar a avaliação PT-BR (baseline e checkpoints treinados).

Por que um script em vez do CLI `lm_eval`:
o CLI não aceita `load_in_4bit` no transformers 5.x (vai direto pro construtor do
modelo e quebra). Aqui montamos o BitsAndBytesConfig e passamos via kwargs do HFLM
— que é o único jeito de fazer um 4B caber nos 8 GB da RTX 5070.

Uso:
    python eval/run_baseline.py                          # baseline da base crua
    python eval/run_baseline.py --limit 200              # amostra rapida (iterar)
    python eval/run_baseline.py --limit 0                # rodada completa (oficial)
    python eval/run_baseline.py --peft models/qwen3.5-4b-ptbr-sft --tag sft
    python eval/run_baseline.py --no-4bit                # se sobrar VRAM
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"

# Duas suítes. Motivo: `mmmlu_pt_br` tem 57 matérias e sozinho responde por ~90%
# das requisições (≈22.800 de 25.300 com --limit 100). Serve para o número oficial,
# não para iterar.
QUICK_TASKS = [
    "arc_pt",                # raciocinio cientifico
    "hellaswag_pt",          # senso comum
    "truthfulqa_pt_mc2",     # veracidade / alucinacao
    "xwinograd_pt",          # correferencia
    "assin_entailment",      # NATIVO em portugues
    "assin_paraphrase",      # NATIVO em portugues
    "belebele_por_Latn",     # compreensao de leitura
]

CORE_TASKS = ["mmmlu_pt_br"] + QUICK_TASKS   # + MMLU pt-BR: o numero oficial

SUITES = {"quick": QUICK_TASKS, "core": CORE_TASKS}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--peft", default=None, help="caminho do adapter LoRA a avaliar")
    ap.add_argument("--suite", choices=sorted(SUITES), default="quick",
                    help="quick = iterar (sem mmmlu) | core = numero oficial")
    ap.add_argument("--tasks", default=None, help="lista explicita; sobrepoe --suite")
    ap.add_argument("--num-fewshot", type=int, default=3)
    # ⚠️ NAO usar "auto": o Qwen3.5 usa gated delta rule e, sem a lib
    # flash-linear-attention, cai num fallback torch que estoura os 8 GB.
    ap.add_argument("--batch-size", default="4")
    ap.add_argument("--limit", type=int, default=200, help="0 = dataset completo")
    ap.add_argument("--no-4bit", action="store_true", help="carregar em bf16 (precisa de VRAM)")
    ap.add_argument("--tag", default="baseline")
    args = ap.parse_args()

    import torch
    from lm_eval import simple_evaluate
    from lm_eval.models.huggingface import HFLM
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    if not torch.cuda.is_available():
        print("ERRO: CUDA indisponivel.")
        return 1
    total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"GPU: {torch.cuda.get_device_name(0)} ({total_vram:.1f} GB)")

    tasks = ([t.strip() for t in args.tasks.split(",") if t.strip()]
             if args.tasks else SUITES[args.suite])
    print(f"suite  : {args.suite if not args.tasks else 'custom'}")
    print(f"modelo : {args.model}")
    print(f"tasks  : {len(tasks)} -> {', '.join(tasks)}")
    print(f"fewshot: {args.num_fewshot} | limit: {args.limit or 'completo'}\n")

    # Carregamos o modelo AQUI, não pelo HFLM. Motivo: passar quantization_config
    # pelos kwargs do HFLM colide com o argumento que ele mesmo repassa para
    # _create_model ("got multiple values for keyword argument"). Entregando um
    # PreTrainedModel já pronto, contornamos isso e controlamos a quantização.
    model_kwargs: dict = {"dtype": torch.bfloat16, "device_map": {"": 0}}
    if not args.no_4bit:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        print("quantizacao: 4-bit NF4")

    print("carregando modelo...")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)

    if args.peft:
        from peft import PeftModel

        print(f"aplicando adapter LoRA: {args.peft}")
        model = PeftModel.from_pretrained(model, args.peft)
    model.eval()

    used = torch.cuda.memory_allocated() / 1024**3
    print(f"VRAM ocupada pelo modelo: {used:.2f} GB de {total_vram:.1f} GB\n")

    lm = HFLM(pretrained=model, tokenizer=tokenizer, batch_size=args.batch_size)

    results = simple_evaluate(
        model=lm,
        tasks=tasks,
        num_fewshot=args.num_fewshot,
        limit=args.limit if args.limit > 0 else None,
    )

    # --- tabela resumida ---
    print("\n" + "=" * 68)
    print(f"{'TASK':<34} {'METRICA':<18} {'VALOR':>10}")
    print("-" * 68)
    rows: dict[str, dict] = {}
    for task, metrics in sorted(results.get("results", {}).items()):
        for metric, value in metrics.items():
            if metric in ("alias",) or metric.endswith("_stderr,none"):
                continue
            if isinstance(value, (int, float)):
                print(f"{task:<34} {metric:<18} {value:>10.4f}")
                rows.setdefault(task, {})[metric] = value
    print("=" * 68)

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = RESULTS / f"{args.tag}_{stamp}.json"
    payload = {
        "tag": args.tag,
        "model": args.model,
        "peft": args.peft,
        "num_fewshot": args.num_fewshot,
        "limit": args.limit,
        "quantized_4bit": not args.no_4bit,
        "timestamp_utc": stamp,
        "results": rows,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nsalvo em {out}")
    print("Compare cada treino contra este numero. Ganho sem regressao = progresso real.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
