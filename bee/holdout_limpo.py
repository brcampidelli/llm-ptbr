"""Holdout de web PT GARANTIDAMENTE limpo, de um parquet que nenhum Bee jamais viu.

⭐ POR QUE (2026-08-06)
  O holdout do Gate 2 (shards [7,23]) foi montado a partir do fineweb-2 `por_Latn`, e as
  coletas do Bee consumiram justamente essa regiao: 0-7 pela coleta original em streaming
  (v1), 8+ pela `expand_corpus.py` (v3), e 0-12 pela coleta nova de PT em volume. Ou seja,
  a linha `fineweb2-por` daquele holdout nao serve para comparar um Bee treinado no corpus
  novo — ele teria visto parte do proprio gabarito.

  Este script constroi a regua que faltava: baixa UM parquet de indice alto, nunca tocado
  por nenhuma coleta, e mede bpb de todos os modelos nele. Conserta a medicao para todos de
  uma vez — Bee antigo, Bee novo, Tucano e SmolLM2 passam a ter uma linha de web PT em que
  nenhum deles pode ter treinado.

⚠️ OS NUMEROS AQUI NAO SAO COMPARAVEIS EM ABSOLUTO COM OS DO HOLDOUT [7,23].
  E' outro texto. bpb 2,20 la e bpb 2,20 aqui nao significam a mesma coisa. O que se compara
  e' o RANKING e as RAZOES entre modelos medidos NESTE mesmo texto. Misturar as duas tabelas
  como se fossem uma serie seria o mesmo erro de aplicar a fertilidade media de duas fontes
  a uma fonte so — que ja abortou uma coleta correta hoje.

⚠️ PARQUETS JA CONSUMIDOS (nao usar como holdout limpo):
    0-7    coleta original em streaming (corpus v1)
    8-12   expand_corpus.py (expansao do v3) e coleta nova de PT em volume
    2,5,14,18,27,31,42,45,56,63   gate pareado bruto x filtrado (nao treinou Bee, mas evitar)
  Indice 40 esta fora de tudo isso.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet-idx", type=int, default=40,
                    help="indice do parquet do por_Latn. ⚠️ ver a lista de ja consumidos "
                         "no topo do arquivo antes de mudar")
    ap.add_argument("--n-docs", type=int, default=400)
    ap.add_argument("--max-chars", type=int, default=4000, help="igual ao eval_gate2")
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--modelos", default=(
        f"Bee-150M-v3={ROOT / 'models' / 'bee-150m-v3-base'},"
        "Tucano-160m=TucanoBR/Tucano-160m,"
        "SmolLM2-135M=HuggingFaceTB/SmolLM2-135M"))
    ap.add_argument("--tmp", type=Path,
                    default=ROOT / "corpus_pt" / "_holdout_limpo")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "holdout-limpo.json")
    args = ap.parse_args()

    import pyarrow.parquet as pq
    import torch
    from huggingface_hub import hf_hub_download

    from eval_gate2 import bits_por_byte
    from expand_corpus import listar_parquets, qualidade_ok

    arqs = listar_parquets()
    arq = arqs[args.parquet_idx]
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print("=" * 74)
    print("HOLDOUT LIMPO — web PT de um parquet que nenhum Bee viu")
    print("=" * 74)
    print(f"  parquet    : [{args.parquet_idx}] {arq}")
    print(f"  dispositivo: {dev}")
    print(f"  ⚠️ bpb daqui NAO se compara em absoluto com o do holdout [7,23] — outro texto.")
    print(f"     Compara-se o ranking e as razoes ENTRE modelos, medidos neste mesmo texto.\n")

    args.tmp.mkdir(parents=True, exist_ok=True)
    print("  baixando o parquet...", flush=True)
    cam = Path(hf_hub_download("HuggingFaceFW/fineweb-2", arq, repo_type="dataset",
                               local_dir=str(args.tmp)))

    textos: list[str] = []
    vistos = 0
    for lote in pq.ParquetFile(cam).iter_batches(batch_size=2000, columns=["text"]):
        for t in lote.column("text").to_pylist():
            vistos += 1
            if qualidade_ok(t) is None:              # ⚠️ None = o doc PRESTA
                textos.append(t[:args.max_chars])
        if len(textos) >= args.n_docs:
            break
    textos = textos[:args.n_docs]
    nb = sum(len(t.encode("utf-8")) for t in textos)
    print(f"  holdout: {len(textos)} docs · {nb/1e6:.2f} MB · de {vistos:,} lidos\n")

    resultados: dict[str, dict] = {}
    for par in args.modelos.split(","):
        nome, _, ident = par.partition("=")
        print(f"  medindo {nome}...", flush=True)
        try:
            r, fert = bits_por_byte(ident, {"fineweb2-por-limpo": textos}, args.seq_len, dev)
        except Exception as e:
            print(f"    FALHOU: {type(e).__name__}: {e}", file=sys.stderr)
            continue
        bits, bytes_ = r["fineweb2-por-limpo"]
        resultados[nome] = {"bpb": bits / bytes_, "fertilidade": fert, "modelo": ident}

    if not resultados:
        print("ERRO: nenhum modelo mediu", file=sys.stderr)
        return 1

    ordem = sorted(resultados, key=lambda k: resultados[k]["bpb"])
    melhor = resultados[ordem[0]]["bpb"]
    print("\n" + "=" * 74)
    print(f"RESULTADO — bpb em web PT LIMPA (parquet {args.parquet_idx}), menor = melhor")
    print("=" * 74)
    print(f"  {'modelo':<16} {'bpb':>8} {'vs melhor':>10} {'fertilidade':>12}")
    print("  " + "-" * 50)
    for nome in ordem:
        d = resultados[nome]
        print(f"  {nome:<16} {d['bpb']:>8.3f} {d['bpb']/melhor:>9.2f}x {d['fertilidade']:>12.4f}")

    meta = {"parquet_idx": args.parquet_idx, "parquet": arq, "n_docs": len(textos),
            "bytes": nb, "max_chars": args.max_chars, "seq_len": args.seq_len,
            "resultados": resultados,
            "aviso": ("bpb deste holdout NAO e comparavel em absoluto com o do holdout "
                      "[7,23] — texto diferente. Comparar ranking e razoes entre modelos.")}
    args.out.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  salvo em {args.out}")

    try:
        cam.unlink()
        print("  parquet apagado (4,8 GB liberados)")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
