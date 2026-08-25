"""Balanceia o TAMANHO DO CATALOGO entre positivos e negativos.

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-25, no treino do e8:

    POSITIVOS (chamam):  1 ferramenta 5777 · 2 ferramentas 1617
    NEGATIVOS (recusam): 6 ferramentas 4617
    SOBREPOSICAO: 0 de 12.011 = 0,0%

**O tamanho do catalogo separa "chamar" de "recusar" com precisao perfeita.** O modelo nunca
precisou aprender *"alguma ferramenta atende o pedido?"* — bastava contar linhas. E ele
aprendeu isso:

    catalogo  1 ->  100% emitiu chamada ·   0% recusou
    catalogo  5 ->    0% emitiu chamada ·  85% recusou
    catalogo 10 ->    0% ·  85%          (penhasco entre 1 e 5, PLATO depois)
    catalogo 15 ->    0% ·  84%

Penhasco seguido de plato nao e' dificuldade crescente — e' chave liga/desliga.

⚠️ **E dois numeros que eu reportei com entusiasmo eram este defeito:** o over-calling de 0,0%
(todo negativo tinha 6 ferramentas, o modelo recusa tudo com 6, logo zero POR CONSTRUCAO) e a
"selecao de ferramenta que generaliza, 96,9%" (medida onde 77% dos casos tinham UMA ferramenta
— emitir a unica presente nao e' selecionar).

⚠️ O holdout herdou a mesma construcao (pos 1-2, neg 6, sobreposicao 0%), entao **a regua nunca
teve como mostrar isso**. Foi preciso construir a variante que ela nao continha.

## O desenho

N ∈ {1..6} para as DUAS classes, sorteado da MESMA distribuicao.

- **negativo**: SUBAMOSTRA das 6 ferramentas que ele ja' tinha. Elas sao verificadamente
  incapazes de atender o pedido, entao qualquer subconjunto tambem e'.
  🔴 Adicionar distrator a um negativo seria arriscado: um sorteio infeliz traria uma
  ferramenta que ATENDE, e eu fabricaria negativos falsos.
- **positivo**: a ferramenta correta + distratores de raiz semantica diferente.

⚠️ Consequencia declarada: catalogos **acima de 6** continuam fora da distribuicao de treino.
A varredura em cat10/cat15 mede extrapolacao, e tem de ser lida como tal.

Uso:
    python comeia/data/balancear_catalogo.py --conferir
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "eval"))
from catalogo_maior import blocos_do_sistema, colher_pool, raiz_de   # noqa: E402

PROC = RAIZ / "data" / "processed"
NL = chr(10)
RX_TOOL = re.compile(r"^- (\w+):", re.M)
TAMANHOS = [1, 2, 3, 4, 5, 6]


def cabecalho(s: str) -> tuple[str, str] | None:
    """(cabecalho ate' a linha 'FERRAMENTAS...:', rodape). Preservados BYTE A BYTE.

    🔴 Reconstruir prompt e' mexer no estimulo. Ao inserir distratores eu reescrevi o
    cabecalho como "FERRAMENTAS DISPONIVEIS:" — sem o acento — e mudei os 728 prompts.
    O que nao for o objeto do experimento tem de sair identico, e isso se VERIFICA.
    """
    m = re.search("^FERRAMENTAS[^" + NL + "]*:" + NL, s or "", re.M)
    if not m:
        return None
    resto = s[m.end():]
    return s[:m.end()], resto.partition(NL + NL)[2]


def remontar(s: str, blocos: list[str]) -> str | None:
    cr = cabecalho(s)
    if cr is None:
        return None
    cab, rodape = cr
    return (cab + NL.join(blocos) + NL + NL + rodape).rstrip() + NL


def processar(fonte: Path, saida: Path, pool: dict[str, str], seed: int) -> Counter:
    raizes: dict[str, list[str]] = {}
    for nome in pool:
        raizes.setdefault(raiz_de(nome), []).append(nome)
    rnd = random.Random(seed)
    st: Counter = Counter()
    fora = []
    for ln in fonte.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        i_s = next((k for k, m in enumerate(r["prompt"]) if m["role"] == "system"), None)
        if i_s is None:
            fora.append(r)
            st["sem system prompt"] += 1
            continue
        s = r["prompt"][i_s]["content"]
        orig = blocos_do_sistema(s)
        if not orig:
            fora.append(r)
            st["catalogo ilegivel"] += 1
            continue
        n = rnd.choice(TAMANHOS)
        positivo = r.get("kind") == "tool_call"
        if positivo:
            certa = json.loads(r["completion"][0]["content"]).get("tool")
            if certa not in orig:
                fora.append(r)
                st["ferramenta correta fora do catalogo"] += 1
                continue
            escolhidos = [certa]
            proibidas = {raiz_de(x) for x in orig}
            cands = [x for rz, xs in raizes.items() if rz not in proibidas for x in xs]
            rnd.shuffle(cands)
            for x in cands:
                if len(escolhidos) >= n:
                    break
                if raiz_de(x) in proibidas:
                    continue
                proibidas.add(raiz_de(x))
                escolhidos.append(x)
            blocos = [orig.get(x) or pool[x] for x in escolhidos]
        else:
            # 🔴 SO' SUBAMOSTRA. Adicionar distrator a um negativo pode trazer uma ferramenta
            #    que ATENDE o pedido — e eu fabricaria um negativo falso.
            nomes = list(orig)
            rnd.shuffle(nomes)
            blocos = [orig[x] for x in nomes[:min(n, len(nomes))]]
        rnd.shuffle(blocos)
        novo = remontar(s, blocos)
        if novo is None:
            fora.append(r)
            st["cabecalho nao reconhecido"] += 1
            continue
        pr = [({**m, "content": novo} if k == i_s else dict(m))
              for k, m in enumerate(r["prompt"])]
        fora.append({**r, "prompt": pr})
        st[("pos" if positivo else "neg") + f" n={len(blocos)}"] += 1
    saida.write_text("".join(json.dumps(x, ensure_ascii=False) + NL for x in fora),
                     encoding="utf-8")
    return st


def conferir(caminho: Path, tok=None) -> int:
    pos: Counter = Counter()
    neg: Counter = Counter()
    longos = 0
    linhas = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    for r in linhas:
        s = next((m["content"] for m in r["prompt"] if m["role"] == "system"), "")
        n = len(RX_TOOL.findall(s)) if s else -1
        (pos if r.get("kind") == "tool_call" else neg)[n] += 1
        if tok is not None:
            t = len(tok(" ".join(m["content"] for m in r["prompt"])
                        + " " + r["completion"][0]["content"])["input_ids"])
            if t > 2048:
                longos += 1
    tot = sum(pos.values()) + sum(neg.values())
    print(f"{caminho.name}: {tot} exemplos")
    print(f"  positivos {dict(sorted(pos.items()))}")
    print(f"  negativos {dict(sorted(neg.items()))}")
    # 🔴 A METRICA QUE IMPORTA: o tamanho do catalogo consegue prever a classe?
    #    Regra otima "chame se n <= k": qual o melhor acerto que ela alcanca?
    tp, tn = sum(pos.values()), sum(neg.values())
    melhor = max((sum(v for k, v in pos.items() if k <= c)
                  + sum(v for k, v in neg.items() if k > c)) / tot
                 for c in range(0, 20))
    base = max(tp, tn) / tot
    print(f"  ⭐ melhor regra 'chame se n<=k': {melhor:.1%}  (chutar a classe maior: {base:.1%})")
    if melhor > base + 0.05:
        print("  🔴 o TAMANHO ainda prediz a classe — o atalho continua disponivel")
        return 1
    print("  [OK] o tamanho do catalogo nao separa as classes")
    if tok is not None:
        print(f"  exemplos acima de 2048 tokens (seriam DESCARTADOS em silencio): {longos}")
        if longos:
            return 1
    return 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260825)
    ap.add_argument("--conferir", action="store_true")
    a = ap.parse_args()
    pool = colher_pool([PROC / "gigaverbo_ferramenta.jsonl",
                        PROC / "treino_ferramenta.jsonl",
                        PROC / "holdout_ferramenta.eval.jsonl"])
    print(f"pool: {len(pool)} ferramentas")
    tok = None
    if a.conferir:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained("BrCamp/bee-350m-pt-base")
    r = 0
    for ent, sai in ((PROC / "treino_ferramenta.jsonl", PROC / "treino_balanceado.jsonl"),
                     (PROC / "holdout_ferramenta.eval.jsonl",
                      PROC / "holdout_balanceado.eval.jsonl")):
        st = processar(ent, sai, pool, a.seed)
        desc = {k: v for k, v in st.items() if not k.startswith(("pos ", "neg "))}
        if desc:
            print(f"  ⚠️ {desc}")
        if a.conferir:
            r |= conferir(sai, tok)
        print()
    return r


if __name__ == "__main__":
    raise SystemExit(main())
