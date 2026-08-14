"""Diff POR PROBLEMA entre dois checkpoints — o custo que o agregado esconde (T4 do estudo).

⭐ POR QUE ESTE SCRIPT EXISTE
  arXiv:2608.11829 mede que destilacao on-policy (e, por extensao, rejection sampling — a
  familia inteira de auto-melhoria) pode manter o agregado ESTAVEL enquanto o conjunto de
  problemas resolviveis DEGRADA: nos tres setups do paper, a fracao ESQUECIDA superou a
  APRENDIDA em pass@1024. Em Qwen3-1.7B o pass@1024 caiu de 70,0% para 53,3% enquanto o
  pass@1 quase TRIPLICAVA.

  O Bee mediu pass@16 72,9% antes e 71,8% depois da colheita e leu isso como "dentro do
  ruido". Pode ser. Mas o agregado nao distingue "nada mudou" de "perdeu 8 e ganhou 7".
  Esse diff custa ZERO — os dados ja estao em disco.

⚠️ O QUE ESTE SCRIPT NAO FAZ: nao decide sozinho. Ele separa quatro populacoes; quem decide
   e' o tamanho relativa delas, com intervalo de Wilson, porque n=85 e' pequeno.

Uso:
    python comeia/eval/diff_por_problema.py \
        --antes comeia/eval/results/passk_curva_base.json \
        --depois comeia/eval/results/passk_curva_v2.json
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


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", type=Path, required=True)
    ap.add_argument("--depois", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    A = json.loads(a.antes.read_text(encoding="utf-8"))
    B = json.loads(a.depois.read_text(encoding="utf-8"))

    pa = {p["idx"]: p for p in A["por_problema"] if p["tipo"] == "tool"}
    pb = {p["idx"]: p for p in B["por_problema"] if p["tipo"] == "tool"}
    comuns = sorted(set(pa) & set(pb))

    # ⚠️ GUARDA: comparar corridas de holdouts diferentes daria numero sem sentido.
    if len(comuns) != len(pa) or len(comuns) != len(pb):
        print(f"🔴 ABORTA: holdouts diferentes — antes {len(pa)}, depois {len(pb)}, comuns {len(comuns)}",
              file=sys.stderr)
        return 3
    if A["n"] != B["n"]:
        print(f"⚠️  n diferente ({A['n']} vs {B['n']}) — a comparacao de 'resolve' fica enviesada"
              f" para quem amostrou mais. Prosseguindo, mas o numero e' fraco.")

    ganhou, perdeu, sempre, nunca = [], [], [], []
    for i in comuns:
        ca, cb = pa[i]["acertos"] > 0, pb[i]["acertos"] > 0
        (sempre if ca and cb else nunca if not ca and not cb else ganhou if cb else perdeu).append(i)

    n = len(comuns)
    print("=" * 72)
    print(f"DIFF POR PROBLEMA — {n} exemplos tool  (n={A['n']} amostras cada)")
    print(f"  antes : {A['modelo']}")
    print(f"  depois: {B['modelo']}")
    print("=" * 72)
    for rot, g in (("resolvia e resolve", sempre), ("⭐ APRENDEU (so depois)", ganhou),
                   ("🔴 ESQUECEU (so antes)", perdeu), ("nunca resolveu", nunca)):
        lo, hi = wilson(len(g), n)
        print(f"  {rot:<26} {len(g):>4}/{n}  = {len(g)/n:6.1%}   [{lo:.1%}–{hi:.1%}]")

    liquido = len(ganhou) - len(perdeu)
    print("-" * 72)
    print(f"  SALDO LIQUIDO: {liquido:+d} problemas")
    print()
    if len(perdeu) > len(ganhou):
        print("🔴 ESQUECEU MAIS DO QUE APRENDEU — e' exatamente a assimetria que o paper mede, e o")
        print("   agregado a esconde. A proxima colheita deve MISTURAR dado do modelo base.")
    elif len(perdeu) == len(ganhou) and len(perdeu) > 0:
        print("🟡 EMPATE em contagem — o agregado nao se moveu porque houve TROCA, nao estabilidade.")
        print("   Sao problemas diferentes; nao e' o mesmo modelo com ruido.")
    elif len(ganhou) > len(perdeu):
        print("🟢 aprendeu mais do que esqueceu. A colheita nao esta cobrando preco escondido.")
    else:
        print("🟢 nenhuma troca de conjunto — estabilidade real, nao compensacao.")

    # tambem: mudanca de TAXA nos que ja resolviam (o piso subindo, sem trocar o conjunto)
    if sempre:
        d = [pb[i]["taxa"] - pa[i]["taxa"] for i in sempre]
        print(f"\n  entre os que resolvem nos dois: taxa media {sum(d)/len(d)*100:+.1f} pp"
              f"  (subiu em {sum(1 for x in d if x>0)}, caiu em {sum(1 for x in d if x<0)})")
        print("  ⭐ e' aqui que o rejection sampling age: move o PISO sem mudar o conjunto.")

    saida = {
        "antes": A["modelo"], "depois": B["modelo"], "n_amostras": A["n"], "exemplos": n,
        "aprendeu": ganhou, "esqueceu": perdeu, "sempre": len(sempre), "nunca": len(nunca),
        "saldo_liquido": liquido,
    }
    dest = a.out or (a.antes.parent / "diff_por_problema.json")
    dest.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nrelatorio: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
