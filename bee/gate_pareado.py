"""Gate pareado: corpus CRU x corpus FILTRADO, mesmo orcamento de tokens.

⭐ POR QUE ESTE GATE EXISTE
  O v3 custou US$ 34 e 21,76 h de A100 para mover o bpb em 0,1%. Um gate pareado
  de ~30 min responde a mesma pergunta antes do run longo. A recomendacao veio da
  leitura dos papers e vale como regra: **nenhum run longo sem gate pareado antes.**

⚠️ A ARMADILHA DE METODO — em que holdout medir
  Se medir na distribuicao CRUA, o braco cru ganha de graca. Se medir na FILTRADA,
  o filtrado ganha. Por isso o FineWeb-Edu avalia em benchmark externo, nao em
  perplexidade do proprio corpus. Aqui o holdout e' **Wikipedia em portugues** —
  fonte diferente do fineweb-2, que NENHUM dos dois bracos ve no treino, e que
  representa o tipo de texto que queremos que o Bee modele bem.
  Reportamos tambem o bpb num holdout CRU de fineweb, para mostrar os dois lados.

O PAREAMENTO (tudo identico menos os dados):
  mesma arquitetura · mesma semente · mesmos passos · mesmo LR · mesmo schedule
  ⭐ e mesmo numero de TOKENS — nao de documentos. Documento filtrado e' mais
  longo em media, entao parear por documento daria mais token ao filtrado e o
  experimento mediria a coisa errada.

Uso:
    python bee/gate_pareado.py --preparar --tokens 40e6
    python bee/gate_pareado.py --treinar
    python bee/gate_pareado.py --avaliar
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))
BASE = ROOT / "bee" / "gate"
TOKENIZER = ROOT / "models" / "bee-150m-v3-base"


# ============================== preparo dos dados ============================
def preparar(args) -> int:
    import joblib
    import numpy as np
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer

    from expand_corpus import listar_parquets, qualidade_ok

    BASE.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    modelo = joblib.load(args.classificador)
    vet, reg = modelo["vetorizador"], modelo["regressor"]
    print(f"classificador: F1 {modelo['f1']:.3f} · correlacao {modelo['correlacao']:.3f}")

    arqs = listar_parquets()
    idxs = [int(x) for x in args.parquets.split(",")]
    docs: list[str] = []
    for i in idxs:
        caminho = hf_hub_download("HuggingFaceFW/fineweb-2", arqs[i], repo_type="dataset")
        n0 = len(docs)
        for lote in pq.ParquetFile(caminho).iter_batches(batch_size=2000, columns=["text"]):
            for t in lote.column("text").to_pylist():
                if qualidade_ok(t) is None:
                    docs.append(t)
            if len(docs) - n0 >= args.docs_por_parquet:
                break
        print(f"  parquet {i:03d}: +{len(docs)-n0} docs (total {len(docs)})")

    print(f"\npontuando {len(docs)} docs com o classificador (em lotes)...")
    partes = []
    for i in range(0, len(docs), 20000):
        partes.append(reg.predict(vet.transform([d[:2500] for d in docs[i:i + 20000]])))
        print(f"  {min(i + 20000, len(docs))}/{len(docs)}", flush=True)
    scores = np.concatenate(partes)
    ordem = np.argsort(-scores)                       # melhor -> pior

    alvo = int(args.tokens)
    def escrever(nome: str, indices) -> dict:
        """Escreve ate ALVO tokens. Parear por TOKEN, nunca por documento."""
        ids_out, n = [], 0
        usados = 0
        for i in indices:
            e = tok(docs[i], add_special_tokens=False)["input_ids"]
            ids_out.extend(e + [0])                   # 0 = <|endoftext|>
            n += len(e) + 1
            usados += 1
            if n >= alvo:
                break
        arr = np.array(ids_out[:alvo], dtype=np.uint16)
        arr.tofile(BASE / f"{nome}.bin")
        m = {"tokens": int(arr.size), "docs": usados,
             "score_medio": float(scores[list(indices)[:usados]].mean())}
        print(f"  {nome:9s}: {m['tokens']/1e6:.1f}M tokens de {usados} docs "
              f"· score medio {m['score_medio']:.2f}")
        return m

    print(f"\nescrevendo os dois bracos com {alvo/1e6:.0f}M tokens CADA:")
    meta = {"cru": escrever("cru", range(len(docs))),          # ordem natural
            "filtrado": escrever("filtrado", ordem)}           # melhores primeiro
    meta["retencao_filtrado"] = meta["filtrado"]["docs"] / len(docs)
    r = meta["retencao_filtrado"]
    print(f"\n  o braco filtrado usou os {r:.1%} melhores documentos")
    print(f"  score medio: cru {meta['cru']['score_medio']:.2f} · "
          f"filtrado {meta['filtrado']['score_medio']:.2f}")

    # ⚠️ GUARDA (a lição da 1a tentativa deste gate, 2026-08-04): o pool bruto tem
    # de ser ~10x o orcamento de tokens. Com pool pequeno o braco "filtrado" desce
    # quase todo o ranking so para encher os tokens — na 1a rodada usou 69% dos docs
    # e o score medio subiu so de 1,78 para 2,27, contra os 3,70 que a curva promete
    # a 10% de retencao. O experimento mediria uma filtragem FRACA e devolveria
    # "empate" por artefato do setup, nao por propriedade do metodo.
    if r > 0.25:
        print(f"\n  POOL PEQUENO DEMAIS ({r:.0%} de retencao). Para testar o regime de "
              f"~10%,\n  o pool bruto precisa ser ~10x o orcamento: aumente "
              f"--docs-por-parquet\n  ou --parquets, ou reduza --tokens.", file=sys.stderr)
        return 1

    # ---- holdouts: Wikipedia PT (NEUTRO) + fineweb cru, para os dois lados ----
    print("\nholdouts (nenhum braco treina neles):")
    from datasets import load_dataset
    wiki = load_dataset("wikimedia/wikipedia", "20231101.pt", split="train",
                        streaming=True)
    textos_wiki = []
    for r in wiki:
        if qualidade_ok(r["text"]) is None:
            textos_wiki.append(r["text"][:4000])
        if len(textos_wiki) >= 300:
            break
    (BASE / "holdout_wiki.json").write_text(json.dumps(textos_wiki, ensure_ascii=False),
                                            encoding="utf-8")
    print(f"  wikipedia-pt : {len(textos_wiki)} docs  <- NEUTRO, o que decide")
    caminho = hf_hub_download("HuggingFaceFW/fineweb-2", arqs[60], repo_type="dataset")
    crus = []
    for lote in pq.ParquetFile(caminho).iter_batches(batch_size=1000, columns=["text"]):
        for t in lote.column("text").to_pylist():
            if qualidade_ok(t) is None:
                crus.append(t[:4000])
        if len(crus) >= 300:
            break
    (BASE / "holdout_cru.json").write_text(json.dumps(crus[:300], ensure_ascii=False),
                                           encoding="utf-8")
    print(f"  fineweb cru  : {len(crus[:300])} docs  <- favorece o braco cru, de proposito")

    (BASE / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return 0


# ================================== treino ===================================
def treinar_um(nome: str, args) -> dict:
    import numpy as np
    import torch
    from transformers import AutoTokenizer

    from config import ESCADA, para_llama_config

    torch.manual_seed(args.seed)                       # ⭐ mesma semente nos dois
    np.random.seed(args.seed)
    dados = np.fromfile(BASE / f"{nome}.bin", dtype=np.uint16)
    import dataclasses
    cfg = dataclasses.replace(ESCADA[args.tamanho], seq_len=args.seq_len)
    from transformers import AutoModelForCausalLM, LlamaForCausalLM
    modelo = LlamaForCausalLM(para_llama_config(cfg)).cuda()
    n_par = sum(p.numel() for p in modelo.parameters())

    passos = args.passos
    tok_por_passo = args.micro_batch * args.grad_accum * args.seq_len
    print(f"\n{'='*66}\nBRACO: {nome}\n{'='*66}")
    print(f"  {n_par/1e6:.1f}M params · {len(dados)/1e6:.1f}M tokens · {passos} passos "
          f"· {tok_por_passo*passos/1e6:.1f}M tokens vistos")

    opt = torch.optim.AdamW(modelo.parameters(), lr=args.lr, betas=(0.9, 0.95),
                            weight_decay=0.1)
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=args.lr, total_steps=passos, pct_start=0.02, anneal_strategy="cos")
    modelo.train()
    t0 = time.time()
    for passo in range(passos):
        opt.zero_grad(set_to_none=True)
        perda_acc = 0.0
        for _ in range(args.grad_accum):
            ini = np.random.randint(0, len(dados) - args.seq_len - 1,
                                    size=args.micro_batch)
            x = torch.from_numpy(np.stack([dados[i:i+args.seq_len] for i in ini]).astype(np.int64)).cuda()
            with torch.autocast("cuda", dtype=torch.bfloat16):
                perda = modelo(input_ids=x, labels=x).loss / args.grad_accum
            perda.backward()
            perda_acc += perda.item()
        torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
        opt.step()
        sched.step()
        if passo % 20 == 0 or passo == passos - 1:
            print(f"  passo {passo:>4}/{passos} · perda {perda_acc:.3f} · "
                  f"{(time.time()-t0)/60:.1f} min", flush=True)
    modelo.save_pretrained(BASE / f"modelo_{nome}")
    AutoTokenizer.from_pretrained(TOKENIZER).save_pretrained(BASE / f"modelo_{nome}")
    return {"params": n_par, "perda_final": perda_acc, "min": (time.time()-t0)/60}


# ================================= avaliacao =================================
def avaliar(args) -> int:
    import math

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(TOKENIZER)
    LN2 = math.log(2.0)
    resultado = {}
    for nome in ("cru", "filtrado"):
        d = BASE / f"modelo_{nome}"
        if not d.exists():
            print(f"faltando {d}", file=sys.stderr)
            return 1
        m = AutoModelForCausalLM.from_pretrained(d, dtype=torch.bfloat16).cuda().eval()
        resultado[nome] = {}
        for hn in ("wiki", "cru"):
            textos = json.loads((BASE / f"holdout_{hn}.json").read_text(encoding="utf-8"))
            bits, byts = 0.0, 0
            with torch.no_grad():
                for t in textos:
                    ids = tok(t, add_special_tokens=False,
                              return_tensors="pt")["input_ids"][:, :args.seq_len].cuda()
                    # ⚠️ Contar os bytes do TRECHO PONTUADO, nao do documento inteiro.
                    # Somar bits de 512 tokens e dividir pelos bytes de 4.000 chars
                    # subestima o bpb em ~1,7x. E' o mesmo defeito que existe latente
                    # no eval_gate2.py (la defendido por max_chars=4000 caber em 2048
                    # tokens); aqui seq_len=512 e o corte DISPARA. Reintroduzi o bug
                    # num script novo depois de documenta-lo — por isso a checagem de
                    # ordem de grandeza contra um numero conhecido (bpb do v3 = 3,457)
                    # vale mais que a revisao do codigo.
                    nb = len(tok.decode(ids[0], skip_special_tokens=True).encode("utf-8"))
                    if ids.shape[1] < 2:
                        continue
                    lg = m(ids).logits
                    nll = torch.nn.functional.cross_entropy(
                        lg[0, :-1].float(), ids[0, 1:], reduction="sum").item()
                    bits += nll / LN2
                    byts += nb
            resultado[nome][hn] = bits / byts
        del m
        torch.cuda.empty_cache()

    print(f"\n{'='*66}\nGATE PAREADO — bits-por-byte (MENOR e' melhor)\n{'='*66}")
    print(f"{'braco':<12}{'wikipedia-pt':>16}{'fineweb cru':>16}")
    print("-" * 46)
    for nome in ("cru", "filtrado"):
        print(f"{nome:<12}{resultado[nome]['wiki']:>16.4f}{resultado[nome]['cru']:>16.4f}")
    dw = (resultado["cru"]["wiki"] - resultado["filtrado"]["wiki"]) / resultado["cru"]["wiki"]
    dc = (resultado["cru"]["cru"] - resultado["filtrado"]["cru"]) / resultado["cru"]["cru"]
    print(f"\n  ganho do filtrado no holdout NEUTRO (wikipedia) : {dw:+.2%}")
    print(f"  ganho do filtrado no holdout cru (favorece o cru): {dc:+.2%}")
    print(f"\n{'='*66}")
    if dw > 0.02:
        print(">>> PASSA: filtrar melhora o modelo com o MESMO orcamento de tokens.")
        print("    Vale coletar pool grande e filtrar antes do proximo run longo.")
    elif dw > -0.02:
        print(">>> EMPATE: filtrar nao piora, mas nao paga o custo de anotar em escala")
        print("    nesta escala de teste. Repetir com mais tokens antes de decidir.")
    else:
        print(">>> NAO PASSA: o corpus filtrado ficou PIOR no holdout neutro.")
        print("    Filtragem agressiva pode ter tirado diversidade. Nao escalar assim.")
    (BASE / "resultado.json").write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preparar", action="store_true")
    ap.add_argument("--treinar", action="store_true")
    ap.add_argument("--avaliar", action="store_true")
    ap.add_argument("--classificador", type=Path, default=ROOT / "bee" / "edu" / "classificador.joblib")
    ap.add_argument("--parquets", default="1,13,26,41,55")
    ap.add_argument("--docs-por-parquet", type=int, default=12000)
    ap.add_argument("--tokens", type=float, default=40e6, help="tokens POR BRACO")
    ap.add_argument("--tamanho", default="150m")
    ap.add_argument("--seq-len", type=int, default=512)
    # ⚠️ micro-batch 2 e o TETO MEDIDO na RTX 5070 8 GB (ver docs/sft-resultado.md):
    # o vilao e o tensor de logits (batch x seq x 32000) + upcast fp32 da CE. Em 8
    # a memoria vaza pra RAM do host e o passo cai ~100x — e o sintoma NAO e OOM,
    # e lentidao silenciosa. grad_accum 32 mantem os mesmos tokens por passo.
    ap.add_argument("--micro-batch", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=32)
    ap.add_argument("--passos", type=int, default=400)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if args.preparar:
        return preparar(args)
    if args.treinar:
        r = {n: treinar_um(n, args) for n in ("cru", "filtrado")}
        (BASE / "treino.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
        return 0
    if args.avaliar:
        return avaliar(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
