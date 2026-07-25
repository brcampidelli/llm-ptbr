"""Fase 2.5 — Montar os splits finais de treino.

Entrada : data/processed/decontaminated.jsonl
Saidas  : data/processed/sft_ptbr.jsonl        (formato chat p/ SFT)
          data/processed/sft_ptbr.eval.jsonl   (holdout interno, nao usado no treino)

Formato de saída (chat template — o que TRL/Unsloth consomem):
    {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}

Uso:
    python data/05_build_splits.py --holdout 500 --seed 42
    python data/05_build_splits.py --cot        # inclui o raciocínio do professor no alvo

Com --cot, exemplos que têm o campo 'reasoning' (destilados com 01_distill_teacher.py --cot)
viram alvo "<think>\\n{raciocínio}\\n</think>\\n\\n{resposta}" — o aluno aprende a raciocinar
no mesmo formato do Qwen3.5. Sem --cot (padrão), treina só a resposta final.
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


def to_chat(row: dict, cot: bool = False, system: str | None = None) -> dict:
    answer = row["response"]
    reasoning = row.get("reasoning", "")
    if cot and reasoning:
        answer = f"<think>\n{reasoning}\n</think>\n\n{answer}"
    msgs = []
    # System message opcional. Necessario para abelhas cujo comportamento depende
    # de contexto — a agentica precisa VER o catalogo de ferramentas no treino,
    # senao decora as 14 em vez de aprender a ler o catalogo e escolher.
    if system:
        msgs.append({"role": "system", "content": system})
    msgs += [
        {"role": "user", "content": row["instruction"]},
        {"role": "assistant", "content": answer},
    ]
    out = {"messages": msgs, "source": row.get("source", "?")}
    if row.get("kind"):          # abelha agentica: tool_call | text
        out["kind"] = row["kind"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", type=int, default=500, help="exemplos reservados p/ avaliacao interna")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--cot", action="store_true",
                    help="inclui o raciocínio (campo 'reasoning') como <think> no alvo de treino")
    # Parametros para servir QUALQUER abelha da comeia (default = pipeline PT-BR original).
    ap.add_argument("--in", dest="in_path", type=Path, default=IN,
                    help="jsonl de entrada {instruction,response}")
    ap.add_argument("--out", type=Path, default=SFT_OUT, help="jsonl de treino")
    ap.add_argument("--eval-out", type=Path, default=EVAL_OUT, help="jsonl de holdout")
    ap.add_argument("--system-file", type=Path, default=None,
                    help="arquivo com a system message a embutir em cada exemplo "
                         "(a abelha agentica precisa do catalogo de ferramentas)")
    args = ap.parse_args()

    ensure_dirs()
    if not args.in_path.exists():
        print(f"ERRO: {args.in_path} nao existe. Rode a etapa anterior antes.", file=sys.stderr)
        return 1

    system = None
    if args.system_file:
        if not args.system_file.exists():
            print(f"ERRO: system-file nao existe: {args.system_file}", file=sys.stderr)
            return 1
        system = args.system_file.read_text(encoding="utf-8-sig").strip()
        print(f"system message: {len(system)} chars de {args.system_file.name}")

    raw_rows = [r for r in read_jsonl(args.in_path) if r.get("instruction") and r.get("response")]
    n_with_reasoning = sum(1 for r in raw_rows if r.get("reasoning"))
    rows = [to_chat(r, cot=args.cot, system=system) for r in raw_rows]
    if not rows:
        print("ERRO: nenhum exemplo valido.", file=sys.stderr)
        return 1
    if args.cot:
        print(f"CoT ligado: {n_with_reasoning}/{len(rows)} exemplos com raciocínio embutido no alvo")
    elif n_with_reasoning:
        print(f"AVISO: {n_with_reasoning} exemplos têm 'reasoning' mas --cot está desligado "
              "(o raciocínio será ignorado). Use --cot para treiná-lo.")

    random.Random(args.seed).shuffle(rows)
    holdout = min(args.holdout, max(0, len(rows) // 10))  # nunca mais que 10% do total
    eval_rows, train_rows = rows[:holdout], rows[holdout:]

    n_train = write_jsonl(args.out, train_rows)
    n_eval = write_jsonl(args.eval_out, eval_rows)

    # Distribuicao por 'kind' (abelha agentica): tool_call vs text. Se o texto
    # sumir, a abelha vira "chama ferramenta pra tudo" (over-calling).
    kinds = {}
    for r in train_rows:
        if r.get("kind"):
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    if kinds:
        tot = sum(kinds.values())
        dist = " | ".join(f"{k}={v} ({v/tot:.0%})" for k, v in sorted(kinds.items()))
        print(f"tipos   : {dist}")

    print(f"treino  : {n_train} -> {args.out}")
    print(f"holdout : {n_eval} -> {args.eval_out}")
    print(f"\nProximo: python train/sft_qlora.py --data {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
