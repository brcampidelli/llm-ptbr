"""Mede quanta duplicata ATRAVESSOU o dedup do corpus — tokens efetivos vs nominais.

⭐ O BURACO QUE ESTE SCRIPT MEDE
  `expand_corpus.py` (que construiu o v3, 3,74B -> 9,87B) faz duas defesas:
    vistos = VistosPersistente(out/"vistos_sha.txt")  -> LE DO DISCO, entao pega
                                                        duplicata EXATA entre o
                                                        corpus original e a expansao ✓
    dedup  = Dedup() if args.minhash else None        -> nasce VAZIO a cada execucao
  O `Dedup` e' LSH por bandas sobre MinHash, e vive so em RAM. Ele pega
  quase-duplicata DENTRO da expansao e **nao** entre a expansao e o corpus v1.
  Como o v3 = v1 + expansao, essa fronteira nunca foi verificada.

⭐ POR QUE MEDIR NA FONTE, E NAO NO CORPUS
  Os shards estao na Drive (~30 GB) e `gdown` bate rate-limit em pasta grande
  (lição de 2026-08-03). Mas os dois lados da fronteira vem do MESMO dataset —
  `fineweb-2` cfg `por_Latn`. Amostrar dois arquivos parquet DIFERENTES do mesmo
  dataset reproduz exatamente a situacao: arquivo A ~ corpus original (o streaming
  le do inicio), arquivo B ~ expansao (rodou com --skip-files). A taxa cruzada A×B
  e' a estimativa do que vazou para o v3.

  ⚠️ E' ESTIMATIVA POR AMOSTRA, nao censo do corpus. Diz a ORDEM DE GRANDEZA da
  contaminacao, nao o numero exato. Isso basta para decidir se vale baixar 30 GB.

Uso:
    python bee/medir_dedup.py --n 4000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))

REPO = "HuggingFaceFW/fineweb-2"
CONFIG_DIR = "por_Latn"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000, help="docs por lado")
    ap.add_argument("--arquivo-a", type=int, default=0, help="indice do parquet 'original'")
    ap.add_argument("--arquivo-b", type=int, default=12, help="indice do parquet 'expansao'")
    args = ap.parse_args()

    # Reusa as funcoes REAIS do coletor — se elas mudarem, esta medicao muda junto.
    from expand_corpus import Dedup, listar_parquets, qualidade_ok, sha_doc

    print("=" * 66)
    print("Duplicata que atravessou o dedup — tokens efetivos vs nominais")
    print("=" * 66)

    arquivos = listar_parquets()
    print(f"  parquets no {REPO}/{CONFIG_DIR}: {len(arquivos)}")
    for rotulo, idx in [("A (original)", args.arquivo_a), ("B (expansao)", args.arquivo_b)]:
        if idx >= len(arquivos):
            print(f"ERRO: indice {idx} fora do intervalo", file=sys.stderr)
            return 1
        print(f"  {rotulo:14s} -> {arquivos[idx]}")

    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    lados = {}
    for rotulo, idx in [("A", args.arquivo_a), ("B", args.arquivo_b)]:
        print(f"\nbaixando lado {rotulo}...", flush=True)
        caminho = hf_hub_download(REPO, arquivos[idx], repo_type="dataset")
        pf = pq.ParquetFile(caminho)
        textos, brutos = [], 0
        for lote in pf.iter_batches(batch_size=1000, columns=["text"]):
            for t in lote.column("text").to_pylist():
                brutos += 1
                # ⚠️ qualidade_ok devolve None quando o doc PRESTA, e o motivo da
                # rejeicao quando nao presta. Usar `if qualidade_ok(t):` coleta as
                # strings de motivo — bug que rendeu "99,92% de duplicata" na 1a rodada.
                if qualidade_ok(t) is None:
                    textos.append(t)
                if len(textos) >= args.n:
                    break
            if len(textos) >= args.n:
                break
        lados[rotulo] = textos
        print(f"  {len(textos)} docs aproveitados de {brutos} brutos "
              f"({len(textos)/brutos:.0%} passam no filtro de qualidade)")

    A, B = lados["A"], lados["B"]

    def bytes_de(ts):
        return sum(len(t.encode("utf-8")) for t in ts)

    print(f"\n{'='*66}\n1) DUPLICATA EXATA (sha_doc — o que o vistos_sha JA pega)\n{'='*66}")
    sa = {sha_doc(t) for t in A}
    sb = {sha_doc(t) for t in B}
    print(f"  dentro de A : {len(A)-len(sa):>6} de {len(A)} ({1-len(sa)/len(A):.2%})")
    print(f"  dentro de B : {len(B)-len(sb):>6} de {len(B)} ({1-len(sb)/len(B):.2%})")
    print(f"  A x B       : {len(sa & sb):>6} ({len(sa & sb)/len(sb):.2%} de B) "
          f"<- coberto pelo vistos_sha [OK]")

    print(f"\n{'='*66}\n2) QUASE-DUPLICATA (MinHash LSH — o buraco)\n{'='*66}")
    # Dentro de cada lado: e' o que o Dedup() da propria execucao pegaria.
    dentro = {}
    for rotulo, ts in [("A", A), ("B", B)]:
        d = Dedup()
        dup = sum(1 for t in ts if d.duplicado(t))
        dentro[rotulo] = dup
        print(f"  dentro de {rotulo} : {dup:>6} de {len(ts)} ({dup/len(ts):.2%})  "
              f"<- o MinHash da execucao pega [OK]")

    # ⭐ A medicao que importa: carrega A no LSH e passa B por cima.
    # Reproduz "corpus v1 ja indexado, expansao chegando" — que e' justamente o
    # que NAO acontece hoje, porque o Dedup nasce vazio a cada execucao.
    d_cruz = Dedup()
    for t in A:
        d_cruz.duplicado(t)
    n_cruz, bytes_cruz = 0, 0
    for t in B:
        if d_cruz.duplicado(t):
            n_cruz += 1
            bytes_cruz += len(t.encode("utf-8"))
    taxa = n_cruz / len(B)
    print(f"  A x B       : {n_cruz:>6} de {len(B)} ({taxa:.2%})  "
          f"<- [BURACO] NAO coberto: o Dedup nasce vazio")

    print(f"\n{'='*66}\n3) O QUE ISSO SIGNIFICA PARA O v3\n{'='*66}")
    bruto_dentro = dentro["B"] / len(B)
    print(f"  quase-duplicata dentro de um lote      : {bruto_dentro:.2%} (pega)")
    print(f"  quase-duplicata cruzando a fronteira   : {taxa:.2%} (NAO pega)")
    if taxa > 0:
        efetivo = 9.87 * (1 - taxa)
        print(f"\n  Se a taxa se mantiver no corpus inteiro, dos 9,87B tokens NOMINAIS")
        print(f"  do v3 restam ~{efetivo:.2f}B EFETIVOS — perda de {9.87-efetivo:.2f}B.")
        print(f"  [!] Ordem de grandeza, nao numero exato: amostra de {len(A)}+{len(B)} docs.")
    else:
        print("\n  Taxa cruzada ZERO na amostra: a fronteira nao contaminou de forma")
        print("  detectavel. A saturacao do Bee NAO se explica por duplicata.")
    print(f"\n  bytes duplicados na amostra de B: {bytes_cruz/1e6:.1f} MB de "
          f"{bytes_de(B)/1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
