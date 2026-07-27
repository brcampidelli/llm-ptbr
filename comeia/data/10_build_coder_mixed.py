"""Fase 2 (dados) — splits HONESTOS da abelha coder: held-out real + mistura de fáceis.

⚠️ CORRIGE UM BUG METODOLÓGICO REAL (2026-07-25). A avaliação anterior usou
`eval_coder.py --limit 60`, que pega as 60 PRIMEIRAS tarefas do arquivo bruto. Mas
o 05_build_splits EMBARALHA antes de separar o holdout — então ~52 dessas 60
estavam no TREINO. O "+45 pp" foi medido majoritariamente sobre tarefas treinadas:
parte era memorização, não generalização. Este script separa um conjunto de teste
que NUNCA entra no treino, com os mesmos ids garantidos.

Faz três coisas, com semente fixa (reprodutível):
  1. Separa as DIFÍCEIS em treino vs TESTE held-out (o teste nunca é treinado).
  2. Separa as FÁCEIS em âncora-de-treino vs TESTE held-out.
  3. Monta o treino misturando difíceis-treino + ~30% de fáceis-âncora.
     Hipótese: dataset 100% difícil empurra o modelo para longe do que já
     funcionava (regressão de 100%→90% nas fáceis). As fáceis ancoram o
     comportamento antigo.

Formato de saída = prompt/completion (o TRL mascara a loss do prompt — lição do
bug de mascaramento). Alvo = solução dentro de bloco ```python (casa com o SYSTEM
do eval_coder).

Uso:
    python data/10_build_coder_mixed.py --easy-frac 0.30 --n-test-hard 60 --n-test-easy 40

Saídas em data/processed/:
  sft_coder_mixed.jsonl        treino (difíceis-treino + fáceis-âncora), prompt/completion
  coder_hard_test.jsonl        DIFÍCEIS held-out — nunca treinadas (a régua honesta)
  coder_easy_test.jsonl        FÁCEIS held-out — teste de não-regressão
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from common import read_jsonl  # noqa: E402

HARD = ROOT / "data" / "raw" / "coder_tasks_hard.jsonl"
EASY = ROOT / "data" / "raw" / "coder_tasks_easy.jsonl"
PROC = ROOT / "data" / "processed"


def to_pair(task: dict) -> dict:
    """{prompt, completion} para o TRL. Alvo = solução em bloco python."""
    return {
        "prompt": [{"role": "user", "content": task["prompt"]}],
        "completion": [{"role": "assistant",
                        "content": "```python\n" + task["solution"] + "\n```"}],
        "name": task["name"],
    }


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--easy-frac", type=float, default=0.30,
                    help="fração de fáceis-âncora sobre o total de treino")
    ap.add_argument("--n-test-hard", type=int, default=60, help="difíceis held-out")
    ap.add_argument("--n-test-easy", type=int, default=40, help="fáceis held-out")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    hard = [t for t in read_jsonl(HARD) if t.get("prompt") and t.get("solution")]
    easy = [t for t in read_jsonl(EASY) if t.get("prompt") and t.get("solution")]
    rng = random.Random(args.seed)
    rng.shuffle(hard)
    rng.shuffle(easy)

    if len(hard) <= args.n_test_hard + 20:
        print(f"ERRO: só {len(hard)} difíceis — poucas para separar {args.n_test_hard} de teste.",
              file=sys.stderr)
        return 1

    # 1) difíceis: teste held-out (NUNCA treinado) vs treino
    hard_test = hard[: args.n_test_hard]
    hard_train = hard[args.n_test_hard:]
    # 2) fáceis: teste held-out vs pool de âncora
    easy_test = easy[: args.n_test_easy]
    easy_pool = easy[args.n_test_easy:]
    # 3) quantas fáceis-âncora para que sejam ~easy_frac do treino total
    #    n_easy / (n_hard_train + n_easy) = frac  =>  n_easy = frac*n_hard_train/(1-frac)
    n_easy_anchor = min(len(easy_pool),
                        round(args.easy_frac * len(hard_train) / (1 - args.easy_frac)))
    easy_anchor = easy_pool[:n_easy_anchor]

    train = [to_pair(t) for t in hard_train] + [to_pair(t) for t in easy_anchor]
    rng.shuffle(train)

    PROC.mkdir(parents=True, exist_ok=True)
    (PROC / "sft_coder_mixed.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in train) + "\n", encoding="utf-8")
    # os testes ficam no formato bruto {name, prompt, tests, solution} p/ o eval_coder
    (PROC / "coder_hard_test.jsonl").write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in hard_test) + "\n", encoding="utf-8")
    (PROC / "coder_easy_test.jsonl").write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in easy_test) + "\n", encoding="utf-8")

    frac_real = n_easy_anchor / len(train)
    print(f"difíceis: {len(hard)}  -> treino {len(hard_train)} | TESTE held-out {len(hard_test)}")
    print(f"fáceis  : {len(easy)}  -> âncora {n_easy_anchor} | TESTE held-out {len(easy_test)}")
    print(f"treino  : {len(train)} exemplos ({frac_real:.0%} fáceis-âncora) -> sft_coder_mixed.jsonl")
    print(f"⚠️ os TESTES ({len(hard_test)} difíceis + {len(easy_test)} fáceis) NUNCA entram no treino.")
    print("\nProximo:")
    print("  train/sft_qlora.py --data data/processed/sft_coder_mixed.jsonl --out /content/coder-mixed --epochs 2 --save-steps 40")
    print("  eval/eval_coder.py --peft /content/coder-mixed --tasks data/processed/coder_hard_test.jsonl --limit 0 --tag mixed-hard")
    print("  eval/eval_coder.py --peft /content/coder-mixed --tasks data/processed/coder_easy_test.jsonl --limit 0 --tag mixed-easy")
    print("  (e o BASE nos MESMOS testes held-out, para a referencia honesta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
