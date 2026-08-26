"""Separa treino e holdout por FERRAMENTA — o único eixo de generalização ainda não medido.

O split anterior (`construir_split_diverso.py`) separou por pedido e por tupla de argumentos,
mas 121 das 123 ferramentas do holdout estavam no treino. Ele mede *"o modelo lê o catálogo?"*.
Este mede outra coisa: *"o modelo usa uma ferramenta que NUNCA VIU?"*.

🔴 A ARMADILHA: separar pelo nome exato deixaria o quase-sinônimo no treino. `calculate_tip` no
holdout com `calculate_tip_amount` no treino não é ferramenta inédita — e o resultado sairia
inflado. Medido: 150 ferramentas pontuáveis colapsam em ~126 raízes.

⚠️ E a agregação por raiz também erra se for ingênua. Tirar o prefixo verbal juntou
`send_email` com `check_email` e `play_music` com `search_music` — **ações diferentes sobre o
mesmo objeto**. A raiz aqui é (FAMILIA DO VERBO, objeto): junta
`find_restaurants`/`search_restaurants`, separa enviar de conferir.

⭐ E quando houver dúvida, AGRUPAR: agrupar demais só custa dado de treino; agrupar de menos
infla o resultado. Os dois erros não são simétricos.

Uso:
    python comeia/data/split_por_ferramenta.py --frac-holdout 0.25
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

PROC = RAIZ / "data" / "processed"

# familias de verbo: sinonimos de ACAO colapsam, acoes distintas ficam separadas
FAMILIAS = {
    "BUSCAR": r"^(search|find|lookup|browse|query|discover)_",
    "OBTER": r"^(get|fetch|retrieve|check|show|list|read|view)_",
    "CRIAR": r"^(create|make|generate|add|new|register|schedule|book|post|set)_",
    "CALCULAR": r"^(calculate|compute|convert|estimate)_",
    "ENVIAR": r"^(send|share|publish|submit|order|deliver)_",
    "ALTERAR": r"^(update|edit|modify|change|delete|remove|cancel)_",
    "EXECUTAR": r"^(play|run|start|stop|execute|translate|analyze|track)_",
}


def nz(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def raiz_de(tool: str) -> str:
    t = tool.lower()
    fam = "OUTRO"
    resto = t
    for nome, rx in FAMILIAS.items():
        m = re.match(rx, t)
        if m:
            fam, resto = nome, t[m.end():]
            break
    # objeto: sem sufixo generico, sem plural, sem separadores
    resto = re.sub(r"_(amount|value|total|price|cost|info|details|data|list|result|rate|"
                   r"payment|status)$", "", resto)
    resto = re.sub(r"(ies)$", "y", resto)
    resto = re.sub(r"(?<![aeiou])s$", "", resto)
    obj = re.sub(r"[_\s]+", "", resto)
    return fam + ":" + obj


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", type=Path, default=PROC / "gigaverbo_ferramenta.jsonl")
    ap.add_argument("--negativos", type=Path, default=PROC / "negativos_com_recusa.jsonl")
    ap.add_argument("--frac-holdout", type=float, default=0.25)
    ap.add_argument("--teto-por-ferramenta", type=float, default=0.06,
                    help="fracao maxima do holdout que uma unica ferramenta pode ocupar")
    ap.add_argument("--seed", type=int, default=20260824)
    a = ap.parse_args()

    perfil = ARG.carregar()
    if not perfil:
        print("ERRO: rode `python comeia/eval/argumentos.py --perfilar`", file=sys.stderr)
        return 2

    itens, stats = [], Counter()
    for ln in a.fonte.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        ms = json.loads(ln).get("messages") or []
        i = next((k for k, m in enumerate(ms)
                  if m.get("role") == "assistant"
                  and (m.get("content") or "").strip().startswith("{")), None)
        if i is None or i == 0:
            continue
        try:
            o = json.loads(ms[i]["content"])
        except Exception:
            continue
        if not isinstance(o, dict) or "tool" not in o:
            continue
        npt = [k for k in (o.get("args") or {})
               if ARG.classe_de(perfil, o["tool"], k) in ("extraido", "temporal")]
        if not npt:
            stats["sem_criterio"] += 1
            continue
        pref = [m for m in ms[:i] if m.get("role") in ("system", "user", "assistant")]
        ctx = nz(" ".join(m["content"] for m in pref))
        pedido = nz(" ".join(m["content"] for m in pref if m["role"] == "user"))
        if not pedido:
            continue
        if any(nz(v) and nz(v) not in ctx for k, v in (o.get("args") or {}).items()
               if not isinstance(v, (dict, list))
               and ARG.classe_de(perfil, o["tool"], k) == "extraido"):
            stats["nao_derivavel"] += 1
            continue
        itens.append({"prompt": pref, "completion": [ms[i]], "kind": "tool_call",
                      "ferramenta": o["tool"], "_raiz": raiz_de(o["tool"]),
                      "_pedido": pedido,
                      "_tupla": o["tool"] + json.dumps(
                          sorted((k, str(v)) for k, v in (o.get("args") or {}).items()),
                          ensure_ascii=False)})

    por_raiz = defaultdict(list)
    for it in itens:
        por_raiz[it["_raiz"]].append(it)
    nomes = defaultdict(set)
    for it in itens:
        nomes[it["_raiz"]].add(it["ferramenta"])
    print(f"itens pontuaveis: {len(itens)} · ferramentas: {len({i['ferramenta'] for i in itens})}"
          f" · RAIZES: {len(por_raiz)}")
    multi = {k: v for k, v in nomes.items() if len(v) > 1}
    print(f"  raizes que agrupam mais de um nome: {len(multi)}")
    for k, v in sorted(multi.items(), key=lambda x: -len(por_raiz[x[0]]))[:6]:
        print(f"    {k:22} {sorted(v)}")

    # ── estratificar por FREQUENCIA **e por TIPO DE VALOR**
    #
    # 🔴 A v1 estratificava so por frequencia, e isso criou um confundidor nao declarado.
    #    `send_email` concentra 479 dos 732 argumentos de e-mail do corpus e e UMA raiz —
    #    mandando-a para o holdout, 65% de toda a copia de cadeia densa foi junto.
    #    Medido: treino com 2,4% de e-mail, holdout com 26,6%.
    #
    #    O holdout media "ferramenta inedita" E "tipo de valor inedito" ao mesmo tempo, e o
    #    acerto de copia acompanhava o TIPO, nao a novidade da ferramenta:
    #        numero 94,0% · frase 89,4% · palavra 79,6% · E-MAIL 35,6%
    #    Sem separar os eixos, qualquer intervencao aposta em qual deles e a causa.
    #
    # ⚠️ E a explicacao simples NAO fecha: `frase` e mais rara que `palavra unica`
    #    (8,7% x 11,9%) e acerta MAIS. O que distingue o e-mail e ser cadeia arbitraria sem
    #    estrutura linguistica — o modelo REGENERA linguagem, mas e-mail tem de ser
    #    TRANSCRITO. Raridade e comprimento agravam; nao sao o mecanismo.
    def tipo_do_valor(s):
        s = str(s)
        if "@" in s:
            return "email"
        if re.match(r"^-?[\d.,]+$", s.strip()):
            return "numero"
        return "palavra" if len(s.split()) == 1 else "frase"

    tipo_raiz = {}
    for rz, its in por_raiz.items():
        c = Counter()
        for it in its:
            o = json.loads(it["completion"][0]["content"])
            for k2, v2 in (o.get("args") or {}).items():
                if ARG.classe_de(perfil, o["tool"], k2) == "extraido":
                    c[tipo_do_valor(v2)] += 1
        tipo_raiz[rz] = c.most_common(1)[0][0] if c else "sem_extraido"
    print("tipo de valor dominante por raiz: "
          + str(dict(Counter(tipo_raiz.values()).most_common())))

    def perfil_tipo(raizes):
        """distribuicao de tipo de valor dos argumentos EXTRAIDOS dessas raizes"""
        c = Counter()
        for rz in raizes:
            for it in por_raiz[rz]:
                o = json.loads(it["completion"][0]["content"])
                for k2, v2 in (o.get("args") or {}).items():
                    if ARG.classe_de(perfil, o["tool"], k2) == "extraido":
                        c[tipo_do_valor(v2)] += 1
        n = max(1, sum(c.values()))
        return {t: c[t] / n for t in ("numero", "palavra", "frase", "email")}

    def desalinho(hold):
        """maior diferenca de proporcao entre treino e holdout, em pp"""
        a1 = perfil_tipo(hold)
        a2 = perfil_tipo([r for r in por_raiz if r not in hold])
        return max(abs(a1[t] - a2[t]) for t in a1)

    # ⭐ Estratificar por tipo DOMINANTE nao basta: cada raiz e' uma MISTURA, e a primeira
    #    versao disto trocou o desalinhamento de e-mail (24,2 pp) por um de frase (19,7 pp).
    #    Entao otimiza-se DIRETAMENTE a propriedade desejada: sortear varias atribuicoes
    #    validas (respeitando a faixa de frequencia) e ficar com a de menor desalinho.
    #    ⚠️ Isto NAO e' escolher o split que da' o numero desejado: o criterio otimizado e'
    #    alinhamento treino/teste, que independe do desempenho de qualquer modelo.
    ordem = sorted(por_raiz, key=lambda r: -len(por_raiz[r]))
    faixa = max(1, len(ordem) // 4)
    melhor, melhor_d = None, 9.9
    for tentativa in range(60):
        rnd = random.Random(a.seed + tentativa)
        h = set()
        for ini in range(0, len(ordem), faixa):
            bloco = ordem[ini:ini + faixa]
            k = max(1, round(len(bloco) * a.frac_holdout))
            h.update(rnd.sample(bloco, k))
        d = desalinho(h)
        if d < melhor_d:
            melhor, melhor_d = h, d
    hold_raiz = melhor
    rnd = random.Random(a.seed)
    print("")
    print(f"raizes no holdout: {len(hold_raiz)}/{len(por_raiz)} "
          f"({len(hold_raiz)/len(por_raiz):.0%}) — melhor de 60 sorteios, "
          f"desalinho de tipo {melhor_d*100:.1f} pp")

    hold_raw = [it for it in itens if it["_raiz"] in hold_raiz]
    treino = [it for it in itens if it["_raiz"] not in hold_raiz]
    # 1 caso por TUPLA no holdout, com TETO por ferramenta.
    # ⚠️ Sem o teto, `create_calendar_event` (29,2%) e `send_email` (25,7%) davam 55% do
    #    holdout e eu estaria medindo "sabe calendario e e-mail ineditos", nao "sabe ferramenta
    #    inedita". E' o mesmo defeito de concentracao que ja' custou um holdout inteiro — so'
    #    que agora no eixo da ferramenta em vez do eixo da tupla.
    rnd.shuffle(hold_raw)
    vistas, hold, por_f = set(), [], Counter()
    # 🔴 o teto era % do POOL (178 casos) e deixou uma ferramenta com 19,8% do
    #    holdout. Agora e' % do holdout ALVO, medido por iteracao.
    teto = max(15, int(min(len(hold_raw), 1000) * a.teto_por_ferramenta))
    for it in hold_raw:
        if it["_tupla"] in vistas or por_f[it["ferramenta"]] >= teto:
            continue
        vistas.add(it["_tupla"])
        por_f[it["ferramenta"]] += 1
        hold.append(it)
    print(f"teto por ferramenta: {teto} casos "
          f"({a.teto_por_ferramenta:.0%} do disponivel)")

    # ── negativos pelo pedido, com guarda posterior
    ped_treino = {it["_pedido"] for it in treino}
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
        (neg_t if nz(uu[0]["content"]) in ped_treino else neg_h).append(reg)
    rnd.shuffle(neg_h)
    rnd.shuffle(neg_t)

    def limpo(r):
        return {k: v for k, v in r.items() if not k.startswith("_")}

    # 🔴 GUARDA POSTERIOR — confere o resultado, nao confia na construcao
    ped_t_final = {it["_pedido"] for it in treino} | {
        nz(" ".join(m["content"] for m in r["prompt"] if m["role"] == "user")) for r in neg_t}
    antes = len(hold)
    hold = [x for x in hold if x["_pedido"] not in ped_t_final]
    negs = [x for x in neg_h
            if nz(" ".join(m["content"] for m in x["prompt"] if m["role"] == "user"))
            not in ped_t_final][: len(hold) // 2]
    print(f"guarda posterior: {antes - len(hold)} casos removidos por pedido no treino")

    n_txt = int(len(treino) / 1.44)
    saida_h = [limpo(x) for x in hold] + negs
    saida_t = [limpo(x) for x in treino] + neg_t[:n_txt]
    rnd.shuffle(saida_h)
    rnd.shuffle(saida_t)
    fh, ft = PROC / "holdout_ferramenta.eval.jsonl", PROC / "treino_ferramenta.jsonl"
    fh.write_text("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in saida_h),
                  encoding="utf-8")
    ft.write_text("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in saida_t),
                  encoding="utf-8")

    print()
    print(f"HOLDOUT {len(saida_h)} = {len(hold)} tool + {len(negs)} text -> {fh.name}")
    print(f"  ferramentas: {len({x['ferramenta'] for x in hold})} · "
          f"raizes: {len({x['_raiz'] for x in hold})} · tuplas: {len(hold)}")
    print(f"TREINO  {len(saida_t)} = {len(treino)} tool + {min(n_txt, len(neg_t))} text")
    print(f"  ferramentas: {len({x['ferramenta'] for x in treino})}")
    print()
    print("top ferramentas do holdout:")
    for t, n in Counter(x["ferramenta"] for x in hold).most_common(8):
        print(f"  {t:32} {n:4} = {n/len(hold):5.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
