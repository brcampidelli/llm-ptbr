"""Comparar duas rodadas de avaliação (ex.: baseline vs. modelo treinado).

Existe para impedir auto-engano: com amostras pequenas, quase toda diferença
"parece" ganho. Este script marca explicitamente o que está dentro do ruído.

Erro-padrão de uma proporção: sqrt(p*(1-p)/n). Para a diferença entre duas
medições independentes: sqrt(se_a² + se_b²). Só chamamos de sinal o que passa
de ~2 erros-padrão (≈95%).

Uso:
    python eval/compare.py                                  # 2 mais recentes
    python eval/compare.py --base eval/results/baseline-quick_*.json \
                           --new  eval/results/sft-v1_*.json
"""

from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"

PREFERRED = ("acc_norm,none", "acc,none")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pick_metric(metrics: dict) -> tuple[str, float] | None:
    for m in PREFERRED:
        if m in metrics:
            return m, metrics[m]
    for k, v in metrics.items():
        if isinstance(v, (int, float)) and k != "sample_len":
            return k, v
    return None


def stderr(p: float, n: int) -> float:
    p = min(max(p, 0.0), 1.0)
    return math.sqrt(p * (1 - p) / n) if n > 0 else float("inf")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="glob do JSON do baseline")
    ap.add_argument("--new", default=None, help="glob do JSON da nova rodada")
    args = ap.parse_args()

    def resolve(pattern: str | None, fallback_idx: int) -> Path:
        if pattern:
            hits = sorted(glob.glob(pattern))
            if not hits:
                raise SystemExit(f"nenhum arquivo casa com {pattern}")
            return Path(hits[-1])
        allr = sorted(RESULTS.glob("*.json"))
        if len(allr) < 2:
            raise SystemExit("preciso de pelo menos 2 rodadas em eval/results/")
        return allr[fallback_idx]

    base_p = resolve(args.base, -2)
    new_p = resolve(args.new, -1)
    base, new = load(base_p), load(new_p)

    print(f"BASE : {base_p.name}  ({base.get('model')}, peft={base.get('peft')})")
    print(f"NOVO : {new_p.name}  ({new.get('model')}, peft={new.get('peft')})")

    n_base = base.get("limit") or 0
    n_new = new.get("limit") or 0
    if n_base != n_new:
        print(f"\n⚠️  limits diferentes ({n_base} vs {n_new}) — comparação não é justa.")
    n = min(n_base or 1000, n_new or 1000)

    print(f"\n{'TASK':<26} {'MÉTRICA':<16} {'BASE':>8} {'NOVO':>8} {'DELTA':>8}   VEREDITO")
    print("-" * 86)

    wins = losses = noise = 0
    for task in sorted(set(base.get("results", {})) & set(new.get("results", {}))):
        mb, mn = pick_metric(base["results"][task]), pick_metric(new["results"][task])
        if not mb or not mn or mb[0] != mn[0]:
            continue
        metric, vb = mb
        vn = mn[1]
        delta = vn - vb
        thresh = 2 * math.sqrt(stderr(vb, n) ** 2 + stderr(vn, n) ** 2)

        if abs(delta) < thresh:
            verdict, sym = "ruído (não conclusivo)", "="
            noise += 1
        elif delta > 0:
            verdict, sym = "GANHO significativo", "+"
            wins += 1
        else:
            verdict, sym = "REGRESSÃO significativa", "-"
            losses += 1

        print(f"{task:<26} {metric:<16} {vb:>8.4f} {vn:>8.4f} {delta:>+8.4f} {sym} {verdict}")

    print("-" * 86)
    print(f"ganhos: {wins} | regressões: {losses} | dentro do ruído: {noise}")
    print(f"\nlimiar de significância usado: ~2 erros-padrão com n={n} por task.")
    if noise and not wins and not losses:
        print("\nNenhuma diferença conclusiva. Com n pequeno isso é o resultado ESPERADO —")
        print("aumente --limit (ou rode --suite core --limit 0) antes de concluir qualquer coisa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
