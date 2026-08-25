"""Amplia o CATALOGO do prompt — o eixo que o instrumento nao tocava.

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-25, no holdout de ferramenta inedita:

    FERRAMENTAS no catalogo do prompt   min 1 · p50 1 · p90 2 · max 2
    558 casos com UMA ferramenta · 170 com duas

Ou seja: quando reportei **"96,9% de acerto em ferramentas nunca vistas, o modelo le' o
catalogo"**, em 77% dos casos havia **uma unica ferramenta** la' dentro. Escolher certo entre
uma nao e' selecao — e' emitir a unica que existe. O instrumento **nao distingue** "le' o
catalogo e escolhe" de "emite a unica presente", e por isso nao produz evidencia sobre selecao.

⭐ E explica o over-calling de 0,0%: com uma ferramenta e um pedido que casa, nao ha' confusao
possivel. O numero era bonito e vazio.

## O desenho

Mesmos itens, mesma referencia, **so' o catalogo cresce**: a ferramenta correta continua la' e
entram N-1 distratores. Se a selecao realmente generaliza, a curva e' plana; se o modelo estava
emitindo a unica opcao, ela desaba.

⚠️ **Distrator tem de ser INCAPAZ de atender o pedido**, senao a referencia vira ambigua e a
queda mede ambiguidade, nao selecao. Criterio: raiz semantica (familia do verbo, objeto)
diferente da referencia E de qualquer ferramenta ja' no catalogo original.

⚠️ **Orcamento de contexto.** O prompt cresce ~25 palavras por ferramenta. O avaliador trunca
em 1536 tokens; truncar o catalogo apagaria justamente a ferramenta correta em parte dos casos
e a queda seria de truncamento, nao de selecao. Por isso `--conferir` mede o comprimento em
TOKENS de cada variante e recusa N que estoure.

Uso:
    python comeia/eval/catalogo_maior.py --tamanhos 1 5 10 25 --conferir
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
sys.path.insert(0, str(RAIZ / "data"))

PROC = RAIZ / "data" / "processed"
RX_TOOL = re.compile(r"^- (\w+):")

FAMILIAS = {
    "BUSCAR": r"^(search|find|lookup|browse|query|discover)_",
    "OBTER": r"^(get|fetch|retrieve|check|show|list|read|view)_",
    "CRIAR": r"^(create|make|generate|add|new|register|schedule|book|post|set)_",
    "CALCULAR": r"^(calculate|compute|convert|estimate)_",
    "ENVIAR": r"^(send|share|publish|submit|order|deliver)_",
    "ALTERAR": r"^(update|edit|modify|change|delete|remove|cancel)_",
    "EXECUTAR": r"^(play|run|start|stop|execute|translate|analyze|track)_",
}


def raiz_de(tool: str) -> str:
    t = tool.lower()
    fam, resto = "OUTRO", t
    for nome, rx in FAMILIAS.items():
        m = re.match(rx, t)
        if m:
            fam, resto = nome, t[m.end():]
            break
    resto = re.sub(r"_(amount|value|total|price|cost|info|details|data|list|result|rate|"
                   r"payment|status)$", "", resto)
    resto = re.sub(r"(ies)$", "y", resto)
    resto = re.sub(r"(?<![aeiou])s$", "", resto)
    return fam + ":" + re.sub(r"[_\s]+", "", resto)


def blocos_do_sistema(sistema: str) -> dict[str, str]:
    """{ferramenta: bloco de texto completo da declaracao}."""
    linhas = (sistema or "").splitlines()
    out: dict[str, list[str]] = {}
    atual = None
    for ln in linhas:
        m = RX_TOOL.match(ln)
        if m:
            atual = m.group(1)
            out[atual] = [ln]
            continue
        if atual is None:
            continue
        if ln.strip().startswith(("args:", "obrigatorios:", "opcionais:")):
            out[atual].append(ln)
        elif ln.strip() == "":
            atual = None
    return {k: "\n".join(v) for k, v in out.items()}


def colher_pool(caminhos: list[Path]) -> dict[str, str]:
    """Todas as declaracoes de ferramenta que existem no corpus, por nome."""
    pool: dict[str, str] = {}
    for c in caminhos:
        if not c.exists():
            continue
        for ln in c.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            r = json.loads(ln)
            ms = r.get("messages") or (list(r.get("prompt") or [])
                                       + list(r.get("completion") or []))
            s = next((m["content"] for m in ms if m.get("role") == "system"), None)
            for nome, bloco in blocos_do_sistema(s or "").items():
                pool.setdefault(nome, bloco)
    return pool


def montar(fonte: Path, tamanhos: list[int], pool: dict[str, str], seed: int,
           conferir: bool) -> int:
    linhas = [json.loads(l) for l in fonte.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    raizes_pool: dict[str, list[str]] = {}
    for nome in pool:
        raizes_pool.setdefault(raiz_de(nome), []).append(nome)
    print(f"pool de distratores: {len(pool)} ferramentas · {len(raizes_pool)} raizes")

    tok = None
    if conferir:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained("BrCamp/bee-350m-pt-base")

    for n in tamanhos:
        rnd = random.Random(seed + n)
        saida, comp, truncados = [], [], 0
        for r in linhas:
            if r.get("kind") != "tool_call":
                saida.append(r)
                continue
            s = next((m["content"] for m in r["prompt"] if m["role"] == "system"), "")
            orig = blocos_do_sistema(s)
            proibidas = {raiz_de(x) for x in orig}
            escolhidas = list(orig)
            # 🔴 distrator de raiz PROIBIDA tornaria a referencia ambigua
            cands = [x for rz, xs in raizes_pool.items() if rz not in proibidas for x in xs]
            rnd.shuffle(cands)
            for x in cands:
                if len(escolhidas) >= n:
                    break
                if raiz_de(x) in proibidas:
                    continue
                proibidas.add(raiz_de(x))
                escolhidas.append(x)
            rnd.shuffle(escolhidas)
            corpo = "\n".join(orig.get(x) or pool[x] for x in escolhidas)
            # 🔴 CABECALHO E RODAPE PRESERVADOS BYTE A BYTE. A v1 reescrevia o cabecalho
            #    como "FERRAMENTAS DISPONIVEIS:" — sem o acento de DISPONIVEIS. Era o unico
            #    caractere que mudava em 635 dos 728 prompts, e o acerto de ferramenta caiu
            #    de 98,0% para 85,9%. DOZE pontos por um acento.
            #    ⭐ Reconstruir prompt e' mexer no estimulo: tudo que nao for o objeto do
            #    experimento tem de sair IDENTICO, e isso se verifica, nao se supoe.
            NL = chr(10)
            m_cab = re.search("^FERRAMENTAS[^" + NL + "]*:" + NL, s, re.M)
            if not m_cab:
                saida.append(r)
                continue
            cab, resto = s[:m_cab.end()], s[m_cab.end():]
            rodape = resto.partition(chr(10) + chr(10))[2]
            novo = (cab + corpo + chr(10) + chr(10) + rodape).rstrip() + chr(10)
            pr = [({**m, "content": novo} if m["role"] == "system" else dict(m))
                  for m in r["prompt"]]
            saida.append({**r, "prompt": pr})
            comp.append(len(escolhidas))
            if tok is not None:
                nt = len(tok(novo + " ".join(m["content"] for m in pr
                                             if m["role"] != "system"))["input_ids"])
                if nt > 1536:
                    truncados += 1
        p = PROC / f"holdout_cat{n}.eval.jsonl"
        p.write_text("".join(json.dumps(x, ensure_ascii=False) + chr(10) for x in saida),
                     encoding="utf-8")
        med = sum(comp) / max(1, len(comp))
        print(f"{p.name}: {len(comp)} casos · catalogo medio {med:.1f} "
              f"(pedido {n}) · min {min(comp)} max {max(comp)}", end="")
        if tok is not None:
            print(f" · ESTOURAM 1536 tokens: {truncados}"
                  + ("  🔴 NAO USAR" if truncados else "  [OK]"))
        else:
            print()
    return 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", type=Path, default=PROC / "holdout_ferramenta.eval.jsonl")
    ap.add_argument("--tamanhos", type=int, nargs="+", default=[1, 5, 10, 25])
    ap.add_argument("--seed", type=int, default=20260825)
    ap.add_argument("--conferir", action="store_true",
                    help="mede o comprimento em TOKENS e recusa N que estoure o truncamento")
    a = ap.parse_args()
    pool = colher_pool([PROC / "gigaverbo_ferramenta.jsonl", a.fonte,
                        PROC / "treino_ferramenta.jsonl"])
    if len(pool) < 100:
        print(f"ERRO: pool de so' {len(pool)} ferramentas", file=sys.stderr)
        return 2
    return montar(a.fonte, a.tamanhos, pool, a.seed, a.conferir)


if __name__ == "__main__":
    raise SystemExit(main())
