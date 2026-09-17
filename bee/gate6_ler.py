"""Consolida o gate #6 (repeticao de idioma escasso em denso, Bee-50M/64k) a partir dos LOGS — por codigo (§2z).

Le <saidas>/<braco>.log e extrai a serie de VALIDACAO (holdout limpo de jpn, nats/token) e a final.
Bracos: jpn_unico_s42/s43 · jpn_rep8_s42/s43 · jpn_unico_mix_s42 · jpn_rep8_mix_s42 · jpn_rep3_s42 (extra).

Criterio declarado ANTES de ler:
  PISO = max(|unico s42 − s43|, |rep8 s42 − s43|)  — duas sementes ALERTAM (§2x); e' o que ha'.
  (1) penalidade de repeticao P_sozinho = media(rep8) − media(unico)        [esperado pelo artigo: pequeno e > 0]
  (2) penalidade na mistura     P_mix     = rep8_mix − unico_mix             [1 semente cada]
      "mistura protege" se P_mix < P_sozinho por mais que o PISO.
  (3) efeito do PT no jpn       T = unico_mix − media(unico)                 [<0 = PT ajuda; >0 = PT rouba capacidade]
  Leitura: um delta so' conta se |delta| > PISO. Abaixo disso e' "dentro do ruido", e o veredito diz isso.
Imprime tambem a curva (val a cada 500 passos) para ver SE o dano da repeticao aparece so' tarde
(o artigo: overfit cresce com as epocas — no ladrilho embaralhado isso vira "cresce com os passos").
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RX_VAL = re.compile(r"VALIDA[ÇC][ÃA]O passo (\d+): loss ([0-9.]+)")
RX_FIM = re.compile(r"validação final: loss ([0-9.]+)")
RX_TPS = re.compile(r"([0-9.]+)k tok/s")


def ler(p: Path):
    t = p.read_text(encoding="utf-8", errors="replace")
    serie = [(int(a), float(b)) for a, b in RX_VAL.findall(t)]
    fim = RX_FIM.search(t)
    tps = sorted(float(x) for x in RX_TPS.findall(t)[20:]) or [0.0]
    return {"serie": serie, "final": float(fim.group(1)) if fim else None, "tps": tps[len(tps) // 2], "passos": serie[-1][0] if serie else 0}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saidas", required=True)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    S = Path(a.saidas)
    B = {p.stem: ler(p) for p in sorted(S.glob("jpn_*.log"))}
    if not B:
        print(f"nenhum jpn_*.log em {S}"); return 1
    print(f"{'braco':20s} {'passos':>7s} {'val final':>10s} {'tok/s':>7s}")
    for n, b in B.items():
        print(f"{n:20s} {b['passos']:7d} {b['final'] if b['final'] is not None else float('nan'):10.4f} {b['tps']:6.0f}k")

    def fin(n):
        return B[n]["final"] if n in B and B[n]["final"] is not None else None
    u42, u43, r42, r43, um, rm = (fin(n) for n in ("jpn_unico_s42", "jpn_unico_s43", "jpn_rep8_s42", "jpn_rep8_s43", "jpn_unico_mix_s42", "jpn_rep8_mix_s42"))
    out = {"bracos": {n: {"final": b["final"], "passos": b["passos"], "tps": b["tps"]} for n, b in B.items()}}
    pisos = [abs(x - y) for x, y in ((u42, u43), (r42, r43)) if None not in (x, y)]
    piso = max(pisos) if pisos else None
    if piso is not None:
        out["piso"] = piso
        print(f"\nPISO DE RUIDO (max |s42 − s43| em unico e rep8): {piso:.4f} nats  ⚠️ duas sementes: alerta, nao decisao")

    def media(*xs):
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None
    mu, mr = media(u42, u43), media(r42, r43)
    print("\nTABELA 2x2 (val loss jpn, nats/token; unico/rep8 = media das sementes disponiveis):")
    print(f"  {'':12s} {'sozinho':>10s} {'+ PT':>10s}")
    print(f"  {'unico':12s} {mu if mu is not None else float('nan'):10.4f} {um if um is not None else float('nan'):10.4f}")
    print(f"  {'rep8':12s} {mr if mr is not None else float('nan'):10.4f} {rm if rm is not None else float('nan'):10.4f}")

    def leia(nome, d):
        if d is None or piso is None:
            return f"{nome}: (faltam bracos)"
        tag = "ALEM DO PISO" if abs(d) > piso else "dentro do ruido"
        return f"{nome} {d:+.4f} nats -> {tag}"
    P_so = (mr - mu) if None not in (mr, mu) else None
    P_mix = (rm - um) if None not in (rm, um) else None
    T = (um - mu) if None not in (um, mu) else None
    print("\nPERGUNTAS (criterio no docstring):")
    print("  (1) " + leia("penalidade de repeticao, sozinho (rep8 − unico)", P_so))
    print("  (2) " + leia("penalidade de repeticao, na mistura (rep8_mix − unico_mix)", P_mix))
    if None not in (P_so, P_mix, piso):
        prot = P_so - P_mix
        print(f"      mistura protege? P_sozinho − P_mix = {prot:+.4f} -> " + ("SIM, alem do piso" if prot > piso else ("NAO (piora)" if prot < -piso else "indistinguivel")))
        out["protecao"] = prot
    print("  (3) " + leia("efeito do PT no jpn (unico_mix − unico)", T))
    out.update({"P_sozinho": P_so, "P_mix": P_mix, "T_pt": T})
    r3 = fin("jpn_rep3_s42")
    if r3 is not None and mu is not None:
        P3 = r3 - mu
        out["P_rep3"] = P3
        print("  (4) " + leia("penalidade de repeticao em R=3, sozinho (rep3 − unico)", P3)
              + (f"   [R=8: {P_so:+.4f}]  -> penalidade por R: 1:0 · 3:{P3:+.3f} · 8:{P_so:+.3f}" if P_so is not None else ""))

    print("\nCURVA (val jpn a cada 500 passos — a repeticao dói cedo ou tarde?):")
    for n in ("jpn_unico_s42", "jpn_rep3_s42", "jpn_rep8_s42", "jpn_unico_mix_s42", "jpn_rep8_mix_s42"):
        if n in B and B[n]["serie"]:
            s = B[n]["serie"]; k = max(1, len(s) // 8)
            print(f"  {n:20s} " + " ".join(f"{p//1000}k:{l:.3f}" for p, l in s[::k]) + f"  fim:{s[-1][1]:.3f}")

    print("\n⚠️ RESSALVAS: 50m/64k (67,3M params) · 1 idioma (jpn, escrita distante do PT) · R=8 so' · mistura 50/50 e nao 7% ·"
          "\n   metrica = nats/token no holdout jpn (bpb = x const., mesmo tokenizador em todos) · 1-2 sementes."
          "\n   Empate NAO refuta o artigo (regime diferente); penalidade grande em R=8 e' o que o proximo run precisa saber.")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"salvo em {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
