"""Consolida o gate #1 (Muon x AdamW, Bee-50M) a partir dos logs dos bracos — por codigo, nao a mao.

Le, de cada braco em <saidas>/<nome>.log: a serie de VALIDACAO (passo, loss, ppl) e a validacao
final. Produz:
  - tabela final por braco
  - PISO DE RUIDO = |adamw_s42 - adamw_s43| na validacao final (§2m/§2x: duas sementes ALERTAM;
    aqui e' o que ha, e vai impresso ao lado do efeito)
  - efeito PAREADO por semente: muon_sXX - adamw_sXX
  - eficiencia de token: em que passo o Muon alcanca a loss FINAL do AdamW (o "1,3-1,9x" do artigo
    e' isso: mesma loss com menos tokens). So' se alcancar; senao diz que nao alcancou.
  - sensibilidade a lr: os bracos a 3x, se existirem
Veredito impresso com as ressalvas do desenho (regime de 1x Chinchilla, 50M, PT 32k).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RX_VAL = re.compile(r"VALIDA[ÇC][ÃA]O passo (\d+): loss ([0-9.]+) · perplexidade ([0-9.]+)")
RX_FIM = re.compile(r"validação final: loss ([0-9.]+) · perplexidade ([0-9.]+)")
RX_TPS = re.compile(r"([0-9.]+)k tok/s")


def ler(p: Path):
    t = p.read_text(encoding="utf-8", errors="replace")
    serie = [(int(a), float(b), float(c)) for a, b, c in RX_VAL.findall(t)]
    fim = RX_FIM.search(t)
    tps = [float(x) for x in RX_TPS.findall(t)]
    tps = sorted(tps[20:]) if len(tps) > 40 else sorted(tps)
    return {"serie": serie, "final": (float(fim.group(1)), float(fim.group(2))) if fim else None,
            "tps_mediana": tps[len(tps) // 2] if tps else None, "passos": serie[-1][0] if serie else 0}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--saidas", required=True)
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    S = Path(args.saidas)
    bracos = {p.stem: ler(p) for p in sorted(S.glob("*.log")) if p.stem != "gate"}
    print(f"{'braco':12s} {'passos':>7s} {'val final':>10s} {'ppl':>7s} {'tok/s':>7s}")
    for n, b in bracos.items():
        f = b["final"]
        print(f"{n:12s} {b['passos']:7d} {f[0] if f else float('nan'):10.4f} {f[1] if f else float('nan'):7.1f} "
              f"{(b['tps_mediana'] or 0):6.0f}k")

    def fin(n): return bracos[n]["final"][0] if n in bracos and bracos[n]["final"] else None
    a42, a43, m42, m43 = fin("adamw_s42"), fin("adamw_s43"), fin("muon_s42"), fin("muon_s43")
    out = {"bracos": {n: {"final": b["final"], "passos": b["passos"], "tps": b["tps_mediana"]} for n, b in bracos.items()}}
    if None not in (a42, a43):
        piso = abs(a42 - a43); out["piso_ruido_adamw"] = piso
        print(f"\nPISO DE RUIDO (|adamw s42 - s43|): {piso:.4f} nats  ⚠️ duas sementes: alerta, nao decisao")
    if None not in (a42, m42, a43, m43):
        d42, d43 = m42 - a42, m43 - a43
        out["pareado"] = {"s42": d42, "s43": d43, "media": (d42 + d43) / 2}
        print(f"PAREADO muon - adamw: s42 {d42:+.4f} · s43 {d43:+.4f} · media {(d42+d43)/2:+.4f} nats")
        # eficiencia de token: em que passo o muon cruza a loss FINAL do adamw da mesma semente
        for s, alvo, nome in (("42", a42, "muon_s42"), ("43", a43, "muon_s43")):
            serie = bracos[nome]["serie"]; tot = bracos[nome]["passos"]
            cruz = next((p for p, l, _ in serie if l <= alvo), None)
            if cruz:
                print(f"  eficiencia de token s{s}: muon alcanca a loss final do adamw no passo {cruz}/{tot} = {tot/cruz:.2f}x menos tokens")
                out.setdefault("eficiencia_token", {})[f"s{s}"] = tot / cruz
            else:
                print(f"  eficiencia de token s{s}: muon NAO alcanca a loss final do adamw ({alvo:.4f}) em {tot} passos")
        piso = out.get("piso_ruido_adamw")
        med = (d42 + d43) / 2
        if piso is not None:
            if med < -piso and d42 < 0 and d43 < 0:
                v = "MUON MELHOR nas duas sementes, alem do piso de ruido"
            elif med > piso and d42 > 0 and d43 > 0:
                v = "ADAMW MELHOR nas duas sementes, alem do piso de ruido"
            else:
                v = "EMPATE dentro do piso de ruido (ou sementes discordam)"
            out["veredito"] = v
            print(f"\nVEREDITO: {v}")
    for n in ("adamw_lr3", "muon_lr3"):
        if fin(n) is not None:
            base = fin(n.split("_")[0] + "_s42")
            print(f"sensibilidade a lr — {n}: {fin(n):.4f} (a 3x) contra {base:.4f} (lr base, s42): {fin(n)-base:+.4f}")
    print("\n⚠️ RESSALVAS DO DESENHO: 50M params · 1,06B tokens = 1x Chinchilla (o artigo cobre 1-8x) · PT 32k ·"
          "\n   duas sementes. Um empate aqui NAO refuta o artigo; um ganho aqui NAO garante o mesmo em 1B/64k.")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
