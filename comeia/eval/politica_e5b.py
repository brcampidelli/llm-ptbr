"""E5b — quanto rende retentar, medido em politicas REALIZAVEIS em runtime.

🔴 pass@k NAO e' entregavel. Ele escolhe a melhor das k amostras olhando a REFERENCIA, e em
producao nao ha' referencia. O plano do E5b supunha que "o executor deterministico e' o
verificador forte" — este script mede se e' verdade.

Politicas comparadas, todas decidiveis sem gabarito:
  A. greedy uma vez                          (o que ja' se faz)
  B. amostrar k, servir a 1a que EXECUTA     (o laco do plano)
  C. greedy; se nao executar, cair para B    (hibrido — >= A por construcao)

Uso:
    python comeia/eval/politica_e5b.py --greedy .../casos_TAG1.jsonl --amostrado .../casos_TAG2.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def carregar(p: Path) -> dict[int, dict]:
    fora = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r["tipo"] == "tool":
            fora[r["i"]] = r
    return fora


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--greedy", type=Path, required=True)
    ap.add_argument("--amostrado", type=Path, required=True)
    a = ap.parse_args()

    g, s4 = carregar(a.greedy), carregar(a.amostrado)
    comuns = sorted(set(g) & set(s4))
    if len(comuns) != len(g) or len(comuns) != len(s4):
        print(f"⚠️ despejos nao alinham: greedy {len(g)}, amostrado {len(s4)}, "
              f"comuns {len(comuns)} — comparando so' os comuns")
    n = len(comuns)

    a_ok = sum(1 for i in comuns if g[i]["exec_ok"])
    b_ok = sum(1 for i in comuns if s4[i].get("servida_certa"))
    c_ok = 0
    disparou = resgatou = estragou = 0
    for i in comuns:
        if g[i].get("executou"):
            c_ok += 1 if g[i]["exec_ok"] else 0
        else:
            disparou += 1
            certo = bool(s4[i].get("servida_certa"))
            c_ok += 1 if certo else 0
            if certo:
                resgatou += 1
    # C nunca pode piorar A, mas conferir e' barato e o projeto ja' pagou por nao conferir
    for i in comuns:
        if g[i].get("executou") and not g[i]["exec_ok"] and s4[i].get("servida_certa"):
            estragou += 1

    print("=" * 74)
    print(f"E5b — POLITICAS REALIZAVEIS, {n} casos com ferramenta")
    print("=" * 74)
    for rot, ok in [("A. greedy uma vez            ", a_ok),
                    ("B. amostrar k, 1a executavel ", b_ok),
                    ("C. greedy, cair para B se nao executar", c_ok)]:
        lo, hi = wilson(ok, n)
        print(f"  {rot:40} {ok}/{n} = {ok/n:6.1%}  [{lo:.1%}–{hi:.1%}]")
    print()
    print(f"  C - A = {(c_ok - a_ok) / n * 100:+.1f} pp   ({c_ok - a_ok:+d} casos)")
    print(f"  B - A = {(b_ok - a_ok) / n * 100:+.1f} pp   ({b_ok - a_ok:+d} casos)")
    print()
    print(f"  o fallback de C disparou em {disparou}/{n} casos "
          f"({disparou/n:.1%}) — greedy nao produziu chamada executavel")
    print(f"  e resgatou {resgatou} deles")
    print(f"  casos em que greedy executou ERRADO e uma amostra estava certa: {estragou}")
    print("    (C nao os pega: sem referencia, 'executou' e' tudo que o harness sabe ver.")
    print("     E' exatamente aqui que mora a folga do pass@k que NAO e' colhivel.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
