"""Teste metamórfico do Choice: mesmo caso, catálogo em outra ORDEM — quanto a decisão muda? (2026-09-24)

Compara casos_calib_<adapter>.jsonl da ordem original com os das variantes (inversa, rotacao), caso a caso,
só nos casos de ferramenta com catálogo >= 2 (os de 1 ferramenta não mudam por construção):
  - taxa de TROCA da ferramenta escolhida (argmax do Choice);
  - distância de variação total média entre as duas distribuições sobre o catálogo (TV = ½·Σ|p−q|);
  - acurácia nas duas ordens e quantos casos passaram de certo a errado e de errado a certo;
  - viés de POSIÇÃO: fração das escolhas no 1º item do catálogo, nas duas ordens (a correta está sorteada).
Literatura: 2,6% (JevLite, Qwen3-4B treinado) a 23% (AnyJev, Qwen3-8B zero-shot) de troca por ordem.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def carregar(p: Path) -> dict[int, dict]:
    return {c["i"]: c for c in (json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip())}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapters", nargs="+", required=True)
    ap.add_argument("--orig-dir", type=Path, default=Path("comeia/eval/results"))
    ap.add_argument("--modos", nargs="+", default=["inversa", "rotacao"])
    ap.add_argument("--saida", default="docs/metamorfico-choice-1g-final-5090.json")
    a = ap.parse_args()
    res = {}
    for adp in a.adapters:
        o = carregar(a.orig_dir / f"casos_calib_{adp}.jsonl")
        res[adp] = {}
        for modo in a.modos:
            v = carregar(a.orig_dir / f"meta_{modo}" / f"casos_calib_{adp}.jsonl")
            ks = [i for i in o if o[i]["is_tool"] and len(o[i]["nomes"]) >= 2 and o[i]["ref"] in o[i]["nomes"]]
            troca = sum(o[i]["pred_tool"] != v[i]["pred_tool"] for i in ks)
            tv = sum(0.5 * sum(abs(o[i]["p_tool"][n] - v[i]["p_tool"].get(n, 0.0)) for n in o[i]["nomes"]) for i in ks) / len(ks)
            acc_o = sum(o[i]["pred_tool"] == o[i]["ref"] for i in ks) / len(ks)
            acc_v = sum(v[i]["pred_tool"] == v[i]["ref"] for i in ks) / len(ks)
            c2e = sum(o[i]["pred_tool"] == o[i]["ref"] and v[i]["pred_tool"] != v[i]["ref"] for i in ks)
            e2c = sum(o[i]["pred_tool"] != o[i]["ref"] and v[i]["pred_tool"] == v[i]["ref"] for i in ks)
            pos1_o = sum(o[i]["pred_tool"] == o[i]["nomes"][0] for i in ks) / len(ks)
            pos1_v = sum(v[i]["pred_tool"] == v[i]["nomes"][0] for i in ks) / len(ks)
            ref1 = sum(o[i]["ref"] == o[i]["nomes"][0] for i in ks) / len(ks)
            res[adp][modo] = {"n": len(ks), "troca": troca / len(ks), "tv_media": tv, "acc_orig": acc_o, "acc_perm": acc_v,
                              "certo_para_errado": c2e, "errado_para_certo": e2c,
                              "escolha_no_1o_orig": pos1_o, "escolha_no_1o_perm": pos1_v, "correta_no_1o_orig": ref1}
            d = res[adp][modo]
            print(f"{adp:10s} {modo:8s} n {d['n']} · TROCA {d['troca']:.1%} · TV {d['tv_media']:.3f} · acc {d['acc_orig']:.3f} -> {d['acc_perm']:.3f} "
                  f"(certo->errado {c2e}, errado->certo {e2c}) · escolhe o 1º item {pos1_o:.1%} -> {pos1_v:.1%} (correta no 1º: {ref1:.1%})")
    Path(a.saida).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nsalvo em {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
