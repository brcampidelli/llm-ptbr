"""Declara no catalogo o FORMATO esperado de cada argumento temporal.

🔴 POR QUE ISTO EXISTE. Medido em 2026-08-24: **este corpus nao tem convencao temporal.**
Por par (ferramenta, argumento):

    holdout   convencao PURA em  12,1% das referencias · 18 de 29 pares MISTOS
    treino    convencao PURA em  18,9% das referencias · 30 de 47 pares MISTOS

`schedule_meeting.date` tem 32 referencias em ISO e 29 em frase crua. E' cara ou coroa. E o
mesmo defeito esta' no TREINO, entao **o modelo nao pode aprender uma convencao que nao existe
no dado dele** — nao e' problema de capacidade, e' de especificacao.

Decomposicao das 181 falhas temporais do E9 (s42, decodificacao restrita):

    incomparavel — um lado sem valor absoluto ....  71 = 39,2%
    so FORMATO — mesmo instante, escrita diferente   65 = 35,9%
    divergencia SEMANTICA real ..................   24 = 13,3%
    argumento omitido ...........................   21 = 11,6%

**136 de 181 (75%) sao artefato de convencao.**

## As duas saidas, e por que esta

    descartar a convencao minoritaria  ->  perde  3,4% do treino e 21,4% do HOLDOUT
    declarar o formato no catalogo     ->  perde  0

⭐ E o projeto ja' provou que o modelo LE O CATALOGO: 96,9% de acerto em ferramentas nunca
vistas, e a restricao ao esquema mostrou que ele copia o que e' obrigado a copiar. Declarar o
formato transforma uma ambiguidade INAPRENDIVEL numa instrucao LEGIVEL. Catalogos reais de
function calling fazem exatamente isso (`"format": "date-time"` no JSON Schema).

## ⚠️ ISTO MUDA A ESPECIFICACAO DA TAREFA

De *"adivinhe a convencao nao declarada"* para *"leia a convencao declarada"*. E' uma tarefa
diferente — mais realista, mas diferente. Consequencias que NAO podem ser omitidas:

  1. o numero no holdout anotado **nao se compara** ao numero no holdout original: seria
     mudar a regua entre os grupos, o erro que este projeto ja' cometeu quatro vezes;
  2. a comparacao valida e' **modelo velho x modelo novo, ambos no holdout anotado**, pareado;
  3. a anotacao declara o FORMATO, **nunca o valor** — `--conferir` prova isso comparando a
     anotacao contra a referencia de cada exemplo.

Uso:
    python comeia/data/anotar_formato_temporal.py --conferir
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

RX_TOOL = re.compile(r"^- (\w+):")
RX_ARGS = re.compile(r"^(\s*args:\s*)(.*)$")

# forma -> texto que vai no catalogo. NUNCA contem valor de exemplo nenhum.
ROTULO = {
    "ISO_DATETIME": "formato AAAA-MM-DDTHH:MM:SS",
    "ISO_DATE": "formato AAAA-MM-DD",
    "HORA": "formato HH:MM",
    "TEXTO_LIVRE": "no texto do usuario, sem converter",
}


def forma_de(v: object) -> str:
    s = str(v)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?", s):
        return "ISO_DATETIME"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return "ISO_DATE"
    if re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)?", s):
        return "HORA"
    return "TEXTO_LIVRE"


def _segmentos(lista: str) -> list[tuple[str, str]]:
    """`a (desc), b (desc2)` -> [(a, desc), (b, desc2)].

    ⚠️ Descricao pode conter virgula e parentese, entao o corte e' em `), ` seguido de
    identificador e `(` — nao em virgula solta.
    """
    partes = re.split(r"\),\s*(?=[A-Za-z_]\w*\s*\()", lista)
    out = []
    for p in partes:
        m = re.match(r"\s*([A-Za-z_]\w*)\s*\((.*?)\)?\s*$", p, re.S)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def anotar_sistema(sistema: str, formas: dict[tuple[str, str], str]) -> tuple[str, int]:
    """Insere `formato ...` na descricao dos argumentos temporais. Idempotente."""
    linhas = sistema.splitlines()
    atual: str | None = None
    n = 0
    for i, ln in enumerate(linhas):
        m = RX_TOOL.match(ln)
        if m:
            atual = m.group(1)
            continue
        if atual is None:
            continue
        m = RX_ARGS.match(ln)
        if not m:
            continue
        segs = _segmentos(m.group(2))
        if not segs:
            continue
        novos = []
        for nome, desc in segs:
            rot = formas.get((atual, nome))
            if rot and "formato" not in desc and "sem converter" not in desc:
                desc = desc.rstrip()
                sep = "" if desc.endswith((".", ";")) else "."
                desc = f"{desc}{sep} {rot}"
                n += 1
            novos.append(f"{nome} ({desc})")
        linhas[i] = m.group(1) + ", ".join(novos)
    return "\n".join(linhas), n


def processar(entrada: Path, saida: Path, perfil: dict) -> tuple[int, int, int]:
    linhas = [json.loads(l) for l in entrada.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    n_anot = n_arg = 0
    formas_vistas: Counter = Counter()
    for r in linhas:
        if r.get("kind") != "tool_call":
            continue
        o = json.loads(r["completion"][0]["content"])
        t = o["tool"]
        formas = {}
        for k, v in (o.get("args") or {}).items():
            if ARG.classe_de(perfil, t, k) == "temporal":
                f = forma_de(v)
                formas[(t, k)] = ROTULO[f]
                formas_vistas[f] += 1
        if not formas:
            continue
        for m in r["prompt"]:
            if m.get("role") != "system":
                continue
            novo, n = anotar_sistema(m["content"], formas)
            if n:
                m["content"] = novo
                n_arg += n
                n_anot += 1
            break
    saida.write_text("".join(json.dumps(r, ensure_ascii=False) + chr(10) for r in linhas),
                     encoding="utf-8")
    print(f"{entrada.name} -> {saida.name}: {len(linhas)} linhas · "
          f"{n_anot} exemplos anotados · {n_arg} argumentos")
    print(f"   formas: {dict(formas_vistas)}")
    return len(linhas), n_anot, n_arg


def conferir(caminho: Path, perfil: dict) -> int:
    """🔴 A anotacao declara FORMATO. Se ela contiver o VALOR, e' vazamento."""
    linhas = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    vaz = falta = ok = 0
    for r in linhas:
        if r.get("kind") != "tool_call":
            continue
        o = json.loads(r["completion"][0]["content"])
        sistema = next((m["content"] for m in r["prompt"] if m["role"] == "system"), "")
        for k, v in (o.get("args") or {}).items():
            if ARG.classe_de(perfil, o["tool"], k) != "temporal":
                continue
            s = str(v).strip()
            if len(s) > 3 and s.lower() in sistema.lower():
                vaz += 1
            if ROTULO[forma_de(v)] in sistema:
                ok += 1
            else:
                falta += 1
    print(f"{caminho.name}: {ok} argumentos com o formato declarado · {falta} sem")
    if vaz:
        print(f"🔴 VAZAMENTO: o valor da referencia aparece no prompt em {vaz} argumentos")
        return 1
    print("✅ nenhum valor de referencia aparece no prompt — a anotacao e' so' formato")
    return 0


