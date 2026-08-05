"""Preparo do gate pareado em STREAMING — para orcamentos que nao cabem na RAM.

⭐ POR QUE UM SEGUNDO PREPARO
  O `gate_pareado.py --preparar` carrega todos os docs em memoria e ordena pelo
  score. Funciona ate ~500k docs. Para 130M tokens por braco com retencao de 10%
  e' preciso VARRER ~1,3B tokens (~1,7M docs) — 6 GB so de texto. Aqui o score
  vira LIMIAR calibrado numa amostra, e o resto e' fluxo: le lote, pontua,
  descarta o que nao passa, tokeniza o que passa, esquece.
  E' tambem como o FineWeb-Edu opera de verdade: limiar, nao ordenacao global.

⚠️ O limiar e' calibrado UMA vez e vale para os dois bracos — se fosse
  recalibrado por parquet, cada um teria um criterio diferente e o braco
  "filtrado" seria uma mistura de politicas, nao uma politica.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))
BASE = ROOT / "bee" / "gate"
TOKENIZER = ROOT / "models" / "bee-150m-v3-base"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", type=float, default=130e6, help="tokens POR BRACO")
    ap.add_argument("--percentil", type=float, default=90.0,
                    help="90 = mantem os 10%% melhores")
    ap.add_argument("--parquets", default="2,14,27,42,56,63,5,18,31,45")
    ap.add_argument("--calibrar-com", type=int, default=30000)
    ap.add_argument("--classificador", type=Path,
                    default=ROOT / "bee" / "edu" / "classificador.joblib")
    args = ap.parse_args()

    import joblib
    import numpy as np
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer

    from expand_corpus import listar_parquets, qualidade_ok

    BASE.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    mod = joblib.load(args.classificador)
    vet, reg = mod["vetorizador"], mod["regressor"]
    arqs = listar_parquets()
    idxs = [int(x) for x in args.parquets.split(",")]
    alvo = int(args.tokens)

    print("=" * 66)
    print(f"Preparo em streaming — {alvo/1e6:.0f}M tokens por braco")
    print("=" * 66)
    print(f"  classificador: F1 {mod['f1']:.3f} · correlacao {mod['correlacao']:.3f}")

    def fluxo(indices):
        """Gera documentos aprovados no filtro de qualidade, em ordem natural."""
        for i in indices:
            caminho = hf_hub_download("HuggingFaceFW/fineweb-2", arqs[i], repo_type="dataset")
            for lote in pq.ParquetFile(caminho).iter_batches(batch_size=2000, columns=["text"]):
                for t in lote.column("text").to_pylist():
                    if qualidade_ok(t) is None:
                        yield t

    # ---- 1) calibrar o limiar numa amostra -----------------------------------
    print(f"\ncalibrando limiar em {args.calibrar_com} docs...")
    amostra = []
    for t in fluxo(idxs[:1]):
        amostra.append(t)
        if len(amostra) >= args.calibrar_com:
            break
    sc = reg.predict(vet.transform([d[:2500] for d in amostra]))
    limiar = float(np.percentile(sc, args.percentil))
    print(f"  limiar (p{args.percentil:.0f}) = {limiar:.3f} · score medio da amostra {sc.mean():.3f}")

    # ---- 2) escrever os dois bracos no MESMO fluxo ---------------------------
    # ⭐ Mesmo fluxo, mesma ordem: o braco cru pega tudo, o filtrado so o que passa
    # do limiar. Assim a unica diferenca entre os dois e' a POLITICA DE SELECAO.
    print(f"\nvarrendo {len(idxs)} parquets...")
    ids_cru: list[int] = []
    ids_flt: list[int] = []
    n_vistos = n_passou = 0
    soma_cru = soma_flt = 0.0
    buffer: list[str] = []

    def drenar():
        nonlocal n_vistos, n_passou, soma_cru, soma_flt
        if not buffer:
            return
        scores = reg.predict(vet.transform([d[:2500] for d in buffer]))
        for texto, s in zip(buffer, scores):
            n_vistos += 1
            if len(ids_cru) < alvo:
                e = tok(texto, add_special_tokens=False)["input_ids"]
                ids_cru.extend(e + [0])
                soma_cru += s
            if s >= limiar:
                n_passou += 1
                if len(ids_flt) < alvo:
                    e = tok(texto, add_special_tokens=False)["input_ids"]
                    ids_flt.extend(e + [0])
                    soma_flt += s
        buffer.clear()

    n_cru_docs = n_flt_docs = 0
    for texto in fluxo(idxs):
        buffer.append(texto)
        if len(buffer) >= 5000:
            antes_c, antes_f = len(ids_cru), len(ids_flt)
            drenar()
            n_cru_docs += 1 if antes_c < alvo else 0
            print(f"  vistos {n_vistos:>9,} · passaram {n_passou:>8,} "
                  f"({n_passou/max(1,n_vistos):.1%}) · cru {len(ids_cru)/1e6:>6.1f}M · "
                  f"filtrado {len(ids_flt)/1e6:>6.1f}M", flush=True)
        if len(ids_cru) >= alvo and len(ids_flt) >= alvo:
            break
    drenar()

    for nome, ids in (("cru", ids_cru), ("filtrado", ids_flt)):
        arr = np.array(ids[:alvo], dtype=np.uint16)
        arr.tofile(BASE / f"{nome}.bin")
        print(f"\n  {nome:9s}: {arr.size/1e6:.1f}M tokens")

    meta = {"tokens_por_braco": alvo, "limiar": limiar, "percentil": args.percentil,
            "docs_vistos": n_vistos, "docs_aprovados": n_passou,
            "retencao": n_passou / max(1, n_vistos)}
    (BASE / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\n  retencao real: {meta['retencao']:.1%} de {n_vistos:,} documentos varridos")
    if not (0.03 <= meta["retencao"] <= 0.25):
        print(f"  AVISO: retencao fora da faixa util (3-25%) — o contraste entre os "
              f"bracos pode ser fraco demais ou seletivo demais.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
