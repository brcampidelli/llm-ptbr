"""Prepara o `sample-10BT` do FineWeb (ingles) como `.bin` tokenizado, para o CENSO de repeticao.

⭐ POR QUE ESTE SCRIPT EXISTE (2026-09-01)
  A triagem recomendou o `HuggingFaceFW/fineweb` como fonte de ingles do Bee-1G — e junto veio a
  guarda: **a dedup do FineWeb e' POR CRAWL**, declarada pelos proprios autores e escolhida por
  medicao (*"training on a sampling of individually deduplicated dumps outperformed training on
  a sampling of all the dumps deduplicated together"*). Consequencia direta: **duplicata ENTRE
  crawls sobrevive por construcao** — e os configs `sample-*BT` sao amostrados ATRAVES dos 96
  dumps, que e' exatamente onde essa duplicata se concentraria.

  O arXiv:2606.24998 mede, num modelo de **344M**, que repeticao interna consumindo 10% do
  orcamento de FLOPs equivale a jogar fora **um terco da computacao** — com o dano em PICO na
  contagem INTERMEDIARIA (3-10x). A **taxa media esconde exatamente essa faixa**.

⭐ POR QUE TOKENIZAR COM O NOSSO TOKENIZADOR, E NAO USAR A CONTAGEM PUBLICADA
  O FineWeb conta em **gpt2**, o HPLT em **Gemma-3**, o CulturaX nao diz. Somar "tokens" dessas
  fontes e' somar quantidades medidas com reguas diferentes (§2g). O `auditar_repeticao.py`
  pesa cada documento em TOKENS porque token == FLOP (por 6ND) — entao o censo tem de ser feito
  na regua com que o Bee vai efetivamente treinar.

⚠️ E O QUE ESTE CENSO **NAO** PODE MOSTRAR
  O `sample-10BT` e' **uma amostra de 10B dos 18,5T** do corpus completo. Duplicata entre crawls
  que exista no todo pode estar sub-representada aqui — e o inverso tambem. Este censo mede **o
  que o `sample-10BT` contem**, que e' precisamente o artefato que seria baixado. Nao e'
  afirmacao sobre o FineWeb inteiro (§2q).

Uso:
    python bee/preparar_fineweb.py --alvo-tokens 0        # tudo
    python bee/preparar_fineweb.py --alvo-tokens 2e9      # piloto
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="HuggingFaceFW/fineweb")
    ap.add_argument("--config", default="sample-10BT")
    ap.add_argument("--tokenizer", default=str(ROOT / "bee" / "tokenizer_bee"))
    ap.add_argument("--out", default=str(ROOT / "fineweb_en"))
    ap.add_argument("--alvo-tokens", type=float, default=0.0, help="0 = tudo")
    ap.add_argument("--lote", type=int, default=2000)
    args = ap.parse_args()

    import numpy as np
    from datasets import load_dataset
    from transformers import AutoTokenizer

    saida = Path(args.out)
    saida.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    eos = tok.convert_tokens_to_ids("<|endoftext|>")
    assert eos is not None and eos < 65536, "EOS fora do alcance de uint16"
    vocab = tok.vocab_size
    assert vocab <= 65536, f"vocab {vocab} nao cabe em uint16"

    print(f"repo={args.repo} config={args.config}")
    print(f"tokenizador: vocab {vocab} · EOS id {eos}")
    alvo = int(args.alvo_tokens) if args.alvo_tokens else None
    print(f"alvo: {'tudo' if alvo is None else f'{alvo/1e9:.2f}B tokens'}")

    ds = load_dataset(args.repo, name=args.config, split="train", streaming=True)

    bin_p = saida / "train.bin"
    n_tok = n_doc = n_bytes = 0
    t0 = time.time()
    lote_txt: list[str] = []

    def descarrega(f, textos):
        nonlocal n_tok, n_doc, n_bytes
        if not textos:
            return
        ids = tok(textos, add_special_tokens=False)["input_ids"]
        buf = []
        for seq in ids:
            buf.extend(seq)
            buf.append(eos)          # ⭐ EOS separa documentos — e' o que o auditor conta
        a = np.asarray(buf, dtype=np.uint16)
        a.tofile(f)
        n_tok += len(a)
        n_doc += len(ids)
        n_bytes += sum(len(t.encode("utf-8")) for t in textos)

    with open(bin_p, "wb") as f:
        for ex in ds:
            lote_txt.append(ex["text"])
            if len(lote_txt) >= args.lote:
                descarrega(f, lote_txt)
                lote_txt = []
                if n_doc % 200_000 < args.lote:
                    dt = time.time() - t0
                    print(f"  {n_doc:>10,} docs · {n_tok/1e9:6.3f}B tok · "
                          f"{n_tok/max(dt,1)/1e6:5.2f}M tok/s · {dt/60:6.1f} min", flush=True)
                if alvo and n_tok >= alvo:
                    break
        descarrega(f, lote_txt)

    dt = time.time() - t0
    meta = {"eos": int(eos), "tokens": int(n_tok), "documentos": int(n_doc),
            "bytes_utf8": int(n_bytes), "tok_por_byte": n_tok / max(1, n_bytes),
            "repo": args.repo, "config": args.config,
            "tokenizador": str(args.tokenizer), "minutos": dt / 60,
            "_amostra": "sample-10BT e' amostra de 10B dos 18,5T do FineWeb completo — "
                        "este censo mede o artefato que seria baixado, nao o corpus inteiro"}
    (saida / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"\n{'='*66}")
    print(f"  documentos ....... {n_doc:,}")
    print(f"  tokens ........... {n_tok:,} ({n_tok/1e9:.3f}B)")
    print(f"  bytes UTF-8 ...... {n_bytes:,}")
    print(f"  tok/byte ......... {n_tok/max(1,n_bytes):.4f}  "
          f"(PT no nosso tokenizador: 0,218)")
    print(f"  arquivo .......... {bin_p} ({bin_p.stat().st_size/1024**3:.1f} GB)")
    print(f"  tempo ............ {dt/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
