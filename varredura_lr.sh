#!/bin/bash
# Varredura de LR — 1 epoca (230 passos) por ponto. O cosine se ajusta ao
# horizonte de cada run, entao cada um recebe um schedule completo: comparavel.
cd "C:/Users/brcam/Desktop/Desenvolvendo Projetos/Desenvolvendo LLM"
for lr in 5e-5 1e-4 3e-4 6e-4; do
  echo "=== LR $lr ==="
  .venv/Scripts/python.exe bee/sft.py \
    --modelo models/bee-150m-v3-base \
    --dados comeia/data/processed/sft_combinado.jsonl \
    --epocas 1 --lr $lr --save-steps 999 \
    --out models/_lr_$lr > docs/lr-$lr.log 2>&1
  tail -c 400 docs/lr-$lr.log | tr '\r' '\n' | grep -E "eval_loss|train_runtime" | tail -2
done
echo "VARREDURA CONCLUIDA"
