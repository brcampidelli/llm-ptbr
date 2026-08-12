"""Fase SFT do Bee — full fine-tune (sem LoRA), local na RTX 5070 8 GB.

Por que FULL fine-tune e nao QLoRA (a receita do Qwen nao serve aqui):
  O Bee tem 151M params. Em bf16 com AdamW cabe folgado em 8 GB
  (~0,3 GB pesos + 0,3 grad + ~1,2 estados do otimizador + ativacoes ≈ 2,5 GB).
  LoRA r=16 num modelo deste tamanho treinaria ~1% dos pesos — amarra justamente
  a adaptacao que um modelo pequeno e subtreinado mais precisa. Full FT e melhor
  E cabe. QLoRA so faz sentido a partir de ~1-3B.

⚠️ MASCARAMENTO DA LOSS (licao paga em 2026-07-24, ver comeia/train/sft_qlora.py):
  com dataset {"messages"} o TRL calcula a loss em TODOS os tokens — o modelo
  gasta capacidade aprendendo a gerar a PERGUNTA do usuario. Este script converte
  messages -> {prompt, completion}, formato em que o TRL mascara o prompt sozinho.

Uso:
    python bee/sft.py --dry-run                      # valida config, nao treina
    python bee/sft.py                                # treina com os defaults
    python bee/sft.py --epochs 3 --lr 3e-5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DADOS = ROOT / "comeia" / "data" / "processed" / "sft_ptbr.jsonl"
EVAL = ROOT / "comeia" / "data" / "processed" / "sft_ptbr.eval.jsonl"
SAIDA = ROOT / "models" / "bee-150m-v3-sft"


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="BrCamp/bee-150m-v3",
                    help="repo HF ou caminho local do Bee base")
    ap.add_argument("--dados", type=Path, default=DADOS)
    ap.add_argument("--eval", type=Path, default=EVAL)
    ap.add_argument("--out", type=Path, default=SAIDA)
    # ⚠️ 2026-08-12: o default era 1024 e isso DESCARTAVA SILENCIOSAMENTE 100% dos
    # exemplos agenticos (prompt de 1096-1191 tok so no catalogo de ferramentas: o
    # prompt sozinho estoura o limite, a completion e truncada fora, o exemplo fica
    # todo mascarado e o TRL o joga fora sem erro). 2048 = seq_len do pre-treino.
    ap.add_argument("--max-seq-len", type=int, default=2048,
                    help="teto do pre-treino; abaixo disso exemplos longos somem sem aviso")
    # ⚠️ 2026-08-12: 3 epocas decorava (loss 1,850 contra 1,768 em 2) e 2e-5 era
    # ordens de grandeza abaixo do otimo. Medido em varredura de 6 pontos sobre a
    # base correta: ver docs/sft-resultado.md.
    ap.add_argument("--epocas", type=float, default=2.0,
                    help="medido: 1ep 1,800 · 2ep 1,768 · 3ep 1,850 (decora)")
    ap.add_argument("--lr", type=float, default=6e-4,
                    help="medido: minimo da curva em U (5e-5 a 2e-3), ruido de 0,001")
    # ⚠️ micro-batch 2 nao e timidez, e o teto fisico dos 8 GB. Medido na RTX 5070
    # (2026-08-04) com sequencia cheia de 1024: bs2 = 5,8 GB e 6,5 amostras/s;
    # bs4 = 10,7 GB — nao cabe, vaza pra RAM do host e despenca pra 1,0; bs8 leva
    # 510 s/passo. O vilao e o tensor de logits (bs x 1024 x 32000, + upcast fp32
    # da cross-entropy). O Liger resolveria fundindo linear+CE, mas nao instala
    # com transformers 5.x. Manter o batch EFETIVO em 32 via grad_accum.
    ap.add_argument("--batch", type=int, default=2, help="por dispositivo (teto de VRAM)")
    ap.add_argument("--grad-accum", type=int, default=16, help="batch efetivo = batch * grad_accum")
    ap.add_argument("--save-steps", type=int, default=200)
    ap.add_argument("--max-steps", type=int, default=-1, help="limita passos (smoke test)")
    ap.add_argument("--permitir-descarte", action="store_true",
                    help="segue mesmo com >1%% do dataset descartado por truncamento")
    # ⚠️ 2026-08-12: sem isto, seq 2048 + batch 8 estoura os 8 GB da RTX 5070 (rodava na
    # 5090 de 31 GB). Checkpointing recomputa ativacoes no backward: ~30% mais lento, mas
    # cabe. Preferivel a baixar seq_len, que descartaria exemplos e — pior — mudaria a
    # configuracao entre variantes, confundindo o efeito medido com o do comprimento.
    ap.add_argument("--grad-checkpoint", action="store_true",
                    help="recomputa ativacoes: cabe em GPU pequena, ~30%% mais lento")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def carregar_prompt_completion(caminho: Path) -> list[dict]:
    """messages [user, assistant] -> {prompt, completion} para a loss ser mascarada."""
    linhas = []
    ignorados = 0
    for linha in caminho.open(encoding="utf-8"):
        linha = linha.strip()
        if not linha:
            continue
        obj = json.loads(linha)
        msgs = obj.get("messages")
        if not msgs:  # ja pode vir no formato certo
            if {"prompt", "completion"} <= set(obj):
                linhas.append({"prompt": obj["prompt"], "completion": obj["completion"]})
            else:
                ignorados += 1
            continue
        # ultimo assistant = completion; tudo antes = prompt
        if msgs[-1].get("role") != "assistant":
            ignorados += 1
            continue
        linhas.append({"prompt": msgs[:-1], "completion": [msgs[-1]]})
    if ignorados:
        print(f"  aviso: {ignorados} exemplos ignorados (formato inesperado)")
    return linhas


def main() -> int:
    args = parse_args()

    if not args.dados.exists():
        print(f"ERRO: dataset nao encontrado: {args.dados}", file=sys.stderr)
        return 1

    treino = carregar_prompt_completion(args.dados)
    avaliacao = carregar_prompt_completion(args.eval) if args.eval.exists() else []

    passos_por_epoca = len(treino) / (args.batch * args.grad_accum)
    print("=" * 62)
    print("SFT Bee-150M — full fine-tune (sem LoRA)")
    print("=" * 62)
    print(f"  modelo base   : {args.modelo}")
    print(f"  treino        : {len(treino)} exemplos ({args.dados.name})")
    print(f"  holdout       : {len(avaliacao)} exemplos")
    print(f"  formato       : prompt/completion -> loss MASCARADA no prompt [OK]")
    print(f"  max_seq_len   : {args.max_seq_len}")
    print(f"  epocas        : {args.epocas}")
    print(f"  batch efetivo : {args.batch * args.grad_accum} ({args.batch} x {args.grad_accum})")
    print(f"  lr            : {args.lr} (cosine, warmup 3%)")
    print(f"  passos        : ~{passos_por_epoca * args.epocas:.0f}")
    print(f"  saida         : {args.out}")

    if args.dry_run:
        print("\n[dry-run] config validada, nada foi treinado.")
        if treino:
            ex = treino[0]
            print(f"\nexemplo — prompt: {str(ex['prompt'])[:150]}")
            print(f"exemplo — completion: {str(ex['completion'])[:150]}")
        return 0

    import torch

    if not torch.cuda.is_available():
        print("ERRO: CUDA indisponivel.", file=sys.stderr)
        return 1
    nome = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"\nGPU: {nome} | {vram:.1f} GB")

    from datasets import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    print("carregando tokenizer/modelo (bf16, sem quantizacao)...")
    tok = AutoTokenizer.from_pretrained(args.modelo)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    modelo = AutoModelForCausalLM.from_pretrained(args.modelo, dtype=torch.bfloat16)
    modelo.config.use_cache = False

    # O pre-treino deixou eos = <|endoftext|>, mas o chat_template fecha o turno com
    # <|im_end|>. Sem isto o modelo pos-SFT gera a resposta e NAO para — emenda um
    # turno de usuario atras do outro. Aceitar os dois como fim de geracao.
    fim_turno = tok.convert_tokens_to_ids("<|im_end|>")
    if fim_turno is not None and fim_turno >= 0:
        ids_eos = sorted({modelo.generation_config.eos_token_id, fim_turno}
                         if isinstance(modelo.generation_config.eos_token_id, int)
                         else {*modelo.generation_config.eos_token_id, fim_turno})
        modelo.generation_config.eos_token_id = ids_eos
        print(f"  eos de geracao: {ids_eos} (inclui <|im_end|>={fim_turno})")
    else:
        print("  AVISO: <|im_end|> nao existe no tokenizer — o modelo nao vai saber parar.")
    n_par = sum(p.numel() for p in modelo.parameters())
    print(f"  parametros treinaveis: {n_par/1e6:.1f}M (100% — full fine-tune)")

    ds_treino = Dataset.from_list(treino)
    ds_eval = Dataset.from_list(avaliacao) if avaliacao else None

    cfg = SFTConfig(
        output_dir=str(args.out),
        num_train_epochs=args.epocas,
        max_steps=args.max_steps,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        gradient_checkpointing=args.grad_checkpoint,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=10,
        save_steps=args.save_steps,
        save_total_limit=2,
        bf16=True,
        max_length=args.max_seq_len,
        eval_strategy="steps" if ds_eval else "no",
        eval_steps=args.save_steps if ds_eval else None,
        per_device_eval_batch_size=args.batch,
        optim="adamw_torch",
        report_to="none",
        seed=42,
    )

    trainer = SFTTrainer(model=modelo, args=cfg, train_dataset=ds_treino,
                         eval_dataset=ds_eval, processing_class=tok)

    # ⚠️ GUARDA — ABORTA (2026-08-12). O TRL descarta em silencio todo exemplo que
    # fica inteiramente mascarado (prompt >= max_length => completion truncada fora).
    # Foi assim que um treino "misto" de 7.152 exemplos rodou 354 passos em vez de
    # 447 e nao viu UM SO dos 1.495 exemplos agenticos — sem erro, sem aviso, com a
    # loss caindo bonito. Mesma familia do bug de rotulos: dado some, nada reclama.
    sobreviveram = len(trainer.train_dataset)
    if sobreviveram < len(treino):
        perdidos = len(treino) - sobreviveram
        print(f"\n  DESCARTADOS por truncamento: {perdidos}/{len(treino)} "
              f"({perdidos/len(treino):.1%}) com max_seq_len={args.max_seq_len}")
        if perdidos / len(treino) > 0.01:
            print("ERRO: mais de 1% do dataset sumiu antes do passo 1. Aumente "
                  "--max-seq-len (ou passe --permitir-descarte se for intencional).",
                  file=sys.stderr)
            if not args.permitir_descarte:
                return 1

    print("\ntreinando... (Ctrl+C interrompe; checkpoints a cada save_steps)")
    trainer.train()

    args.out.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.out))
    tok.save_pretrained(str(args.out))
    (args.out / "sft_args.json").write_text(
        json.dumps(vars(args), default=str, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Modelo SFT salvo em {args.out}")
    print("Proximo: python bee/chat.py --modelo " + str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
