"""Separa treino e holdout por COMPONENTE CONEXO — a única separação que não vaza aqui.

🔴 POR QUE ISTO EXISTE. Três medições minhas morreram por separação errada:

  1. separei por hash do prompt inteiro -> 93% dos pedidos do holdout apareciam no treino,
     porque o *function masking* do E3 CRIA o mesmo pedido com e sem a ferramenta;
  2. deduplicei por tupla (ferramenta,args) -> 76,2% ainda tinham o prompt EXATO no treino;
  3. e o holdout "de 600" tinha 87 problemas distintos, um deles 42% do total.

⭐ A regra que sai disso: **a unidade de separação tem de ser tudo que é compartilhado.** Dois
exemplos ficam do mesmo lado se dividem o TEXTO DO PEDIDO ou a TUPLA (ferramenta, args). Isso
é um grafo; a separação correta é por componente conexo.

⭐⭐ E o escopo agora são as 149 ferramentas com pelo menos um argumento PONTUÁVEL (ver
`argumentos.py`), não só as 12 com fórmula — 4.293 tuplas distintas contra 181.

⚠️ Caso sem nenhum argumento pontuável é RECUSADO. Contar como acerto quem só tem argumento
formulado (`subject`, `body`, `task`) infla tudo.

Uso:
    python comeia/data/construir_split_diverso.py --n-holdout 1000
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "eval"))
import argumentos as ARG      # noqa: E402
import mundo_aberto as MA     # noqa: E402

PROC = RAIZ / "data" / "processed"


def nz(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


class Uniao:
    """Union-find sobre chaves de texto — pedido e tupla entram no mesmo grafo."""

    def __init__(self):
        self.pai: dict[str, str] = {}

    def acha(self, x: str) -> str:
        self.pai.setdefault(x, x)
        while self.pai[x] != x:
            self.pai[x] = self.pai[self.pai[x]]
            x = self.pai[x]
        return x

    def une(self, a: str, b: str) -> None:
        ra, rb = self.acha(a), self.acha(b)
        if ra != rb:
            self.pai[rb] = ra


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", type=Path, default=PROC / "gigaverbo_ferramenta.jsonl")
    ap.add_argument("--negativos", type=Path, default=PROC / "negativos_com_recusa.jsonl")
    ap.add_argument("--n-holdout", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20260824)
    a = ap.parse_args()

    perfil = ARG.carregar()
    if not perfil:
        print("ERRO: rode antes `python comeia/eval/argumentos.py --perfilar`", file=sys.stderr)
        return 2
    aprovadas = set(json.loads((RAIZ / "eval" / "mundo_aberto_aprovadas.json")
                               .read_text(encoding="utf-8")))

    itens, stats = [], Counter()
    for ln in a.fonte.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        ms = json.loads(ln).get("messages") or []
        i = next((k for k, m in enumerate(ms)
                  if m.get("role") == "assistant"
                  and (m.get("content") or "").strip().startswith("{")), None)
        if i is None or i == 0:
            stats["sem_chamada"] += 1
            continue
        try:
            o = json.loads(ms[i]["content"])
        except Exception:
            continue
        if not isinstance(o, dict) or "tool" not in o:
            continue
        pref = [m for m in ms[:i] if m.get("role") in ("system", "user", "assistant")]
        pedido = nz(" ".join(m["content"] for m in pref if m["role"] == "user"))
        if not pedido:
            stats["sem_pedido"] += 1
            continue

        # pontuavel? formula validada OU >=1 argumento extraido/temporal
        tem_formula = o["tool"] in aprovadas
        npt = sum(1 for k in (o.get("args") or {})
                  if ARG.classe_de(perfil, o["tool"], k) in ("extraido", "temporal"))
        if not tem_formula and npt == 0:
            stats["sem_criterio"] += 1
            continue

        # RESPONDIBILIDADE: todo valor pontuavel tem de estar no contexto
        ctx = nz(" ".join(m["content"] for m in pref))
        falta = False
        for k, v in (o.get("args") or {}).items():
            if isinstance(v, (dict, list)):
                continue
            if ARG.classe_de(perfil, o["tool"], k) != "extraido":
                continue
            if nz(v) and nz(v) not in ctx:
                falta = True
                break
        if falta:
            stats["nao_derivavel"] += 1
            continue

        tupla = f"T\t{o['tool']}\t" + json.dumps(
            sorted((k, str(v)) for k, v in (o.get("args") or {}).items()), ensure_ascii=False)
        itens.append({"prompt": pref, "completion": [ms[i]], "kind": "tool_call",
                      "ferramenta": o["tool"], "_pedido": f"P\t{pedido}", "_tupla": tupla,
                      "_npt": npt, "_formula": tem_formula})

    print(f"itens pontuaveis: {len(itens)}")
    for k, v in stats.most_common():
        print(f"  descartado · {k:16} {v}")

    # ── grafo: pedido e tupla ligam exemplos
    u = Uniao()
    for it in itens:
        u.une(it["_pedido"], it["_tupla"])
    comp = defaultdict(list)
    for it in itens:
        comp[u.acha(it["_pedido"])].append(it)
    print(f"componentes conexos: {len(comp)}  (media {len(itens)/len(comp):.1f} exemplos cada)")
    tam = Counter(len(v) for v in comp.values())
    print(f"  maior componente: {max(len(v) for v in comp.values())} exemplos")
    print(f"  componentes com 1 exemplo: {tam[1]}")

    rnd = random.Random(a.seed)
    chaves = sorted(comp)
    rnd.shuffle(chaves)
    hold, treino, tuplas_hold = [], [], set()
    for c in chaves:
        grupo = comp[c]
        if len(hold) < a.n_holdout:
            # 1 exemplo por TUPLA dentro do componente — o resto do componente NAO vai
            # para o treino (vazaria o pedido), e' descartado
            vistas = set()
            for it in grupo:
                if it["_tupla"] in vistas:
                    continue
                vistas.add(it["_tupla"])
                tuplas_hold.add(it["_tupla"])
                hold.append(it)
        else:
            treino.extend(grupo)

    # ── negativos: mesmo grafo, pelo pedido
    # 🔴 A v1 roteava perguntando so' "este pedido esta' no holdout?" e ESQUECIA de
    #    perguntar "esta' no treino?". Negativo cujo pedido ja' aparece num exemplo de
    #    treino tem de ir para o TREINO — senao o modelo ve' o pedido treinando e o
    #    reencontra no holdout. Vazaram 265 de 2.000 assim, TODOS do tipo `text`.
    pedidos_hold = {it["_pedido"] for it in hold}
    pedidos_treino = {it["_pedido"] for it in treino}
    neg_h, neg_t = [], []
    for ln in a.negativos.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        ms = r.get("messages") or (list(r.get("prompt") or []) + list(r.get("completion") or []))
        uu = [m for m in ms if m["role"] == "user"]
        aa = [m for m in ms if m["role"] == "assistant"]
        ss = [m for m in ms if m["role"] == "system"]
        if not (uu and aa):
            continue
        reg = {"prompt": ss[:1] + uu[:1],
               "completion": [{"role": "assistant", "content": aa[-1]["content"]}],
               "kind": "text"}
        pk = "P" + chr(9) + nz(uu[0]["content"])
        if pk in pedidos_treino:
            neg_t.append(reg)          # o pedido ja esta no treino: fica no treino
        elif pk in pedidos_hold:
            neg_h.append(reg)
        else:
            neg_t.append(reg)          # inedito dos dois lados -> treino
    rnd.shuffle(neg_t)
    n_neg = min(len(hold), len(neg_h) + len(neg_t))
    negs = (neg_h + neg_t)[:n_neg]

    def limpo(r):
        return {k: v for k, v in r.items() if not k.startswith("_")}

    limpo0 = limpo

    # 🔴 GUARDA POSTERIOR — nao confia no roteamento, CONFERE o resultado.
    #    O roteamento compara a 1a fala do usuario do negativo contra o texto JUNTADO dos
    #    exemplos de treino, e nem sempre coincidem. Cacar o descasamento e' fragil; filtrar o
    #    holdout final contra o treino final e' garantido. Guarda que depende de a construcao
    #    estar certa nao e' guarda — e' a mesma suposicao escrita duas vezes.
    ped_treino = {nz(" ".join(m["content"] for m in r["prompt"] if m["role"] == "user"))
                  for r in ([limpo0(x) for x in treino] + neg_t)}
    antes = len(hold) + len(negs)
    hold = [x for x in hold
            if nz(" ".join(m["content"] for m in x["prompt"] if m["role"] == "user"))
            not in ped_treino]
    negs = [x for x in negs
            if nz(" ".join(m["content"] for m in x["prompt"] if m["role"] == "user"))
            not in ped_treino]
    print(f"guarda posterior: {antes - len(hold) - len(negs)} casos removidos do holdout "
          f"por terem o pedido no treino")

    fh = PROC / "holdout_diverso.eval.jsonl"
    ft = PROC / "treino_diverso.jsonl"
    saida_h = [limpo(x) for x in hold] + negs
    rnd.shuffle(saida_h)
    fh.write_text("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in saida_h),
                  encoding="utf-8")
    saida_t = [limpo(x) for x in treino] + neg_t[n_neg:][: len(treino)]
    rnd.shuffle(saida_t)
    ft.write_text("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in saida_t),
                  encoding="utf-8")

    print()
    print(f"HOLDOUT {len(saida_h)} = {len(hold)} tool + {len(negs)} text -> {fh.name}")
    print(f"  tuplas distintas: {len(tuplas_hold)}  (o holdout anterior tinha 87 em 600 casos)")
    print(f"  ferramentas: {len({x['ferramenta'] for x in hold})}")
    print(f"  com formula validada: {sum(1 for x in hold if x['_formula'])} · "
          f"so' por argumento: {sum(1 for x in hold if not x['_formula'])}")
    print(f"TREINO  {len(saida_t)} -> {ft.name}")
    print()
    print("top ferramentas do holdout:")
    for t, n in Counter(x["ferramenta"] for x in hold).most_common(10):
        print(f"  {t:30} {n:4} = {n/len(hold):5.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
