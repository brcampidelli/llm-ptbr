"""Gate T4 §3.2 — bpb por idioma no ponto FINAL do Bee-1G (docs/gate-sucesso-bee-1g.md).

Holdout: os 8 idiomas do `bee/corpus_multi`, balde canonico `sha1(texto) % 100 < 2`, teto de 1,5 MB
por idioma (o mesmo `gate_t1_bpb.textos` + `bpb_idioma` dos gates T1/T2 — mesma regua, §2g).
Por que o holdout e' limpo para o 1G: a metade nao-PT do pool foi filtrada documento a documento pelo
MESMO sha1 (`bee/tokenizar_naopt_1g.py`), e o filtro e' por conteudo — se um documento do holdout
existisse na fonte de treino, cairia no mesmo balde e sairia do treino.

Criterio declarado: bpb do Bee-1G <= o do modelo publico Apache-2.0 mais proximo, POR IDIOMA
(candidato: Qwen3-0.6B-Base). 🔴 Ler por COLUNA, nunca entre colunas (2608.25089): bpb carrega vies de
tokenizacao e ortografia entre idiomas. Piso ao lado: bpb do gzip -9 do mesmo texto.

⚠️ O que nao mostra: um modelo de vocab 150k tokeniza CJK/arabe melhor que o nosso 64k — perder para
ele ali pode ser tokenizador, nao modelo (a §3.3 separa, com NLL em corpus paralelo). E o Bee-350M
entra como referencia de PT: o tokenizador dele e' 32k PT, os outros idiomas nele sao byte-fallback.

Uso:
  .venv/Scripts/python.exe bee/bpb_idiomas_t4.py --modelos <dir_1g> BrCamp/bee-350m-pt-base Qwen/Qwen3-0.6B-Base \
        --saida docs/bpb-idiomas-t4-final-20B.json
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_t1_bpb import IDIOMAS, bpb_idioma, textos   # noqa: E402


def bpb_gzip(txts: list[str], teto: int) -> float:
    sel, n = [], 0
    for t in txts:
        b = len(t.encode("utf-8"))
        if n + b > teto and sel:
            break
        sel.append(t); n += b
    bruto = "\n".join(sel).encode("utf-8")
    return len(gzip.compress(bruto, 9)) * 8 / len(bruto)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8")
        except Exception: pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelos", nargs="+", required=True)
    ap.add_argument("--bytes-holdout", type=int, default=1_500_000)
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--dispositivo", default="cuda")
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()

    dest = ROOT / a.saida
    if dest.exists():
        raise SystemExit(f"🔴 {dest} ja existe — nome deriva do que se mede; nao sobrescrevo (§2z)")

    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    hold = {c: list(textos(c, "holdout", a.bytes_holdout)) for c in IDIOMAS}
    piso = {c: bpb_gzip(hold[c], a.bytes_holdout) for c in IDIOMAS}
    print("holdout por idioma (docs · MB · piso gzip):")
    for c in IDIOMAS:
        mb = sum(len(t.encode("utf-8")) for t in hold[c]) / 1e6
        print(f"  {c}: {len(hold[c]):4d} docs · {mb:.2f} MB · gzip {piso[c]:.3f}")

    doc = {"_gate": "T4 §3.2 — bpb por idioma, ponto final", "_regua": "gate_t1_bpb.bpb_idioma · nats/ln2/BYTES · "
           f"bf16 · seq_len {a.seq_len} · teto {a.bytes_holdout} B por idioma · holdout sha1%100<2 do corpus_multi",
           "_ler": "por COLUNA, nunca entre colunas (2608.25089)", "transformers": transformers.__version__,
           "gpu": torch.cuda.get_device_name(0) if a.dispositivo == "cuda" else "cpu",
           "holdout": {c: {"docs": len(hold[c]), "bytes": sum(len(t.encode("utf-8")) for t in hold[c])} for c in IDIOMAS},
           "piso_gzip": piso, "bpb": {}}
    for m in a.modelos:
        t0 = time.time()
        tok = AutoTokenizer.from_pretrained(m)
        mod = AutoModelForCausalLM.from_pretrained(m, dtype=torch.bfloat16).to(a.dispositivo).eval()
        doc["bpb"][m] = {}
        for c in IDIOMAS:
            b, nd, nb = bpb_idioma(a.dispositivo, mod, tok, hold[c], a.seq_len, a.bytes_holdout)
            doc["bpb"][m][c] = b
        print(f"{Path(m).name:<28} " + " ".join(f"{c} {doc['bpb'][m][c]:.4f}" for c in IDIOMAS) + f"   ({time.time()-t0:.0f} s)", flush=True)
        del mod; torch.cuda.empty_cache()
        dest.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nartefato: {a.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
