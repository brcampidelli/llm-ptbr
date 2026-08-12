"""Monta o sft_misto.jsonl — a mistura EXATA usada no SFT publicado (BrCamp/bee-150m-pt-sft).

⚠️ POR QUE ESTE ARQUIVO EXISTE (2026-08-12):
    O modelo publicado foi treinado sobre `sft_misto.jsonl`, que foi criado a mao com um
    `cat a.jsonl b.jsonl > misto.jsonl` no terminal de um pod efemero e NUNCA foi versionado.
    O `sft_args.json` dentro do modelo aponta para um arquivo que nao existe no repositorio e
    que nenhum script gerava — ou seja, **o treino do modelo publicado nao era reproduzivel**.
    Uma auditoria pegou isso. Sem um script versionado, qualquer A/B posterior seria desonesto:
    nao daria para saber se a diferenca veio da mudanca ou da mistura.

    Este script torna a mistura deterministica e verificavel por hash.

Uso:
    python comeia/data/14_montar_sft_misto.py            # gera e confere o hash
    python comeia/data/14_montar_sft_misto.py --conferir # so confere, nao escreve
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "comeia" / "data" / "processed"

# Ordem IMPORTA: o arquivo final e a concatenacao nesta sequencia, e o embaralhamento
# fica por conta do Trainer (seed 42). Mudar a ordem muda o resultado do treino.
PARTES = ["sft_ptbr.jsonl", "sft_agentic.jsonl"]
SAIDA = PROC / "sft_misto.jsonl"

# Referencia do que foi de fato treinado e publicado (medido em 2026-08-12).
REF_LINHAS = 7152
REF_PARTES = {"sft_ptbr.jsonl": 5657, "sft_agentic.jsonl": 1495}


def montar(escrever: bool) -> int:
    faltando = [p for p in PARTES if not (PROC / p).exists()]
    if faltando:
        print(f"ERRO: partes ausentes: {faltando}", file=sys.stderr)
        return 1

    linhas: list[str] = []
    contagem: dict[str, int] = {}
    for nome in PARTES:
        n_antes = len(linhas)
        for linha in (PROC / nome).open(encoding="utf-8"):
            linha = linha.rstrip("\n")
            if linha.strip():
                linhas.append(linha)
        contagem[nome] = len(linhas) - n_antes

    conteudo = "\n".join(linhas) + "\n"
    h = hashlib.sha256(conteudo.encode("utf-8")).hexdigest()

    print(f"partes    : {contagem}")
    print(f"total     : {len(linhas)} exemplos")
    print(f"sha256    : {h}")

    ok = True
    for nome, esperado in REF_PARTES.items():
        if contagem.get(nome) != esperado:
            print(f"  AVISO: {nome} tem {contagem.get(nome)}, o publicado tinha {esperado}")
            ok = False
    if len(linhas) != REF_LINHAS:
        print(f"  AVISO: total {len(linhas)} != {REF_LINHAS} do modelo publicado")
        ok = False
    print("  [OK] a mistura bate com a do modelo publicado" if ok
          else "  [!!] a mistura DIVERGE do modelo publicado — nao compare A/B as cegas")

    if escrever:
        SAIDA.write_text(conteudo, encoding="utf-8")
        print(f"\n[OK] escrito em {SAIDA}")
    return 0 if ok else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conferir", action="store_true", help="nao escreve, so confere")
    args = ap.parse_args()
    return montar(escrever=not args.conferir)


if __name__ == "__main__":
    raise SystemExit(main())
