"""Re-tokeniza os 21,97B de portugues do 32k para o `64k-multi` — sem perder um byte.

🔴 POR QUE ISTO E' NECESSARIO. O `coletar_pt_volume.py` apaga o texto cru depois de tokenizar
   ("os parquets sao apagados apos o uso", linha 34). O corpus PT existe **so'** como 39 shards
   uint16 no tokenizador de 32k do Bee-150M. O Bee-1G decidiu o `64k-multi` (Gate T1).

✅ POR QUE E' LOSSLESS, e foi VERIFICADO antes de escrever este arquivo (§2ad):
   o 32k e' BPE **ByteLevel** com `byte_fallback: False`, decoder ByteLevel e normalizador **NFC**.
   Logo `decode(ids)` devolve o texto exato que foi tokenizado, e o corpus ja' foi gravado NFC.
   Medido em 200.000 tokens do `pt_A_000.bin`: 917.368 caracteres saem e voltam **identicos**.

⚠️ E POR QUE O CORTE E' NA FRONTEIRA DE DOCUMENTO. Processar em blocos arbitrarios preservaria o
   TEXTO mas quebraria tokens na emenda — a tokenizacao resultante nao seria a de uma passada
   unica. O EOS (id 0) separa documentos; cortando nele, cada documento e' re-tokenizado inteiro,
   exatamente como seria numa passada so'.

⚠️ uint16 E' SEGURO AQUI, e a razao vai escrita porque o contrario ja' custou caro: vocab 64.000
   => max id 63.999 < 65.535. O perigo do §T1 era `astype(np.uint16)`, que ENVOLVE em silencio;
   aqui se usa o construtor `np.asarray(..., dtype=np.uint16)`, que LEVANTA OverflowError, mais um
   assert explicito. uint32 dobraria o disco de 44 para 88 GB sem comprar nada.

Uso:
    python bee/retokenizar_pt.py --processos 6
    python bee/retokenizar_pt.py --so-verificar        # confere o que ja' foi escrito
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIGEM = ROOT / "corpus_pt"
DESTINO = ROOT / "corpus_pt_64k"
TOK_ORIGEM = "models/bee-150m-v3-base"
TOK_DESTINO = "bee/tok_t1/64k-multi"
EOS = 0                      # <|endoftext|> no 32k — verificado
VOCAB_DESTINO = 64_000
TOK_POR_BLOCO = 2_000_000    # ~2.200 documentos por bloco, ~9 MB de texto

# razao esperada 64k/32k, medida em amostra: 1,0738. Fora desta faixa, algo mudou.
RAZAO_MIN, RAZAO_MAX = 1.00, 1.20


def caminho(c):
    return c if c.startswith("models") else str(ROOT / c)


def um_shard(args):
    """Re-tokeniza UM shard. Roda em processo proprio."""
    import numpy as np
    from transformers import AutoTokenizer

    origem, destino, verboso = args
    if destino.exists():
        return {"shard": origem.name, "pulado": True}

    t0 = time.time()
    t32 = AutoTokenizer.from_pretrained(caminho(TOK_ORIGEM))
    t64 = AutoTokenizer.from_pretrained(caminho(TOK_DESTINO))
    eos64 = t64.convert_tokens_to_ids("<|endoftext|>")

    dados = np.fromfile(origem, dtype=np.uint16)
    fronteiras = np.flatnonzero(dados == EOS)
    n_docs_ent = len(fronteiras)

    # 🔴 GUARDA DE ROUND-TRIP (§2t): antes de converter o shard inteiro, prova que a conversao
    #    preserva o texto NESTE shard. Uma guarda que so' foi testada noutro arquivo nao guarda
    #    este. Custa ~1 s e aborta antes de escrever 1 GB errado.
    amostra = dados[:200_000].astype(np.int64).tolist()
    txt_a = t32.decode(amostra, skip_special_tokens=False)
    if t64.decode(t64(txt_a, add_special_tokens=False)["input_ids"],
                  skip_special_tokens=False) != txt_a:
        raise SystemExit(f"🔴 {origem.name}: round-trip NAO e' lossless — abortando o shard")

    saida: list[int] = []
    n_max = 0
    tmp = destino.with_suffix(".bin.tmp")
    ini = 0
    with open(tmp, "wb") as fh:
        while ini < len(dados):
            # corta no PROXIMO EOS depois de TOK_POR_BLOCO — nunca no meio de um documento
            alvo = ini + TOK_POR_BLOCO
            j = np.searchsorted(fronteiras, alvo)
            fim = int(fronteiras[j]) + 1 if j < len(fronteiras) else len(dados)
            bloco = dados[ini:fim].astype(np.int64).tolist()
            texto = t32.decode(bloco, skip_special_tokens=False)
            # o EOS do 32k decodifica como '<|endoftext|>'; o 64k o reconhece como token proprio
            ids = t64(texto, add_special_tokens=False)["input_ids"]
            if ids:
                n_max = max(n_max, max(ids))
                # construtor que LEVANTA em vez de envolver (a licao do Gate T1)
                np.asarray(ids, dtype=np.uint16).tofile(fh)
                saida.append(len(ids))
            ini = fim

    n_saida = sum(saida)
    if n_max >= VOCAB_DESTINO:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"🔴 {origem.name}: id {n_max} >= vocab {VOCAB_DESTINO}")
    razao = n_saida / max(1, len(dados))
    if not (RAZAO_MIN <= razao <= RAZAO_MAX):
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"🔴 {origem.name}: razao 64k/32k = {razao:.4f}, fora de "
                         f"[{RAZAO_MIN}, {RAZAO_MAX}] — a conversao fez outra coisa")

    # §2r — QUANTO A CONVERSAO AGIU: o numero de documentos tem de sobreviver. Se sumir
    # documento, o corpus encolheu em silencio, que e' a familia "dado some e nada reclama".
    conf = np.fromfile(tmp, dtype=np.uint16)
    n_docs_sai = int((conf == eos64).sum())
    if abs(n_docs_sai - n_docs_ent) > max(2, 0.001 * n_docs_ent):
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"🔴 {origem.name}: {n_docs_ent:,} documentos entraram e "
                         f"{n_docs_sai:,} sairam — perda silenciosa")
    if len(conf) != n_saida:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"🔴 {origem.name}: gravou {len(conf):,} != {n_saida:,} contados")

    os.replace(tmp, destino)
    return {"shard": origem.name, "tok_entrada": int(len(dados)), "tok_saida": n_saida,
            "razao": razao, "docs_entrada": n_docs_ent, "docs_saida": n_docs_sai,
            "max_id": n_max, "minutos": (time.time() - t0) / 60}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--processos", type=int, default=6)
    ap.add_argument("--so-verificar", action="store_true")
    args = ap.parse_args()

    DESTINO.mkdir(exist_ok=True)
    shards = sorted(Path(p) for p in glob.glob(str(ORIGEM / "pt_*.bin")))
    print(f"{len(shards)} shards em {ORIGEM.name} -> {DESTINO.name}")

    meta_p = DESTINO / "MANIFEST.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {
        "_origem": str(ORIGEM), "_tok_origem": TOK_ORIGEM, "_tok_destino": TOK_DESTINO,
        "_lossless": ("verificado por round-trip POR SHARD antes de converter: o 32k e' BPE "
                      "ByteLevel sem byte_fallback com normalizador NFC, entao decode(ids) "
                      "devolve o texto exato e o corpus ja' foi gravado NFC"),
        "_dtype": "uint16 — vocab 64.000, max id 63.999 < 65.535; construtor que LEVANTA, "
                  "nao astype() que envolve em silencio",
        "_corte": "na fronteira de EOS: cada documento e' re-tokenizado inteiro, como numa "
                  "passada unica",
        "shards": {}}

    if args.so_verificar:
        feitos = sorted(glob.glob(str(DESTINO / "pt_*.bin")))
        print(f"{len(feitos)} de {len(shards)} convertidos")
        for k, v in meta["shards"].items():
            print(f"  {k}: {v['tok_saida']/1e6:>8.1f}M tok · razao {v['razao']:.4f} · "
                  f"{v['docs_saida']:,} docs · {v['minutos']:.1f} min")
        return 0

    tarefas = [(s, DESTINO / s.name, True) for s in shards]
    from concurrent.futures import ProcessPoolExecutor
    t0, feitos = time.time(), 0
    with ProcessPoolExecutor(max_workers=args.processos) as ex:
        for r in ex.map(um_shard, tarefas):
            feitos += 1
            if r.get("pulado"):
                print(f"  [{feitos}/{len(shards)}] {r['shard']}: ja' existe", flush=True)
                continue
            meta["shards"][r["shard"]] = r
            meta_p.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  [{feitos}/{len(shards)}] {r['shard']}: {r['tok_entrada']/1e6:.0f}M -> "
                  f"{r['tok_saida']/1e6:.0f}M tok (razao {r['razao']:.4f}) · "
                  f"{r['docs_saida']:,} docs · {r['minutos']:.1f} min", flush=True)

    tot_e = sum(v["tok_entrada"] for v in meta["shards"].values())
    tot_s = sum(v["tok_saida"] for v in meta["shards"].values())
    meta["total"] = {"tok_entrada": tot_e, "tok_saida": tot_s,
                     "razao": tot_s / max(1, tot_e), "horas": (time.time() - t0) / 3600}
    meta_p.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{tot_e/1e9:.2f}B tokens em 32k -> {tot_s/1e9:.2f}B em 64k "
          f"(razao {tot_s/max(1,tot_e):.4f}) em {(time.time()-t0)/3600:.1f} h")
    print(f"manifesto: {meta_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
