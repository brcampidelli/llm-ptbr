"""Compara braços nos MESMOS itens — teste pareado (McNemar), não intervalos soltos.

🔴 POR QUE PAREADO. Com n=85 o intervalo de Wilson de cada braço é ±10 pp, e dois braços que
diferem 5 pp têm intervalos que se sobrepõem quase inteiros. Concluir "não há diferença" dali
seria errado: os intervalos medem incerteza sobre a TAXA ABSOLUTA, e a pergunta do gate é
sobre a DIFERENÇA entre dois modelos avaliados nos MESMOS itens.

A variância da diferença pareada é muito menor, porque a maioria dos itens concorda entre os
braços e se cancela. Só os DISCORDANTES carregam informação — é exatamente isso que McNemar
conta. É a mesma lição do §2g do projeto: quando a intervenção pode ser aplicada aos mesmos
itens, o teste pareado é o que separa efeito de instrumento.

⚠️ E isto só vale porque a avaliação é GREEDY, logo determinística: as rodadas do E5 deram
55, 55, 55 e depois 56, 56 — reprodutíveis ao caso. Sob amostragem (pass@k) o ruído entre
rodadas idênticas é 2,3 pp e nada disso se aplica.

Uso:
    python comeia/eval/comparar_pareado.py --base .../casos_A.jsonl --braco .../casos_B.jsonl
    python comeia/eval/comparar_pareado.py --base A.jsonl --braco B.jsonl C.jsonl D.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def carregar(p: Path) -> dict[int, bool]:
    fora = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r["tipo"] == "tool":
            fora[r["i"]] = bool(r["exec_ok"])
    return fora


def over_calls(p: Path) -> dict[int, bool]:
    fora = {}
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if r["tipo"] == "text":
            fora[r["i"]] = bool(r.get("over_call"))
    return fora


def mcnemar(b: int, c: int) -> float:
    """p bicaudal exato (binomial), que é o certo para n discordante pequeno.

    A aproximação qui-quadrado precisa de b+c >= 25; aqui b+c costuma ser < 15, e usá-la
    daria um p otimista. Com poucos discordantes o exato é barato e correto.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cauda = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * cauda)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True, help="o CONTROLE (SFT+RS, nao SFT puro)")
    ap.add_argument("--braco", type=Path, nargs="+", required=True)
    ap.add_argument("--limiar", type=float, default=5.0,
                    help="folga absoluta em pp para ADOTAR — declarada ANTES (default 5)")
    a = ap.parse_args()

    base = carregar(a.base)
    base_over = over_calls(a.base)
    n = len(base)
    ok_b = sum(base.values())
    print("=" * 78)
    print(f"COMPARACAO PAREADA — {n} itens com ferramenta · controle {a.base.stem}")
    print(f"  controle: {ok_b}/{n} = {ok_b/n:.1%}   over-calling {sum(base_over.values())}/{len(base_over)}")
    print(f"  criterio de adocao declarado ANTES: folga >= {a.limiar:.0f} pp")
    print("=" * 78)

    for pb in a.braco:
        br = carregar(pb)
        comuns = sorted(set(base) & set(br))
        if len(comuns) != n:
            print(f"\n⚠️ {pb.stem}: so' {len(comuns)}/{n} itens em comum — comparando os comuns")
        ok_r = sum(br[i] for i in comuns)
        # b = o braco acertou e o controle errou; c = o inverso
        b = sum(1 for i in comuns if br[i] and not base[i])
        c = sum(1 for i in comuns if base[i] and not br[i])
        delta = (ok_r - sum(base[i] for i in comuns)) / len(comuns) * 100
        p = mcnemar(b, c)
        ov = over_calls(pb)
        d_ov = (sum(ov.values()) - sum(base_over.values()))

        print()
        print(f"### {pb.stem}")
        print(f"  acerto            {ok_r}/{len(comuns)} = {ok_r/len(comuns):6.1%}   "
              f"folga {delta:+5.1f} pp")
        print(f"  discordantes      +{b} (so' o braco) / -{c} (so' o controle)   "
              f"McNemar p={p:.3f}")
        print(f"  over-calling      {sum(ov.values())}/{len(ov)}  ({d_ov:+d} vs controle)")
        # ⚠️ MEDIR OS DOIS LADOS: subir execucao chamando mais nao e' ganho liquido.
        if delta >= a.limiar and d_ov > 2:
            print("  ⚠️ subiu a execucao MAS o over-calling tambem — ganho pode ser so' "
                  "chamar mais")
        veredito = ("ADOTAR" if delta >= a.limiar else "NAO ADOTAR")
        print(f"  ⇒ {veredito}  (criterio: folga >= {a.limiar:.0f} pp)")
        if delta > 0 and delta < a.limiar:
            print("     efeito positivo abaixo do limiar. O plano diz: o resultado e' 'nao")
            print("     adotar', NAO 'repetir com outro beta'.")
        if p > 0.05 and abs(delta) > 0:
            print(f"     ⚠️ com {b}+{c}={b+c} discordantes, p={p:.3f}: a diferenca nao se")
            print("     distingue de acaso. Com n=85 isso e' limitacao do HOLDOUT, nao do metodo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
