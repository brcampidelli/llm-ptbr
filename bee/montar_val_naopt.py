"""Constroi a metade NAO-PT do conjunto de VALIDACAO, e PROVA que ela nao esta no treino.

🔴 POR QUE ELA FALTA. O `montar_pool_1g.py` reservou val do portugues a partir de documentos NAO
   usados no treino. O `tokenizar_naopt_1g.py` nao reservou nada: ele para exatamente na cota.
   Ficar so' com o val de PT faria a curva de validacao de um modelo treinado em 50%% nao-PT
   medir apenas metade do objetivo — e uma curva que nao ve metade do treino nao serve de monitor.

⭐ DE ONDE VEM, sem sobreposicao por CONSTRUCAO: o treino consumiu os shards de cada idioma na
   ordem crescente e parou na cota (~57%% do idioma). Este script le' na ordem INVERSA, do ultimo
   shard para tras. Os documentos sao outros porque estao no fim do que o treino nem alcancou.

⚠️ MAS CONSTRUCAO NAO E' PROVA (§2o). O projeto ja' montou uma separacao "disjunta por
   construcao" que vazou 265 documentos por um descasamento de roteamento; o conserto nao foi
   caçar o descasamento, foi uma GUARDA POSTERIOR sobre os arquivos finais. Aqui e' a mesma
   coisa: depois de montar, cada documento do val e' conferido por fingerprint contra TODOS os
   11,9M documentos do treino, e a sobreposicao tem de ser ZERO.

⚠️ O filtro de holdout continua valendo aqui: val e holdout sao coisas diferentes, e um documento
   do holdout do gate nao pode virar val — senao a decisao de treino passa a olhar a regua final.

Uso:
    python bee/montar_val_naopt.py --tokens 2e7
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
TREINO = ROOT / "pool" / "naopt.bin"
TOK = "bee/tok_t1/64k-multi"
VOCAB = 64_000
EOS = 0
HOLDOUT_PCT = 2
PREFIXO = 32
IDIOMAS = ["spa", "fra", "deu", "eng", "arb", "cmn", "jpn"]


def no_holdout(t: str) -> bool:
    """True = pertence ao holdout do gate, logo fica fora TAMBEM do val."""
    return int(hashlib.sha1(t.encode("utf-8")).hexdigest()[:8], 16) % 100 < HOLDOUT_PCT


def um_idioma(args_t):
    """Le' os shards de UM idioma na ordem INVERSA e tokeniza ate' a cota de val."""
    import numpy as np
    import zstandard as zstd
    from transformers import AutoTokenizer

    cod, cota = args_t
    tok = AutoTokenizer.from_pretrained(str(ROOT / TOK))
    eos = tok.convert_tokens_to_ids("<|endoftext|>")
    saida = ROOT / "pool" / "val_naopt_partes" / f"{cod}.bin"
    saida.parent.mkdir(parents=True, exist_ok=True)

    n_tok = n_doc = 0
    n_max = 0
    buf: list[str] = []
    with open(saida, "wb") as fh:
        def descarrega():
            nonlocal buf, n_tok, n_doc, n_max
            if not buf:
                return
            for ids in tok(buf, add_special_tokens=False)["input_ids"]:
                if n_tok >= cota:
                    break
                ids = ids + [eos]
                n_max = max(n_max, max(ids))
                np.asarray(ids, dtype=np.uint16).tofile(fh)
                n_tok += len(ids)
                n_doc += 1
            buf = []

        # ⭐ ordem INVERSA: o treino leu do primeiro shard para a frente e parou na cota
        for shard in sorted(glob.glob(str(CORPUS / f"bee_corpus_{cod}_*.jsonl.zst")), reverse=True):
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
                    if no_holdout(t):
                        continue
                    buf.append(t)
                    if len(buf) >= 500:
                        descarrega()
                        if n_tok >= cota:
                            break
        descarrega()
    return {"idioma": cod, "tokens": n_tok, "docs": n_doc, "max_id": n_max}


def fingerprints(caminho: Path, prefixo: int) -> set:
    """Fingerprint (primeiros N tokens) de cada documento de um .bin."""
    import numpy as np

    d = np.fromfile(caminho, dtype=np.uint16)
    fim = np.flatnonzero(d == EOS)
    ini = np.concatenate(([0], fim[:-1] + 1))
    fp = set()
    for a, b in zip(ini, fim):
        p = d[a:b][:prefixo]
        if len(p) == prefixo:
            fp.add(p.tobytes())
    return fp


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokens", type=float, default=2e7, help="tokens de val nao-PT no total")
    ap.add_argument("--processos", type=int, default=7)
    args = ap.parse_args()

    import numpy as np

    cota = int(args.tokens) // len(IDIOMAS)
    print(f"val nao-PT: {args.tokens/1e6:.0f}M tokens · {cota/1e6:.2f}M por idioma · "
          f"shards lidos em ordem INVERSA\n")

    from concurrent.futures import ProcessPoolExecutor
    t0 = time.time()
    res = []
    with ProcessPoolExecutor(max_workers=args.processos) as ex:
        for r in ex.map(um_idioma, [(c, cota) for c in IDIOMAS]):
            res.append(r)
            print(f"  {r['idioma']}: {r['tokens']/1e6:.2f}M tok · {r['docs']:,} docs", flush=True)

    partes = [ROOT / "pool" / "val_naopt_partes" / f"{c}.bin" for c in IDIOMAS]
    alvo = ROOT / "pool" / "val_naopt.bin"
    with open(alvo, "wb") as out:
        for p in partes:
            out.write(p.read_bytes())

    # ---- §2o: construcao nao e' prova. Conferir contra o treino INTEIRO ----
    print(f"\nconferindo sobreposicao com o treino ({TREINO.name}, censo COMPLETO)...")
    fp_val = fingerprints(alvo, PREFIXO)
    fp_tr = fingerprints(TREINO, PREFIXO)
    inter = fp_val & fp_tr
    print(f"  val: {len(fp_val):,} fingerprints · treino: {len(fp_tr):,} · "
          f"SOBREPOSICAO: {len(inter):,}")

    # 🔴 MEDIDO 2026-09-06: a construcao ACHOU QUE ERA disjunta e NAO ERA — 337 dos 22.745
    #    documentos do val tinham fingerprint dentro do treino. Ler os shards ao contrario poe o
    #    val no fim do idioma, longe da cota, mas nao impede que o MESMO documento (ou um que
    #    compartilhe os 32 tokens iniciais — boilerplate de cabecalho) apareca nos dois pontos.
    #    §2o outra vez: guarda posterior sobre o ARQUIVO FINAL, nunca confianca na construcao.
    #    O conserto nao e' cacar a causa: e' FILTRAR e reconferir ate' dar zero.
    if inter:
        print(f"  filtrando {len(inter):,} documentos sobrepostos e reescrevendo o val...")
        d = np.fromfile(alvo, dtype=np.uint16)
        fim = np.flatnonzero(d == EOS)
        ini = np.concatenate(([0], fim[:-1] + 1))
        with open(alvo.with_suffix(".bin.tmp"), "wb") as fh:
            for a, b in zip(ini, fim):
                if d[a:b][:PREFIXO].tobytes() in inter:
                    continue
                d[a:b + 1].tofile(fh)
        os.replace(alvo.with_suffix(".bin.tmp"), alvo)
        fp_val = fingerprints(alvo, PREFIXO)
        inter = fp_val & fp_tr
        print(f"  apos filtrar: {len(fp_val):,} fingerprints · SOBREPOSICAO: {len(inter):,}")

    va = np.fromfile(alvo, dtype=np.uint16)
    erros = []
    if inter:
        erros.append(f"{len(inter)} documentos do val AINDA estao no treino apos filtrar")
    if int(va.max()) >= VOCAB:
        erros.append(f"max_id {int(va.max())} >= vocab {VOCAB}")
    if len(va) < args.tokens * 0.9:
        erros.append(f"val tem {len(va):,} tokens, esperado ~{int(args.tokens):,}")
    if erros:
        for e in erros:
            print(f"🔴 {e}")
        raise SystemExit("🔴 guardas falharam")

    doc = {"_val": "metade NAO-PT do conjunto de validacao do Bee-1G",
           "_origem": "shards lidos em ordem INVERSA — o treino leu do inicio e parou na cota",
           "_prova": f"sobreposicao com {TREINO.name} conferida por fingerprint de {PREFIXO} "
                     f"tokens sobre TODOS os documentos dos dois lados: {len(inter)}",
           "_holdout": f"documentos com sha1 % 100 < {HOLDOUT_PCT} ficam fora tambem do val — "
                       "val e holdout sao coisas diferentes e nao podem se misturar",
           "tokens": int(len(va)), "por_idioma": {r["idioma"]: r for r in res},
           "fingerprints_val": len(fp_val), "fingerprints_treino": len(fp_tr),
           "sobreposicao": len(inter), "minutos": (time.time() - t0) / 60}
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "val-naopt-1g.json").write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\n✅ val nao-PT: {len(va)/1e6:.2f}M tokens · sobreposicao ZERO · "
          f"{(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
