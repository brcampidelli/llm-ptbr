"""Seleção de checkpoint por validação — o "holdout com ground-truth" acionável.

Motivo (docs de tuning do Google): NÃO treinar às cegas e pegar o último checkpoint.
Avaliar CADA checkpoint salvo num holdout com ground-truth e escolher o melhor.
Aqui o "ground-truth" são os benchmarks PT-BR do lm-eval (ENEM/BLUEX/ASSIN...),
que têm respostas de referência — mais honesto que um holdout destilado (mesma
distribuição do treino).

Como funciona: para cada `checkpoint-*` no diretório do run (+ o adapter final),
roda `eval/run_baseline.py --peft <ckpt>` na suíte quick, lê o JSON de resultado,
computa um score composto (média das métricas primárias) e ranqueia.

Uso:
    python eval/select_checkpoint.py --run-dir models/qwen3.5-4b-ptbr-sft
    python eval/select_checkpoint.py --run-dir /content/drive/MyDrive/qwen35-4b-ptbr-sft --limit 200
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"

# Métrica primária por task (a que conta no score composto).
PRIMARY = {
    "arc_pt": "acc_norm,none",
    "hellaswag_pt": "acc_norm,none",
    "belebele_por_Latn": "acc_norm,none",
    "truthfulqa_pt_mc2": "acc,none",
    "xwinograd_pt": "acc,none",
    "assin_entailment": "acc,none",
    "assin_paraphrase": "acc,none",
    "mmmlu_pt_br": "acc,none",
}


def checkpoint_step(path: Path) -> int:
    m = re.search(r"checkpoint-(\d+)", path.name)
    return int(m.group(1)) if m else 10**9  # adapter final ordena por ultimo


def composite_score(result_json: Path) -> tuple[float, dict]:
    data = json.loads(result_json.read_text(encoding="utf-8"))
    res = data.get("results", {})
    per_task = {}
    for task, metrics in res.items():
        key = PRIMARY.get(task)
        if key and key in metrics:
            per_task[task] = metrics[key]
    score = sum(per_task.values()) / len(per_task) if per_task else 0.0
    return score, per_task


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, required=True,
                    help="diretorio de saida do treino (contem checkpoint-*/ e o adapter final)")
    ap.add_argument("--model", default="Qwen/Qwen3.5-4B", help="modelo base")
    ap.add_argument("--suite", default="quick")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--include-final", action="store_true", default=True,
                    help="tambem avalia o adapter final (a propria run-dir)")
    args = ap.parse_args()

    if not args.run_dir.exists():
        print(f"ERRO: {args.run_dir} nao existe.", file=sys.stderr)
        return 1

    # Coleta candidatos: checkpoint-*/ + o adapter final (run-dir raiz).
    candidates = sorted(
        (Path(p) for p in glob.glob(str(args.run_dir / "checkpoint-*")) if Path(p).is_dir()),
        key=checkpoint_step,
    )
    if args.include_final and (args.run_dir / "adapter_model.safetensors").exists():
        candidates.append(args.run_dir)

    if not candidates:
        print(f"Nenhum checkpoint em {args.run_dir}. O treino salvou algo? (--save-steps)",
              file=sys.stderr)
        return 1

    print(f"candidatos ({len(candidates)}):")
    for c in candidates:
        print(f"  - {c.name}")
    print()

    scored: list[tuple[str, float, dict, Path]] = []
    for ckpt in candidates:
        tag = f"sel-{ckpt.name}"
        print(f"=== avaliando {ckpt.name} ===")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "eval" / "run_baseline.py"),
             "--model", args.model, "--peft", str(ckpt),
             "--suite", args.suite, "--limit", str(args.limit), "--tag", tag],
            cwd=str(ROOT),
        )
        if proc.returncode != 0:
            print(f"  FALHA ao avaliar {ckpt.name} (rc={proc.returncode}) — pulando", file=sys.stderr)
            continue
        # pega o JSON mais recente com esse tag
        hits = sorted(RESULTS.glob(f"{tag}_*.json"))
        if not hits:
            print(f"  sem resultado para {ckpt.name}", file=sys.stderr)
            continue
        score, per_task = composite_score(hits[-1])
        scored.append((ckpt.name, score, per_task, ckpt))
        print(f"  score composto: {score:.4f}\n")

    if not scored:
        print("Nenhum checkpoint avaliado com sucesso.", file=sys.stderr)
        return 1

    scored.sort(key=lambda x: -x[1])
    print("\n" + "=" * 60)
    print(f"{'CHECKPOINT':<24} {'SCORE':>8}")
    print("-" * 60)
    for name, score, _, _ in scored:
        print(f"{name:<24} {score:>8.4f}")
    print("=" * 60)
    best = scored[0]
    print(f"\n🏆 MELHOR: {best[0]}  (score {best[1]:.4f})")
    print(f"   caminho: {best[3]}")
    print("   por task:", {k: round(v, 3) for k, v in best[2].items()})
    print("\nUse ESTE checkpoint para release/DPO, nao necessariamente o ultimo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
