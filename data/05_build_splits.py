"""Fase 2.5 — Montar os splits finais de treino.

Entrada : data/processed/decontaminated.jsonl
Saidas  : data/processed/sft_ptbr.jsonl        (formato chat p/ SFT)
          data/processed/sft_ptbr.eval.jsonl   (holdout interno, nao usado no treino)

Formato de saída (chat template — o que TRL/Unsloth consomem):
    {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}

Uso:
    python data/05_build_splits.py --holdout 500 --seed 42
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PROCESSED_DIR, SFT_OUT, ensure_dirs  # noqa: E402
from common import read_jsonl, write_jsonl  # noqa: E402

IN = PROCESSED_DIR / "decontaminated.jsonl"
EVAL_OUT = PROCESSED_DIR / "sft_ptbr.eval.jsonl"


def to_chat(row: dict) -> dict:
    return {
        "messages": [
            {"role": "user", "content": row["instruction"]},
            {"role": "assistant", "content": row["response"]},
        ],
        "source": row.get("source", "?"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", type=int, default=500, help="exemplos reservados p/ avaliacao interna")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    ensure_dirs()
    if not IN.exists():
        print(f"ERRO: {IN} nao existe. Rode data/04_decontaminate.py antes.", file=sys.stderr)
        return 1

    rows = [to_chat(r) for r in read_jsonl(IN) if r.get("instruction") and r.get("response")]
    if not rows:
        print("ERRO: nenhum exemplo valido.", file=sys.stderr)
        return 1

    random.Random(args.seed).shuffle(rows)
    holdout = min(args.holdout, max(0, len(rows) // 10))  # nunca mais que 10% do total
    eval_rows, train_rows = rows[:holdout], rows[holdout:]

    n_train = write_jsonl(SFT_OUT, train_rows)
    n_eval = write_jsonl(EVAL_OUT, eval_rows)

    print(f"treino  : {n_train} -> {SFT_OUT}")
    print(f"holdout : {n_eval} -> {EVAL_OUT}")
    print("\nProximo: python train/sft_qlora.py --data data/processed/sft_ptbr.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
