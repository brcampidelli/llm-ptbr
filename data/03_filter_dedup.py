"""Fase 2.3 — Filtro de qualidade + deduplicação.

Junta todos os data/raw/*.jsonl, aplica filtros de qualidade e remove duplicatas
(exatas e aproximadas), gravando data/processed/clean.jsonl.

Filtros:
  - tamanho de resposta dentro da faixa
  - "portuguesidade" mínima (pega item que ficou em inglês)
  - resposta que é recusa/vazia/eco da pergunta
  - dedup exato (hash do texto normalizado)
  - dedup aproximado (Jaccard de n-gramas, via índice invertido — evita O(n²))

Uso:
    python data/03_filter_dedup.py
    python data/03_filter_dedup.py --report-only
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (  # noqa: E402
    MAX_RESPONSE_CHARS,
    MIN_PT_RATIO,
    MIN_RESPONSE_CHARS,
    NEAR_DUP_THRESHOLD,
    PROCESSED_DIR,
    RAW_DIR,
    ensure_dirs,
)
from common import jaccard, ngrams, normalize, pt_ratio, read_jsonl, write_jsonl  # noqa: E402

OUT = PROCESSED_DIR / "clean.jsonl"

# Respostas que não ensinam nada — descartar.
REFUSAL_MARKERS = (
    "não posso ajudar", "nao posso ajudar", "como modelo de linguagem",
    "i cannot", "i'm sorry", "as an ai language model",
)

# Tarefas cuja RESPOSTA deve sair em outro idioma — o filtro de português não se
# aplica a elas (senão perdemos toda a capacidade de tradução).
TRANSLATE_OUT = re.compile(
    r"traduz(a|ir).{0,40}\bpara\s+(o\s+)?(ingl[eê]s|espanhol|franc[eê]s|alem[aã]o|italiano|japon[eê]s|chin[eê]s)"
    r"|translate.{0,30}(into|to)\s+english",
    re.IGNORECASE,
)


def quality_reason(row: dict) -> str | None:
    """Retorna o motivo da rejeição, ou None se o item passa."""
    instr = (row.get("instruction") or "").strip()
    resp = (row.get("response") or "").strip()

    if not instr or not resp:
        return "campo vazio"
    if len(resp) < MIN_RESPONSE_CHARS:
        return f"resposta curta ({len(resp)} chars)"
    if len(resp) > MAX_RESPONSE_CHARS:
        return f"resposta longa ({len(resp)} chars)"
    if normalize(resp) == normalize(instr):
        return "resposta e eco da pergunta"
    low = resp.lower()
    if any(m in low for m in REFUSAL_MARKERS):
        return "recusa/boilerplate de assistente"
    # Tradução para outro idioma: a resposta NÃO deve estar em português.
    if not TRANSLATE_OUT.search(instr):
        ratio = pt_ratio(resp)  # mede só a prosa; código é removido
        if ratio < MIN_PT_RATIO:
            return f"portuguesidade baixa ({ratio:.2f})"
    return None


def exact_key(row: dict) -> str:
    blob = normalize(row.get("instruction", "")) + "||" + normalize(row.get("response", ""))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-only", action="store_true", help="nao grava, so mostra as estatisticas")
    ap.add_argument("--ngram", type=int, default=5, help="n-grama do dedup aproximado")
    args = ap.parse_args()

    ensure_dirs()
    raw_files = sorted(RAW_DIR.glob("*.jsonl"))
    raw_files = [p for p in raw_files if not p.name.endswith(".rejects.jsonl")]
    if not raw_files:
        print(f"Nenhum .jsonl em {RAW_DIR}. Rode os scripts 01/02 primeiro.")
        return 1

    print(f"Lendo {len(raw_files)} arquivo(s) de {RAW_DIR}:")
    rows: list[dict] = []
    for p in raw_files:
        n = 0
        for row in read_jsonl(p):
            rows.append(row)
            n += 1
        print(f"  {p.name}: {n}")
    print(f"total bruto: {len(rows)}")

    # --- 1) filtro de qualidade ---
    reasons: dict[str, int] = defaultdict(int)
    kept: list[dict] = []
    for row in rows:
        why = quality_reason(row)
        if why:
            reasons[why.split("(")[0].strip()] += 1
        else:
            kept.append(row)
    print(f"\napos filtro de qualidade: {len(kept)} (removidos {len(rows) - len(kept)})")
    for why, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"    - {why}: {n}")

    # --- 2) dedup exato ---
    seen: set[str] = set()
    unique: list[dict] = []
    for row in kept:
        k = exact_key(row)
        if k in seen:
            continue
        seen.add(k)
        unique.append(row)
    print(f"apos dedup exato: {len(unique)} (removidos {len(kept) - len(unique)})")

    # --- 3) dedup aproximado (indice invertido por n-grama) ---
    # Só compara pares que compartilham ao menos um n-grama → evita O(n²).
    index: dict[str, list[int]] = defaultdict(list)
    grams_of: list[set[str]] = []
    final: list[dict] = []
    dropped_near = 0

    for row in unique:
        g = ngrams(row.get("instruction", "") + " " + row.get("response", ""), args.ngram)
        candidates: set[int] = set()
        for gram in g:
            candidates.update(index[gram])

        is_dup = False
        for ci in candidates:
            if jaccard(g, grams_of[ci]) >= NEAR_DUP_THRESHOLD:
                is_dup = True
                break
        if is_dup:
            dropped_near += 1
            continue

        idx = len(final)
        final.append(row)
        grams_of.append(g)
        for gram in g:
            index[gram].append(idx)

    print(f"apos dedup aproximado (Jaccard>={NEAR_DUP_THRESHOLD}): {len(final)} (removidos {dropped_near})")

    # --- resumo por fonte ---
    by_source: dict[str, int] = defaultdict(int)
    for row in final:
        by_source[row.get("source", "?")] += 1
    print("\ncomposicao final por fonte:")
    for s, n in sorted(by_source.items(), key=lambda kv: -kv[1]):
        print(f"    {s}: {n}")

    if args.report_only:
        print("\n[report-only] nada foi gravado.")
        return 0

    written = write_jsonl(OUT, final)
    print(f"\nGravado: {written} exemplos -> {OUT}")
    print("Proximo: python data/04_decontaminate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
