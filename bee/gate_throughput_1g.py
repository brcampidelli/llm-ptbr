"""Gate de throughput do Bee-1G — medir ANTES de comprometer orcamento (§3, §4).

Foi esta medicao que, no Bee-350M, cortou uma estimativa de custo PELA METADE por US$ 0,15.
Aqui ela responde tres coisas que nenhuma conta de guardanapo responde:

    1. o que CABE em 32 GB na geometria real (1,052B params, seq_len 4096)
    2. quantos tokens por segundo, em REGIME
    3. quanto custa 1B de tokens, em $/B — nunca em $/h (§4)

⚠️ E ela e' obrigatoria porque a extrapolacao ja' errou neste projeto: a estimativa do 350M saiu
   pela metade, e a escolha de GPU por $/h em vez de $/B mandou comprar a placa 36% mais cara
   por token. O preditor de throughput entre placas e' o TDP, e nem ele dispensa medir.

CONFIGURACAO — as decisoes ja' fechadas dos gates anteriores:
    geometria   ESCADA["1b"]: 28 camadas · d_model 1792 · 28q/4kv · intermediate 4864 · seq 4096
    vocab       64.000 (Gate T1: folga contra 96k converge, e o custo nao)
    dado        pool `pt-50` (Gate T2: troca 3,5x a favor do portugues)
    => 1,052B params, embedding 10,9%

🔴 O QUE ESTE GATE NAO MEDE:
   · qualidade de nada. E' relogio e memoria, so'.
   · o custo de um run LONGO: throughput cai com o tempo se houver termica ou I/O de checkpoint,
     e 40 passos nao veem isso. O numero e' um TETO otimista.
   · a leitura vale para ESTA placa. §4: o preditor entre placas e' o TDP, e mesmo assim mede-se.

Uso:
    python bee/gate_throughput_1g.py --pool bee/gate_t2_mistura/pool_pt-50.bin
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
VOCAB = 64_000
PRECO_HORA = 0.99


def _e_oom(e: BaseException) -> bool:
    """OOM chega como OutOfMemoryError num caminho e AcceleratorError noutro (medido 09-02)."""
    return "out of memory" in str(e).lower() or type(e).__name__ in (
        "OutOfMemoryError", "AcceleratorError")


def grava(doc, dest):
    """Persiste A CADA configuracao medida.

    🔴 Tres vezes em dois dias este projeto perdeu medicao por gravar so' no fim: o meta.json
    por braco (T1), o probe por lote (T-TRAD) e o `avaliar` que morreu montando a tabela com os
    6 modelos ja' medidos. Num gate cujo objetivo E' estourar a memoria ate' achar o limite,
    gravar no fim seria garantir a perda.
    """
    dest.parent.mkdir(exist_ok=True)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(dest)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", default="bee/gate_t2_mistura/pool_pt-50.bin")
    ap.add_argument("--passos", type=int, default=40,
                    help="§3: so' se le' throughput a partir do passo 20, com 3 leituras iguais")
    ap.add_argument("--micro-batches", default="1,2,4,8")
    ap.add_argument("--seq-lens", default="4096")
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--grad-checkpoint", action="store_true",
                    help="recomputa ativacoes no backward — troca ~30% de tempo por muita VRAM. "
                         "MEDIDO 09-04: sem isto o 1,052B NAO CABE em 32 GB nem com mb=1 a "
                         "seq 4096, e o vilao e' o tensor de logits (4096 x 64k x 2B = 524 MB "
                         "em bf16, dobrado pelo upcast da perda) — a mesma licao do SFT.")
    ap.add_argument("--compile", action="store_true",
                    help="torch.compile — no 350M deu +17%, a unica otimizacao que funcionou")
    args = ap.parse_args()

    import numpy as np
    import torch
    import torch.nn.functional as F
    from transformers import LlamaForCausalLM
    from config import ESCADA, para_llama_config

    gpu = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 2 ** 30
    print(f"{gpu} · {vram:.1f} GB")

    dados = np.fromfile(ROOT / args.pool, dtype=np.uint32)
    print(f"pool {args.pool}: {len(dados)/1e6:.1f}M tokens · max id {int(dados.max()):,}")
    if int(dados.max()) >= VOCAB:
        raise SystemExit(f"🔴 pool tem id {dados.max()} >= vocab {VOCAB}")

    doc = {"_gate": "throughput do Bee-1G na configuracao real",
           "_regua": "tokens/s em REGIME: passo >= 20, mediana das 3 ultimas leituras (§3)",
           "_nao_mede": [
               "qualidade de nada — e' relogio e memoria",
               "queda de throughput em run LONGO (termica, I/O de checkpoint): 40 passos nao "
               "veem isso, entao o numero e' um TETO otimista",
               "outras placas: §4 mede que o preditor e' o TDP, e mesmo assim mede-se",
           ],
           "gpu": gpu, "vram_gb": vram, "vocab": VOCAB, "pool": args.pool,
           "grad_checkpoint": args.grad_checkpoint, "compile": args.compile,
           "preco_hora": PRECO_HORA, "configs": {}}
    dest = ROOT / "docs" / "gate-throughput-1g.json"

    print(f"\n{'mb':>4}{'seq':>6}{'accum':>7}{'tok/passo':>11}{'tok/s':>9}"
          f"{'VRAM GB':>9}{'$/B tok':>9}  params")
    print("-" * 72)

    for seq in [int(x) for x in args.seq_lens.split(",")]:
        for mb in [int(x) for x in args.micro_batches.split(",")]:
            chave = f"mb{mb}_seq{seq}_ac{args.grad_accum}"
            try:
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                cfg = dataclasses.replace(ESCADA["1b"], vocab=VOCAB, seq_len=seq)
                modelo = LlamaForCausalLM(para_llama_config(cfg)).cuda()
                n_par = sum(p.numel() for p in modelo.parameters())
                if args.grad_checkpoint:
                    modelo.gradient_checkpointing_enable()
                    modelo.config.use_cache = False
                if args.compile:
                    modelo = torch.compile(modelo)
                opt = torch.optim.AdamW(modelo.parameters(), lr=args.lr, betas=(0.9, 0.95),
                                        weight_decay=0.1)
                modelo.train()

                nb = len(dados) // seq
                rng = np.random.default_rng(42)
                tok_passo = mb * args.grad_accum * seq
                leituras, t0, primeiro = [], None, True

                for passo in range(args.passos):
                    opt.zero_grad(set_to_none=True)
                    for _ in range(args.grad_accum):
                        idx = rng.integers(0, nb, size=mb)
                        lote = np.stack([dados[i * seq:(i + 1) * seq] for i in idx])
                        x = torch.from_numpy(lote.astype(np.int64)).cuda()
                        # §1 — a guarda de rotulos, com DADO REAL, antes do passo 1
                        if primeiro:
                            with torch.no_grad():
                                s1 = modelo(input_ids=x[:1], labels=x[:1])
                                man = F.cross_entropy(s1.logits[0, :-1].float(),
                                                      x[0, 1:]).item()
                            if abs(s1.loss.item() - man) > 0.01:
                                raise SystemExit("🔴 convencao de rotulos errada — abortando")
                            print(f"  guarda de rotulos: {s1.loss.item():.4f} vs {man:.4f} ✅",
                                  flush=True)
                            primeiro = False
                        with torch.autocast("cuda", dtype=torch.bfloat16):
                            perda = modelo(input_ids=x, labels=x).loss / args.grad_accum
                        perda.backward()
                    torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
                    opt.step()
                    # §3: o aquecimento NAO entra. So' a partir do passo 20.
                    if passo == 19:
                        torch.cuda.synchronize()
                        t0 = time.time()
                    elif passo > 19 and passo % 5 == 0:
                        torch.cuda.synchronize()
                        leituras.append(tok_passo * (passo - 19) / (time.time() - t0))

                if len(leituras) < 3:
                    raise SystemExit(f"🔴 so' {len(leituras)} leituras — aumente --passos "
                                     f"(§3 exige 3 coincidentes em regime)")
                import statistics as st
                tps = st.median(leituras[-3:])
                disp = (max(leituras[-3:]) - min(leituras[-3:])) / tps
                pico = torch.cuda.max_memory_allocated() / 2 ** 30
                custo = 1e9 / tps / 3600 * PRECO_HORA
                print(f"{mb:>4}{seq:>6}{args.grad_accum:>7}{tok_passo:>11,}{tps:>9,.0f}"
                      f"{pico:>9.2f}{custo:>9.2f}  {n_par/1e9:.3f}B", end="")
                print(f"   ⚠️ dispersao {100*disp:.1f}% entre as 3 ultimas" if disp > 0.03 else "")
                doc["configs"][chave] = {"micro_batch": mb, "seq_len": seq,
                                         "grad_accum": args.grad_accum, "params": int(n_par),
                                         "tok_por_passo": tok_passo, "tok_s": tps,
                                         "dispersao_3_ultimas": disp, "vram_pico_gb": pico,
                                         "usd_por_bilhao": custo, "compile": args.compile}
                grava(doc, dest)
                del modelo, opt
            except Exception as e:
                if not _e_oom(e):
                    raise
                print(f"{mb:>4}{seq:>6}{args.grad_accum:>7}   🔴 OOM em {vram:.0f} GB")
                doc["configs"][chave] = {"micro_batch": mb, "seq_len": seq, "oom": True,
                                         "grad_checkpoint": args.grad_checkpoint}
                grava(doc, dest)
                torch.cuda.empty_cache()
                break   # micro_batch maior tambem nao cabe NESTE seq_len

    ok = {k: v for k, v in doc["configs"].items() if not v.get("oom")}
    if ok:
        melhor = max(ok, key=lambda k: ok[k]["tok_s"])
        m = ok[melhor]
        doc["melhor"] = melhor
        grava(doc, dest)
        print(f"\n{'='*72}\nCUSTO do Bee-1G — medido, nunca extrapolado (§4)\n{'='*72}")
        print(f"melhor: {melhor} · {m['tok_s']:,.0f} tok/s · {m['vram_pico_gb']:.1f} GB de "
              f"{vram:.0f}")
        print(f"{'orcamento':<26}{'tok/param':>10}{'horas':>9}{'US$':>10}")
        print("-" * 55)
        for rot, tok in [("Chinchilla ~20x", 21e9), ("como o 350M (63x)", 66e9),
                         ("como o 150M (143x)", 150e9)]:
            h = tok / m["tok_s"] / 3600
            print(f"{rot:<26}{tok/m['params']:>10.0f}{h:>9.0f}{h*PRECO_HORA:>10,.0f}")
        print("\n⚠️ TETO OTIMISTA: 40 passos nao veem queda termica nem I/O de checkpoint.")
    print(f"\nartefato: docs/{dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
