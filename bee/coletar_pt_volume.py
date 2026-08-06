"""Coleta de portugues EM VOLUME a partir do fineweb-2 por_Latn, com filtro em FAIXAS.

⭐ POR QUE ESTE SCRIPT EXISTE (2026-08-06)
  A medicao contra o Tucano-160m (docs/gate-tucano.md) mostrou que a causa n1 do Bee ser
  fraco e' VOLUME DE PORTUGUES: temos ~6,9B tokens PT (o corpus e' ~70% PT) contra ~200B
  do Tucano, de mesmo tamanho e 1,88x melhor em texto limpo. Este script fecha essa
  distancia. Saida 100% PT — sem ingles, sem codigo.

⭐ POR QUE FAIXAS EM VEZ DE UM CORTE
  Duas medicoes nossas, lado a lado:
    gate pareado a 131M tokens : filtrar a 10% da +1,6% de bpb, e NAO cresce com escala
    Tucano                     : 20x mais token da +88%
  Volume vence filtro por ~50x. Cortar a 10% jogaria fora 90% do corpus por 1,6%. Entao a
  passada (cara) pontua TUDO uma vez e escreve em tres arquivos por faixa; o corte vira um
  botao barato depois — treinar com A, A+B ou A+B+C. Uma varredura, tres corpora.

⭐ NUMEROS MEDIDOS (2026-08-06, parquet real 000_00000)
    3.502.000 docs/parquet · 3.940 bytes/doc · 13,8 GB de texto · ~3,05B tokens crus
    66 parquets => ~201B tokens crus na fonte. ~30B de saida vem de ~13 parquets.

  Custo por documento, medido (o que determinou o desenho):
    filtro de qualidade  0,28 ms   | hash exato (blake2b)  0,006 ms
    MinHash/LSH          1,94 ms   | TF-IDF + Ridge        1,32 ms  | tokenizar 0,24 ms
  MinHash sozinho custava mais que todo o resto somado, para pegar ~0,9% de duplicata
  (medido em 2026-08-04). Trocado por hash EXATO, 320x mais barato. E como TF-IDF domina
  o que sobrou e nao paraleliza sozinho, o trabalho e' dividido POR PARQUET entre processos.

⚠️ ARMADILHAS QUE ESTE SCRIPT DEFENDE (todas ja custaram caro neste projeto)
  1. `qualidade_ok` devolve None quando o documento PRESTA. Usar `if qualidade_ok(t):`
     coleta as strings de motivo e produz numeros absurdos em silencio.
  2. O limiar e' calibrado UMA vez, no processo pai, e passado pronto aos trabalhadores.
     Recalibrar por parquet faria de cada arquivo uma politica diferente — a saida seria
     uma mistura, nao um criterio.
  3. Os parquets sao apagados apos o uso. Sao 4,85 GB cada; com N processos ha N deles em
     disco ao mesmo tempo.
  4. Checagem de ordem de grandeza contra numero CONHECIDO (fertilidade em fineweb2-por).
     Ja reintroduzi um bug de bpb num script novo depois de documenta-lo — revisar o
     codigo nao basta, tem que bater com um numero que ja se conhece.

⚠️ LIMITACAO ACEITA CONSCIENTEMENTE: o dedup e' EXATO e por parquet. Nao pega
  quase-duplicata, e nao cruza a fronteira entre parquets. O fineweb-2 ja deduplica dentro
  de cada dump; medimos 0,90% de duplicata cruzando fronteira na coleta antiga. Pagar 1,94
  ms/doc (= dobrar o tempo total) por ~1% nao se justifica quando o objetivo declarado e'
  VOLUME. Se algum dia importar, rodar bee/medir_dedup.py sobre a saida.

⚠️ NO WINDOWS: `ls`/`Get-ChildItem` mostram tamanho ZERO ou desatualizado para os .bin
  enquanto o processo escreve — o NTFS so' atualiza a entrada de diretorio quando o handle
  fecha, e `np.tofile` escreve direto no descritor. Isso ja me fez cacar um bug que nao
  existia. O registro autoritativo e' o `estado.json`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))

REPO = "HuggingFaceFW/fineweb-2"
# Fertilidade do tokenizador do Bee em `fineweb2-por` PURO, medida em 2026-08-06:
# 0,2213 tok/byte = 4,52 bytes/token.
# ⚠️ NAO usar aqui o 0,3114 do Gate 2: aquele e' a media da MISTURA do holdout
# (fineweb2-por + portuguese-pd), e os livros de dominio publico — ortografia antiga,
# ruido de OCR — tokenizam muito pior que web limpa. Aplicar media de duas fontes como
# referencia de uma fonte so' fez o guarda abortar uma coleta CORRETA na 1a tentativa.
FERT_ESPERADA = 0.2213
FAIXAS = ("A", "B", "C")            # A = melhor

_G: dict = {}                       # estado por processo trabalhador


def humano(n: float) -> str:
    return f"{n/1e9:.2f}B" if n >= 1e9 else f"{n/1e6:.1f}M"


def _iniciar_worker(tokenizer: str, classificador: str, sem) -> None:
    """Carrega tokenizador e classificador UMA vez por processo (nao por parquet)."""
    import joblib
    from transformers import AutoTokenizer
    _G["tok"] = AutoTokenizer.from_pretrained(tokenizer)
    mod = joblib.load(classificador)
    _G["vet"], _G["reg"] = mod["vetorizador"], mod["regressor"]
    _G["sem"] = sem


def _baixar_com_limite(arq: str, destino: Path) -> Path:
    """Baixa UM parquet respeitando o limite global de downloads simultaneos.

    ⚠️ MEDIDO EM 2026-08-06, e custou uma rodada: com 13 downloads simultaneos e SEM
    token, o HF Hub estrangula ate ZERO — 4 parquets terminaram e os outros 9 ficaram
    parados em 1 MB indefinidamente (0 bytes em 75 s). Nao ha erro, nao ha timeout: as
    conexoes simplesmente nao andam, e o job parece vivo enquanto nao faz nada.

    O limite resolve sem credencial nenhuma: processar um parquet leva ~2,9 h e baixar
    ~10 min, entao 2 downloads por vez sobra para manter 13 trabalhadores ocupados.
    """
    from huggingface_hub import hf_hub_download
    ultimo = None
    for tentativa in range(5):
        try:
            with _G["sem"]:
                return Path(hf_hub_download(REPO, arq, repo_type="dataset",
                                            local_dir=str(destino)))
        except Exception as e:                       # rede/rate-limit: tentar de novo
            ultimo = e
            time.sleep(30 * (tentativa + 1))
    raise RuntimeError(f"falhou baixar {arq} apos 5 tentativas: {ultimo}")


def processar_parquet(tarefa: tuple) -> dict:
    """Baixa, filtra, pontua, tokeniza e grava UM parquet. Roda em processo separado."""
    i, arq, lim, out_dir, tmp_dir, lote_n, manter, limite_docs = tarefa
    import numpy as np
    import pyarrow.parquet as pq
    from expand_corpus import qualidade_ok

    tok, vet, reg = _G["tok"], _G["vet"], _G["reg"]
    out, tmp = Path(out_dir), Path(tmp_dir)
    t0 = time.time()
    cam = _baixar_com_limite(arq, tmp / f"w{i}")
    t_baixa = time.time() - t0

    saidas = {f: open(out / f"pt_{f}_{i:03d}.bin", "wb") for f in FAIXAS}
    st = {"i": i, "vistos": 0, "aprovados": 0, "dup": 0, "bytes": 0,
          "tokens": {f: 0 for f in FAIXAS}}
    vistos_hash: set[bytes] = set()
    buf: list[str] = []

    def drenar():
        if not buf:
            return
        scores = reg.predict(vet.transform([d[:2500] for d in buf]))
        por_faixa: dict[str, list[str]] = {f: [] for f in FAIXAS}
        for texto, s in zip(buf, scores):
            if s >= lim["A"]:
                por_faixa["A"].append(texto)
            elif s >= lim["B"]:
                por_faixa["B"].append(texto)
            elif s >= lim["C"]:
                por_faixa["C"].append(texto)
            # abaixo do limiar de C: descartado
        for f, textos in por_faixa.items():
            if not textos:
                continue
            # ⚠️ Contar os bytes AQUI, dos docs que de fato entram no .bin — nao de todos
            # os aprovados. Somar tokens dos 60% guardados sobre os bytes de 100% dos
            # aprovados da uma "fertilidade" de populacoes diferentes, que nao mede nada
            # e desarma o guarda de sanidade.
            st["bytes"] += sum(len(x.encode("utf-8")) for x in textos)
            ids = tok(textos, add_special_tokens=False)["input_ids"]
            # 0 = <|endoftext|> separa documentos, igual ao prepare_data.py do v3
            plano = [t for seq in ids for t in (seq + [0])]
            np.array(plano, dtype=np.uint16).tofile(saidas[f])
            st["tokens"][f] += len(plano)
        buf.clear()

    try:
        for lote in pq.ParquetFile(cam).iter_batches(batch_size=2000, columns=["text"]):
            for t in lote.column("text").to_pylist():
                st["vistos"] += 1
                if qualidade_ok(t) is not None:      # ⚠️ != None = REJEITADO
                    continue
                h = hashlib.blake2b(t.encode("utf-8"), digest_size=16).digest()
                if h in vistos_hash:
                    st["dup"] += 1
                    continue
                vistos_hash.add(h)
                st["aprovados"] += 1
                buf.append(t)
                if len(buf) >= lote_n:
                    drenar()
            if limite_docs and st["vistos"] >= limite_docs:
                break                                # so' para --limite-docs (teste)
        drenar()
    finally:
        for fh in saidas.values():
            fh.close()
        if not manter:
            try:
                os.remove(cam)
            except OSError:
                pass

    st["segundos"] = time.time() - t0
    st["seg_download"] = t_baixa
    return st


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "corpus_pt")
    ap.add_argument("--parquets", type=int, default=13,
                    help="quantos parquets varrer (~2,4B tokens de saida cada; 13 = ~30B)")
    ap.add_argument("--processos", type=int, default=0, help="0 = nucleos-4")
    ap.add_argument("--tokenizer", type=Path, default=ROOT / "models" / "bee-150m-v3-base")
    ap.add_argument("--classificador", type=Path,
                    default=ROOT / "bee" / "edu" / "classificador.joblib")
    ap.add_argument("--calibrar-com", type=int, default=50_000)
    ap.add_argument("--percentis", default="90,70,40",
                    help="cortes das faixas A,B,C — 90,70,40 = top10%%, 10-30%%, 30-60%%")
    ap.add_argument("--manter-parquet", action="store_true")
    ap.add_argument("--lote", type=int, default=5000)
    ap.add_argument("--downloads", type=int, default=2,
                    help="downloads simultaneos. ⚠️ NAO subir sem token do HF: com 13 "
                         "paralelos e sem autenticacao o Hub estrangula ate zero, em "
                         "silencio (medido em 2026-08-06).")
    ap.add_argument("--limite-docs", type=int, default=0,
                    help="0 = parquet inteiro. >0 corta cada parquet — SO para teste de "
                         "fumaca do caminho paralelo; a saida fica truncada.")
    args = ap.parse_args()

    import multiprocessing as mp

    import joblib
    import numpy as np
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer

    from expand_corpus import listar_parquets, qualidade_ok

    args.out.mkdir(parents=True, exist_ok=True)
    tmp = args.out / "_parquet_tmp"
    tmp.mkdir(exist_ok=True)
    estado_p = args.out / "estado.json"
    n_proc = args.processos or max(1, (os.cpu_count() or 8) - 4)

    arqs = listar_parquets()[:args.parquets]
    mod = joblib.load(args.classificador)

    print("=" * 74)
    print("COLETA PT EM VOLUME — fineweb-2 por_Latn, saida 100% portugues")
    print("=" * 74)
    print(f"  parquets     : {len(arqs)} de 66 (~2,4B tokens de saida cada)")
    print(f"  processos    : {n_proc} (de {os.cpu_count()} nucleos)")
    print(f"  classificador: F1 {mod['f1']:.3f} · correlacao {mod['correlacao']:.3f}")
    print(f"  dedup        : hash EXATO por parquet (MinHash custaria 2x o tempo por ~1%)")

    estado = {"limiares": None, "concluidos": [], "stats": []}
    if estado_p.exists():
        estado.update(json.loads(estado_p.read_text(encoding="utf-8")))

    # ---- calibrar os limiares UMA vez, no pai --------------------------------
    if estado["limiares"] is None:
        tok = AutoTokenizer.from_pretrained(args.tokenizer)
        vet, reg = mod["vetorizador"], mod["regressor"]
        pcts = [float(x) for x in args.percentis.split(",")]
        print(f"\ncalibrando limiares em ate {args.calibrar_com} docs aprovados...")
        cam = Path(hf_hub_download(REPO, arqs[0], repo_type="dataset",
                                   local_dir=str(tmp / "calib")))
        amostra: list[str] = []
        for lote in pq.ParquetFile(cam).iter_batches(batch_size=2000, columns=["text"]):
            for t in lote.column("text").to_pylist():
                if qualidade_ok(t) is None:          # ⚠️ None = o doc PRESTA
                    amostra.append(t)
            if len(amostra) >= args.calibrar_com:
                break
        amostra = amostra[:args.calibrar_com]
        sc = reg.predict(vet.transform([d[:2500] for d in amostra]))
        estado["limiares"] = {f: float(np.percentile(sc, p)) for f, p in zip(FAIXAS, pcts)}
        print(f"  amostra: {len(sc):,} docs · score medio {sc.mean():.3f}")
        for f, p in zip(FAIXAS, pcts):
            print(f"  faixa {f} (p{p:.0f}): score >= {estado['limiares'][f]:.3f}")

        # ---- sanidade contra numero CONHECIDO --------------------------------
        prova = amostra[:200]
        nb = sum(len(t.encode("utf-8")) for t in prova)
        nt = sum(len(x) for x in tok(prova, add_special_tokens=False)["input_ids"])
        fert = nt / nb
        print(f"\n  SANIDADE fertilidade {fert:.4f} tok/byte (ref. {FERT_ESPERADA:.4f})")
        if not (0.75 * FERT_ESPERADA <= fert <= 1.35 * FERT_ESPERADA):
            print("  ERRO: fora da faixa — tokenizador ou campo de texto errado. Abortando.",
                  file=sys.stderr)
            return 1
        if tok.decode(tok(prova[0][:200], add_special_tokens=False)["input_ids"]) != prova[0][:200]:
            print("  ERRO: decode nao fecha com o original. Abortando.", file=sys.stderr)
            return 1
        print("  round-trip do decode: OK")
        estado_p.write_text(json.dumps(estado, indent=2), encoding="utf-8")
        del tok, vet, reg

    lim = estado["limiares"]
    pendentes = [i for i in range(len(arqs)) if i not in estado["concluidos"]]
    if not pendentes:
        print("\n  nada a fazer — todos os parquets ja foram varridos")
    else:
        print(f"\nvarrendo {len(pendentes)} parquets em {n_proc} processos...\n")

    tarefas = [(i, arqs[i], lim, str(args.out), str(tmp), args.lote, args.manter_parquet,
                args.limite_docs) for i in pendentes]
    if args.limite_docs:
        print(f"  ⚠️ MODO TESTE: so os primeiros {args.limite_docs:,} docs de cada parquet")
    t0 = time.time()
    if tarefas:
        ctx = mp.get_context("spawn")
        sem = ctx.Semaphore(args.downloads)
        print(f"  (no maximo {args.downloads} downloads simultaneos)\n")
        with ctx.Pool(n_proc, initializer=_iniciar_worker,
                      initargs=(str(args.tokenizer), str(args.classificador), sem)) as pool:
            for st in pool.imap_unordered(processar_parquet, tarefas):
                estado["concluidos"].append(st["i"])
                estado["stats"].append(st)
                estado_p.write_text(json.dumps(estado, indent=2), encoding="utf-8")
                tot = sum(sum(s["tokens"].values()) for s in estado["stats"])
                feitos = len(estado["concluidos"])
                dt = time.time() - t0
                falta = (dt / max(1, feitos)) * (len(tarefas) - feitos) / 3600
                print(f"  parquet {st['i']:>2} OK · {st['vistos']:>9,} docs "
                      f"({st['aprovados']/max(1,st['vistos']):.0%} aprov · "
                      f"{st['dup']/max(1,st['vistos']):.1%} dup) · "
                      f"{humano(sum(st['tokens'].values())):>6} tokens · "
                      f"{st['segundos']/60:.0f}min ({st['seg_download']/60:.0f} baixando) "
                      f"|| {feitos}/{len(tarefas)} · total {humano(tot)} "
                      f"({tot*2/1e9:.1f} GB) · faltam {falta:.1f}h", flush=True)

    # ---- relatorio ----------------------------------------------------------
    S = estado["stats"]
    tot_faixa = {f: sum(s["tokens"][f] for s in S) for f in FAIXAS}
    tot = sum(tot_faixa.values())
    vistos = sum(s["vistos"] for s in S)
    aprov = sum(s["aprovados"] for s in S)
    dup = sum(s["dup"] for s in S)
    bytes_txt = sum(s["bytes"] for s in S)

    print("\n" + "=" * 74)
    print("RESULTADO")
    print("=" * 74)
    acc = 0
    for f in FAIXAS:
        acc += tot_faixa[f]
        print(f"  pt_{f}  {humano(tot_faixa[f]):>8} tokens · {tot_faixa[f]*2/1e9:5.1f} GB"
              f"   | acumulado ate {f}: {humano(acc):>8} ({acc*2/1e9:5.1f} GB)")
    print(f"  SOMA  {humano(tot):>8} tokens · {tot*2/1e9:5.1f} GB")
    print(f"\n  docs vistos {vistos:,} · aprovados {aprov:,} ({aprov/max(1,vistos):.1%}) · "
          f"duplicata exata {dup:,} ({dup/max(1,vistos):.2%})")
    print(f"  parquets varridos: {len(estado['concluidos'])}/66 da fonte")
    if bytes_txt:
        fert = tot / bytes_txt
        print(f"  fertilidade real: {fert:.4f} tok/byte (ref. {FERT_ESPERADA:.4f})")
        if not (0.75 * FERT_ESPERADA <= fert <= 1.4 * FERT_ESPERADA):
            print("  AVISO: fertilidade final fora da faixa — conferir antes de treinar.",
                  file=sys.stderr)
    print(f"\n  Os .bin sao por parquet (pt_A_000.bin, ...). Juntar com bee/juntar_pt.py.")
    print("  Treinar com A, A+B ou A+B+C — o corte e' decisao de treino, nao da varredura.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
