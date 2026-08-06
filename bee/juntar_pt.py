"""Junta os shards por faixa da coleta PT em `train.bin` + `val.bin` para o pre-treino.

Uso:
    python bee/juntar_pt.py --faixas A      # so' o topo (~1/3 dos tokens)
    python bee/juntar_pt.py --faixas AB     # top 30% dos documentos
    python bee/juntar_pt.py --faixas ABC    # top 60% — volume maximo

⭐ POR QUE A VALIDACAO SAI DE TODOS OS SHARDS, E NAO DO FIM
  Cada shard vem de um parquet, e cada parquet e' um recorte diferente do Common Crawl.
  Reservar "o final do arquivo concatenado" daria um holdout que e' UM dump — mede o
  ajuste aquele dump, nao ao portugues. Aqui a validacao e' a cauda de CADA shard, entao
  ela tem a mesma composicao do treino.

⚠️⚠️ NAO COMPARE A PERPLEXIDADE DE VALIDACAO DESTE CORPUS COM A DO v3.
  Perplexidade so' e' comparavel no MESMO texto. O v3 validou em 185,2M tokens da mistura
  antiga (70% PT + EN + codigo); este corpus e' 100% PT e mais limpo — a perplexidade vai
  cair sozinha, por mudanca de distribuicao, sem o modelo ter melhorado em nada. Cair de
  63 para 40 aqui nao significaria absolutamente nada.

  A regua para comparar corpora e' EXTERNA e ja existe: `bee/eval_gate2.py` mede bpb no
  holdout compartilhado (shards [7,23]), onde ja temos os numeros de referencia —
  Bee 3,457 · Tucano-160m 1,739 · SmolLM2 2,010. E' esse numero que decide se trocar de
  corpus adiantou. Ver docs/gate-tucano.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, default=ROOT / "corpus_pt")
    ap.add_argument("--saida", type=Path, default=ROOT / "dados_pt")
    ap.add_argument("--faixas", default="ABC", help="A, AB ou ABC")
    ap.add_argument("--val-frac", type=float, default=0.01,
                    help="fracao da CAUDA DE CADA SHARD reservada para validacao")
    ap.add_argument("--pedaco-mb", type=int, default=256)
    args = ap.parse_args()

    import numpy as np

    faixas = [c for c in args.faixas.upper() if c in "ABC"]
    if not faixas:
        print("ERRO: --faixas precisa conter A, B ou C", file=sys.stderr)
        return 1
    args.saida.mkdir(parents=True, exist_ok=True)

    shards = sorted(p for f in faixas for p in args.entrada.glob(f"pt_{f}_*.bin"))
    if not shards:
        print(f"ERRO: nenhum shard pt_[{args.faixas}]_*.bin em {args.entrada}", file=sys.stderr)
        return 1

    total_bytes = sum(p.stat().st_size for p in shards)
    print("=" * 70)
    print(f"JUNTANDO faixas {'+'.join(faixas)} — {len(shards)} shards")
    print("=" * 70)
    print(f"  entrada: {total_bytes/1e9:.1f} GB = {total_bytes/2/1e9:.2f}B tokens")
    print(f"  val    : cauda de {args.val_frac:.1%} de CADA shard\n")

    n_tr = n_val = 0
    pedaco = args.pedaco_mb * 1_000_000 // 2          # em tokens (uint16)
    with open(args.saida / "train.bin", "wb") as ftr, open(args.saida / "val.bin", "wb") as fva:
        for p in shards:
            n = p.stat().st_size // 2
            corte = int(n * (1 - args.val_frac))
            # ⚠️ Ler em pedacos: um shard tem varios GB e np.fromfile inteiro estoura a RAM
            # quando ha 39 deles. O corte cai no meio de um pedaco, entao dividimos ali.
            lido = 0
            with open(p, "rb") as f:
                while lido < n:
                    a = np.fromfile(f, dtype=np.uint16, count=min(pedaco, n - lido))
                    if a.size == 0:
                        break
                    ini, fim = lido, lido + a.size
                    if fim <= corte:
                        a.tofile(ftr); n_tr += a.size
                    elif ini >= corte:
                        a.tofile(fva); n_val += a.size
                    else:
                        k = corte - ini
                        a[:k].tofile(ftr); n_tr += k
                        a[k:].tofile(fva); n_val += a.size - k
                    lido = fim
            print(f"  {p.name:<18} {n/1e6:8.1f}M tokens", flush=True)

    meta = {"faixas": faixas, "shards": [p.name for p in shards],
            "tokens_treino": n_tr, "tokens_val": n_val,
            "val_frac": args.val_frac, "fonte": "fineweb-2 por_Latn (ODC-By)",
            "idioma": "100% pt"}
    (args.saida / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"  train.bin  {n_tr/1e9:6.2f}B tokens · {n_tr*2/1e9:5.1f} GB")
    print(f"  val.bin    {n_val/1e6:6.1f}M tokens · {n_val*2/1e9:5.2f} GB")
    print(f"\n  Para o Bee-150M (151,2M params): {n_tr/151.2e6:.0f} tokens por parametro")
    print("  (o v3 rodou com 65; Chinchilla-otimo e' 20; o Tucano-160m usou ~1.230)")
    print("\n  ⚠️ Avaliar com bee/eval_gate2.py no holdout [7,23] — NAO com a perplexidade")
    print("     de validacao daqui, que nao e' comparavel com a do v3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
