"""Junta os shards por faixa da coleta PT em `train.bin` + `val.bin` para o pre-treino.

Uso:
    python bee/juntar_pt.py --faixas A      # so' o topo (~1/3 dos tokens)
    python bee/juntar_pt.py --faixas AB     # top 30% dos documentos
    python bee/juntar_pt.py --faixas ABC    # top 60% — volume maximo

⭐ POR QUE A VALIDACAO SAI DE TODOS OS SHARDS, E NAO DO FIM
  Cada shard vem de um parquet, e cada parquet e' um recorte diferente do Common Crawl.
  Reservar "o final do arquivo concatenado" daria um holdout que e' UM dump — mede o
  ajuste aquele dump, nao ao portugues. Aqui a validacao e' a cauda de CADA shard, entao
  ela tem a mesma composicao do treino.

⚠️⚠️ NAO COMPARE A PERPLEXIDADE DE VALIDACAO DESTE CORPUS COM A DO v3.
  Perplexidade so' e' comparavel no MESMO texto. O v3 validou em 185,2M tokens da mistura
  antiga (70% PT + EN + codigo); este corpus e' 100% PT e mais limpo — a perplexidade vai
  cair sozinha, por mudanca de distribuicao, sem o modelo ter melhorado em nada. Cair de
  63 para 40 aqui nao significaria absolutamente nada.

  A regua para comparar corpora e' EXTERNA e ja existe: `bee/eval_gate2.py` mede bpb no
  holdout compartilhado (shards [7,23]), onde ja temos os numeros de referencia —
  Bee 3,457 · Tucano-160m 1,739 · SmolLM2 2,010. E' esse numero que decide se trocar de
  corpus adiantou. Ver docs/gate-tucano.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, default=ROOT / "corpus_pt")
    ap.add_argument("--saida", type=Path, default=ROOT / "dados_pt")
    ap.add_argument("--faixas", default="ABC", help="A, AB ou ABC")
    ap.add_argument("--val-frac", type=float, default=0.01,
                    help="fracao da CAUDA DE CADA SHARD reservada para validacao")
    ap.add_argument("--pedaco-mb", type=int, default=256)
    ap.add_argument("--tokenizer", type=Path, default=ROOT / "models" / "bee-150m-v3-base",
                    help="so' para ler vocab e eos e gravar no meta.json")
    ap.add_argument("--max-tokens", type=float, default=0,
                    help="0 = corpus inteiro. >0 amostra PROPORCIONALMENTE de cada shard "
                         "ate esse total — nao corta o inicio, que pegaria so os primeiros "
                         "parquets e testaria uma fatia estreita do crawl em vez do corpus")
    ap.add_argument("--incompleto-ok", action="store_true",
                    help="permite juntar com a coleta em andamento (⚠️ corpus TRUNCADO)")
    args = ap.parse_args()

    import numpy as np

    faixas = [c for c in args.faixas.upper() if c in "ABC"]
    if not faixas:
        print("ERRO: --faixas precisa conter A, B ou C", file=sys.stderr)
        return 1
    args.saida.mkdir(parents=True, exist_ok=True)

    # ⚠️ GUARDA CONTRA TRUNCAMENTO SILENCIOSO — o defeito que este script tinha e que so
    # apareceu ao testa-lo com a coleta rodando: `glob` pega TAMBEM os .bin dos parquets
    # ainda em escrita, e ignora os que nem comecaram. O resultado e um train.bin de
    # aparencia perfeitamente normal, com metade do corpus, e nenhum aviso. So entram aqui
    # os shards de parquets que o coletor declarou CONCLUIDOS no estado.json.
    estado_p = args.entrada / "estado.json"
    if not estado_p.exists():
        print(f"ERRO: {estado_p} nao existe — nao da para saber quais shards estao "
              f"completos. Rode a coleta primeiro.", file=sys.stderr)
        return 1
    est = json.loads(estado_p.read_text(encoding="utf-8"))
    prontos = sorted(est.get("concluidos") or [])
    todos = sorted({int(p.stem.rsplit("_", 1)[1])
                    for f in faixas for p in args.entrada.glob(f"pt_{f}_*.bin")})
    em_curso = [i for i in todos if i not in prontos]
    if em_curso and not args.incompleto_ok:
        for linha in (
            "ERRO: a coleta ainda esta em andamento.",
            f"  parquets concluidos: {prontos}",
            f"  ainda escrevendo   : {em_curso}",
            "  Juntar agora produziria um corpus TRUNCADO com aparencia normal.",
            "  Espere terminar, ou use --incompleto-ok se e' mesmo o que voce quer.",
        ):
            print(linha, file=sys.stderr)
        return 1
    if em_curso:
        print(f"  ⚠️ --incompleto-ok: IGNORANDO {len(em_curso)} parquets em escrita {em_curso}\n")

    shards = sorted(p for f in faixas for i in prontos
                    for p in args.entrada.glob(f"pt_{f}_{i:03d}.bin"))
    if not shards:
        print(f"ERRO: nenhum shard concluido de pt_[{args.faixas}]_* em {args.entrada}",
              file=sys.stderr)
        return 1
    print(f"  parquets concluidos: {len(prontos)} {prontos}")

    total_bytes = sum(p.stat().st_size for p in shards)
    print("=" * 70)
    print(f"JUNTANDO faixas {'+'.join(faixas)} — {len(shards)} shards")
    print("=" * 70)
    print(f"  entrada: {total_bytes/1e9:.1f} GB = {total_bytes/2/1e9:.2f}B tokens")
    print(f"  val    : cauda de {args.val_frac:.1%} de CADA shard\n")

    # ⚠️ Amostragem proporcional, nao prefixo. Um corte nos primeiros N tokens do arquivo
    # concatenado pegaria so os 2 primeiros parquets de 13 — o braco do gate mediria
    # "os dois primeiros dumps", nao o corpus. Aqui cada shard cede a mesma FRACAO.
    fracao = 1.0
    if args.max_tokens:
        disponivel = total_bytes / 2
        fracao = min(1.0, args.max_tokens / disponivel)
        print(f"  amostra: {fracao:.1%} de CADA shard -> alvo "
              f"{args.max_tokens/1e9:.2f}B tokens\n")

    n_tr = n_val = 0
    pedaco = args.pedaco_mb * 1_000_000 // 2          # em tokens (uint16)
    with open(args.saida / "train.bin", "wb") as ftr, open(args.saida / "val.bin", "wb") as fva:
        for p in shards:
            n = int((p.stat().st_size // 2) * fracao)
            corte = int(n * (1 - args.val_frac))
            # ⚠️ Ler em pedacos: um shard tem varios GB e np.fromfile inteiro estoura a RAM
            # quando ha 39 deles. O corte cai no meio de um pedaco, entao dividimos ali.
            lido = 0
            with open(p, "rb") as f:
                while lido < n:
                    a = np.fromfile(f, dtype=np.uint16, count=min(pedaco, n - lido))
                    if a.size == 0:
                        break
                    ini, fim = lido, lido + a.size
                    if fim <= corte:
                        a.tofile(ftr); n_tr += a.size
                    elif ini >= corte:
                        a.tofile(fva); n_val += a.size
                    else:
                        k = corte - ini
                        a[:k].tofile(ftr); n_tr += k
                        a[k:].tofile(fva); n_val += a.size - k
                    lido = fim
            print(f"  {p.name:<18} {n/1e6:8.1f}M tokens", flush=True)

    # ⚠️ O meta.json tem que satisfazer o CONTRATO do pretrain.py, que le vocab/eos e
    # ABORTA sem eles. Na primeira tentativa gravei um meta com esquema proprio, subi so
    # os .bin, e os dois bracos do gate morreram no pod em 1 minuto com "meta.json nao
    # existe". Barato porque falhou alto — mas evitavel lendo o contrato antes.
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    eos = tok.convert_tokens_to_ids("<|endoftext|>")
    meta = {"tokens_treino": n_tr, "tokens_val": n_val,
            "vocab": tok.vocab_size, "eos": eos, "dtype": "uint16",
            "faixas": faixas, "shards": [p.name for p in shards],
            "parquets_concluidos": prontos, "parquets_ignorados": em_curso,
            "val_frac": args.val_frac, "fonte": "fineweb-2 por_Latn (ODC-By)",
            "idioma": "100% pt", "tokenizer": str(args.tokenizer)}
    (args.saida / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"  train.bin  {n_tr/1e9:6.2f}B tokens · {n_tr*2/1e9:5.1f} GB")
    print(f"  val.bin    {n_val/1e6:6.1f}M tokens · {n_val*2/1e9:5.2f} GB")
    print(f"\n  Para o Bee-150M (151,2M params): {n_tr/151.2e6:.0f} tokens por parametro")
    print("  (o v3 rodou com 65; Chinchilla-otimo e' 20; o Tucano-160m usou ~1.230)")
    print("\n  ⚠️ Avaliar com bee/eval_gate2.py no holdout [7,23] — NAO com a perplexidade")
    print("     de validacao daqui, que nao e' comparavel com a do v3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
