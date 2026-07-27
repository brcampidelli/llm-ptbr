"""Fase 2.4 — Decontaminação: remover treino que vaza os benchmarks de teste.

Esta é a etapa que torna a avaliação HONESTA. Sem ela, o modelo pode "acertar" o
ENEM/BLUEX simplesmente porque viu as questões no treino — e o número do
leaderboard vira mentira.

Método: n-grama de 13 palavras (padrão da literatura). Se um exemplo de treino
compartilha QUALQUER 13-grama com QUALQUER item dos conjuntos de teste, ele sai.

Entrada : data/processed/clean.jsonl  (saida do script 03)
Saida   : data/processed/decontaminated.jsonl
          data/processed/contaminated.jsonl  (o que foi removido — auditar!)

Uso:
    python data/04_decontaminate.py --benchmarks eval/benchmarks/*.jsonl
    python data/04_decontaminate.py --benchmarks ... --ngram 13
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DECONTAM_NGRAM, PROCESSED_DIR, ensure_dirs  # noqa: E402
from common import ngrams, read_jsonl, write_jsonl  # noqa: E402

IN = PROCESSED_DIR / "clean.jsonl"
OUT = PROCESSED_DIR / "decontaminated.jsonl"
OUT_BAD = PROCESSED_DIR / "contaminated.jsonl"

# Campos onde costuma morar o enunciado/resposta nos arquivos de benchmark.
TEXT_FIELDS = ("question", "query", "text", "prompt", "instruction", "answer", "output", "response")


def collect_benchmark_ngrams(patterns: list[str], n: int) -> set[str]:
    grams: set[str] = set()
    files: list[str] = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    if not files:
        raise FileNotFoundError(
            "Nenhum arquivo de benchmark encontrado.\n"
            "Exporte os conjuntos de TESTE (ENEM/BLUEX/ASSIN2...) como .jsonl em "
            "eval/benchmarks/ e passe o caminho em --benchmarks."
        )
    for fp in files:
        p = Path(fp)
        cnt = 0
        for row in read_jsonl(p):
            for field in TEXT_FIELDS:
                val = row.get(field)
                if isinstance(val, str) and val.strip():
                    grams |= ngrams(val, n)
                    cnt += 1
        print(f"  {p.name}: {cnt} campos de texto indexados")
    return grams


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--benchmarks",
        nargs="+",
        default=["eval/benchmarks/*.jsonl"],
        help="glob(s) dos arquivos de teste dos benchmarks",
    )
    ap.add_argument("--ngram", type=int, default=DECONTAM_NGRAM)
    args = ap.parse_args()

    ensure_dirs()
    if not IN.exists():
        print(f"ERRO: {IN} nao existe. Rode data/03_filter_dedup.py antes.", file=sys.stderr)
        return 1

    print(f"Indexando n-gramas ({args.ngram}) dos benchmarks de teste:")
    bench_grams = collect_benchmark_ngrams(args.benchmarks, args.ngram)
    print(f"total de n-gramas de teste: {len(bench_grams)}\n")

    clean: list[dict] = []
    dirty: list[dict] = []
    for row in read_jsonl(IN):
        blob = f"{row.get('instruction', '')} {row.get('response', '')}"
        overlap = ngrams(blob, args.ngram) & bench_grams
        if overlap:
            row["contamination_ngram"] = sorted(overlap)[0]
            dirty.append(row)
        else:
            clean.append(row)

    total = len(clean) + len(dirty)
    pct = (len(dirty) / total * 100) if total else 0.0
    print(f"examinados     : {total}")
    print(f"limpos         : {len(clean)}")
    print(f"CONTAMINADOS   : {len(dirty)}  ({pct:.2f}%)")

    write_jsonl(OUT, clean)
    write_jsonl(OUT_BAD, dirty)
    print(f"\n-> {OUT}")
    print(f"-> {OUT_BAD}  (auditar: se a % for alta, a fonte do dado esta suspeita)")

    if pct > 5.0:
        print(
            "\n⚠️  ALERTA: mais de 5% contaminado. Investigue a origem antes de treinar — "
            "provavelmente alguma fonte inclui os proprios benchmarks."
        )
    print("\nProximo: python data/05_build_splits.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
