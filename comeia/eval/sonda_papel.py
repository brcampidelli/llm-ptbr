"""Sonda contrafactual: o modelo liga argumento por ROTULO ou por POSICAO?

🔴 POR QUE ISTO EXISTE. No holdout de ferramenta inedita o modelo troca os slots em apenas
**3 de 705 casos** (semente 42) e 1 de 704 (semente 43) — 0,3%, muito abaixo do piso de ruido
de semente (1,5 pp). Seria facil arquivar como irrelevante.

⚠️ E arquivar seria repetir o erro que este projeto acabou de catalogar: **um instrumento que
nao consegue exibir o efeito nao produz evidencia contra ele.** Neste corpus a ordem de mencao
quase sempre COINCIDE com a ordem do esquema, entao a ligacao posicional acerta por acidente e
o holdout nao a distingue da ligacao por rotulo. Os 3 casos que aparecem sao justamente aqueles
em que as ordens divergem:

    pedido  "Eu tenho um TOTAL de 500 e meu VALOR e' 125"
    ref     value=125 · total=500
    previu  value=500 · total=125      <- primeiro numero -> primeiro slot

## O desenho

Contrafactual minimo: **trocar os dois valores no texto e trocar a referencia junto.** O pedido
continua gramatical e os rotulos continuam corretos; so' muda qual numero pertence a qual
papel.

    original  "total de 500 e valor e' 125"   ->  value=125, total=500
    trocado   "total de 125 e valor e' 500"   ->  value=500, total=125

- liga por ROTULO  -> acerta os dois, a taxa nao se move;
- liga por POSICAO -> no trocado ele repete a resposta do original e **erra**.

⭐ E a distincao e' observavel: no trocado, a previsao que bate com a referencia ORIGINAL e'
assinatura de ligacao posicional, nao ruido.

⚠️ CONFUNDIDOR DECLARADO: trocar os valores pode gerar pedido implausivel (um "valor" maior que
o "total"). O relatorio conta quantos casos invertem a ordem de grandeza, para que a leitura
nao atribua ao vies posicional o que pode ser estranhamento semantico. Um par de valores muito
proximos nao sofre disso, entao a fatia implausivel e' reportada separada.

Uso:
    python comeia/eval/sonda_papel.py --montar
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "eval"))
import argumentos as ARG      # noqa: E402

PROC = RAIZ / "data" / "processed"


def _numerico(v: str) -> bool:
    try:
        float(str(v).replace(",", "."))
        return True
    except Exception:
        return False


def _uma_ocorrencia(texto: str, v: str) -> int | None:
    """Posicao da unica ocorrencia de `v` como token inteiro, ou None."""
    if not v:
        return None
    achados = [m.start() for m in re.finditer(rf"(?<![\w.,]){re.escape(v)}(?![\w.,])", texto)]
    return achados[0] if len(achados) == 1 else None


def _do_gigaverbo(caminho: Path) -> list[dict]:
    """Converte o corpus cru para o formato prompt/completion do avaliador."""
    out = []
    for ln in caminho.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        ms = json.loads(ln).get("messages") or []
        i = next((k for k, m in enumerate(ms)
                  if m.get("role") == "assistant"
                  and (m.get("content") or "").strip().startswith("{")), None)
        if i is None or i == 0:
            continue
        out.append({"kind": "tool_call",
                    "prompt": [m for m in ms[:i]
                               if m.get("role") in ("system", "user", "assistant")],
                    "completion": [ms[i]]})
    return out


def montar(fonte: Path, perfil: dict, excluir: Path | None = None) -> int:
    if fonte.name.startswith("gigaverbo"):
        linhas = _do_gigaverbo(fonte)
    else:
        linhas = [json.loads(l) for l in fonte.read_text(encoding="utf-8").splitlines()
                  if l.strip()]
    # 🔴 GUARDA DE CONTAMINACAO: pedido que o modelo viu no treino nao serve de sonda —
    #    ele reproduziria a resposta memorizada e isso se disfarcaria de vies posicional.
    #    Medido: holdout_diverso tem 65,5% dos pedidos no treino do e8. Inutilizavel.
    if excluir and excluir.exists():
        vistos = set()
        for ln in excluir.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            r = json.loads(ln)
            ms = r.get("messages") or (list(r.get("prompt") or [])
                                       + list(r.get("completion") or []))
            u = " ".join(m["content"] for m in ms if m.get("role") == "user")
            if u:
                vistos.add(ARG.nz(u))
        antes = len(linhas)
        linhas = [r for r in linhas
                  if ARG.nz(" ".join(m["content"] for m in r["prompt"]
                                     if m.get("role") == "user")) not in vistos]
        print(f"guarda de contaminacao: {antes - len(linhas)} de {antes} descartados "
              f"por estarem no treino")
    orig, troca = [], []
    st: Counter = Counter()
    for r in linhas:
        if r.get("kind") != "tool_call":
            continue
        o = json.loads(r["completion"][0]["content"])
        t = o["tool"]
        args = o.get("args") or {}
        ext = [k for k in args if ARG.classe_de(perfil, t, k) == "extraido"]
        if len(ext) < 2:
            st["menos de 2 argumentos extraidos"] += 1
            continue
        alvo = [m for m in r["prompt"] if m["role"] == "user"]
        if not alvo:
            continue
        # ⭐ o PRIMEIRO par cujos dois valores aparecem 1x na MESMA fala. Com 3+ extraidos
        #    trocar so' dois mantem o resto do pedido intacto — o contrafactual fica minimo.
        a = b = va = vb = None
        msg = None
        for ia in range(len(ext)):
            for ib in range(ia + 1, len(ext)):
                x, y = str(args[ext[ia]]).strip(), str(args[ext[ib]]).strip()
                if not x or not y or x == y:
                    continue
                # 🔴 SO' PARES DO MESMO TIPO. A v1 trocava valores de tipos diferentes e
                #    gerava gabarito absurdo — `{"name": 25, "age": "John Doe"}`,
                #    `{"car_model": 200, "distance": "Prius"}`. Isso nao testa ligacao de
                #    papel: testa se o modelo aceita escrever besteira. E ele NAO aceita —
                #    devolveu a atribuicao correta, que a minha referencia trocada dava por
                #    errada. A queda de 14 pp medida assim era SANIDADE do modelo, nao vies
                #    posicional. So' com valores do mesmo tipo o rotulo e' o unico
                #    desambiguador, que e' exatamente a pergunta.
                if not (_numerico(x) and _numerico(y)):
                    st["par nao e' numerico dos dois lados"] += 1
                    continue
                m0 = next((m for m in alvo
                           if _uma_ocorrencia(m["content"], x) is not None
                           and _uma_ocorrencia(m["content"], y) is not None), None)
                if m0 is not None:
                    a, b, va, vb, msg = ext[ia], ext[ib], x, y, m0
                    break
            if msg is not None:
                break
        if msg is None:
            st["nenhum par aparece 1x na mesma fala"] += 1
            continue
        idx = alvo.index(msg)
        novo = re.sub(rf"(?<![\w.,]){re.escape(va)}(?![\w.,])", "\x00", msg["content"])
        novo = re.sub(rf"(?<![\w.,]){re.escape(vb)}(?![\w.,])", va, novo)
        novo = novo.replace("\x00", vb)
        if novo == msg["content"]:
            st["troca foi no-op"] += 1
            continue
        # 🔴 GUARDA: depois da troca os dois valores continuam la', uma vez cada
        if (_uma_ocorrencia(novo, va) is None) or (_uma_ocorrencia(novo, vb) is None):
            st["troca deixou o texto ambiguo"] += 1
            continue

        def clone(msgs, subst=None):
            out = []
            for m in msgs:
                m2 = dict(m)
                if subst and m is msg:
                    m2["content"] = subst
                out.append(m2)
            return out

        ref_troca = dict(args)
        ref_troca[a], ref_troca[b] = args[b], args[a]
        base = {"kind": "tool_call"}
        orig.append({**base, "prompt": clone(r["prompt"]),
                     "completion": [{"role": "assistant",
                                     "content": json.dumps({"tool": t, "args": args},
                                                           ensure_ascii=False)}]})
        pr = []
        for m in r["prompt"]:
            pr.append({**m, "content": novo} if m is msg else dict(m))
        troca.append({**base, "prompt": pr,
                      "completion": [{"role": "assistant",
                                      "content": json.dumps({"tool": t, "args": ref_troca},
                                                            ensure_ascii=False)}]})
        st["PAR MONTADO"] += 1
        # ⚠️ CONFUNDIDOR: se um dos papeis e' uma PORCENTAGEM/TAXA, trocar valores pode
        #    gerar pedido absurdo (gorjeta de 850%). Isso NAO e' vies posicional, e' estranheza
        #    semantica — vai contado a parte para nao inflar a leitura.
        pct = re.compile(r"(percent|percentagem|porcent|rate|taxa|tip|desconto|discount)", re.I)
        try:
            if ((pct.search(a) and float(vb) > 100) or (pct.search(b) and float(va) > 100)):
                st["  (troca gera valor absurdo para % — confundidor)"] += 1
        except Exception:
            pass
        _ = idx

    # negativos, para a regua ter denominador em over-calling
    negs = [r for r in linhas if r.get("kind") != "tool_call"][: max(1, len(orig) // 4)]
    for nome, dados in (("sonda_papel_orig", orig), ("sonda_papel_troca", troca)):
        p = PROC / f"{nome}.eval.jsonl"
        p.write_text("".join(json.dumps(x, ensure_ascii=False) + chr(10)
                             for x in dados + negs), encoding="utf-8")
        print(f"{p.name}: {len(dados)} tool + {len(negs)} text")
    print()
    for k, v in st.most_common():
        print(f"  {k:38} {v}")
    if st["PAR MONTADO"] < 30:
        print("\n⚠️  menos de 30 pares: a sonda nao tem poder para decidir nada.")
        return 1
    return 0


def comparar(tag_o: str, tag_t: str) -> int:
    """Le os dois despejos e separa VIES POSICIONAL de erro generico."""
    def C(t):
        p = Path(__file__).parent / "results" / f"casos_{t}.jsonl"
        return {x["i"]: x for x in map(json.loads, p.read_text(encoding="utf-8").splitlines())}
    O, T = C(tag_o), C(tag_t)
    ids = [i for i in O if O[i]["tipo"] == "tool" and i in T]
    ok_o = sum(1 for i in ids if O[i]["exec_ok"])
    ok_t = sum(1 for i in ids if T[i]["exec_ok"])
    # no TROCADO, previu a referencia do ORIGINAL? -> assinatura posicional
    posic = sum(1 for i in ids
                if not T[i]["exec_ok"]
                and {k: str(v) for k, v in (T[i]["args_pred"] or {}).items()}
                == {k: str(v) for k, v in (O[i]["args_ref"] or {}).items()})
    print(f"pares: {len(ids)}")
    print(f"  original {ok_o}/{len(ids)} = {ok_o/len(ids):6.1%}")
    print(f"  trocado  {ok_t}/{len(ids)} = {ok_t/len(ids):6.1%}   "
          f"queda {(ok_o-ok_t)/len(ids)*100:+.1f} pp")
    print(f"  ⭐ no trocado, previu a referencia do ORIGINAL: {posic} = {posic/len(ids):.1%}")
    print("     (assinatura de ligacao POSICIONAL — nao e' erro generico)")
    return 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--montar", action="store_true")
    ap.add_argument("--comparar", nargs=2, metavar=("TAG_ORIG", "TAG_TROCA"))
    ap.add_argument("--fonte", type=Path, default=PROC / "holdout_ferramenta.eval.jsonl")
    ap.add_argument("--excluir", type=Path, default=PROC / "treino_ferramenta.jsonl",
                    help="pedidos deste arquivo nao entram na sonda")
    a = ap.parse_args()
    perfil = ARG.carregar()
    if a.comparar:
        return comparar(*a.comparar)
    if a.montar:
        return montar(a.fonte, perfil, a.excluir)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
