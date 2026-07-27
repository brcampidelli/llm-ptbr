"""BEE — pré-treino do zero. Pesos aleatórios → modelo de linguagem.

⭐ ESTE É O ARQUIVO QUE FAZ O BEE SER NOSSO. Tudo antes dele (corpus, tokenizador,
arquitetura) é preparação; é aqui que os pesos deixam de ser ruído.

⚠️ O COLAB VAI CAIR. Nesta sessão o runtime foi reciclado 4 vezes. O plano não torce
contra isso: checkpoint a cada N passos direto na Drive, retomada automática que
restaura modelo + otimizador + scheduler + POSIÇÃO NO DADO. Retomar sem a posição
faria o modelo reler o mesmo começo do corpus a cada queda — e memorizar justamente
o que já viu mais.

⭐ O QUE MONITORAR, em ordem de honestidade:
  1. amostras de texto geradas — o sinal mais cru de que está aprendendo
  2. perplexidade em holdout PT e EN SEPARADOS (misturar esconde regressão num idioma)
  3. norma do gradiente — dispara antes de a loss explodir
  4. loss — o menos informativo, porque cai mesmo quando o modelo está decorando

Uso:
    python bee/pretrain.py --tamanho 150m --dados bee/dados --out <drive>/bee-150m
    python bee/pretrain.py --passos 50 --dry-run     # valida o pipeline em 2 min
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bee"))


def lote(dados, batch, seq_len, device, gerador):
    """Amostra `batch` janelas de `seq_len+1` do memmap. x = [:-1], y = [1:].

    ⚠️ Amostragem ALEATÓRIA e não sequencial: com dado ordenado por fonte (o nosso é —
    as fontes foram coletadas uma após a outra), ler em ordem faria o modelo ver 4 GB de
    web, depois 1,8 GB de livros, depois código. Isso é currículo acidental, não
    escolhido: o modelo esqueceria a primeira fonte ao chegar na última.
    """
    import numpy as np
    import torch
    ix = torch.randint(len(dados) - seq_len - 1, (batch,), generator=gerador)
    x = torch.stack([torch.from_numpy(dados[i:i + seq_len].astype(np.int64)) for i in ix])
    y = torch.stack([torch.from_numpy(dados[i + 1:i + 1 + seq_len].astype(np.int64)) for i in ix])
    if device.type == "cuda":
        return x.pin_memory().to(device, non_blocking=True), y.pin_memory().to(device, non_blocking=True)
    return x.to(device), y.to(device)


def init_pesos(modelo, n_camadas: int):
    """normal(0, 0.02), com as projeções residuais escaladas por 1/sqrt(2*n_camadas).

    ⭐ SEM ESSA ESCALA REDES PROFUNDAS DIVERGEM nos primeiros passos. A intuição: cada
    bloco SOMA sua saída ao residual, então a variância cresce com a profundidade; se
    todas as projeções de saída começam com a mesma escala, o sinal explode ao atravessar
    30 camadas. Escalar as projeções que ESCREVEM no residual (`o_proj` da atenção e
    `down_proj` do MLP) mantém a variância estável na entrada de cada bloco.
    É o que GPT-2 faz, e o motivo de ele treinar sem warmup heroico.
    """
    import torch.nn as nn
    std_res = 0.02 / math.sqrt(2 * n_camadas)
    n_esc = 0
    for nome, p in modelo.named_parameters():
        if p.dim() >= 2:
            if nome.endswith(("o_proj.weight", "down_proj.weight")):
                nn.init.normal_(p, mean=0.0, std=std_res)
                n_esc += 1
            else:
                nn.init.normal_(p, mean=0.0, std=0.02)
    return std_res, n_esc


def lr_do_passo(passo: int, total: int, lr_max: float, warmup: int, lr_min_frac: float = 0.1):
    """Warmup linear + cosine decay até `lr_min_frac * lr_max`.

    ⚠️ O warmup não é ritual: com LR alto (3e-3, que modelos pequenos toleram e
    aproveitam), os primeiros passos sobre pesos aleatórios produzem gradientes enormes.
    Sem warmup, o otimizador dá um passo gigante numa direção sem sentido e a loss trava
    num platô do qual não sai.
    """
    if passo < warmup:
        return lr_max * (passo + 1) / warmup
    prog = (passo - warmup) / max(1, total - warmup)
    return lr_max * (lr_min_frac + (1 - lr_min_frac) * 0.5 * (1 + math.cos(math.pi * prog)))


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--tamanho", default="150m")
    ap.add_argument("--dados", type=Path, default=ROOT / "bee" / "dados")
    ap.add_argument("--tokenizer", type=Path, default=ROOT / "bee" / "tokenizer")
    ap.add_argument("--out", type=Path, default=Path("/content/drive/MyDrive/BEE/bee-150m"))
    ap.add_argument("--tokens-alvo", type=float, default=3e9)
    ap.add_argument("--epocas", type=float, default=0.0,
                    help="se >0, IGNORA --tokens-alvo e deriva do tamanho REAL do train.bin. "
                         "1.0 = ve cada token exatamente uma vez. Mais robusto que estimar: "
                         "o numero sai do arquivo, nao de uma conta minha com bytes/palavra.")
    ap.add_argument("--micro-batch", type=int, default=8)
    ap.add_argument("--grad-accum", type=int, default=32,
                    help="batch efetivo = micro-batch * grad_accum * seq_len tokens")
    ap.add_argument("--lr", type=float, default=3e-3,
                    help="3e-3: modelos pequenos toleram LR alto; 2e-4 seria desperdicio")
    ap.add_argument("--warmup-frac", type=float, default=0.02)
    ap.add_argument("--ckpt-cada", type=int, default=250)
    ap.add_argument("--aval-cada", type=int, default=250)
    ap.add_argument("--amostra-cada", type=int, default=500)
    ap.add_argument("--passos", type=int, default=0, help="0 = derivado de --tokens-alvo")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="valida o pipeline e sai")
    args = ap.parse_args()

    import numpy as np
    import torch
    from transformers import AutoTokenizer, LlamaForCausalLM
    from config import ESCADA, para_llama_config

    cfg = ESCADA[args.tamanho]
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed)
    g = torch.Generator().manual_seed(args.seed)

    meta_p = args.dados / "meta.json"
    if not meta_p.exists():
        print(f"ERRO: {meta_p} não existe. Rode bee/prepare_data.py antes.", file=sys.stderr)
        return 1
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    treino = np.memmap(args.dados / "train.bin", dtype=np.uint16, mode="r")
    val = np.memmap(args.dados / "val.bin", dtype=np.uint16, mode="r")

    tokens_por_passo = args.micro_batch * args.grad_accum * cfg.seq_len
    # ⭐ `--epocas` deriva o alvo do arquivo REAL. Estimar tokens a partir de GB de texto
    # depende de "bytes por palavra" e da fertilidade — duas aproximações minhas que
    # erram fácil. O `len(treino)` não erra: é o número de tokens que existe no disco.
    alvo = args.epocas * len(treino) if args.epocas else args.tokens_alvo
    passos = args.passos or int(alvo / tokens_por_passo)
    warmup = max(10, int(passos * args.warmup_frac))

    print("=" * 76)
    print(f"⭐ PRÉ-TREINO {cfg.nome} — pesos aleatórios → modelo")
    print("=" * 76)
    print(f"  dispositivo   {dev}  {torch.cuda.get_device_name(0) if dev.type=='cuda' else ''}")
    print(f"  parâmetros    {cfg.params/1e6:.1f}M · vocab {cfg.vocab} · seq_len {cfg.seq_len}")
    print(f"  dados         treino {len(treino)/1e9:.3f}B tok · val {len(val)/1e6:.1f}M tok")
    print(f"  batch         {args.micro_batch} x {args.grad_accum} x {cfg.seq_len} = "
          f"{tokens_por_passo/1e3:.0f}k tokens/passo")
    print(f"  passos        {passos} (warmup {warmup}) → {passos*tokens_por_passo/1e9:.2f}B tokens")
    print(f"  épocas        {passos*tokens_por_passo/max(1,len(treino)):.2f}")
    print(f"  LR            {args.lr:.0e} cosine → {args.lr*0.1:.0e}")
    print(f"  horas est.    {cfg.horas_treino_l4(passos*tokens_por_passo):.1f} h de L4")
    print(f"  checkpoint    a cada {args.ckpt_cada} passos em {args.out}")

    if meta["vocab"] != cfg.vocab:
        print(f"\n🔴 INCOMPATÍVEL: dados tokenizados com vocab {meta['vocab']}, "
              f"modelo espera {cfg.vocab}. Os ids não significam a mesma coisa — "
              f"retokenize ou troque o config.", file=sys.stderr)
        return 1

    modelo = LlamaForCausalLM(para_llama_config(cfg))
    std_res, n_esc = init_pesos(modelo, cfg.n_camadas)
    print(f"\n  init          normal(0, 0.02); {n_esc} projeções residuais com std="
          f"{std_res:.5f} (=0.02/sqrt(2*{cfg.n_camadas}))")
    modelo.to(dev)
    real = sum(p.numel() for p in modelo.parameters())
    print(f"  conferido     {real/1e6:.1f}M params instanciados")

    # ⭐ weight decay SÓ nas matrizes. Aplicar em bias e RMSNorm encolhe parâmetros que
    # controlam escala, e isso atrapalha em vez de regularizar — erro comum e silencioso.
    decay = [p for n, p in modelo.named_parameters() if p.dim() >= 2]
    no_decay = [p for n, p in modelo.named_parameters() if p.dim() < 2]
    opt = torch.optim.AdamW(
        [{"params": decay, "weight_decay": 0.1},
         {"params": no_decay, "weight_decay": 0.0}],
        lr=args.lr, betas=(0.9, 0.95), eps=1e-8, fused=(dev.type == "cuda"))
    print(f"  otimizador    AdamW β(0.9,0.95) wd 0.1 em {len(decay)} matrizes, "
          f"0.0 em {len(no_decay)} bias/norm")

    inicio = 0
    args.out.mkdir(parents=True, exist_ok=True)
    ckpt_p = args.out / "checkpoint.pt"
    if ckpt_p.exists():
        # ⭐ RETOMADA COMPLETA: modelo + otimizador + passo. Sem o estado do Adam, os
        # momentos zeram e o treino leva centenas de passos para se recuperar — o que
        # numa sessão com 4 quedas significaria nunca convergir.
        ck = torch.load(ckpt_p, map_location=dev, weights_only=False)
        modelo.load_state_dict(ck["modelo"])
        opt.load_state_dict(ck["opt"])
        inicio = ck["passo"] + 1
        if "gerador" in ck:
            g.set_state(ck["gerador"])
        print(f"\n♻️  RETOMANDO do passo {inicio}/{passos} "
              f"(loss {ck.get('loss', float('nan')):.4f})")

    if args.dry_run:
        print("\n[dry-run] validando 3 passos…")
        passos, args.ckpt_cada, args.aval_cada, args.amostra_cada = 3, 999, 999, 999

    tok = AutoTokenizer.from_pretrained(str(args.tokenizer))

    @torch.no_grad()
    def perplexidade(dados_, n_lotes=20):
        modelo.eval()
        perdas = []
        gv = torch.Generator().manual_seed(1234)          # fixo: comparável entre passos
        for _ in range(n_lotes):
            x, y = lote(dados_, args.micro_batch, cfg.seq_len, dev, gv)
            with torch.autocast(device_type=dev.type, dtype=torch.bfloat16,
                                enabled=dev.type == "cuda"):
                perdas.append(modelo(input_ids=x, labels=y).loss.item())
        modelo.train()
        m = sum(perdas) / len(perdas)
        return m, math.exp(min(20, m))

    @torch.no_grad()
    def amostra(prompt="O Brasil é", n=60):
        modelo.eval()
        ids = torch.tensor([tok(prompt, add_special_tokens=False)["input_ids"]], device=dev)
        out = modelo.generate(ids, max_new_tokens=n, do_sample=True, temperature=0.8,
                              top_k=50, pad_token_id=meta["eos"])
        modelo.train()
        return tok.decode(out[0], skip_special_tokens=True)

    print("\n" + "-" * 76)
    modelo.train()
    t0, t_ult = time.time(), time.time()
    hist = []
    for passo in range(inicio, passos):
        lr = lr_do_passo(passo, passos, args.lr, warmup)
        for grupo in opt.param_groups:
            grupo["lr"] = lr

        opt.zero_grad(set_to_none=True)
        perda_acc = 0.0
        for _ in range(args.grad_accum):
            x, y = lote(treino, args.micro_batch, cfg.seq_len, dev, g)
            with torch.autocast(device_type=dev.type, dtype=torch.bfloat16,
                                enabled=dev.type == "cuda"):
                perda = modelo(input_ids=x, labels=y).loss / args.grad_accum
            perda.backward()
            perda_acc += perda.item()
        # clip global: o gradiente dispara ANTES de a loss explodir — é o alarme precoce
        gnorm = torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0).item()
        opt.step()

        if passo % 10 == 0 or passo == passos - 1:
            dt = time.time() - t_ult
            t_ult = time.time()
            tks = 10 * tokens_por_passo / max(1e-9, dt) if passo else 0
            resta = (passos - passo) * dt / 10 / 3600
            print(f"passo {passo:>5}/{passos} · loss {perda_acc:.4f} · gnorm {gnorm:>6.2f} · "
                  f"lr {lr:.2e} · {tks/1e3:>5.1f}k tok/s · faltam {resta:>4.1f}h", flush=True)
            hist.append({"passo": passo, "loss": perda_acc, "gnorm": gnorm, "lr": lr})
            if gnorm > 50:
                print(f"  ⚠️ gnorm {gnorm:.1f} muito alto — se persistir, baixe o LR",
                      file=sys.stderr)

        if passo and passo % args.aval_cada == 0:
            lv, ppl = perplexidade(val)
            print(f"  ⭐ VALIDAÇÃO passo {passo}: loss {lv:.4f} · perplexidade {ppl:.1f}",
                  flush=True)
            hist.append({"passo": passo, "val_loss": lv, "ppl": ppl})

        if passo and passo % args.amostra_cada == 0:
            print(f"  💬 amostra: {amostra()!r}", flush=True)

        if passo and passo % args.ckpt_cada == 0:
            torch.save({"modelo": modelo.state_dict(), "opt": opt.state_dict(),
                        "passo": passo, "loss": perda_acc, "gerador": g.get_state(),
                        "cfg": args.tamanho}, ckpt_p)
            (args.out / "historico.json").write_text(json.dumps(hist, indent=1),
                                                     encoding="utf-8")
            print(f"  💾 checkpoint no passo {passo} → {ckpt_p}", flush=True)

    # ---------------------------------------------------------------- fim ---
    lv, ppl = perplexidade(val, n_lotes=50)
    print("\n" + "=" * 76)
    print(f"✅ TREINO CONCLUÍDO em {(time.time()-t0)/3600:.2f} h")
    print(f"   validação final: loss {lv:.4f} · perplexidade {ppl:.1f}")
    print(f"   amostra: {amostra()!r}")
    modelo.save_pretrained(str(args.out / "modelo"))
    tok.save_pretrained(str(args.out / "modelo"))
    (args.out / "historico.json").write_text(json.dumps(hist, indent=1), encoding="utf-8")
    print(f"   modelo salvo em {args.out / 'modelo'}")
    print("\n   Próximo: eval/eval_bee_vs_smollm.py — ⭐ o GATE 2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
