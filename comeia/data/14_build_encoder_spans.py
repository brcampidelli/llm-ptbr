"""Deriva spans BIO para o baseline de ENCODER — a objeção de 2026-07-25, medida.

⚠️ A OBJEÇÃO QUE ESTE SCRIPT EXISTE PARA TESTAR. Em 2026-07-25 registrei contra o
próprio plano: extração estruturada é classicamente tarefa de ENCODER, e um modelo
de 110–300M faria em CPU por ~1/40 do custo do nosso 4B. Nunca medi. Se o encoder
ganhar, estou defendendo elegância arquitetural contra economia real.

ESCOPO DELIBERADO — só campos EXTRATIVOS. A objeção vale para o que se COPIA do
documento. Campo inferido (enum, booleano, data normalizada) não é span: exigiria
cabeças de classificação separadas por campo, e aí o encoder deixa de ser "110M
barato" e vira um sistema de N cabeças. Testo a objeção onde ela se aplica, e
declaro o resto. Previsão registrada ANTES de medir: o encoder deve ir bem nos
extrativos e não competir nos inferidos — se for isso, a conclusão honesta é
HÍBRIDO (encoder para copiar, decoder para inferir), não substituição.

⭐ O QUE TORNA ISTO POSSÍVEL: a groundedness. Todo valor marcado `grounded` foi
verificado como presente no documento, então o span EXISTE e dá para localizá-lo
automaticamente. Sem essa garantia, derivar spans de pares (documento, JSON) seria
adivinhação.

⚠️ MESMO SPLIT do decoder — o `bucket()` (sha1 do documento) é importado do
13_build_extraction_splits, não reimplementado. Se os dois usassem splits
diferentes, a comparação encoder × adapter não valeria nada.

Uso:
    python data/14_build_encoder_spans.py
    python data/14_build_encoder_spans.py --report-misses 10   # ver o que não achou

Saída: data/processed/encoder_ner.{train,eval}.jsonl
       ({tokens: [...], labels: [...], lang, schema})
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data"))
from config import PROCESSED_DIR, RAW_DIR, ensure_dirs  # noqa: E402
from common import read_jsonl, write_jsonl  # noqa: E402
from schema_check import load_schemas, norm_texto  # noqa: E402

_spec = importlib.util.spec_from_file_location("s13", ROOT / "data" / "13_build_extraction_splits.py")
_s13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s13)
bucket = _s13.bucket                      # ⚠️ MESMO split do decoder

IN_HARD = RAW_DIR / "extraction_hard.jsonl"
IN_EASY = RAW_DIR / "extraction_easy.jsonl"
OUT_TRAIN = PROCESSED_DIR / "encoder_ner.train.jsonl"
OUT_EVAL = PROCESSED_DIR / "encoder_ner.eval.jsonl"

# Tokenização por palavra COM offsets — o encoder precisa alinhar rótulo a token.
_TOK = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenizar(texto: str) -> list[tuple[str, int, int]]:
    return [(m.group(), m.start(), m.end()) for m in _TOK.finditer(texto)]


def achar_span(valor: str, documento: str) -> tuple[int, int] | None:
    """Offsets (início, fim) do valor no documento. None se não achar.

    Três tentativas, da mais estrita para a mais tolerante — porque a
    groundedness foi verificada com `norm_texto` (casefold + sem acento + espaço
    colapsado), então o valor pode não bater byte a byte com o documento.
    """
    if not isinstance(valor, str) or not valor.strip():
        return None
    i = documento.find(valor)                                  # 1. literal
    if i >= 0:
        return i, i + len(valor)
    low_d, low_v = documento.casefold(), valor.casefold()       # 2. sem caixa
    i = low_d.find(low_v)
    if i >= 0:
        return i, i + len(valor)
    # 3. sem acento e com espaço flexível — reconstrói a posição no original
    alvo = norm_texto(valor)
    if not alvo:
        return None
    padrao = r"\s+".join(re.escape(p) for p in alvo.split())
    m = re.search(padrao, norm_texto_pos(documento)[0], re.IGNORECASE)
    if not m:
        return None
    mapa = norm_texto_pos(documento)[1]
    ini, fim = mapa[m.start()], mapa[min(m.end(), len(mapa) - 1)]
    return ini, fim


def norm_texto_pos(texto: str) -> tuple[str, list[int]]:
    """Versão normalizada + mapa de posição para o texto ORIGINAL.

    Necessário porque `norm_texto` colapsa espaço e remove acento: sem o mapa, um
    match na versão normalizada não diz onde recortar no original, e o span sairia
    deslocado — rótulo no token errado é pior que rótulo ausente.
    """
    import unicodedata
    out, mapa = [], []
    espaco = False
    for i, c in enumerate(texto):
        d = "".join(x for x in unicodedata.normalize("NFD", c)
                    if unicodedata.category(x) != "Mn").casefold()
        if c.isspace():
            if espaco:
                continue
            espaco = True
            out.append(" ")
            mapa.append(i)
            continue
        espaco = False
        for ch in d or c:
            out.append(ch)
            mapa.append(i)
    mapa.append(len(texto))
    return "".join(out), mapa


def rotular(documento: str, extracao: dict, schema: dict) -> tuple[list[str], list[str], int, int]:
    """(tokens, labels BIO, achados, tentados) — só campos `grounded` de texto."""
    toks = tokenizar(documento)
    labels = ["O"] * len(toks)
    achados = tentados = 0
    for nome, spec in schema["fields"].items():
        if not spec.get("grounded") or spec["type"] not in ("string", "array[string]"):
            continue
        v = extracao.get(nome)
        if v is None:
            continue
        for valor in (v if isinstance(v, list) else [v]):
            tentados += 1
            span = achar_span(str(valor), documento)
            if not span:
                continue
            ini, fim = span
            dentro = [i for i, (_, a, b) in enumerate(toks) if a >= ini and b <= fim]
            if not dentro:
                continue
            achados += 1
            labels[dentro[0]] = f"B-{nome}"
            for i in dentro[1:]:
                labels[i] = f"I-{nome}"
    return [t[0] for t in toks], labels, achados, tentados


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", type=int, default=140)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--report-misses", type=int, default=5)
    args = ap.parse_args()

    ensure_dirs()
    schemas = load_schemas()
    itens = list(read_jsonl(IN_HARD)) + list(read_jsonl(IN_EASY))
    if not itens:
        print(f"ERRO: rode o 12_filter_extraction antes ({IN_HARD.name} vazio).",
              file=sys.stderr)
        return 1

    # ⚠️ MESMO corte por hash do decoder, para a comparação ser válida
    por_lang: dict[str, list] = defaultdict(list)
    for r in itens:
        por_lang[r["lang"]].append(r)

    treino, evalset = [], []
    achados = tentados = 0
    misses: list[tuple[str, str]] = []
    rotulos = Counter()

    for lang, rows in por_lang.items():
        cota = min(len(rows), max(1, args.holdout // max(1, len(por_lang))))
        corte = round(1000 * cota / max(1, len(rows)))
        for r in rows:
            sch = schemas[r["schema"]]
            toks, labs, a, t = rotular(r["documento"], r["extracao"], sch)
            achados += a
            tentados += t
            if a < t and len(misses) < args.report_misses:
                faltando = [str(v) for k, spec in sch["fields"].items()
                            if spec.get("grounded") and k in r["extracao"]
                            for v in ([r["extracao"][k]] if not isinstance(r["extracao"][k], list)
                                      else r["extracao"][k])
                            if achar_span(str(v), r["documento"]) is None]
                if faltando:
                    misses.append((faltando[0][:50], r["documento"][:60]))
            if not toks:
                continue
            rotulos.update(l for l in labs if l != "O")
            reg = {"tokens": toks, "labels": labs, "lang": lang, "schema": r["schema"]}
            (evalset if bucket(r["documento"], args.seed) < corte else treino).append(reg)

    write_jsonl(OUT_TRAIN, treino)
    write_jsonl(OUT_EVAL, evalset)

    print(f"itens        : {len(itens)}  →  treino {len(treino)} · eval {len(evalset)}")
    print(f"idiomas eval : {dict(sorted(Counter(r['lang'] for r in evalset).items()))}")
    print(f"tipos de rotulo: {len(rotulos)}  (B-/I- por campo extrativo)")
    print()
    print(f"⭐ COBERTURA DOS SPANS: {achados}/{tentados} = {achados/max(1,tentados):.1%}")
    if achados / max(1, tentados) < 0.9:
        print("   ⚠️ abaixo de 90%: o encoder treinaria com rotulo faltando e a")
        print("   comparacao ficaria injusta CONTRA ele. Investigar antes de treinar.")
    else:
        print("   ✅ alta o bastante para a comparacao ser justa com o encoder.")
    if misses:
        print(f"\nvalores nao localizados ({len(misses)} amostras):")
        for v, d in misses:
            print(f"   {v!r}\n      no doc: {d!r}")
    print(f"\n{OUT_TRAIN}\n{OUT_EVAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
