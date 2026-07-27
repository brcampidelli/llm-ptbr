"""Exportar os conjuntos de TESTE dos benchmarks para decontaminação.

O script data/04_decontaminate.py precisa saber o que está nos testes para remover
qualquer exemplo de treino que os vaze. Este script materializa esses conjuntos em
eval/benchmarks/*.jsonl.

Rodar UMA vez (e de novo se a suíte de tasks mudar):
    python eval/export_benchmarks.py
    python eval/export_benchmarks.py --tasks mmmlu_pt_br,arc_pt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "eval" / "benchmarks"

DEFAULT_TASKS = [
    "mmmlu_pt_br",
    "arc_pt",
    "hellaswag_pt",
    "truthfulqa_pt_mc2",
    "xwinograd_pt",
    "assin_entailment",
    "assin_paraphrase",
    "belebele_por_Latn",
]

# Campos de texto que valem indexar (enunciado + alternativas + resposta).
TEXT_KEYS = (
    "question", "query", "text", "sentence", "premise", "hypothesis", "ctx",
    "passage", "flores_passage", "goal", "activity_label", "answer", "output",
    "sentence1", "sentence2", "doc", "input",
)


def extract_texts(doc: dict) -> list[str]:
    out: list[str] = []
    for k, v in doc.items():
        if k in TEXT_KEYS and isinstance(v, str) and v.strip():
            out.append(v)
        elif isinstance(v, list):
            out.extend(x for x in v if isinstance(x, str) and len(x.strip()) > 10)
        elif isinstance(v, dict):
            out.extend(x for x in v.values() if isinstance(x, str) and len(x.strip()) > 10)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=",".join(DEFAULT_TASKS))
    args = ap.parse_args()

    from lm_eval.tasks import TaskManager

    tm = TaskManager()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]

    grand_total = 0
    for name in tasks:
        try:
            loaded = tm.load_task_or_group([name])
        except Exception as e:
            print(f"  {name:<28} FALHA: {str(e)[:70]}")
            continue

        rows: list[dict] = []
        # load_task_or_group devolve dict aninhado (grupo -> subtasks)
        stack = list(loaded.values())
        while stack:
            obj = stack.pop()
            if isinstance(obj, dict):
                stack.extend(obj.values())
                continue
            for split_getter in ("test_docs", "validation_docs"):
                try:
                    has = getattr(obj, f"has_{split_getter.split('_')[0]}_docs")()
                except Exception:
                    continue
                if not has:
                    continue
                try:
                    docs = list(getattr(obj, split_getter)())
                except Exception:
                    continue
                for d in docs:
                    for t in extract_texts(d):
                        rows.append({"text": t})
                break  # test tem prioridade sobre validation

        if not rows:
            print(f"  {name:<28} sem docs extraidos")
            continue

        out = OUT_DIR / f"{name}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        grand_total += len(rows)
        print(f"  {name:<28} {len(rows):>7} trechos -> {out.name}")

    print(f"\ntotal: {grand_total} trechos de teste em {OUT_DIR}")
    print('Proximo: python data/04_decontaminate.py --benchmarks "eval/benchmarks/*.jsonl"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
