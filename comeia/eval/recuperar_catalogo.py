"""Recuperação em dois passos: filtra o catálogo ANTES de mostrar ao modelo.

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-27, curva de catálogo:

    catalogo   350M ferram   150M ferram   350M recusa   150M recusa
        1-6       80,0%         71,8%         82,5%        78,4%
         15       48,5%         39,4%         82,5%        78,4%

**"Alguma ferramenta serve?" e' PLANO** (0,7 pp de amplitude em 15 pontos, nos dois modelos).
**"Qual delas?" desaba 31,5 pp.** E escalar nao conserta: queda relativa 39% (350M) contra 45%
(150M), com queda absoluta praticamente igual.

Se o gargalo e' *selecionar entre muitos*, entao **reduzir o numero de candidatos antes de
perguntar** deveria devolver o desempenho — sem tocar no modelo. E' o unico caminho que sobrou
depois de fechar quantidade de negativos, diversidade deles e tamanho do modelo.

## O desenho

Passo 1: um recuperador **lexical e deterministico** pontua cada ferramenta do catalogo contra
o pedido e devolve as k melhores. Passo 2: o modelo recebe so' essas k.

⚠️ **O TETO E' O RECALL@k**, nao o modelo. Se a ferramenta correta nao sobreviver ao filtro, o
caso vira impossivel por construcao — o gargalo so' se MUDA de lugar, do modelo para o
recuperador. Por isso `--recall` mede isso primeiro, e sozinho.

⭐ Pontuacao: sobreposicao de palavras entre o pedido e a declaracao da ferramenta (nome +
descricao + nomes de argumento), com peso IDF sobre o proprio catalogo — palavra que aparece em
todas as ferramentas nao discrimina e pesa ~0.

⚠️ Isto NAO e' o "catalogo hierarquico com o modelo escolhendo a categoria": aquilo exigiria o
modelo emitir categoria, e ele nunca foi treinado para isso. Sao experimentos diferentes.

Uso:
    python comeia/eval/recuperar_catalogo.py --recall            # so' o teto
    python comeia/eval/recuperar_catalogo.py --montar --k 5
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
NL = chr(10)
RX_TOOL = re.compile(r"^- (\w+):", re.M)

# palavras funcionais que aparecem em quase todo pedido e nao discriminam
PARE = set("""a o as os um uma de do da dos das em no na nos nas para por com sem sobre
e ou que qual quais me meu minha eu voce voce's pode poderia gostaria preciso quero
favor ajudar ajuda isso isto esse essa aquele por favor obrigado ola oi bom dia""".split())


def nz(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def palavras(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9_]{2,}", nz(t)) if w not in PARE}


def blocos(sistema: str) -> dict[str, str]:
    """{ferramenta: bloco completo da declaracao} — reaproveita o formato do prompt."""
    out: dict[str, list[str]] = {}
    atual = None
    for ln in (sistema or "").splitlines():
        m = re.match(r"^- (\w+):", ln)
        if m:
            atual = m.group(1)
            out[atual] = [ln]
            continue
        if atual is None:
            continue
        if ln.strip().startswith(("args:", "obrigatorios:", "opcionais:")):
            out[atual].append(ln)
        elif not ln.strip():
            atual = None
    return {k: NL.join(v) for k, v in out.items()}


def ranquear(pedido: str, decl: dict[str, str], k: int) -> list[str]:
    """As k ferramentas mais parecidas com o pedido, por sobreposicao com peso IDF."""
    toks = {n: palavras(b) for n, b in decl.items()}
    N = len(toks)
    df: Counter = Counter()
    for s in toks.values():
        df.update(s)
    # ⭐ palavra presente em TODAS as ferramentas do catalogo nao discrimina: idf -> 0
    idf = {w: math.log((N + 1) / (c + 0.5)) for w, c in df.items()}
    p = palavras(pedido)
    nota = {n: sum(idf.get(w, 0.0) for w in (s & p)) for n, s in toks.items()}
    return sorted(nota, key=lambda n: (-nota[n], n))[:k]


def carregar(fonte: Path) -> list[dict]:
    return [json.loads(l) for l in fonte.read_text(encoding="utf-8").splitlines() if l.strip()]


def recall(fonte: Path, ks: list[int]) -> int:
    linhas = carregar(fonte)
    tot = 0
    acerto = {k: 0 for k in ks}
    tam = Counter()
    for r in linhas:
        if r.get("kind") != "tool_call":
            continue
        sist = next((m["content"] for m in r["prompt"] if m["role"] == "system"), "")
        decl = blocos(sist)
        certa = json.loads(r["completion"][0]["content"])["tool"]
        if certa not in decl:
            continue
        ped = " ".join(m["content"] for m in r["prompt"] if m["role"] != "system")
        tot += 1
        tam[len(decl)] += 1
        ordem = ranquear(ped, decl, max(ks))
        for k in ks:
            if certa in ordem[:k]:
                acerto[k] += 1
    print(f"{fonte.name}: {tot} casos · catalogo {dict(tam)}")
    print(f"  🔴 TETO da recuperacao — se a correta nao sobreviver, o caso e' impossivel:")
    for k in ks:
        print(f"     recall@{k:<2} = {acerto[k]}/{tot} = {acerto[k]/tot:6.1%}")
    return 0


def montar(fonte: Path, k: int) -> int:
    linhas = carregar(fonte)
    saida = []
    st: Counter = Counter()
    for r in linhas:
        sist_i = next((i for i, m in enumerate(r["prompt"]) if m["role"] == "system"), None)
        if sist_i is None:
            saida.append(r)
            continue
        sist = r["prompt"][sist_i]["content"]
        decl = blocos(sist)
        if len(decl) <= k:
            saida.append(r)
            st["catalogo ja' menor que k"] += 1
            continue
        ped = " ".join(m["content"] for m in r["prompt"] if m["role"] != "system")
        escolhidas = ranquear(ped, decl, k)
        if r.get("kind") == "tool_call":
            certa = json.loads(r["completion"][0]["content"])["tool"]
            st["correta SOBREVIVEU" if certa in escolhidas else "🔴 correta FILTRADA FORA"] += 1
        # 🔴 cabecalho e rodape preservados byte a byte (ver catalogo_maior.py)
        m_cab = re.search("^FERRAMENTAS[^" + NL + "]*:" + NL, sist, re.M)
        if not m_cab:
            saida.append(r)
            continue
        cab, resto = sist[:m_cab.end()], sist[m_cab.end():]
        rodape = resto.partition(NL + NL)[2]
        corpo = NL.join(decl[x] for x in escolhidas)
        novo = (cab + corpo + NL + NL + rodape).rstrip() + NL
        pr = [({**m, "content": novo} if i == sist_i else dict(m))
              for i, m in enumerate(r["prompt"])]
        saida.append({**r, "prompt": pr})
    p = PROC / f"{fonte.stem.replace('.eval','')}_top{k}.eval.jsonl"
    p.write_text("".join(json.dumps(x, ensure_ascii=False) + NL for x in saida),
                 encoding="utf-8")
    print(f"{p.name}: {len(saida)} linhas")
    for kk, v in st.most_common():
        print(f"  {kk:32} {v}")
    return 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", type=Path, default=PROC / "holdout_cat15.eval.jsonl")
    ap.add_argument("--recall", action="store_true")
    ap.add_argument("--montar", action="store_true")
    ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    if a.recall:
        return recall(a.fonte, [1, 3, 5, 8])
    if a.montar:
        return montar(a.fonte, a.k)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
