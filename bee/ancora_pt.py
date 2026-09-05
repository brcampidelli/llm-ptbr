"""Ancora de portugues para o Gate T4 — e a validacao da regua pela §2aa.

🔴 POR QUE ISTO E' NECESSARIO. O gate de sucesso diz *"o portugues nao pode ficar abaixo do
   Bee-350M — 0,8207"*. Esse numero saiu do `eval_gate2.py` sobre os shards {7,23,41} de
   `bee/corpus`, e **`bee/corpus` nao existe nesta maquina**. Comparar o Bee-1G ao 0,8207 seria
   comparar reguas diferentes (§2g). A ancora tem de ser remedida num holdout que EXISTA.

⭐ E A §2aa NAO PODE SER CUMPRIDA NA FORMA LITERAL — o que se faz e' declarar isso e cumpri-la
   na forma que resta. A §2aa exige que ao menos um braco reproduza um numero ja' publicado; o
   numero publicado do 350M e' 0,8207, e o holdout dele se foi. Mas ha' um numero publicado que
   **e'** reproduzivel: a **folga de 2,76% do 350M sobre o Bee-150M**
   (`docs/bee-350m-resultado-final.md`). Uma folga entre dois modelos medidos na MESMA regua
   sobrevive a troca de holdout de um jeito que o valor absoluto nao sobrevive.
   ✅ Se a folga reproduzir, a regua esta' validada e a ancora nova vale.
   🔴 Se nao reproduzir, nao ha' ancora — e a diferenca e' informacao sobre o holdout, nao sobre
   os modelos.

⚠️ bpb normaliza por BYTE, entao compara modelos de tokenizadores diferentes — e' exatamente
   para isso que ele existe. O 150M e o 350M usam o mesmo 32k; o Qwen3 usa outro, e a comparacao
   com ele so' vale DENTRO de cada idioma (§3.2 do gate, `2608.25089`).

Uso:
    python bee/ancora_pt.py
    python bee/ancora_pt.py --modelos BrCamp/bee-350m-pt-base,Qwen/Qwen3-0.6B-Base
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent

# a folga publicada que serve de checagem de regua (§2aa)
FOLGA_PUBLICADA = 0.0276          # 350M sobre 150M, docs/bee-350m-resultado-final.md
TOL_FOLGA = 0.010                 # +-1,0 pp: a folga tem de reproduzir, nao ser identica

MODELOS_PADRAO = "BrCamp/bee-150m-pt-base,BrCamp/bee-350m-pt-base"


def _contaminados() -> set[bytes]:
    """Fingerprints (32 tokens no 64k) dos documentos de holdout que estao DENTRO do corpus."""
    fp: set[bytes] = set()
    for h in ("corpus_multi_pt", "wiki"):
        q = ROOT / "docs" / f"contaminacao-pt-{h}.json"
        if not q.exists():
            raise SystemExit(f"🔴 {q} nao existe — rode bee/checar_contaminacao_pt.py")
        fp |= {bytes.fromhex(x)
               for x in json.loads(q.read_text(encoding="utf-8"))["fingerprints_contaminados"]}
    return fp


def parte_por_contaminacao(docs: list[str], tok64, excl: set[bytes], prefixo: int = 32):
    """Separa os documentos que o corpus de treino CONTEM dos que ele nao contem.

    ⭐ O fingerprint tem de ser calculado com o MESMO tokenizador e o MESMO prefixo do censo,
    senao a lista de exclusao nao casa com nada e a limpeza fica inerte sem dar erro (§2t).
    """
    import numpy as np
    limpos, sujos = [], []
    for t in docs:
        ids = tok64(t, add_special_tokens=False)["input_ids"][:prefixo]
        if len(ids) < prefixo:
            limpos.append(t)          # curto demais para ter fingerprint; o censo tambem o ignorou
            continue
        (sujos if np.asarray(ids, dtype=np.uint16).tobytes() in excl else limpos).append(t)
    return limpos, sujos


def holdouts(teto_bytes: int) -> dict[str, list[str]]:
    """Os dois holdouts de PT que EXISTEM nesta maquina, como TEXTO.

    ⭐ `wiki` e' o holdout do gate das faixas — Wikipedia-PT, *"que nenhum braco ve"*. E' o mais
       proximo de um holdout limpo que o projeto tem, e por isso e' a ancora primaria.
    ⭐ `corpus_multi` e' o holdout dos Gates T1 e T2 (balde `sha1 % 100 < 2`). Ele importa por
       outro motivo: e' a MESMA regua em que o Bee-1G vai ser medido, entao a ancora nele e' a
       que compara direto, sem troca de conjunto.
    """
    from gate_t1_bpb import textos

    saida: dict[str, list[str]] = {}
    p = ROOT / "bee" / "gate" / "holdout_wiki.json"
    if p.exists():
        docs, n = [], 0
        for t in json.loads(p.read_text(encoding="utf-8")):
            b = len(t.encode("utf-8"))
            if n + b > teto_bytes and docs:
                break
            docs.append(t)
            n += b
        saida["wiki"] = docs
    docs, n = [], 0
    for t in textos("por", "holdout", teto_bytes):
        b = len(t.encode("utf-8"))
        if n + b > teto_bytes and docs:
            break
        docs.append(t)
        n += b
    saida["corpus_multi_pt"] = docs
    return saida


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelos", default=MODELOS_PADRAO)
    ap.add_argument("--bytes-holdout", type=int, default=1_500_000)
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--dispositivo", default="cuda")
    args = ap.parse_args()

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from gate_t1_bpb import bpb_idioma

    conj = holdouts(args.bytes_holdout)
    tok64 = AutoTokenizer.from_pretrained(str(ROOT / "bee" / "tok_t1" / "64k-multi"))
    excl = _contaminados()
    print(f"{len(excl)} fingerprints contaminados (censo de 2026-09-05)")

    # 🔴 O holdout inteiro NAO serve mais de ancora: 56,1% do `corpus_multi_pt` e 8,0% do `wiki`
    #    estao dentro do corpus de treino, e o Bee-350M treinou neles. Medir os TRES subconjuntos
    #    e' o que separa capacidade de memorizacao — e o `sujo` e' a propria verificacao de que a
    #    contaminacao e' real, e nao artefato do metodo de fingerprint (§2r: quanto agiu).
    partes: dict[str, list[str]] = {}
    print(f"\nholdouts (teto {args.bytes_holdout/1e6:.1f} MB cada):")
    for k, v in conj.items():
        limpos, sujos = parte_por_contaminacao(v, tok64, excl)
        for nome, docs in (("completo", v), ("limpo", limpos), ("sujo", sujos)):
            if not docs:
                continue
            nb = sum(len(t.encode("utf-8")) for t in docs)
            partes[f"{k}/{nome}"] = docs
            print(f"  {k+'/'+nome:<28} {len(docs):>4} docs · {nb/1e6:.2f} MB")
    conj = partes

    modelos = [m.strip() for m in args.modelos.split(",") if m.strip()]
    res: dict[str, dict[str, float]] = {}
    print(f"\n{'modelo':<26}" + "".join(f"{k:>27}" for k in conj))
    print("-" * (26 + 27 * len(conj)))

    for nome in modelos:
        t0 = time.time()
        tok = AutoTokenizer.from_pretrained(nome)
        m = AutoModelForCausalLM.from_pretrained(
            nome, dtype=torch.bfloat16 if args.dispositivo == "cuda" else torch.float32
        ).to(args.dispositivo).eval()
        res[nome] = {}
        for k, txts in conj.items():
            b, nd, nb = bpb_idioma(args.dispositivo, m, tok, txts,
                                   args.seq_len, args.bytes_holdout)
            res[nome][k] = b
        del m
        if args.dispositivo == "cuda":
            torch.cuda.empty_cache()
        print(f"{nome:<26}" + "".join(f"{res[nome][k]:>27.4f}" for k in conj)
              + f"   ({(time.time()-t0)/60:.1f} min)")

    # --- §2aa: a folga publicada reproduz? ---
    p150 = next((m for m in modelos if "150m" in m.lower()), None)
    p350 = next((m for m in modelos if "350m" in m.lower()), None)
    doc = {"_gate": "ancora de PT para o T4",
           "_regua": f"bpb = nats/ln2 / BYTES · {args.dispositivo} · teto "
                     f"{args.bytes_holdout} B por holdout · seq_len {args.seq_len}",
           "_por_que": ("o 0,8207 publicado do 350M saiu dos shards {7,23,41} de `bee/corpus`, "
                        "que nao existe nesta maquina — a ancora tem de ser remedida num "
                        "holdout que exista (§2g)"),
           "_nao_mostra": [
               "capacidade — o E2 mediu que bpb e capacidade sao coisas diferentes",
               "comparacao ENTRE idiomas: bpb carrega vies crosslinguistico (2608.25089); "
               "estes numeros sao todos de PT e so' comparam entre si",
               "o valor absoluto NAO e' comparavel ao 0,8207 publicado — holdout diferente",
           ],
           "bytes_holdout": args.bytes_holdout, "seq_len": args.seq_len,
           "dispositivo": args.dispositivo,
           "holdouts": {k: {"docs": len(v),
                            "bytes": sum(len(t.encode("utf-8")) for t in v)}
                        for k, v in conj.items()},
           "bpb": res}

    if p150 and p350:
        print(f"\n{'='*72}\n§2aa — a folga publicada de 2,76% reproduz?\n{'='*72}")
        doc["checagem_2aa"] = {"folga_publicada": FOLGA_PUBLICADA, "tolerancia": TOL_FOLGA,
                               "por_holdout": {}}
        todas_ok = True
        for k in conj:
            f = 1 - res[p350][k] / res[p150][k]
            if not k.endswith("/limpo"):
                # a folga so' e' evidencia no subconjunto que nenhum dos dois modelos viu
                print(f"  {k:<28} 150M {res[p150][k]:.4f} · 350M {res[p350][k]:.4f} · "
                      f"folga {100*f:+.2f}%  (informativo, nao entra na checagem)")
                doc.setdefault("_folga_informativa", {})[k] = f
                continue
            ok = abs(f - FOLGA_PUBLICADA) <= TOL_FOLGA
            todas_ok &= ok
            print(f"  {k:<18} 150M {res[p150][k]:.4f} · 350M {res[p350][k]:.4f} · "
                  f"folga {100*f:+.2f}%  {'✅ reproduz' if ok else '🔴 NAO reproduz'}")
            doc["checagem_2aa"]["por_holdout"][k] = {"folga": f, "reproduz": ok}
        doc["checagem_2aa"]["todas_reproduzem"] = bool(todas_ok)
        if todas_ok:
            print("\n✅ A REGUA ESTA' VALIDADA. As ancoras do T4 sao os valores do 350M acima,")
            print("   no holdout correspondente — e NAO o 0,8207, que e' de outro conjunto.")
        else:
            print("\n🔴 A FOLGA NAO REPRODUZ. Nao ha' ancora: a diferenca e' informacao sobre o")
            print("   HOLDOUT, nao sobre os modelos. O criterio de PT do T4 fica sem base ate'")
            print("   que se entenda por que (§5: aparato antes de fenomeno).")

    # §2z: o nome deriva do que foi medido — esta rodada parte o holdout por contaminacao
    #      e NAO e" comparavel com a de 09-04, que media o holdout inteiro.
    dest = ROOT / "docs" / "ancora-pt-t4-limpa.json"
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(dest)
    print(f"\nartefato: docs/{dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
