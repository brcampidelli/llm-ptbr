"""Sweep de LR do Bee-1G — a grade tem de CERCAR o ótimo, nunca ficar de um lado só.

🔴 POR QUE ISTO EXISTE. O `config.py` nao tem regra de LR, e o gate de throughput usou `1e-3`
   POR ARBITRIO. Este projeto ja' perdeu **7 de 15 bracos** por grade de LR mal centrada (§2f):
   varri LoRA de 5x a 20x acima do otimo medido, 3 de 4 bracos morreram no maior LR, e o unico
   sobrevivente ficou na BORDA — o que transforma qualquer comparacao numa afirmacao sobre o LR
   em vez de sobre o que se queria medir.

⭐ A Step Law que o projeto usa (`eta* = 1,79 * N^-0,713 * D^0,307`) da', para N = 1,052B:
       20B tokens -> 9,6e-4        66B -> 1,4e-3        150B -> 1,8e-3
   A grade padrao [5e-4, 1e-3, 2e-3] CERCA os tres — e o script ABORTA se a grade dada ficar
   toda de um lado do intervalo previsto.

⚠️ E ha' um aviso da literatura que este sweep NAO cobre: com vocab >> largura entra-se no
   *regime Large Vocab*, onde a razao otima LR-embedding / LR-oculto escala Θ(√width)
   (`2506.15025`, validado pre-treinando 1B do zero). Aqui usa-se **um LR unico** para todas as
   camadas, como o resto do projeto — entao o resultado e' "qual LR unico e' menos ruim", nao
   "qual e' o LR otimo". Fica declarado.

🔴 SONDA DE COLAPSO (§2f). Um braco morto e um braco ruim marcam parecido na loss e viram a
   mesma linha na tabela — mas so' um e' evidencia. Aqui o colapso e' detectado por:
     · loss NaN ou infinita;
     · loss final PIOR que a do passo 50 (divergiu);
     · grad-norm mediano acima de um teto.
   Braco colapsado ENTRA na tabela com o motivo — omiti-lo faria "testado e morreu" parecer
   "nao testado".

Uso:
    python bee/gate_lr_1g.py --pool bee/gate_t2_mistura/pool_pt-50.bin --lrs 5e-4,1e-3,2e-3
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import statistics as st
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
VOCAB = 64_000
# intervalo que a Step Law preve para N=1,052B entre 20B e 150B de tokens
STEP_LAW_MIN, STEP_LAW_MAX = 9.6e-4, 1.8e-3


def _e_oom(e: BaseException) -> bool:
    return "out of memory" in str(e).lower() or type(e).__name__ in (
        "OutOfMemoryError", "AcceleratorError")


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", default="bee/gate_t2_mistura/pool_pt-50.bin")
    ap.add_argument("--lrs", default="5e-4,1e-3,2e-3")
    ap.add_argument("--passos", type=int, default=1000)
    ap.add_argument("--micro-batch", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--semente", type=int, default=42)
    ap.add_argument("--teto-grad-norm", type=float, default=50.0)
    args = ap.parse_args()

    lrs = sorted(float(x) for x in args.lrs.split(","))
    # 🔴 §2f — a grade tem de CERCAR o intervalo previsto, nao ficar toda de um lado
    if min(lrs) > STEP_LAW_MIN or max(lrs) < STEP_LAW_MAX:
        raise SystemExit(
            f"🔴 GRADE NAO CERCA a Step Law. Ela preve [{STEP_LAW_MIN:.1e}, {STEP_LAW_MAX:.1e}] "
            f"para N=1,052B entre 20B e 150B de tokens; a grade dada e' "
            f"[{min(lrs):.1e}, {max(lrs):.1e}].\n"
            f"   Grade toda de um lado do otimo mede o LR, nao o modelo (§2f: 7 de 15 bracos).")

    import numpy as np
    import torch
    import torch.nn.functional as F
    from transformers import LlamaForCausalLM
    from config import ESCADA, para_llama_config

    gpu = torch.cuda.get_device_name(0)
    dados = np.fromfile(ROOT / args.pool, dtype=np.uint32)
    print(f"{gpu} · pool {args.pool}: {len(dados)/1e6:.1f}M tokens")
    print(f"grade {[f'{x:.1e}' for x in lrs]} cerca [{STEP_LAW_MIN:.1e}, {STEP_LAW_MAX:.1e}] ✅\n")

    doc = {"_gate": "sweep de LR do Bee-1G",
           "_regua": "loss media dos ultimos 50 passos, semente unica — compara LR, nao modelos",
           "_nao_mostra": [
               "o LR otimo por CAMADA: usa-se um LR unico, e o 2506.15025 mede que no regime "
               "de vocab grande a razao embedding/oculto escala Θ(√width). Isto responde 'qual "
               "LR unico e' menos ruim', nao 'qual e' o otimo'",
               "o comportamento em run LONGO: 1.000 passos veem instabilidade inicial, nao "
               "divergencia tardia",
               "interacao com o schedule: aqui e' LR constante, e o run usara' WSD ou cosine",
           ],
           "gpu": gpu, "passos": args.passos, "semente": args.semente,
           "step_law": {"min": STEP_LAW_MIN, "max": STEP_LAW_MAX}, "bracos": {}}
    dest = ROOT / "docs" / "gate-lr-1g.json"

    print(f"{'LR':>9}{'loss@50':>10}{'loss fim':>10}{'|grad|':>9}{'min':>7}  veredito")
    print("-" * 62)
    for lr in lrs:
        chave = f"{lr:.1e}"
        try:
            torch.cuda.empty_cache()
            torch.manual_seed(args.semente)
            np.random.seed(args.semente)
            cfg = dataclasses.replace(ESCADA["1b"], vocab=VOCAB, seq_len=args.seq_len)
            m = LlamaForCausalLM(para_llama_config(cfg)).cuda()
            m.gradient_checkpointing_enable()
            m.config.use_cache = False
            opt = torch.optim.AdamW(m.parameters(), lr=lr, betas=(0.9, 0.95), weight_decay=0.1)
            m.train()

            nb = len(dados) // args.seq_len
            rng = np.random.default_rng(args.semente)
            t0, perdas, gnorms, primeiro = time.time(), [], [], True
            for passo in range(args.passos):
                opt.zero_grad(set_to_none=True)
                acc = 0.0
                for _ in range(args.grad_accum):
                    idx = rng.integers(0, nb, size=args.micro_batch)
                    lote = np.stack([dados[i * args.seq_len:(i + 1) * args.seq_len] for i in idx])
                    x = torch.from_numpy(lote.astype(np.int64)).cuda()
                    if primeiro:                      # §1, com dado real, antes do passo 1
                        with torch.no_grad():
                            s1 = m(input_ids=x[:1], labels=x[:1])
                            man = F.cross_entropy(s1.logits[0, :-1].float(), x[0, 1:]).item()
                        if abs(s1.loss.item() - man) > 0.01:
                            raise SystemExit("🔴 convencao de rotulos errada — abortando")
                        primeiro = False
                    with torch.autocast("cuda", dtype=torch.bfloat16):
                        perda = m(input_ids=x, labels=x).loss / args.grad_accum
                    perda.backward()
                    acc += perda.item()
                gn = torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
                gnorms.append(float(gn))
                opt.step()
                perdas.append(acc)

            l50 = st.mean(perdas[40:60])
            lfim = st.mean(perdas[-50:])
            gmed = st.median(gnorms)
            # sonda de colapso — braco morto e braco ruim nao podem virar a mesma linha
            morto = (not all(map(lambda v: v == v and abs(v) != float("inf"), perdas))
                     or lfim >= l50 or gmed > args.teto_grad_norm)
            motivo = ("NaN/inf" if not all(v == v for v in perdas) else
                      "divergiu (fim >= passo 50)" if lfim >= l50 else
                      f"grad-norm {gmed:.0f} > {args.teto_grad_norm:.0f}" if gmed > args.teto_grad_norm
                      else "")
            print(f"{lr:>9.1e}{l50:>10.4f}{lfim:>10.4f}{gmed:>9.2f}"
                  f"{(time.time()-t0)/60:>7.1f}  "
                  + (f"🔴 COLAPSOU — {motivo}" if morto else "✅ treinou"))
            doc["bracos"][chave] = {"lr": lr, "loss_50": l50, "loss_fim": lfim,
                                    "grad_norm_mediano": gmed, "colapsou": bool(morto),
                                    "motivo": motivo, "minutos": (time.time() - t0) / 60}
            del m, opt
        except Exception as e:
            if not _e_oom(e):
                raise
            print(f"{lr:>9.1e}   🔴 OOM")
            doc["bracos"][chave] = {"lr": lr, "oom": True}
        dest.parent.mkdir(exist_ok=True)
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(dest)

    vivos = {k: v for k, v in doc["bracos"].items()
             if not v.get("oom") and not v.get("colapsou")}
    if vivos:
        melhor = min(vivos, key=lambda k: vivos[k]["loss_fim"])
        doc["melhor"] = melhor
        borda = melhor in (f"{min(lrs):.1e}", f"{max(lrs):.1e}")
        print(f"\nmelhor: LR {melhor} · loss {vivos[melhor]['loss_fim']:.4f}")
        if borda:
            print("⚠️ O MELHOR ESTA' NA BORDA DA GRADE — o otimo pode estar fora dela. §2f: um")
            print("   sobrevivente na borda nao decide; estender a grade para aquele lado.")
        doc["melhor_na_borda"] = bool(borda)
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(dest)
    else:
        print("\n🔴 TODOS os bracos colapsaram ou estouraram — a grade esta' inteira do lado errado.")
    print(f"\nartefato: docs/{dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
