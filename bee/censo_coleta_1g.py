"""Censo do que a coleta multilingue REALMENTE pos em disco — contado, nao estimado.

🔴🔴 POR QUE ISTO EXISTE (medido 2026-09-04). A pasta `bee/corpus_multi_1g` tem 221 shards e
   **nenhuma contabilidade valida deles**. Os seis `MANIFEST_<idioma>.json` foram todos escritos
   as 09:03 — ANTES de existir um unico shard dos idiomas que nomeiam — e todos carregam o mesmo
   registro de `fra`, de uma corrida anterior. E `fra` tem **zero** shards em disco agora.
   O `MANIFEST.json` (12:41) descreve so' `jpn`, o ultimo idioma, ignorando 218 dos 221 shards.

   A causa esta' no `coletar_1g.sh`: o `cp MANIFEST.json MANIFEST_<c>.json` fica no ramo de
   SUCESSO, entao idioma que nao chega a 90%% do alvo nunca atualiza o proprio arquivo — e o que
   sobrou ali e' o de outra corrida. §2z: arquivo cujo NOME afirma o que o CONTEUDO nao e'.

⚠️ E o segundo defeito, que este censo substitui: o `mcar_em_disco()` do driver ESTIMA o numero
   de caracteres a partir do **tamanho comprimido**, com uma razao cravada a mao por idioma. Essa
   estimativa decide (a) se o idioma esta' pronto e (b) se os shards parciais sao **APAGADOS**
   (`rm -f ... — refazendo do zero`). Estimativa dirigindo acao destrutiva.

✅ Aqui se conta. Descompacta cada shard, conta documentos, caracteres e bytes UTF-8, e converte
   para TOKENS pela fertilidade medida por idioma (`docs/gate-t1-vocab.json`) — que e' a unidade
   que o treino consome. Caractere nao e' comparavel entre escritas (§2g): 1 caractere han nao
   custa o mesmo que 1 caractere latino.

⚠️ Censo COMPLETO, nunca piloto. Aqui o vies do §2ac nao se aplica (contagem de item unico nao
   exige coincidencia de dois itens na amostra), mas contar 14,65 GB custa minutos — comprar um
   numero estimado quando o exato esta' ao alcance e' o erro que o §2ac descreve.

Uso:
    python bee/censo_coleta_1g.py
    python bee/censo_coleta_1g.py --processos 8 --out docs/censo-coleta-1g.json
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PADRAO = "bee/corpus_multi_1g/bee_corpus_*.jsonl.zst"

# alvo por idioma, em MILHOES de caracteres — copiado do `coletar_1g.sh` para o censo poder
# dizer "quanto falta" sem que se precise abrir dois arquivos.
ALVO_MCAR = {"spa": 10541, "fra": 9810, "deu": 9282, "eng": 10017,
             "arb": 7801, "cmn": 3405, "jpn": 4752}


def idioma_do_arquivo(p: str) -> str:
    """bee_corpus_<idioma>_0000.jsonl.zst -> <idioma>. O NOME do shard e' a fonte da verdade
    sobre o idioma; os manifestos provaram nao ser."""
    return os.path.basename(p).split("_")[2]


def um_shard(p: str) -> dict:
    import zstandard as z

    t0 = time.time()
    docs = carac = bytes_utf8 = 0
    fontes: dict[str, int] = {}
    with open(p, "rb") as fh:
        leitor = z.ZstdDecompressor().stream_reader(fh)
        for linha in io.TextIOWrapper(leitor, encoding="utf-8"):
            if not linha.strip():
                continue
            d = json.loads(linha)
            t = d.get("text") or ""
            docs += 1
            carac += len(t)
            bytes_utf8 += len(t.encode("utf-8"))
            f = d.get("fonte", "?")
            fontes[f] = fontes.get(f, 0) + 1
    return {"arquivo": os.path.basename(p), "idioma": idioma_do_arquivo(p),
            "documentos": docs, "caracteres": carac, "bytes_utf8": bytes_utf8,
            "bytes_comprimido": os.path.getsize(p), "fontes": fontes,
            "segundos": time.time() - t0}


def fertilidades() -> dict[str, float]:
    """tokens/CARACTERE por idioma, do braco 64k-multi do Gate T1.

    ⚠️ Se o artefato nao existir ou nao trouxer o 64k, devolve {} — e o censo reporta so'
    caracteres, dizendo que nao converteu. Inventar uma fertilidade seria pior que nao ter.
    """
    p = ROOT / "docs" / "gate-t1-vocab.json"
    if not p.exists():
        return {}
    try:
        idiomas = json.loads(p.read_text(encoding="utf-8"))["bracos"]["64k-multi"]["idiomas"]
    except Exception:
        return {}
    # as chaves com "_" na frente sao metadados do braco (_vocab_quebrado, _vocab_tokens)
    return {k: float(v["tok_por_caractere"]) for k, v in idiomas.items()
            if not k.startswith("_") and isinstance(v, dict) and "tok_por_caractere" in v}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--processos", type=int, default=6)
    ap.add_argument("--out", default="docs/censo-coleta-1g.json")
    args = ap.parse_args()

    shards = sorted(glob.glob(str(ROOT / PADRAO)))
    if not shards:
        raise SystemExit(f"🔴 nenhum shard em {PADRAO}")
    gb = sum(os.path.getsize(p) for p in shards) / 1e9
    print(f"{len(shards)} shards · {gb:.2f} GB comprimido · {args.processos} processos\n")

    dest = ROOT / args.out
    dest.parent.mkdir(exist_ok=True)
    fert = fertilidades()

    doc = {
        "_censo": "o que a coleta multilingue pos em disco — CONTADO",
        "_por_que": ("os MANIFEST_<idioma>.json foram escritos as 09:03, antes dos shards que "
                     "nomeiam, e todos carregam um registro de `fra` que nao tem shard nenhum "
                     "em disco. O MANIFEST.json descreve so' `jpn`. Nao havia contabilidade."),
        "_regua": "documentos e caracteres lidos do JSONL descompactado, shard a shard",
        "_nao_mostra": [
            "qualidade: isto conta volume, nao mede nada sobre o texto",
            "duplicacao: contagem de item unico nao vê repeticao — o censo de duplicacao "
            "(§2ac) e' outro, e tem de ser COMPLETO quando for feito",
            "se o idioma serve: fineweb-2 ja' vem filtrado, mas nada aqui verifica isso",
        ],
        "fertilidade_64k_tok_por_caractere": fert or None,
        "_fertilidade_ausente": None if fert else (
            "docs/gate-t1-vocab.json nao trouxe fertilidade por idioma do 64k-multi — o censo "
            "reporta CARACTERES e nao converte para tokens. Inventar a razao seria pior."),
        "alvo_mcar_por_idioma": ALVO_MCAR,
        "shards": {},
    }

    from concurrent.futures import ProcessPoolExecutor
    t0, feitos = time.time(), 0
    with ProcessPoolExecutor(max_workers=args.processos) as ex:
        for r in ex.map(um_shard, shards):
            feitos += 1
            doc["shards"][r["arquivo"]] = r
            if feitos % 10 == 0 or feitos == len(shards):
                # grava a CADA 10 — artefato so' no fim ja' custou tres medicoes neste projeto
                tmp = dest.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
                tmp.replace(dest)
                falta = (time.time() - t0) / feitos * (len(shards) - feitos) / 60
                print(f"  [{feitos}/{len(shards)}] {r['idioma']} · "
                      f"{falta:.1f} min restantes", flush=True)

    # --- agrega por idioma ---
    por: dict[str, dict] = {}
    for r in doc["shards"].values():
        a = por.setdefault(r["idioma"], {"shards": 0, "documentos": 0, "caracteres": 0,
                                         "bytes_utf8": 0, "bytes_comprimido": 0, "fontes": {}})
        a["shards"] += 1
        for k in ("documentos", "caracteres", "bytes_utf8", "bytes_comprimido"):
            a[k] += r[k]
        for f, n in r["fontes"].items():
            a["fontes"][f] = a["fontes"].get(f, 0) + n

    print(f"\n{'idioma':<7}{'shards':>8}{'documentos':>13}{'Mcaracteres':>14}"
          f"{'% do alvo':>11}{'Mtokens 64k':>13}")
    print("-" * 66)
    for c in sorted(ALVO_MCAR):
        a = por.get(c)
        alvo = ALVO_MCAR[c]
        if not a:
            print(f"{c:<7}{0:>8}{0:>13}{0:>14.0f}{0.0:>10.1f}%{'—':>13}   🔴 ZERO em disco")
            por[c] = {"shards": 0, "documentos": 0, "caracteres": 0, "bytes_utf8": 0,
                      "bytes_comprimido": 0, "fontes": {}}
        else:
            mc = a["caracteres"] / 1e6
            f = fert.get(c)
            mt = f"{mc * f:>13.0f}" if f else f"{'—':>13}"
            print(f"{c:<7}{a['shards']:>8}{a['documentos']:>13,}{mc:>14.0f}"
                  f"{100 * mc / alvo:>10.1f}%{mt}")
        por[c]["alvo_mcar"] = alvo
        por[c]["pct_do_alvo"] = 100 * por[c]["caracteres"] / 1e6 / alvo
    print("-" * 66)
    tot_c = sum(a["caracteres"] for a in por.values()) / 1e6
    tot_a = sum(ALVO_MCAR.values())
    print(f"{'TOTAL':<7}{sum(a['shards'] for a in por.values()):>8}"
          f"{sum(a['documentos'] for a in por.values()):>13,}{tot_c:>14.0f}"
          f"{100 * tot_c / tot_a:>10.1f}%")

    doc["por_idioma"] = por
    doc["total"] = {"shards": sum(a["shards"] for a in por.values()),
                    "documentos": sum(a["documentos"] for a in por.values()),
                    "caracteres": int(tot_c * 1e6),
                    "alvo_mcar": tot_a, "pct_do_alvo": 100 * tot_c / tot_a,
                    "minutos": (time.time() - t0) / 60}
    zerados = [c for c in ALVO_MCAR if por[c]["shards"] == 0]
    doc["idiomas_em_zero"] = zerados
    incompletos = [c for c in ALVO_MCAR if 0 < por[c]["pct_do_alvo"] < 90]
    doc["idiomas_incompletos"] = incompletos

    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(dest)

    if zerados:
        print(f"\n🔴 EM ZERO: {', '.join(zerados)} — nenhum shard em disco")
    if incompletos:
        print(f"⚠️ INCOMPLETOS (<90% do alvo): {', '.join(incompletos)}")
    if not fert:
        print("\n⚠️ sem fertilidade por idioma no artefato do Gate T1 — o censo reporta "
              "CARACTERES e nao converte para tokens.")
    print(f"\nartefato: {args.out}  ({(time.time()-t0)/60:.1f} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
