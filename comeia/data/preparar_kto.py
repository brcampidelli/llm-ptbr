"""Monta o conjunto DESPAREADO do KTO a partir da colheita do rejection sampling.

⭐ POR QUE O KTO E' DIFERENTE DOS OUTROS BRACOS. DPO e IPO exigem PAR: o mesmo prompt com uma
resposta boa e uma ruim. Isso restringe o sinal aos prompts `misto` (324). O KTO come rotulo
binario despareado, entao alcanca tambem os `all_right` — prompts em que o modelo acerta
sempre e que, por nao terem contraexemplo, nao formam par nenhum.

    DPO / IPO   324 prompts  (so' misto)
    KTO         657 prompts  (misto + all_right)

⚠️ E NAO os 866. Os 209 `all_wrong` ficam de fora porque o rejection sampling nao guarda as
amostras erradas de um prompt sem nenhuma certa — nao havia o que colher. Corrigir isso
exigiria outra passada de geracao.

🔴 E ISSO QUEBRA "quatro bracos, mesmo dado". Se o KTO ganhar com 657 prompts contra 324, a
diferenca mede VOLUME, nao funcao de perda. Por isso este script emite DOIS conjuntos:

    --modo restrito  -> so' os prompts que tambem viraram par. Comparavel com DPO/IPO.
    --modo completo  -> tudo que o KTO alcanca. Responde "vale a pena usar KTO".

Sao perguntas diferentes e os resultados vao reportados separados.

Uso:
    python comeia/data/preparar_kto.py --reforco .../e6_reforco_v2.jsonl \\
        --pares .../e6_pares_v2.jsonl --out .../e6_kto_MODO.jsonl --modo restrito
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def chave(msgs) -> str:
    return json.dumps(msgs, sort_keys=True, ensure_ascii=False)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--reforco", type=Path, required=True)
    ap.add_argument("--pares", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--modo", choices=["restrito", "completo"], required=True)
    a = ap.parse_args()

    pares = [json.loads(l) for l in a.pares.read_text(encoding="utf-8").splitlines() if l.strip()]
    reforco = [json.loads(l) for l in a.reforco.read_text(encoding="utf-8").splitlines()
               if l.strip()]

    prompts_com_par = {chave(r["prompt"]) for r in pares}
    linhas, stats = [], Counter()

    # negativos: sempre dos pares (e' o unico lugar onde ha' amostra errada guardada)
    for r in pares:
        linhas.append({"prompt": r["prompt"], "completion": r["rejected"], "label": False})
        stats[f"neg_{r.get('tipo_negativo', '?')}"] += 1

    # positivos: as chamadas corretas colhidas
    for r in reforco:
        if r.get("kind") != "tool_call":
            continue
        k = chave(r["prompt"])
        if a.modo == "restrito" and k not in prompts_com_par:
            stats["pos_fora_do_restrito"] += 1
            continue
        linhas.append({"prompt": r["prompt"],
                       "completion": r["completion"][0]["content"], "label": True})
        stats["pos_com_par" if k in prompts_com_par else "pos_all_right"] += 1

    n_pos = sum(1 for x in linhas if x["label"])
    n_neg = len(linhas) - n_pos
    print(f"modo {a.modo}: {len(linhas)} exemplos · {n_pos} desejaveis / {n_neg} indesejaveis "
          f"({n_pos / max(1, n_neg):.2f}:1)")
    for k2, v in sorted(stats.items()):
        print(f"  {k2:24} {v}")
    print()
    print("⚠️ O KTO tem desirable_weight/undesirable_weight justamente porque a proporcao")
    print("   importa. A do avaliador NAO e' a que se deve treinar — o E4 ja' pagou por herdar")
    print("   proporcao de negativo sem medir (docs/e4-resultado.md §3).")

    a.out.write_text("".join(json.dumps(x, ensure_ascii=False) + chr(10) for x in linhas),
                     encoding="utf-8")
    print()
    print(f"[OK] {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
