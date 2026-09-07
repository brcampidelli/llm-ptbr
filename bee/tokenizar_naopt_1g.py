"""Tokeniza a METADE NAO-PT do pool `pt-50` — 10B tokens, 7 idiomas, filtrando o holdout.

⭐ AQUI DA' PARA FAZER CERTO O QUE NO PT NAO DEU. O `corpus_pt` so' existe como TOKEN (o texto
   cru foi apagado), entao a exclusao de holdout la' teve de ser por fingerprint de prefixo — que
   pega duplicata exata de 32 tokens e deixa passar quase-duplicata. Aqui os shards sao TEXTO,
   entao aplica-se o filtro CANONICO do projeto, `sha1(texto) % 100 < 2`, documento a documento.

🔴 E ELE E' NECESSARIO. O `corpus_multi_1g` e o `corpus_multi` sao prefixos do MESMO stream do
   fineweb-2, coletados em momentos diferentes — exatamente a situacao que, no portugues, pos
   **56,1% do holdout dentro do corpus de treino**. Sem este filtro, o bpb por idioma do Gate T4
   mediria memorizacao nos sete idiomas.

⚠️ GUARDA DE POLARIDADE, dos DOIS lados (§2q). Ja' inverti este filtro uma vez neste projeto e
   montei os pools A PARTIR do holdout. A taxa de descarte tem de cair em [PCT/3, PCT*3]:
   fora disso, ou o filtro esta' invertido (descarta ~98%) ou esta' morto (descarta 0%). As duas
   falhas sao silenciosas — o arquivo sai, com o tamanho certo.

⚠️ O QUE ISTO NAO FAZ: dedup. A dedup do fineweb-2 e' POR CRAWL, entao duplicata entre crawls
   sobrevive por construcao — medido em 2026-09-01 no FineWeb: 0,682% exata, 0,975% quase.
   Nestes sete idiomas isso nunca foi medido; roda depois, sobre o .bin resultante.

Uso:
    python bee/tokenizar_naopt_1g.py --tokens 10e9 --processos 24
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "bee" / "corpus_multi_1g"
TOK = "bee/tok_t1/64k-multi"
VOCAB = 64_000
HOLDOUT_PCT = 2
IDIOMAS = ["spa", "fra", "deu", "eng", "arb", "cmn", "jpn"]


def no_holdout(t: str) -> bool:
    """True = o documento PERTENCE ao holdout, logo NAO pode entrar no treino.

    🔴 O nome e' portugues e ja' me enganou: eu li como o ingles "no holdout" (= fora do
    holdout) e inverti o uso. Mantido identico ao `gate_t1_bpb._no_holdout` para que os dois
    gates concordem por construcao, e com este comentario para nao acontecer de novo.
    """
    return int(hashlib.sha1(t.encode("utf-8")).hexdigest()[:8], 16) % 100 < HOLDOUT_PCT


def um_idioma(args_t):
    """Tokeniza UM idioma ate' a cota. Roda em processo proprio."""
    import numpy as np
    import zstandard as zstd
    from transformers import AutoTokenizer

    cod, cota, lote_docs = args_t
    tok = AutoTokenizer.from_pretrained(str(ROOT / TOK))
    eos = tok.convert_tokens_to_ids("<|endoftext|>")
    saida = CORPUS.parent / "pool_naopt" / f"{cod}.bin"
    saida.parent.mkdir(parents=True, exist_ok=True)
    tmp = saida.with_suffix(".bin.tmp")

    t0 = time.time()
    n_tok = n_doc = n_desc = n_vistos = 0
    n_max = 0
    buf: list[str] = []
    with open(tmp, "wb") as fh:
        def descarrega():
            nonlocal buf, n_tok, n_doc, n_max
            if not buf:
                return
            for ids in tok(buf, add_special_tokens=False)["input_ids"]:
                # 🔴 MEDIDO 2026-09-06: o corte estava DEPOIS do lote inteiro, entao um lote de
                #    2.000 documentos (~2M tokens) ultrapassava a cota — em ensaio de 10M por
                #    idioma o excesso chegou a 25%%. Funcionaria na escala real (0,14%%) e por
                #    isso e' perigoso: a guarda passaria sem que o corte estivesse certo.
                #    Agora para no documento, e o excesso e' de no maximo um documento.
                if n_tok >= cota:
                    break
                ids = ids + [eos]
                n_max = max(n_max, max(ids))
                np.asarray(ids, dtype=np.uint16).tofile(fh)
                n_tok += len(ids)
                n_doc += 1
            buf = []

        for shard in sorted(glob.glob(str(CORPUS / f"bee_corpus_{cod}_*.jsonl.zst"))):
            if n_tok >= cota:
                break
            with open(shard, "rb") as f:
                leitor = zstd.ZstdDecompressor().stream_reader(f)
                for linha in io.TextIOWrapper(leitor, encoding="utf-8"):
                    if not linha.strip():
                        continue
                    try:
                        t = json.loads(linha)["text"]
                    except Exception:
                        continue
                    n_vistos += 1
                    if no_holdout(t):          # cai no holdout -> FORA do treino
                        n_desc += 1
                        continue
                    buf.append(t)
                    if len(buf) >= lote_docs:
                        descarrega()
                        if n_tok >= cota:
                            break
        descarrega()

    os.replace(tmp, saida)
    return {"idioma": cod, "tokens": n_tok, "docs": n_doc, "descartados": n_desc,
            "vistos": n_vistos, "max_id": n_max, "minutos": (time.time() - t0) / 60,
            "taxa_descarte_pct": 100 * n_desc / max(1, n_vistos)}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokens", type=float, default=10e9)
    ap.add_argument("--processos", type=int, default=7)
    ap.add_argument("--lote-docs", type=int, default=2000)
    args = ap.parse_args()

    cota = int(args.tokens) // len(IDIOMAS)
    print(f"metade nao-PT: {args.tokens/1e9:.1f}B tokens em {len(IDIOMAS)} idiomas "
          f"= {cota/1e9:.3f}B cada · {args.processos} processos")
    print(f"filtro de holdout: sha1(texto) %% 100 < {HOLDOUT_PCT} sai do treino\n")

    from concurrent.futures import ProcessPoolExecutor
    t0 = time.time()
    res = []
    with ProcessPoolExecutor(max_workers=args.processos) as ex:
        for r in ex.map(um_idioma, [(c, cota, args.lote_docs) for c in IDIOMAS]):
            res.append(r)
            print(f"  {r['idioma']}: {r['tokens']/1e9:.3f}B tok · {r['docs']:,} docs · "
                  f"descartou {r['taxa_descarte_pct']:.2f}% · max_id {r['max_id']} · "
                  f"{r['minutos']:.1f} min", flush=True)

    # ---- guardas ----
    erros = []
    for r in res:
        # §2q: polaridade, dos DOIS lados — invertido descarta ~98%, morto descarta 0
        if not (HOLDOUT_PCT / 3 <= r["taxa_descarte_pct"] <= HOLDOUT_PCT * 3):
            erros.append(f"{r['idioma']}: descarte {r['taxa_descarte_pct']:.2f}% fora de "
                         f"[{HOLDOUT_PCT/3:.2f}, {HOLDOUT_PCT*3:.0f}] — filtro invertido ou morto")
        if r["max_id"] >= VOCAB:
            erros.append(f"{r['idioma']}: max_id {r['max_id']} >= vocab {VOCAB}")
        if abs(r["tokens"] - cota) / cota > 0.02:
            erros.append(f"{r['idioma']}: {r['tokens']:,} tokens, cota {cota:,} — desvio > 2%")
    if erros:
        for e in erros:
            print(f"🔴 {e}")
        raise SystemExit("🔴 guardas falharam — nada a promover")

    tot = sum(r["tokens"] for r in res)
    doc = {"_pool": "metade NAO-PT do pt-50 do Bee-1G",
           "_filtro": f"sha1(texto) % 100 < {HOLDOUT_PCT} FORA do treino — o filtro canonico do "
                      "projeto, aplicado sobre TEXTO (no PT so' deu para usar fingerprint de "
                      "prefixo, porque o texto cru foi apagado)",
           "_nao_faz": ["dedup: a do fineweb-2 e' POR CRAWL e duplicata entre crawls sobrevive "
                        "por construcao; o censo de repeticao roda depois, sobre o .bin",
                        "balanceamento por dificuldade: sao 1/7 do orcamento para cada idioma, "
                        "por decisao, nao por medicao"],
           "tokens_total": tot, "cota_por_idioma": cota,
           "por_idioma": {r["idioma"]: r for r in res},
           "minutos": (time.time() - t0) / 60}
    dest = ROOT / "docs" / "pool-naopt-1g.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\n{'='*72}")
    print(f"total {tot/1e9:.3f}B tokens · {sum(r['docs'] for r in res):,} docs · "
          f"{tot*2/1e9:.1f} GB")
    print(f"descarte medio {sum(r['taxa_descarte_pct'] for r in res)/len(res):.2f}% "
          f"(esperado ~{HOLDOUT_PCT}%)")
    print("=" * 72)
    print(f"✅ guardas passaram · {(time.time()-t0)/60:.1f} min · artefato docs/{dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
