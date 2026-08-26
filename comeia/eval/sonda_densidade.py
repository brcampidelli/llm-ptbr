"""Sonda de densidade: o modelo consegue COPIAR uma cadeia longa do pedido?

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-25: o acerto de copia de argumento extraido
desaba com o comprimento do valor.

    numero 94,0% (1 token) · frase 89,4% (3) · palavra 79,6% (3) · E-MAIL 35,6% (8)

Hipotese: **o modelo parafraseia onde deveria transcrever.** Ele regenera linguagem — uma
frase plausivel sai certa mesmo sem copia exata — e falha em cadeia arbitraria, que so' pode
ser transcrita. `boss@company.com` virava `Boss@Company`.

⚠️ E o eixo NAO E' MENSURAVEL no corpus: `send_email` concentra 65% de todos os e-mails e e'
UMA raiz, entao ela fica de um lado so'. Com ela no treino (split novo), o holdout tem 0,5% de
e-mail; com ela no holdout (split antigo), o treino tem 2,4% e o resultado confunde novidade de
ferramenta com novidade de tipo de valor. Medido: ferramentas de e-mail livres do treino dao
**24 casos**; mesma ferramenta com pedido inedito da' **4**. Nenhum decide nada.

## O desenho

Contrafactual controlado: pegar caso LIMPO do holdout, achar um argumento `extraido` cujo valor
aparece no pedido, e substitui-lo por uma escada de cadeias **inventadas** de densidade
crescente — no pedido E na referencia. Ferramenta, pedido e estrutura ficam iguais; so' o
comprimento do que precisa ser copiado muda.

⭐ As cadeias sao INVENTADAS de proposito: o modelo nao pode recuperá-las da memoria, so'
copiando. E' isso que separa transcricao de regeneracao.

⚠️ **Confundidor declarado:** cadeia mais longa tambem e' mais estranha. Densidade e raridade
andam juntas por construcao e esta sonda nao as separa — ela mede "dificuldade de copia", nao
"efeito do comprimento com naturalidade constante".

⚠️ **E o texto e' sintetico**, entao isto mede capacidade de copia, nao desempenho em pedido
natural.

Uso:
    python comeia/eval/sonda_densidade.py --montar
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "eval"))
import argumentos as ARG      # noqa: E402

PROC = RAIZ / "data" / "processed"
NL = chr(10)

# escada: mesmo papel sintatico (nome/titulo/consulta), so' o comprimento muda.
# ⚠️ os degraus sao MEDIDOS com o tokenizador em --montar, nunca assumidos.
ESCADA = {
    "d1": "Zorak",
    "d2": "Zorak Vintel",
    "d3": "Zorak Vintel Quandrix",
    "d4": "Zorak-Vintel-Quandrix-7739",
    # ⭐ d5 e d6 nao sao degraus de comprimento: sao o CONTROLE DE FORMATO. A escada d1-d4
    #    mostrou copia PLANA de 3 a 14 tokens (74,1% -> 71,3%), refutando a hipotese de
    #    densidade. Mas o e-mail real (8 tokens) era copiado a 35,6% — menos que uma
    #    cadeia de 14. Se a estrutura de E-MAIL for o mecanismo, d5 desaba e d6 nao.
    "d5": "Zorak.Vintel@Quandrix-7739.com",
    "d6": "Zorak.Vintel.Quandrix-7739.com",
}


def nz(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def _uma(texto: str, v: str) -> bool:
    return len(re.findall(rf"(?<![\w.@-]){re.escape(v)}(?![\w.@-])", texto)) == 1


def montar(fonte: Path, tok) -> int:
    linhas = [json.loads(l) for l in fonte.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    perfil = ARG.carregar()
    st: Counter = Counter()
    base: list[tuple[dict, str, str]] = []      # (registro, chave, valor original)
    for r in linhas:
        if r.get("kind") != "tool_call":
            continue
        o = json.loads(r["completion"][0]["content"])
        f = o["tool"]
        args = o.get("args") or {}
        alvo = None
        for k, v in args.items():
            if ARG.classe_de(perfil, f, k) != "extraido":
                continue
            s = str(v).strip()
            # 🔴 so' valores TEXTUAIS: trocar um numero por "Zorak" faz pedido absurdo
            #    ("calcule 20% de Zorak") e mediria estranheza, nao copia.
            if not s or re.match(r"^-?[\d.,:/]+$", s) or "@" in s:
                continue
            msg = next((m for m in r["prompt"]
                        if m["role"] == "user" and _uma(m["content"], s)), None)
            if msg is None:
                continue
            alvo = (k, s, msg)
            break
        if alvo is None:
            st["sem argumento textual substituivel"] += 1
            continue
        st["ELEGIVEL"] += 1
        base.append((r, alvo[0], alvo[1]))
    print(f"casos elegiveis: {len(base)}")
    for k, v in st.most_common():
        print(f"  {k:38} {v}")
    if len(base) < 40:
        print(f"{NL}⚠️  menos de 40 casos: a sonda nao decide nada.")
        return 1

    print(f"{NL}escada (tokens MEDIDOS, nao assumidos):")
    for d, s in ESCADA.items():
        print(f"  {d}: {s!r:34} {len(tok(s, add_special_tokens=False)['input_ids'])} tokens")

    for d, novo_v in ESCADA.items():
        saida = []
        for r, k, velho in base:
            o = json.loads(r["completion"][0]["content"])
            args = dict(o.get("args") or {})
            args[k] = novo_v
            pr = []
            trocou = 0
            for m in r["prompt"]:
                c = m["content"]
                if m["role"] == "user" and _uma(c, velho):
                    c = re.sub(rf"(?<![\w.@-]){re.escape(velho)}(?![\w.@-])", novo_v, c)
                    trocou += 1
                pr.append({**m, "content": c})
            if trocou != 1 or not _uma(" ".join(x["content"] for x in pr
                                                if x["role"] == "user"), novo_v):
                continue                       # 🔴 guarda: troca tem de ser unica e limpa
            saida.append({"kind": "tool_call", "prompt": pr,
                          "completion": [{"role": "assistant",
                                          "content": json.dumps({"tool": o["tool"],
                                                                 "args": args},
                                                                ensure_ascii=False)}]})
        p = PROC / f"sonda_dens_{d}.eval.jsonl"
        p.write_text("".join(json.dumps(x, ensure_ascii=False) + NL for x in saida),
                     encoding="utf-8")
        print(f"  {p.name}: {len(saida)} casos")
    return 0


def comparar(tags: list[str]) -> int:
    print(f"{'degrau':>8}{'tokens':>8}{'acerto de copia':>18}{'exec':>9}{'n':>6}")
    for d, tag in zip(ESCADA, tags):
        p = Path(__file__).parent / "results" / f"casos_{tag}.jsonl"
        if not p.exists():
            print(f"{d:>8}  (falta {tag})")
            continue
        cs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
        t = [x for x in cs if x["tipo"] == "tool"]
        alvo = ESCADA[d]
        copiou = sum(1 for x in t
                     if any(nz(v) == nz(alvo) for v in (x.get("args_pred") or {}).values()))
        ok = sum(1 for x in t if x["exec_ok"])
        print(f"{d:>8}{'':>8}{copiou}/{len(t)} = {copiou/max(1,len(t)):7.1%}"
              f"{ok/max(1,len(t)):9.1%}{len(t):6}")
    return 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--montar", action="store_true")
    ap.add_argument("--comparar", nargs="+")
    ap.add_argument("--fonte", type=Path, default=PROC / "holdout_balanceado.eval.jsonl")
    a = ap.parse_args()
    if a.comparar:
        return comparar(a.comparar)
    if a.montar:
        from transformers import AutoTokenizer
        return montar(a.fonte, AutoTokenizer.from_pretrained("BrCamp/bee-350m-pt-base"))
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
