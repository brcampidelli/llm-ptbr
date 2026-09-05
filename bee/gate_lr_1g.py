"""Sweep de LR do Bee-1G — a grade tem de CERCAR o ótimo, nunca ficar de um lado só.

🔴 POR QUE ISTO EXISTE. O `config.py` nao tem regra de LR, e o gate de throughput usou `1e-3`
   POR ARBITRIO. Este projeto ja' perdeu **7 de 15 bracos** por grade de LR mal centrada (§2f):

   varri LoRA de 5x a 20x acima do otimo medido, 3 de 4 bracos morreram no maior LR, e o unico
   sobrevivente ficou na BORDA — o que transforma qualquer comparacao numa afirmacao sobre o LR
   em vez de sobre o que se queria medir.

🔴🔴 E A PRIMEIRA VERSAO DESTA GUARDA MIRAVA O HORIZONTE ERRADO (medido 2026-09-04).
   A Step Law (`eta* = 1,79 * N^-0,713 * D^0,307`) depende de **D**, e para N = 1,052B da':

       32,8M tokens (o SWEEP) -> 1,34e-4   |   20B -> 9,6e-4   66B -> 1,4e-3   150B -> 1,8e-3

   A guarda velha cravava `[9,6e-4, 1,8e-3]` — a faixa do **RUN** — e exigia que a grade
   cercasse aquilo. Mas 1.000 passos x 4 x 4 x 2048 sao **32,8M tokens**, 600x menos: o sweep
   nao tem como enxergar o otimo de um run de 20B, so' o do proprio horizonte.

   ⭐ O que se mediu com a grade `[1,25e-4 … 2e-3]`: otimo em **2,5e-4** (loss 5,501), e o pior
      braco vivo foi **1e-3** (5,722) — que esta' DENTRO da faixa da guarda velha. Lido sem
      cuidado isso vira *"a Step Law erra 4x neste modelo"*; lido no horizonte certo, o medido
      esta' a **1,86x** do previsto (2,5e-4 contra 1,34e-4) e a **confirma**.

🔴🔴 E ESTE DOCSTRING PRESCREVIA O ERRO — corrigido em 2026-09-05.
   Ele dizia: *"Para o run, escale: eta*(D_run) = 2,5e-4 * (D_run/32,8e6)^0,307 (20B -> ~1,8e-3)"*.
   **NAO FACA ISSO.** Validado contra o Bee-350M, que funcionou e e' o melhor modelo do projeto:

       modelo              Step Law (pico)   fase estavel usada   o que a formula acima daria
       Bee-350M @ 21,75B         2,18e-3          1,20e-3 (55%)      4,07e-3  -> 3,39x mais quente
       Bee-1G   @ 20B            9,61e-4          5,28e-4 (55%)      1,79e-3  -> 3,39x mais quente

   O 350M rodou a fase estavel em 55% do pico (`docs/gate2-350m-marcos.json`) e produziu o melhor
   bpb do projeto. A formula o poria 3,4x acima disso.

   ⚠️ O defeito e' §2d puro: este sweep mede LR **CONSTANTE** em **1.000 PASSOS**; a Step Law e'
      ajustada sobre **runs completos** com **cosine**. Multiplicar um otimo de passo-1.000 pelo
      termo D^0,307 de um run completo mistura duas grandezas. As duas ressalvas ja' estavam no
      `_nao_mostra` deste mesmo artefato — "1.000 passos veem instabilidade inicial" e "aqui e'
      LR constante, e o run usara' WSD ou cosine" — e a extrapolacao foi feita assim mesmo.

   ⚠️ E ha' uma segunda armadilha encadeada: em `pretrain.py` o `--lr` e' o **PICO**, e a fase
      estavel do WSD roda em `--lr * --lr-estavel-frac` (0,55). Passar um numero ja' corrigido
      como `--lr` aplica a correcao **duas vezes** — o formato da §1, onde nada da' erro.

   ✅ O QUE ESTE SWEEP ENTREGA, e so' isso: que a regiao [1,25e-4; 2e-3] e' **segura** (nenhum
      colapso), que o minimo e' **interior** e que o grad-norm vira em 2e-3. Ele NAO determina o
      LR do run. Para o run, use a Step Law com a fracao de fase estavel validada no degrau
      vizinho: `--lr <pico da Step Law> --lr-estavel-frac 0.55`.

   ✅ A guarda agora calcula a Step Law no horizonte **deste sweep** e exige que a grade o
      cerque. Testada contra o estado quebrado (§2t): rejeita `[5e-4, 1e-3, 2e-3]` (a 1a
      rodada), rejeita a propria faixa `[9,6e-4, 1,8e-3]` que a versao velha impunha, e
      rejeita `[3e-3, 6e-3, 1,2e-2]` (a grade do E2 que matou 7 de 15 bracos).

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
    python bee/gate_lr_1g.py --pool bee/gate_t2_mistura/pool_pt-50.bin --lrs 1.25e-4,2.5e-4,5e-4,1e-3,2e-3
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
N_PARAM = 1.052e9            # Bee-1G

# 🔴🔴 MEDIDO 2026-09-04 — A GUARDA ANTERIOR MIRAVA O HORIZONTE ERRADO.
#    Ela cravava [9,6e-4, 1,8e-3], que e' a Step Law para o RUN (20B a 150B de tokens), e
#    exigia que a grade cercasse ISSO. Mas o sweep roda 1.000 passos = **32,8M tokens**, e a
#    Step Law depende de D: `eta* = 1,79 * N^-0,713 * D^0,307`. No horizonte do proprio sweep
#    ela preve **1,34e-4**, sete vezes abaixo da faixa que a guarda impunha.
#
#    O efeito medido: a grade [1,25e-4 … 2e-3] deu otimo em **2,5e-4** e o pior braco vivo foi
#    **1e-3** — que esta' DENTRO da faixa da guarda velha. Lido sem cuidado, isso vira "a Step
#    Law erra 4x neste modelo"; lido no horizonte certo, o medido esta' a **1,86x** do previsto
#    e a confirma. Sao §2d outra vez: comparar uma medida feita numa condicao com uma previsao
#    feita para outra.
#
#    ⚠️ E o dano potencial e' de uma direcao so': adotar 2,5e-4 para um run de 20B poria o LR
#    **7x abaixo** do previsto — sem erro, sem excecao, com a loss caindo bonito.
def step_law(N: float, D: float) -> float:
    """LR otimo da Step Law (~3.700 modelos) para N parametros e D tokens."""
    return 1.79 * N ** -0.713 * D ** 0.307


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
    # o default TEM de passar na propria guarda — o antigo ("5e-4,1e-3,2e-3") nao passa mais
    ap.add_argument("--lrs", default="1.25e-4,2.5e-4,5e-4,1e-3,2e-3")
    ap.add_argument("--passos", type=int, default=1000)
    ap.add_argument("--micro-batch", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--semente", type=int, default=42)
    ap.add_argument("--teto-grad-norm", type=float, default=50.0)
    args = ap.parse_args()

    lrs = sorted(float(x) for x in args.lrs.split(","))

    # o horizonte que ESTE sweep enxerga — nao o do run
    d_sweep = args.passos * args.grad_accum * args.micro_batch * args.seq_len
    alvo = step_law(N_PARAM, d_sweep)
    # 🔴 §2f — a grade tem de CERCAR o otimo previsto PARA O HORIZONTE DO SWEEP.
    if not (min(lrs) <= alvo <= max(lrs)):
        raise SystemExit(
            "🔴 GRADE NAO CERCA a Step Law NO HORIZONTE DESTE SWEEP." + chr(10)
            + f"   {args.passos} passos x {args.grad_accum} x {args.micro_batch} x "
            + f"{args.seq_len} = {d_sweep/1e6:.1f}M tokens -> eta* previsto "
            + f"{alvo:.2e}" + chr(10)
            + f"   grade dada: [{min(lrs):.1e}, {max(lrs):.1e}]" + chr(10)
            + "   Grade toda de um lado do otimo mede o LR, nao o modelo "
            + "(§2f: 7 de 15 bracos).")

    print(f"horizonte do sweep: {d_sweep/1e6:.1f}M tokens -> Step Law preve {alvo:.2e}")
    print("grade " + str([f"{x:.1e}" for x in lrs]) + f" cerca {alvo:.2e} ✅" + chr(10))

    import numpy as np
    import torch
    import torch.nn.functional as F
    from transformers import LlamaForCausalLM
    from config import ESCADA, para_llama_config

    gpu = torch.cuda.get_device_name(0)
    dados = np.fromfile(ROOT / args.pool, dtype=np.uint32)
    print(f"{gpu} · pool {args.pool}: {len(dados)/1e6:.1f}M tokens")

    doc = {"_gate": "sweep de LR do Bee-1G",
           "_regua": "loss media dos ultimos 50 passos, semente unica — compara LR, nao modelos",
           "_nao_mostra": [
               "o LR otimo por CAMADA: usa-se um LR unico, e o 2506.15025 mede que no regime "
               "de vocab grande a razao embedding/oculto escala Θ(√width). Isto responde 'qual "
               "LR unico e' menos ruim', nao 'qual e' o otimo'",
               "o comportamento em run LONGO: 1.000 passos veem instabilidade inicial, nao "
               "divergencia tardia",
               "🔴 o LR do RUN. Este sweep mede o otimo no SEU horizonte (32,8M tokens); a "
               "Step Law escala com D^0,307, entao levar o numero medido aqui direto para um "
               "run de 20B poria o LR ~7x abaixo do previsto. Use "
               "`step_law_no_run` ou escale o medido por (D_run/D_sweep)^0,307",
               "interacao com o schedule: aqui e' LR constante, e o run usara' WSD ou cosine",
           ],
           "gpu": gpu, "passos": args.passos, "semente": args.semente,
           "tokens_do_sweep": d_sweep,
           "step_law_no_horizonte_do_sweep": alvo,
           "step_law_no_run": {f"{d/1e9:.0f}B": step_law(N_PARAM, d)
                               for d in (2e10, 6.6e10, 1.5e11)},
           "bracos": {}}
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
