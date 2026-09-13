"""Censo de QUASE-duplicatas entre o holdout (val.bin) e o treino (train.bin) do Bee-1G — gate #5.

🔴 POR QUE EXISTE. O censo por fingerprint (bee/checar_contaminacao_pt.py, montar_val_naopt.py)
   garante que NENHUM documento do holdout compartilha os primeiros 32 tokens com um documento
   do treino. Isso pega duplicata exata e cabecalho repetido. NAO pega quase-duplicata: um documento
   que compartilha 60% dos seus 13-gramas com o treino mas comeca diferente passa pelo fingerprint
   inteiro. O artigo 2609.03350 mostrou o FineWeb-2 (fonte dos 7 idiomas nao-PT) vazando entre
   splits — e o 2609.10357 mostrou que familiaridade sobrevive a decontaminacao exata.

O QUE MEDE. Para cada documento do holdout, a FRACAO dos seus 13-gramas (de tokens) que aparece em
qualquer lugar do treino. Documento com fracao >= 0,5 e' quase-duplicata (criterio do GPT-3/Pile);
>= 0,8 e' duplicata com outro inicio. Reporta o histograma, por idioma, e a lista dos piores.

⚠️ CENSO, NAO PILOTO (§2ac): o lado do holdout entra INTEIRO (todos os 13-gramas) e o lado do
   treino e' varrido INTEIRO. Amostrar o treino subestimaria a taxa pela fracao amostrada.

⚠️ 13-gramas COMUNS (boilerplate, marcacao) aparecem legitimamente nos dois lados — por isso o
   criterio e' por DOCUMENTO (fracao alta), nao "algum 13-grama coincide".

Roda no POD (64 vCPU), com nice, em paralelo por fatias do train.bin. Nao toca a GPU.
Uso:  nice -n 19 python3 bee/censo_ngram_val.py --val pool/val.bin --train pool/train.bin \
          --meta pool/meta.json --saida censo_ngram_val.json --procs 40
"""
from __future__ import annotations

import argparse
import json
import os
import time
from multiprocessing import Pool

import numpy as np

N = 13
# 13 constantes impares de 64 bits (hash polinomial vetorizado; overflow em uint64 e' o modulo)
P = np.array([0x9E3779B97F4A7C15, 0xBF58476D1CE4E5B9, 0x94D049BB133111EB, 0xD6E8FEB86659FD93,
              0xA5A5A5A5A5A5A5A5 | 1, 0x7F4A7C159E3779B9, 0x1CE4E5B9BF58476D, 0x133111EB94D049BB,
              0x6659FD93D6E8FEB8 | 1, 0xC2B2AE3D27D4EB4F, 0x165667B19E3779F9, 0x27D4EB2F165667C5,
              0x9FB21C651E98DF25], dtype=np.uint64)


def hashes_13gram(tok: np.ndarray) -> np.ndarray:
    """hash de cada 13-grama de um vetor de tokens (uint16) — vetorizado, uint64 com wrap."""
    t = tok.astype(np.uint64)
    n = len(t) - N + 1
    if n <= 0:
        return np.empty(0, dtype=np.uint64)
    h = np.zeros(n, dtype=np.uint64)
    for j in range(N):
        h += t[j:j + n] * P[j]
    h ^= h >> np.uint64(29)
    return h


