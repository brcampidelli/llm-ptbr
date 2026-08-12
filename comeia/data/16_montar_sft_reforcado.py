"""Mistura o SFT original com o reforco do rejection sampling, vigiando a PROPORCAO.

⚠️ O RISCO QUE ESTE SCRIPT EXISTE PARA CONTROLAR:
    O reforco colhido por rejection sampling e 100% `tool_call` — por construcao, porque
    so a chamada de ferramenta tem verificacao por execucao. Jogar isso na mistura sem
    olhar desloca a proporcao tool/text do dataset, e a proporcao e justamente o que
    ensina o modelo a DECIDIR se chama.

    Original: 886 tool / 609 text = 59% / 41%.
    Somando ~880 de reforco as cegas: 73% / 27%.

    Ou seja: o script que existe para melhorar a taxa de acerto pode PIORAR o
    over-calling, que ja e o pior numero do modelo (23,1%). O ganho de um eixo pago com
    perda em outro — e sem ninguem perceber, porque so se mediria o eixo que melhorou.

    Aqui a proporcao e um parametro explicito (--teto-tool), com aviso em voz alta quando
    o reforco precisa ser cortado para respeita-la.

Uso:
    python comeia/data/16_montar_sft_reforcado.py                  # preserva a proporcao
    python comeia/data/16_montar_sft_reforcado.py --teto-tool 0.65 # afrouxa de proposito
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"


def carregar(nome: str) -> list[dict]:
    p = PROC / nome
    if not p.exists():
        print(f"ERRO: falta {p}", file=sys.stderr)
        raise SystemExit(1)
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--teto-tool", type=float, default=None,
                    help="fracao maxima de tool_call na mistura agentica. "
                         "Padrao: a MESMA do dataset original (nao desloca a decisao).")
    ap.add_argument("--out", type=Path, default=PROC / "sft_misto_reforcado.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    ptbr = carregar("sft_ptbr.jsonl")
    agentic = carregar("sft_agentic.jsonl")
    reforco = carregar("sft_agentic_reforco.jsonl")

    n_tool = sum(1 for r in agentic if r.get("kind") == "tool_call")
    n_text = len(agentic) - n_tool
    prop_original = n_tool / len(agentic)
    teto = args.teto_tool if args.teto_tool is not None else prop_original

    print(f"original agentico : {n_tool} tool / {n_text} text = {prop_original:.1%} tool")
    print(f"reforco disponivel: {len(reforco)} (100% tool, por construcao)")
    print(f"teto de tool      : {teto:.1%}")

    # quantos de reforco cabem sem passar do teto:  (n_tool + x) / (len + x) <= teto
    if teto >= 1.0:
        cabe = len(reforco)
    else:
        cabe = int((teto * len(agentic) - n_tool) / (1 - teto))
    cabe = max(0, min(cabe, len(reforco)))

    if cabe < len(reforco):
        print(f"\n⚠️ CORTANDO o reforco: {len(reforco)} -> {cabe} para nao passar do teto.")
        print("   Sem este corte a proporcao de tool_call subiria e o modelo aprenderia a")
        print("   chamar ferramenta com mais frequencia — piorando o over-calling.")
        rng = random.Random(args.seed)
        reforco = rng.sample(reforco, cabe)
    else:
        print(f"\n[OK] todo o reforco cabe ({len(reforco)}) sem deslocar a proporcao.")

    agentico_final = agentic + reforco
    n_tool_f = sum(1 for r in agentico_final if r.get("kind") == "tool_call")
    print(f"agentico final    : {n_tool_f} tool / {len(agentico_final)-n_tool_f} text "
          f"= {n_tool_f/len(agentico_final):.1%} tool")

    saida = ptbr + agentico_final
    conteudo = "\n".join(json.dumps(r, ensure_ascii=False) for r in saida) + "\n"
    args.out.write_text(conteudo, encoding="utf-8")
    h = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()

    print(f"\ntotal             : {len(saida)} exemplos "
          f"({len(ptbr)} PT + {len(agentico_final)} agentico)")
    print(f"sha256            : {h}")
    print(f"[OK] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
