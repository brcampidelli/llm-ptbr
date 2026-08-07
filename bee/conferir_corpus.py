"""Confere se um corpus reconstruido e' IDENTICO ao de referencia.

⭐ POR QUE ISTO EXISTE
  O corpus de 21,75B tokens foi montado uma vez na maquina do Bruno e depois
  reconstruido no pod (subir 43,5 GB a 0,7 MB/s levaria 17 h; refazer leva ~4 h).
  Refazer so' vale se o resultado for o MESMO corpus — senao nao e' reconstrucao,
  e' um corpus novo, e nenhuma medida anterior serve de comparacao.

  A cadeia inteira e' deterministica: os limiares saem de percentis de uma amostra
  fixa, o classificador e' o mesmo .joblib, o filtro de qualidade e' deterministico,
  o dedup e' hash exato e o tokenizador e' o mesmo. Entao o mesmo parquet tem que
  produzir o mesmo byte. Este script verifica isso em vez de supor.

⚠️ POR QUE val.bin INTEIRO E train.bin POR AMOSTRA
  val.bin tem 439 MB — da' para hashear inteiro em segundos, e ele e' a cauda de 1%
  de CADA shard, ou seja, toca todos os 39 shards. E' a melhor prova por dinheiro.
  train.bin tem 43,5 GB; hashear inteiro leva minutos de I/O que competem com o
  treino. Cinco janelas de 16 MB em posicoes fixas (0, 1/4, 1/2, 3/4, fim) pegam
  regioes de shards diferentes e detectam qualquer deslocamento de conteudo.

⚠️ O tamanho em bytes e' condicao NECESSARIA, nao suficiente — dois corpora podem
  ter o mesmo tamanho e conteudo diferente. Por isso o hash.

Uso:
    python bee/conferir_corpus.py /dados22b
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# Referencia: corpus montado em 2026-08-06 na maquina do Bruno (dados_pt_22b/).
REF = {
    "val.bin": {
        "bytes": 439_387_812,
        "sha256": "51e62950fe02d03889807674fb674906d1041ae5725de61d80c3d24041f55936",
        "modo": "completo",
    },
    "train.bin": {
        "bytes": 43_499_389_106,
        "sha256": "c7dd0bf9b72a7fc10d2ab7ceff3a066a4b2ee3e0211d0e247004df548d2d0f20",
        "modo": "5 janelas de 16 MB em 0, 1/4, 1/2, 3/4 e fim",
    },
}
JANELA = 1 << 24                                  # 16 MB


def hash_completo(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while (b := f.read(1 << 24)):
            h.update(b)
    return h.hexdigest()


def hash_janelas(p: Path, tamanho: int) -> str:
    """5 janelas em posicoes FIXAS. Tem que casar com o script que gerou a referencia."""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for m in (0, tamanho // 4, tamanho // 2, 3 * tamanho // 4, tamanho - JANELA):
            f.seek(m)
            h.update(f.read(JANELA))
    return h.hexdigest()


def main() -> int:
    # O console do Windows e' cp1252 e morre nos ✅/⚠️ — e morrer DEPOIS de imprimir
    # o hash certo seria o pior dos mundos: o trabalho feito e o veredito perdido.
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("dados", type=Path)
    args = ap.parse_args()

    print("=" * 70)
    print("CONFERENCIA DE REPRODUTIBILIDADE DO CORPUS")
    print("=" * 70)

    meta_p = args.dados / "meta.json"
    if meta_p.exists():
        m = json.loads(meta_p.read_text(encoding="utf-8"))
        print(f"  meta: {m.get('tokens_treino', 0)/1e9:.3f}B treino · "
              f"{m.get('tokens_val', 0)/1e6:.1f}M val · vocab {m.get('vocab')} · "
              f"parquets {len(m.get('parquets_concluidos') or [])}")

    tudo_bate = True
    for nome, ref in REF.items():
        p = args.dados / nome
        if not p.exists():
            print(f"\n  {nome}: AUSENTE")
            tudo_bate = False
            continue
        tam = os.path.getsize(p)
        ok_tam = tam == ref["bytes"]
        print(f"\n  {nome}")
        print(f"    bytes    : {tam:,}")
        print(f"    esperado : {ref['bytes']:,}   {'IGUAL' if ok_tam else '⚠️ DIFERENTE'}"
              f" ({tam - ref['bytes']:+,})")
        # Hashear com tamanho diferente do de referencia nao prova nada util: as
        # janelas cairiam em posicoes distintas e o hash divergiria por construcao.
        if not ok_tam:
            print("    sha256   : nao calculado — tamanho diferente ja' decide")
            tudo_bate = False
            continue
        got = (hash_completo(p) if ref["modo"] == "completo"
               else hash_janelas(p, tam))
        ok_h = got == ref["sha256"]
        print(f"    sha256   : {got}   ({ref['modo']})")
        print(f"    esperado : {ref['sha256']}   {'IGUAL ✅' if ok_h else '⚠️ DIFERENTE'}")
        tudo_bate &= ok_h

    print("\n" + "=" * 70)
    if tudo_bate:
        print("  ✅ REPRODUZIDO — corpus identico ao de referencia, byte a byte.")
        print("     Toda medida feita sobre o corpus original vale para este.")
    else:
        print("  ⚠️ NAO REPRODUZIDO. Antes de treinar, decidir explicitamente:")
        print("     - se faltam parquets, este corpus e' MENOR (veja parquets no meta)")
        print("     - se o tamanho bate e o hash nao, algo na cadeia mudou e a causa")
        print("       precisa ser achada — nao e' para ignorar")
        print("     Treinar assim mesmo e' uma escolha valida, mas as comparacoes com")
        print("     numeros anteriores passam a ser entre corpora diferentes.")
    print("=" * 70)
    return 0 if tudo_bate else 2


if __name__ == "__main__":
    sys.exit(main())