def _fatia(args):
    """Um trabalhador: varre [ini, fim) do train.bin e devolve quais hashes do holdout apareceram."""
    train_path, ini, fim, alvo_path = args
    alvo = np.load(alvo_path)                       # hashes do holdout, ORDENADOS, unicos
    mm = np.memmap(train_path, dtype=np.uint16, mode="r")
    achados = np.zeros(len(alvo), dtype=bool)
    passo = 50_000_000
    for a in range(ini, fim, passo):
        b = min(a + passo + N - 1, fim + N - 1, len(mm))     # sobrepoe N-1 para nao perder 13-gramas na borda
        h = hashes_13gram(np.asarray(mm[a:b]))
        h = np.unique(h)
        idx = np.searchsorted(alvo, h)
        idx[idx >= len(alvo)] = 0
        ok = alvo[idx] == h
        achados[idx[ok]] = True
    return achados


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--val", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--eos", type=int, required=True, help="id do token de fim de documento")
    ap.add_argument("--idiomas-val", default="", help="json opcional: lista de (idioma, n_tokens) na ordem do val.bin")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--procs", type=int, default=40)
    args = ap.parse_args()

    t0 = time.time()
    val = np.fromfile(args.val, dtype=np.uint16)
    # documentos = trechos entre EOS
    fins = np.flatnonzero(val == args.eos)
    inis = np.concatenate([[0], fins[:-1] + 1])
    docs = [(int(i), int(f)) for i, f in zip(inis, fins) if f - i >= N]
    print(f"holdout: {len(val):,} tokens · {len(docs):,} documentos com >= {N} tokens", flush=True)

    # hashes do holdout, com o documento de origem
    hs, dono = [], []
    for k, (i, f) in enumerate(docs):
        h = hashes_13gram(val[i:f])
        hs.append(h); dono.append(np.full(len(h), k, dtype=np.int32))
    hs = np.concatenate(hs); dono = np.concatenate(dono)
    ordem = np.argsort(hs, kind="stable")
    hs, dono = hs[ordem], dono[ordem]
    alvo, primeiro = np.unique(hs, return_index=True)
    alvo_path = args.saida + ".alvo.npy"
    np.save(alvo_path, alvo)
    print(f"holdout: {len(hs):,} 13-gramas · {len(alvo):,} unicos · alvo salvo · {time.time()-t0:.0f}s", flush=True)

    # varredura COMPLETA do treino, em fatias
    n_train = os.path.getsize(args.train) // 2
    fatias = np.linspace(0, n_train, args.procs + 1, dtype=np.int64)
    trabalhos = [(args.train, int(fatias[k]), int(fatias[k + 1]), alvo_path) for k in range(args.procs)]
    print(f"treino: {n_train:,} tokens · {args.procs} fatias · varrendo...", flush=True)
    with Pool(args.procs) as pool:
        partes = pool.map(_fatia, trabalhos)
    achado_unico = np.any(np.stack(partes), axis=0)              # por hash unico
    print(f"varredura: {time.time()-t0:.0f}s · 13-gramas unicos do holdout presentes no treino: "
          f"{achado_unico.sum():,} de {len(alvo):,} ({100*achado_unico.mean():.2f}%)", flush=True)

    # de volta ao documento: fracao dos 13-gramas de cada doc que estao no treino
    pos = np.searchsorted(alvo, hs)                              # cada 13-grama do holdout -> indice unico
    hit = achado_unico[pos]
    n_por_doc = np.bincount(dono, minlength=len(docs))
    hit_por_doc = np.bincount(dono, weights=hit, minlength=len(docs))
    frac = hit_por_doc / np.maximum(n_por_doc, 1)

    # idioma por documento, se fornecido (lista de (idioma, n_tokens) na ordem do arquivo)
    idioma_doc = ["?"] * len(docs)
    if args.idiomas_val:
        faixas = json.load(open(args.idiomas_val, encoding="utf-8"))
        limites, acc = [], 0
        for nome, n in faixas:
            acc += n; limites.append((acc, nome))
        for k, (i, f) in enumerate(docs):
            for lim, nome in limites:
                if i < lim:
                    idioma_doc[k] = nome; break

    def resumo(mask):
        f = frac[mask]
        return {"docs": int(mask.sum()), "frac_media": float(f.mean()) if len(f) else None,
                "docs_frac>=0.5": int((f >= 0.5).sum()), "docs_frac>=0.8": int((f >= 0.8).sum()),
                "docs_frac>=0.2": int((f >= 0.2).sum()),
                "hist": {f"{lo:.1f}-{lo+0.1:.1f}": int(((f >= lo) & (f < lo + 0.1)).sum()) for lo in np.arange(0, 1.0, 0.1)}}

    saida = {"_o_que_mede": "fracao dos 13-gramas (tokens) de cada doc do holdout presentes em QUALQUER lugar do treino; "
                            "censo completo dos dois lados (§2ac)",
             "n": N, "eos": args.eos, "holdout_tokens": int(len(val)), "holdout_docs": len(docs),
             "treino_tokens": int(n_train), "ngrams_unicos_holdout": int(len(alvo)),
             "ngrams_unicos_presentes_no_treino": int(achado_unico.sum()),
             "geral": resumo(np.ones(len(docs), dtype=bool)),
             "por_idioma": {nome: resumo(np.array([x == nome for x in idioma_doc])) for nome in sorted(set(idioma_doc))},
             "piores": [{"doc": int(k), "idioma": idioma_doc[k], "frac": float(frac[k]), "tokens": int(n_por_doc[k]),
                         "ini": docs[k][0]} for k in np.argsort(-frac)[:40]],
             "segundos": round(time.time() - t0)}
    # ✅ vetor POR DOCUMENTO (ini, fim, frac), para medir o efeito na loss depois — o resumo
    #    sozinho nao permite separar docs limpos de contaminados.
    np.save(args.saida + ".por_doc.npy", np.array([(i, f, float(frac[k])) for k, (i, f) in enumerate(docs)], dtype=np.float64))
    json.dump(saida, open(args.saida, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    g = saida["geral"]
    print(f"\nGERAL: {g['docs']:,} docs · frac media {g['frac_media']:.4f} · >=0,5: {g['docs_frac>=0.5']} · >=0,8: {g['docs_frac>=0.8']}")
    for nome, r in saida["por_idioma"].items():
        print(f"  {nome:14s} {r['docs']:6,} docs · media {r['frac_media']:.4f} · >=0,5: {r['docs_frac>=0.5']:4d} · >=0,8: {r['docs_frac>=0.8']:4d}")
    os.remove(alvo_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
