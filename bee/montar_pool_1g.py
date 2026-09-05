"""Monta a METADE PT do pool `pt-50` do Bee-1G — a opcao C do plano de transporte.

⭐ POR QUE SO' A METADE. O `pretrain.py` le' UM `train.bin` em uint16 (2 B/token). Subir os dois
   corpora crus sao 70 GB; subir o pool inteiro sao 40 GB; subir so' a metade PT sao **20 GB**, e
   a metade nao-PT se reconstroi no pod — ficou provado por hash em 2026-09-05 que a coleta do
   fineweb-2 e' prefixo deterministico e que o pod coleta ~9x mais rapido que esta maquina.
   Os 10B de PT tem de subir: o texto cru foi apagado pelo `coletar_pt_volume.py`.

⭐ FAIXAS A+B+C, e isso NAO e' escolha em aberto. O gate de faixas (2026-09-01, 9 runs, 3
   sementes, US$ 3,2) mediu no holdout wiki: ABC 1,3894 · AB 1,3802 (t = −0,85, DENTRO do ruido)
   · A 1,4633 (t = +7,17, significativamente PIOR). Fica ABC, e a composicao original e'
   preservada tomando a mesma fracao de CADA shard.

🔴 EXCLUSAO DE HOLDOUT — a razao de este script existir em vez de um `head` de bytes.
   Censo completo de 2026-09-05 (`bee/checar_contaminacao_pt.py`): **56,1% do holdout
   `corpus_multi_pt` e 8,0% do holdout `wiki` estao DENTRO do corpus de treino**. Treinar neles
   faria a ancora de PT do Gate T4 medir memorizacao. Os fingerprints estao nos artefatos
   `docs/contaminacao-pt-*.json` e sao excluidos documento a documento aqui.

⚠️ O QUE ISTO NAO RESOLVE: o Bee-350M ja' foi treinado nesses documentos. Excluir do pool do 1G
   deixa a comparacao ASSIMETRICA — o 350M mantem a vantagem da memorizacao. O conserto dessa
   parte e' do lado da AVALIACAO: tirar os 308 documentos do holdout e reancorar os dois modelos.

⚠️ E o fingerprint e' de PREFIXO EXATO (32 tokens): quase-duplicata passa. Isto nao e' dedup.

Uso:
    python bee/montar_pool_1g.py --tokens 10e9
    python bee/montar_pool_1g.py --tokens 1e8 --out bee/pool_1g_teste   # ensaio barato
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus_pt_64k"
VOCAB = 64_000
EOS = 0
FRAC_VAL = 0.002          # 0,2% do pool vira validacao, de documentos NAO usados no treino


def fingerprints_excluidos() -> set[bytes]:
    """Os documentos de holdout achados dentro do corpus, dos dois censos."""
    fp: set[bytes] = set()
    for h in ("corpus_multi_pt", "wiki"):
        p = ROOT / "docs" / f"contaminacao-pt-{h}.json"
        if not p.exists():
            raise SystemExit(f"🔴 {p} nao existe — rode bee/checar_contaminacao_pt.py primeiro")
        d = json.loads(p.read_text(encoding="utf-8"))
        fp |= {bytes.fromhex(x) for x in d["fingerprints_contaminados"]}
    return fp


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokens", type=float, default=10e9, help="tokens de PT no pool")
    ap.add_argument("--prefixo", type=int, default=32, help="tem de bater com o do censo")
    ap.add_argument("--out", default="bee/pool_1g")
    args = ap.parse_args()

    import numpy as np

    alvo = int(args.tokens)
    excl = fingerprints_excluidos()
    print(f"{len(excl)} fingerprints de holdout a excluir (prefixo {args.prefixo} tokens)")

    shards = sorted(glob.glob(str(CORPUS / "pt_*.bin")))
    tam = {p: Path(p).stat().st_size // 2 for p in shards}
    total = sum(tam.values())
    frac = alvo / total
    if frac > 1.0:
        raise SystemExit(f"🔴 alvo {alvo/1e9:.2f}B > corpus {total/1e9:.2f}B")
    print(f"{len(shards)} shards · {total/1e9:.3f}B tokens · tomando {100*frac:.1f}% de CADA um "
          f"(preserva a composicao A:B:C)\n")

    destino = ROOT / args.out
    destino.mkdir(parents=True, exist_ok=True)
    p_tr, p_va = destino / "train_pt.bin", destino / "val_pt.bin"
    t0 = time.time()
    n_tr = n_va = n_doc_tr = n_doc_va = n_excl = n_curto = 0
    por_faixa: dict[str, int] = {}

    with open(p_tr.with_suffix(".bin.tmp"), "wb") as ftr, \
         open(p_va.with_suffix(".bin.tmp"), "wb") as fva:
        for i, cam in enumerate(shards, 1):
            faixa = Path(cam).name.split("_")[1]
            dados = np.fromfile(cam, dtype=np.uint16)
            fim = np.flatnonzero(dados == EOS)
            ini = np.concatenate(([0], fim[:-1] + 1))
            cota_tr = int(tam[cam] * frac)
            cota_va = max(1, int(cota_tr * FRAC_VAL))
            usado_tr = usado_va = 0
            for a, b in zip(ini, fim):
                doc = dados[a:b + 1]                       # inclui o EOS
                if len(doc) - 1 < args.prefixo:
                    n_curto += 1
                elif doc[:args.prefixo].tobytes() in excl:
                    n_excl += 1
                    continue
                if usado_tr < cota_tr:
                    doc.tofile(ftr); usado_tr += len(doc); n_doc_tr += 1
                elif usado_va < cota_va:
                    doc.tofile(fva); usado_va += len(doc); n_doc_va += 1
                else:
                    break
            n_tr += usado_tr; n_va += usado_va
            por_faixa[faixa] = por_faixa.get(faixa, 0) + usado_tr
            if i % 6 == 0 or i == len(shards):
                print(f"  [{i}/{len(shards)}] {n_tr/1e9:.3f}B treino · {n_va/1e6:.1f}M val · "
                      f"{n_excl} excluidos · {(time.time()-t0)/60:.1f} min", flush=True)

    # ---- guardas, todas contra o arquivo em disco ----
    tr = np.fromfile(p_tr.with_suffix(".bin.tmp"), dtype=np.uint16)
    va = np.fromfile(p_va.with_suffix(".bin.tmp"), dtype=np.uint16)
    erros = []
    # §2r: a exclusao tem de ter AGIDO. Zero exclusoes com 308 fingerprints e' defeito.
    if n_excl == 0:
        erros.append(f"a exclusao nao agiu: 0 documentos removidos com {len(excl)} fingerprints")
    if int(tr.max()) >= VOCAB or (len(va) and int(va.max()) >= VOCAB):
        erros.append(f"id fora do vocab: max {max(int(tr.max()), int(va.max()) if len(va) else 0)}")
    if int((tr == EOS).sum()) != n_doc_tr:
        erros.append(f"treino: {n_doc_tr:,} docs emitidos, {int((tr==EOS).sum()):,} EOS no arquivo")
    if abs(len(tr) - alvo) / alvo > 0.02:
        erros.append(f"treino {len(tr):,} tokens, alvo {alvo:,} — desvio > 2%")
    if len(va) == 0:
        erros.append("val vazio")
    # a composicao A:B:C do pool tem de reproduzir a do corpus
    orig = {}
    for p, n in tam.items():
        orig[Path(p).name.split("_")[1]] = orig.get(Path(p).name.split("_")[1], 0) + n
    for f in orig:
        a_pct, b_pct = 100 * orig[f] / total, 100 * por_faixa.get(f, 0) / max(1, n_tr)
        if abs(a_pct - b_pct) > 1.0:
            erros.append(f"faixa {f}: corpus {a_pct:.1f}% x pool {b_pct:.1f}% — composicao mudou")
    if erros:
        for e in erros:
            print(f"🔴 {e}")
        raise SystemExit("🔴 guardas falharam — os .tmp ficam para inspecao, nada foi promovido")

    p_tr.with_suffix(".bin.tmp").replace(p_tr)
    p_va.with_suffix(".bin.tmp").replace(p_va)

    doc = {"_pool": "metade PT do pt-50 do Bee-1G (opcao C de transporte)",
           "_faixas": "A+B+C, fracao igual de CADA shard — composicao preservada; a escolha vem "
                      "do gate de faixas de 2026-09-01 (ABC 1,3894 x AB 1,3802 t=-0,85 x A "
                      "1,4633 t=+7,17), nao de preferencia",
           "_exclusao": f"{n_excl} documentos de holdout removidos, dos censos completos de "
                        f"2026-09-05 (corpus_multi_pt 56,1% e wiki 8,0% estavam dentro do corpus)",
           "_nao_resolve": [
               "o Bee-350M ja' treinou nesses documentos: excluir so' do pool do 1G deixa a "
               "comparacao ASSIMETRICA. O conserto e' tirar os 308 do HOLDOUT e reancorar os dois",
               "quase-duplicata: o fingerprint e' de prefixo exato de 32 tokens",
               "a metade NAO-PT, que se monta no pod",
           ],
           "tokens_treino": int(len(tr)), "tokens_val": int(len(va)),
           "docs_treino": n_doc_tr, "docs_val": n_doc_va,
           "docs_excluidos": n_excl, "docs_curtos": n_curto,
           "fracao_do_corpus": frac, "max_id": int(tr.max()),
           "composicao_pool_pct": {f: 100 * por_faixa.get(f, 0) / n_tr for f in sorted(orig)},
           "composicao_corpus_pct": {f: 100 * orig[f] / total for f in sorted(orig)},
           "bytes_treino": int(len(tr)) * 2, "minutos": (time.time() - t0) / 60}
    (destino / "MANIFEST.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\n{'='*72}")
    print(f"treino  {len(tr)/1e9:.3f}B tokens · {n_doc_tr:,} docs · {len(tr)*2/1e9:.1f} GB")
    print(f"val     {len(va)/1e6:.1f}M tokens · {n_doc_va:,} docs")
    print(f"excluidos por holdout: {n_excl}   ·   curtos demais para fingerprint: {n_curto:,}")
    print("composicao   " + " · ".join(
        f"{f} {100*por_faixa.get(f,0)/n_tr:.1f}% (corpus {100*orig[f]/total:.1f}%)"
        for f in sorted(orig)))
    print("=" * 72)
    print(f"✅ guardas passaram · {destino}/  ({(time.time()-t0)/60:.1f} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