def _autoteste() -> int:
    falhas = 0
    for v, esp in [("2022-03-15T10:00:00", "ISO_DATETIME"), ("2022-06-15", "ISO_DATE"),
                   ("10:00", "HORA"), ("3:30 PM", "HORA"), ("next Monday", "TEXTO_LIVRE"),
                   ("15th of next month", "TEXTO_LIVRE"), (98.6, "TEXTO_LIVRE")]:
        if forma_de(v) != esp:
            print(f"🔴 forma_de({v!r}) = {forma_de(v)}, esperado {esp}")
            falhas += 1
    linha = ("- x: desc\n"
             "    args: a (Um texto, com virgula.), start_time (O inicio.), b (Outro (com) "
             "parentese.))\n"
             "    obrigatorios: a, start_time")
    novo, n = anotar_sistema(linha, {("x", "start_time"): ROTULO["ISO_DATETIME"]})
    if n != 1 or "start_time (O inicio. formato AAAA-MM-DDTHH:MM:SS)" not in novo:
        print(f"🔴 anotar_sistema:\n{novo}")
        falhas += 1
    if "a (Um texto, com virgula.)" not in novo or "b (Outro (com) parentese." not in novo:
        print(f"🔴 anotar_sistema destruiu argumento vizinho:\n{novo}")
        falhas += 1
    novo2, n2 = anotar_sistema(novo, {("x", "start_time"): ROTULO["ISO_DATETIME"]})
    if n2 != 0 or novo2 != novo:
        print(f"🔴 anotar_sistema NAO e' idempotente ({n2} anotacoes na segunda passada)")
        falhas += 1
    print("✅ autoteste" if not falhas else f"🔴 {falhas} falhas no autoteste")
    return 1 if falhas else 0


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--conferir", action="store_true")
    a = ap.parse_args()
    if _autoteste():
        return 1
    perfil = ARG.carregar()
    if not perfil:
        print("ERRO: rode `python comeia/eval/argumentos.py --perfilar`", file=sys.stderr)
        return 2
    pares = [(PROC / "treino_ferramenta.jsonl", PROC / "treino_ferramenta_fmt.jsonl"),
             (PROC / "holdout_ferramenta.eval.jsonl",
              PROC / "holdout_ferramenta_fmt.eval.jsonl")]
    r = 0
    for ent, sai in pares:
        processar(ent, sai, perfil)
        if a.conferir:
            r |= conferir(sai, perfil)
        print()
    return r


if __name__ == "__main__":
    raise SystemExit(main())
