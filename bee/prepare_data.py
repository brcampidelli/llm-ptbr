"""BEE — tokeniza o corpus UMA vez e grava como `uint16` para o treino ler por memmap.

⭐ POR QUE ESTA ETAPA EXISTE. Tokenizar durante o treino é desperdício puro: o mesmo texto
seria tokenizado de novo a cada época, gastando CPU que a GPU está esperando. Tokenizar
antes transforma o treino num `memmap` de inteiros — leitura sequencial, zero CPU, e o
`DataLoader` deixa de ser gargalo. É o que o nanoGPT faz, e é o certo.

⭐ `uint16` e não `int32`: o nosso vocab é 32.000, que cabe folgado em 16 bits (< 65.536).
Isso corta o arquivo pela METADE — 3B tokens viram 6 GB em vez de 12 GB. Num Colab com
disco e banda limitados, isso não é detalhe.

⚠️ EMPACOTAMENTO SEM PADDING. Documentos são concatenados com `<|endoftext|>` entre eles e
cortados em blocos de `seq_len`. Nenhum token de padding entra: num pré-treino, padding é
FLOP jogado fora. O modelo aprende a usar o `eos` como fronteira, que é o comportamento
desejado.

⚠️ O SPLIT É POR SHARD, não por documento embaralhado. Os shards de validação ficam
INTEIROS de fora — assim a perplexidade de validação mede generalização de verdade, e não
"o modelo já viu 90% deste documento".

Uso:
    python bee/prepare_data.py --corpus <dir> --tokenizer <dir> --out <dir>
    python bee/prepare_data.py --limite-gb 1     # amostra para testar o pipeline rápido
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ⭐ Os shards de VALIDAÇÃO. Escolhidos por índice fixo (não aleatório) para que a escolha
# seja reproduzível e auditável: qualquer pessoa confere quais ficaram de fora.
# 3 de 53 ≈ 5,7% — suficiente para perplexidade estável e barato de segurar.
SHARDS_VAL = {7, 23, 41}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=ROOT / "bee" / "corpus")
    ap.add_argument("--tokenizer", type=Path, default=ROOT / "bee" / "tokenizer")
    ap.add_argument("--out", type=Path, default=ROOT / "bee" / "dados")
    ap.add_argument("--limite-gb", type=float, default=0.0,
                    help="0 = tudo. Use 1 para validar o pipeline em minutos antes das 25 h")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import numpy as np
    import zstandard as zstd
    from transformers import AutoTokenizer

    shards = sorted(args.corpus.glob("bee_corpus_*.jsonl.zst"))
    if not shards:
        print(f"ERRO: nenhum shard em {args.corpus}", file=sys.stderr)
        return 1
    tok = AutoTokenizer.from_pretrained(str(args.tokenizer))
    eos = tok.convert_tokens_to_ids("<|endoftext|>")
    if eos is None or eos < 0:
        print("ERRO: tokenizador sem <|endoftext|> — o empacotamento depende dele.",
              file=sys.stderr)
        return 1
    # ⭐ A checagem que evita corromper 6 GB em silêncio: uint16 só serve até 65.535.
    if tok.vocab_size > 65535:
        print(f"ERRO: vocab {tok.vocab_size} não cabe em uint16. Troque o dtype para uint32 "
              f"(e o arquivo dobra de tamanho).", file=sys.stderr)
        return 1

    print(f"corpus     : {len(shards)} shards em {args.corpus}")
    print(f"tokenizador: {args.tokenizer}  (vocab {tok.vocab_size}, eos id {eos})")
    print(f"validação  : shards {sorted(SHARDS_VAL)} ficam INTEIROS de fora do treino")
    print(f"saída      : {args.out}\n")
    if args.dry_run:
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    dctx = zstd.ZstdDecompressor()
    lim = int(args.limite_gb * 1024 ** 3) if args.limite_gb else 0

    stats = {"train": {"tokens": 0, "docs": 0, "bytes": 0},
             "val": {"tokens": 0, "docs": 0, "bytes": 0},
             "por_fonte": {}}
    saidas = {p: open(args.out / f"{p}.bin", "wb") for p in ("train", "val")}
    t0 = time.time()

    for i, shard in enumerate(shards):
        parte = "val" if i in SHARDS_VAL else "train"
        if lim and stats["train"]["bytes"] >= lim and parte == "train":
            continue
        dados = dctx.decompress(shard.read_bytes()).decode("utf-8")
        # ⭐ EM LOTE, não um documento por vez. O `tokenizers` é Rust e paraleliza
        # internamente quando recebe uma LISTA — chamado texto a texto, paga overhead de
        # travessia Python↔Rust por documento e usa um núcleo só. Medido nesta sessão:
        # um-a-um levava ~12 min por 0,6 GB, o que daria ~4 h no corpus inteiro.
        textos, fontes = [], []
        for linha in dados.splitlines():
            if not linha.strip():
                continue
            try:
                reg = json.loads(linha)
            except Exception:
                continue
            t = reg.get("text", "")
            if t:
                textos.append(t)
                fontes.append(reg.get("fonte", "?"))
        buf: list[int] = []
        LOTE = 1000
        for i0 in range(0, len(textos), LOTE):
            pedaco = textos[i0:i0 + LOTE]
            enc = tok(pedaco, add_special_tokens=False)["input_ids"]
            for j, ids in enumerate(enc):
                buf.extend(ids)
                buf.append(eos)          # fronteira de documento
                f = fontes[i0 + j]
                stats["por_fonte"][f] = stats["por_fonte"].get(f, 0) + len(ids) + 1
        stats[parte]["docs"] += len(textos)
        stats[parte]["bytes"] += sum(len(t.encode("utf-8")) for t in textos)
        arr = np.array(buf, dtype=np.uint16)
        arr.tofile(saidas[parte])
        stats[parte]["tokens"] += len(arr)
        vel = stats["train"]["tokens"] / max(1e-9, time.time() - t0) / 1e6
        print(f"  [{i+1:>2}/{len(shards)}] {shard.name} → {parte:<5} "
              f"{len(arr)/1e6:>6.1f}M tokens · total treino {stats['train']['tokens']/1e9:.3f}B "
              f"· {vel:.1f}M tok/s", flush=True)

    for f in saidas.values():
        f.close()

    # ---------------- relatório: o que o pré-treino vai realmente ver ----------------
    tt, tv = stats["train"]["tokens"], stats["val"]["tokens"]
    print("\n" + "=" * 72)
    print("⭐ DADOS PRONTOS")
    print("=" * 72)
    print(f"  treino    {tt/1e9:>8.3f}B tokens · {stats['train']['docs']:>9} docs · "
          f"{tt*2/1024**3:.2f} GB em disco (uint16)")
    print(f"  validação {tv/1e9:>8.3f}B tokens · {stats['val']['docs']:>9} docs")
    print(f"\n  fertilidade real: {tt / max(1, stats['train']['bytes'] / 5.5):.3f} tokens/palavra "
          f"(aprox., 5,5 bytes/palavra)")
    print("\n  tokens por fonte (o que o modelo vai ver de cada uma):")
    tot = max(1, sum(stats["por_fonte"].values()))
    for f, n in sorted(stats["por_fonte"].items(), key=lambda kv: -kv[1]):
        print(f"    {f:<18} {n/1e9:>7.3f}B  {100*n/tot:>5.1f}%")

    (args.out / "meta.json").write_text(json.dumps({
        "tokens_treino": tt, "tokens_val": tv, "vocab": tok.vocab_size, "eos": eos,
        "dtype": "uint16", "shards_val": sorted(SHARDS_VAL),
        "docs_treino": stats["train"]["docs"], "docs_val": stats["val"]["docs"],
        "tokens_por_fonte": stats["por_fonte"],
        "tokenizer": str(args.tokenizer)}, indent=2, ensure_ascii=False), encoding="utf-8")

    # ⭐ O aviso que evita 25 h de GPU num orçamento que não fecha
    alvo = 3e9
    if tt < alvo:
        print(f"\n⚠️ {tt/1e9:.2f}B tokens < {alvo/1e9:.0f}B do orçamento planejado. "
              f"O treino vai repetir dado ({alvo/max(1,tt):.1f} épocas) — o que é aceitável até "
              f"~4 épocas, mas acima disso vira memorização.")
    print(f"\n✅ {args.out}/train.bin e val.bin prontos. Próximo: bee/pretrain.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
