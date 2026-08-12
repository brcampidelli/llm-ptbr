"""Avalia um modelo ja treinado num holdout de SFT, sem retreinar.

Por que existe: comparar dois modelos SFT (ou o mesmo modelo em holdouts
diferentes) exige que a loss seja calculada com a MESMA mascara de prompt do
treino. Reimplementar essa mascara a mao e a receita para medir outra coisa e
nao perceber — foi assim que o pre-treino deste projeto perdeu duas semanas.
Este script reusa o proprio SFTTrainer, entao a regua e identica por construcao.

Uso:
    python bee/eval_sft.py --modelo /workspace/ep_2 \
        --eval comeia/data/processed/sft_ptbr.eval.jsonl

    # varios holdouts de uma vez (imprime uma linha por arquivo)
    python bee/eval_sft.py --modelo /workspace/misto \
        --eval a.eval.jsonl b.eval.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bee.sft import carregar_prompt_completion  # noqa: E402  (mesma conversao do treino)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", required=True, help="caminho local ou repo HF do modelo SFT")
    ap.add_argument("--eval", type=Path, nargs="+", required=True,
                    help="um ou mais .jsonl de holdout")
    ap.add_argument("--max-seq-len", type=int, default=1024,
                    help="tem de bater com o usado no treino, senao a loss nao e comparavel")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--json", type=Path, help="opcional: grava os resultados aqui")
    return ap.parse_args()


def main() -> int:
    args = parse_args()

    faltando = [p for p in args.eval if not p.exists()]
    if faltando:
        print(f"ERRO: holdout nao encontrado: {faltando}", file=sys.stderr)
        return 1

    import torch

    if not torch.cuda.is_available():
        print("ERRO: CUDA indisponivel.", file=sys.stderr)
        return 1

    from datasets import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    print(f"carregando {args.modelo} (bf16)...")
    tok = AutoTokenizer.from_pretrained(args.modelo)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(args.modelo, dtype=torch.bfloat16)
    modelo.config.use_cache = False

    resultados = {}
    for caminho in args.eval:
        exemplos = carregar_prompt_completion(caminho)
        ds = Dataset.from_list(exemplos)

        cfg = SFTConfig(
            output_dir="/tmp/eval_sft",
            per_device_eval_batch_size=args.batch,
            bf16=True,
            max_length=args.max_seq_len,
            report_to="none",
            seed=42,
        )
        # train_dataset e exigido pelo construtor; nada e treinado — so evaluate().
        trainer = SFTTrainer(model=modelo, args=cfg, train_dataset=ds,
                             eval_dataset=ds, processing_class=tok)
        m = trainer.evaluate()

        resultados[caminho.name] = {
            "exemplos": len(exemplos),
            "eval_loss": round(m["eval_loss"], 4),
            "acuracia_token": round(m.get("eval_mean_token_accuracy", float("nan")), 4),
        }
        r = resultados[caminho.name]
        print(f"  {caminho.name:<32} n={r['exemplos']:>5}  "
              f"loss={r['eval_loss']:.4f}  acc/token={r['acuracia_token']:.4f}")

    if args.json:
        args.json.write_text(json.dumps({"modelo": args.modelo, "holdouts": resultados},
                                        indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[OK] resultados em {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
