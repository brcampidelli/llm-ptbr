"""O corpus PT de treino contem documentos do HOLDOUT de PT? Censo COMPLETO, sem decodificar.

🔴 POR QUE ISTO E' NECESSARIO ANTES DE MONTAR O POOL. O `corpus_pt` (23,868B tokens) e o
   `corpus_multi` PT vieram os DOIS do fineweb-2 portugues, em coletas diferentes. O holdout do
   projeto e' `sha1(texto) % 100 < 2` — um hash de CONTEUDO, nao de posicao — entao ele e'
   disjunto por construcao DENTRO de um corpus, mas nada garante que um documento do holdout de
   `corpus_multi` nao esteja tambem dentro de `corpus_pt`. Se estiver, o Bee-1G treina nele e a
   ancora de PT do Gate T4 (0,8576 no `corpus_multi_pt`) mede memorizacao, nao capacidade.

⚠️ E NAO DA' PARA APLICAR O FILTRO DIRETO: o `corpus_pt_64k` e' TOKEN, nao texto, e o filtro
   precisa de `sha1(texto)`. Decodificar 23,868B tokens custaria outras ~6 h de CPU.

⭐ A SAIDA: os dois lados usam o MESMO tokenizador 64k. Logo um documento presente nos dois tem
   o MESMO prefixo de tokens. Fingerprint = hash dos primeiros N tokens do documento, calculado
   nos dois lados — e a comparacao vira um `set` de inteiros sobre um passe de numpy. Sem
   decodificar nada.

⚠️ CENSO COMPLETO, NUNCA PILOTO (§2ac). Detectar coincidencia entre DOIS conjuntos exige que os
   dois lados estejam inteiros: amostrar o corpus subestimaria a sobreposicao pela fracao
   amostrada, e imprimiria "limpo" com a mesma cara. O lado do holdout ja' e' pequeno; o lado do
   corpus e' varrido inteiro, shard a shard.

⚠️ O QUE ISTO NAO MOSTRA:
   · quase-duplicata — o fingerprint e' de prefixo EXATO. Documento reescrito passa;
   · contaminacao vinda de outra fonte que nao o `corpus_multi` PT;
   · o holdout `wiki`, que e' de outra origem (Wikipedia) e nao e' coberto aqui.

Uso:
    python bee/checar_contaminacao_pt.py
    python bee/checar_contaminacao_pt.py --prefixo 32 --faixas A,B
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
CORPUS_TOK = ROOT / "corpus_pt_64k"
TOK_64K = "bee/tok_t1/64k-multi"
EOS = 0
HOLDOUT_PCT = 2


def docs_do_holdout_wiki():
    """Os 300 documentos do holdout Wikipedia-PT, como TEXTO.

    🔴 POR QUE ESTE TAMBEM PRECISA SER CONFERIDO, e completo. O `gate_faixas.py` ja' checou
    sobreposicao wiki x pool — mas AMOSTRADA: 20 8-gramas por documento, contra um passo de 8
    sobre os primeiros 40M tokens do pool. §2ac: detectar coincidencia entre dois conjuntos exige
    os dois INTEIROS; amostrar subestima pela fracao amostrada e imprime "limpo" com a mesma cara.
    Aquele check varreu 40M de 100M tokens de um pool que hoje tem 23,868B — fracao ~0,17%.
    """
    p = ROOT / "bee" / "gate" / "holdout_wiki.json"
    if not p.exists():
        raise SystemExit(f"🔴 {p} nao existe")
    for t in json.loads(p.read_text(encoding="utf-8")):
        yield t


def docs_do_holdout_pt():
    """Todos os documentos PT de `corpus_multi` que caem no balde de holdout.

    ⚠️ Pega o holdout INTEIRO, nao o recorte de 1,5 MB que a ancora usa: se amanha o teto da
    ancora subir, os documentos novos ja' terao sido conferidos. Verificar de menos aqui e'
    exatamente o erro que a §2ac descreve.
    """
    import zstandard as zstd

    n_total = 0
    for shard in sorted(glob.glob(str(ROOT / "bee" / "corpus_multi" / "bee_corpus_por_*.jsonl.zst"))):
        bruto = zstd.ZstdDecompressor().decompress(open(shard, "rb").read()).decode("utf-8")
        for linha in bruto.splitlines():
            if not linha.strip():
                continue
            try:
                t = json.loads(linha)["text"]
            except Exception:
                continue
            n_total += 1
            if int(hashlib.sha1(t.encode("utf-8")).hexdigest()[:8], 16) % 100 < HOLDOUT_PCT:
                yield t
    if n_total == 0:
        raise SystemExit("🔴 nenhum documento PT lido de bee/corpus_multi — caminho errado?")


def fingerprints_do_shard(args_t):
    """Fingerprints de TODOS os documentos de um shard de token. Roda em processo proprio."""
    import numpy as np

    caminho, prefixo = args_t
    dados = np.fromfile(caminho, dtype=np.uint16)
    fim = np.flatnonzero(dados == EOS)
    ini = np.concatenate(([0], fim[:-1] + 1))
    fp = set()
    curtos = 0
    for a, b in zip(ini, fim):
        pedaco = dados[a:b][:prefixo]
        if len(pedaco) < prefixo:          # documento curto demais para o fingerprint
            curtos += 1
            continue
        fp.add(pedaco.tobytes())
    return caminho, fp, len(ini), curtos


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prefixo", type=int, default=32,
                    help="tokens do inicio de cada documento que formam o fingerprint")
    ap.add_argument("--faixas", default="A,B,C", help="faixas de qualidade a varrer")
    ap.add_argument("--processos", type=int, default=6)
    ap.add_argument("--holdout", choices=["corpus_multi_pt", "wiki"],
                    default="corpus_multi_pt",
                    help="qual holdout de PT conferir contra o corpus de treino")
    args = ap.parse_args()

    import numpy as np
    from transformers import AutoTokenizer

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(str(ROOT / TOK_64K))

    fonte = (docs_do_holdout_pt if args.holdout == "corpus_multi_pt"
             else docs_do_holdout_wiki)
    print(f"1. tokenizando o holdout {args.holdout} (INTEIRO, nao um recorte)")
    alvo, curtos_h = {}, 0
    for t in fonte():
        ids = tok(t, add_special_tokens=False)["input_ids"][:args.prefixo]
        if len(ids) < args.prefixo:
            curtos_h += 1
            continue
        alvo[np.asarray(ids, dtype=np.uint16).tobytes()] = t[:80]
    print(f"   {len(alvo):,} fingerprints de holdout · {curtos_h} documentos curtos demais "
          f"(prefixo {args.prefixo} tokens)")
    if not alvo:
        raise SystemExit("🔴 nenhum fingerprint de holdout — a guarda estaria inerte (§2t)")

    faixas = [f.strip() for f in args.faixas.split(",") if f.strip()]
    shards = sorted(p for f in faixas
                    for p in glob.glob(str(CORPUS_TOK / f"pt_{f}_*.bin")))
    print(f"\n2. varrendo {len(shards)} shards de token (faixas {','.join(faixas)}) — "
          f"censo COMPLETO, {args.processos} processos")

    from concurrent.futures import ProcessPoolExecutor
    achados: dict[bytes, list[str]] = {}
    n_docs = n_curtos = 0
    with ProcessPoolExecutor(max_workers=args.processos) as ex:
        for i, (cam, fp, nd, nc) in enumerate(
                ex.map(fingerprints_do_shard, [(s, args.prefixo) for s in shards]), 1):
            n_docs += nd
            n_curtos += nc
            for k in fp & alvo.keys():
                achados.setdefault(k, []).append(Path(cam).name)
            if i % 6 == 0 or i == len(shards):
                print(f"   [{i}/{len(shards)}] {n_docs/1e6:.1f}M docs · "
                      f"{len(achados)} colisoes ate' aqui", flush=True)

    taxa = 100 * len(achados) / max(1, len(alvo))
    print(f"\n{'='*72}")
    print(f"documentos do holdout PT ............ {len(alvo):,}")
    print(f"documentos varridos no corpus ....... {n_docs:,}  ({n_curtos:,} curtos, sem fingerprint)")
    print(f"COLISOES (holdout dentro do treino) . {len(achados):,}  = {taxa:.3f}% do holdout")
    print("=" * 72)

    doc = {"_check": f"holdout {args.holdout} dentro do corpus de treino",
           "_regua": f"fingerprint = primeiros {args.prefixo} tokens no 64k-multi; "
                     f"censo COMPLETO das faixas {','.join(faixas)}",
           "_nao_mostra": [
               "quase-duplicata: o fingerprint e' de prefixo EXATO, documento reescrito passa",
               "contaminacao de outra origem que nao o corpus_multi PT",
               "o holdout `wiki`, que vem da Wikipedia e nao e' coberto aqui",
               f"documentos com menos de {args.prefixo} tokens ficam de fora dos dois lados",
           ],
           "prefixo_tokens": args.prefixo, "faixas": faixas,
           "docs_holdout": len(alvo), "docs_corpus": n_docs, "docs_curtos": n_curtos,
           "colisoes": len(achados), "taxa_pct": taxa,
           # 🔴 os fingerprints TEM de vir no artefato: a mensagem final dizia "os
           #    fingerprints estao no artefato" e so' os 5 exemplos de texto vinham —
           #    guarda que AFIRMA o que o codigo nao faz (§2t). Sem eles, quem monta o
           #    pool nao tem como excluir os documentos, que e' o unico uso deste check.
           "fingerprints_contaminados": [k.hex() for k in achados],
           "exemplos": [alvo[k] for k in list(achados)[:5]],
           "minutos": (time.time() - t0) / 60}
    dest = ROOT / "docs" / f"contaminacao-pt-{args.holdout}.json"
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(dest)

    if achados:
        print("\n🔴 HA' CONTAMINACAO. A ancora de PT do Gate T4 mediria memorizacao em parte.")
        print("   O pool tem de EXCLUIR estes documentos — os fingerprints estao no artefato.")
        for k in list(achados)[:3]:
            print(f'     {achados[k][0]}: "{alvo[k][:70]}..."')
    else:
        print("\n✅ ZERO colisoes: os dois corpora sao disjuntos no prefixo medido, e a ancora")
        print("   de PT nao esta' contaminada por esta via.")
        print("   ⚠️ Isto NAO cobre quase-duplicata — o fingerprint e' de prefixo exato.")
    print(f"\nartefato: docs/{dest.name}  ({(time.time()-t0)/60:.1f} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
