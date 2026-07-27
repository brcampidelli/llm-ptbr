"""Treina o baseline de ENCODER (XLM-R) — a objeção de 2026-07-25, medida.

A objeção era: "um encoder de 110–300M faz extração em CPU por ~1/40 do custo do
4B". XLM-RoBERTa base (278M) é a escolha certa para testá-la, porque a nossa tarefa
é multilíngue (pt/en/es/fr) — um encoder monolíngue perderia por motivo errado, e o
teste não valeria.

⚠️ Só campos EXTRATIVOS (ver data/14). Isto NÃO é um substituto da abelha: é o
concorrente na fatia onde a objeção se aplica.

Uso (na L4, ~5-8 min — é 15× menor que o nosso backbone):
    python train/encoder_ner.py
    python train/encoder_ner.py --model xlm-roberta-base --epochs 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRAIN = ROOT / "data" / "processed" / "encoder_ner.train.jsonl"
EVAL = ROOT / "data" / "processed" / "encoder_ner.eval.jsonl"
DEFAULT_OUT = "/content/bee-encoder-ner"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="xlm-roberta-base",
                    help="multilingue de proposito: a tarefa e pt/en/es/fr e um "
                         "encoder monolingue perderia por motivo errado")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--epochs", type=float, default=5.0)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=512)
    args = ap.parse_args()

    import numpy as np
    import torch
    from datasets import Dataset
    from transformers import (AutoModelForTokenClassification, AutoTokenizer,
                              DataCollatorForTokenClassification, Trainer,
                              TrainingArguments)

    tr = [json.loads(l) for l in TRAIN.open(encoding="utf-8")]
    ev = [json.loads(l) for l in EVAL.open(encoding="utf-8")]
    if not tr:
        print(f"ERRO: rode data/14_build_encoder_spans.py antes.", file=sys.stderr)
        return 1

    rotulos = sorted({l for r in tr + ev for l in r["labels"]})
    l2i = {l: i for i, l in enumerate(rotulos)}
    print(f"modelo : {args.model}")
    print(f"dados  : treino {len(tr)} · eval {len(ev)} | {len(rotulos)} rotulos")

    tok = AutoTokenizer.from_pretrained(args.model, add_prefix_space=True)

    def prep(lote):
        enc = tok(lote["tokens"], is_split_into_words=True, truncation=True,
                  max_length=args.max_len)
        todos = []
        for i, labs in enumerate(lote["labels"]):
            wids = enc.word_ids(i)
            ids, ant = [], None
            for w in wids:
                if w is None:
                    ids.append(-100)                 # especiais fora da loss
                elif w != ant:
                    ids.append(l2i[labs[w]])
                else:
                    # subtoken: mantem I- para nao ensinar B- repetido
                    L = labs[w]
                    ids.append(l2i["I-" + L[2:]] if L.startswith("B-") and
                               "I-" + L[2:] in l2i else l2i[L])
                ant = w
            todos.append(ids)
        enc["labels"] = todos
        return enc

    dtr = Dataset.from_list(tr).map(prep, batched=True, remove_columns=["tokens", "labels", "lang", "schema"])
    dev = Dataset.from_list(ev).map(prep, batched=True, remove_columns=["tokens", "labels", "lang", "schema"])

    model = AutoModelForTokenClassification.from_pretrained(
        args.model, num_labels=len(rotulos),
        id2label={i: l for l, i in l2i.items()}, label2id=l2i)
    n = sum(p.numel() for p in model.parameters())
    print(f"params : {n/1e6:.0f}M  (o backbone da comeia tem 4.227M — {4227/(n/1e6):.0f}× maior)")

    def metricas(p):
        pred = np.argmax(p.predictions, axis=2)
        ok = tot = 0
        for pr, la in zip(pred, p.label_ids):
            for a, b in zip(pr, la):
                if b != -100:
                    tot += 1
                    ok += int(a == b)
        return {"token_acc": ok / max(1, tot)}

    trainer = Trainer(
        model=model,
        args=TrainingArguments(
            output_dir=args.out, num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch_size,
            per_device_eval_batch_size=args.batch_size,
            learning_rate=args.lr, warmup_ratio=0.1, logging_steps=25,
            eval_strategy="epoch", save_strategy="no", report_to=[],
            bf16=torch.cuda.is_available()),
        train_dataset=dtr, eval_dataset=dev,
        data_collator=DataCollatorForTokenClassification(tok),
        compute_metrics=metricas)
    trainer.train()
    trainer.save_model(args.out)
    tok.save_pretrained(args.out)
    print(f"\n✅ encoder salvo em {args.out}")
    print("Proximo: eval/eval_encoder_vs_adapter.py — a comparacao que decide a objecao.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
