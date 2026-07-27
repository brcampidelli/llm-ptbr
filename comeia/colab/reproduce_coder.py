"""Reproduz a abelha CODER inteira em ~17 min — um comando só.

Existe porque o adapter da coder vive em /content no Colab (efêmero: morre com o
runtime). Em vez de depender de um artefato que some, o projeto trata o TREINO
como o artefato: 4 etapas determinísticas a partir do que já está versionado.

    python colab/reproduce_coder.py --out /content/qwen35-4b-coder

Etapas (pula as que já estiverem prontas — é retomável):
  1. filtro "o base erra"  -> coder_tasks_hard.jsonl   (~35 min na 1ª vez, GPU)
  2. conversão p/ pares    -> coder_pairs.jsonl         (segundos)
  3. splits held-out       -> sft_coder.jsonl           (segundos)
  4. treino QLoRA          -> o adapter                 (~17 min, GPU)

⚠️ CONFIG VENCEDORA (medida em held-out limpo, 2026-07-25): 2 épocas, 100%
difícil. Deu 1,7% -> 41,7% nas difíceis (24× o base) e 82,5% nas fáceis.
Alternativas medidas e PIORES: 1 época (28,3%/87,5%) e mistura de 30% de fáceis
(36,7%/77,5% — dominada). Não mexer nos defaults sem re-medir as duas pontas.

⚠️ --prompt-completion é OBRIGATÓRIO: sem ele o TRL calcula a loss em TODOS os
tokens, e com system prompt grande o sinal de treino vira lixo (bug real medido:
93,8% da loss caía em prompt repetido).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"


def sh(cmd: list[str], desc: str) -> None:
    print(f"\n{'='*66}\n▶ {desc}\n{'='*66}", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        print(f"FALHOU: {desc}", file=sys.stderr)
        raise SystemExit(r.returncode)
    print(f"✔ {desc} ({time.time()-t0:.0f}s)", flush=True)


def n_linhas(p: Path) -> int:
    return sum(1 for l in p.open(encoding="utf-8") if l.strip()) if p.exists() else 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/content/qwen35-4b-coder",
                    help="onde salvar o adapter. Aponte para o Drive se quiser persistir.")
    ap.add_argument("--epochs", type=float, default=2.0, help="2 = config vencedora medida")
    ap.add_argument("--holdout", type=int, default=30)
    ap.add_argument("--force", action="store_true", help="refaz mesmo o que ja existe")
    args = ap.parse_args()

    hard = RAW / "coder_tasks_hard.jsonl"
    pares = PROC / "coder_pairs.jsonl"
    sft = PROC / "sft_coder.jsonl"

    # ── 1. filtro "o base erra" (a etapa cara; so roda se faltar) ──
    if args.force or n_linhas(hard) < 50:
        sh([sys.executable, "data/09_filter_hard_tasks.py", "--batch-size", "8"],
           "1/4 filtro 'o base erra' (~35 min — so na 1a vez)")
    else:
        print(f"✔ 1/4 filtro: {n_linhas(hard)} tarefas dificeis ja existem (pulando)")

    # ── 2. conversão para {instruction, response} ──
    # O alvo vai em bloco ```python para casar com o SYSTEM do eval_coder.
    if args.force or not pares.exists():
        rows = [json.loads(l) for l in hard.open(encoding="utf-8") if l.strip()]
        PROC.mkdir(parents=True, exist_ok=True)
        with pares.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({
                    "instruction": r["prompt"],
                    "response": "```python\n" + r["solution"] + "\n```",
                }, ensure_ascii=False) + "\n")
        print(f"✔ 2/4 conversao: {len(rows)} pares -> {pares.name}")
    else:
        print(f"✔ 2/4 conversao: {n_linhas(pares)} pares ja existem (pulando)")

    # ── 3. splits (⚠️ --prompt-completion obrigatorio) ──
    sh([sys.executable, "data/05_build_splits.py",
        "--in", str(pares), "--out", str(sft),
        "--eval-out", str(PROC / "sft_coder.eval.jsonl"),
        "--prompt-completion", "--holdout", str(args.holdout)],
       "3/4 splits held-out (loss mascarada no prompt)")

    # ── 4. treino ──
    sh([sys.executable, "train/sft_qlora.py", "--data", str(sft), "--out", args.out,
        "--epochs", str(args.epochs), "--max-seq-len", "1536", "--save-steps", "40"],
       f"4/4 treino QLoRA ({args.epochs:g} epoca(s)) -> {args.out}")

    print(f"\n{'='*66}")
    print(f"✅ abelha coder pronta em {args.out}")
    print("Registre no orchestrator/bees.json (campo adapter_path da abelha 'coder').")
    print("Avaliar:")
    print(f"  python eval/eval_coder.py --peft {args.out} "
          "--tasks data/processed/coder_hard_test.jsonl --limit 0   # dificeis")
    print(f"  python eval/eval_coder.py --peft {args.out} "
          "--tasks data/processed/coder_easy_test.jsonl --limit 0   # nao-regressao")
    print("Referencia medida: 41,7% dificeis / 82,5% faceis (base: 1,7% / 100%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
